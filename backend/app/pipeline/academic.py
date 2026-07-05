"""Academic-layer analysis: OpenAlex papers, converged citations, schools."""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any

from sqlmodel import Session, select

from app import config, llm
from app.collectors import crossref, openalex
from app.db import Paper, PaperCitation, Topic, TopicPaper


def run_academic_analysis(
    session: Session,
    topic: Topic,
    *,
    top_n: int = 30,
    on_step: Any | None = None,
) -> dict[str, Any]:
    if on_step:
        on_step("fetch", "running")
    search_query = academic_search_query(topic.name)
    papers = fetch_academic_papers(search_query, top_n=top_n)
    if on_step:
        on_step("fetch", "done", {"paper_count": len(papers)})

    if on_step:
        on_step("graph", "running")
    edges = build_citation_graph(papers)
    schools_data = analyze_schools(papers, edges)
    if on_step:
        on_step("graph", "done", {"edge_count": len(edges), "school_count": len(schools_data["schools"])})

    if on_step:
        on_step("synthesize", "running")
    # LLM 综合可能超时/失败(实测 ReadTimeout)。降级而非中断: 已抓到的论文+引用图
    # 不能因综述失败就丢, 后续 persist 必须照常跑。守"无 LLM 也能跑"红线。
    try:
        summary_md = synthesize_academic(topic, papers, edges, schools_data)
        synth_status = "done"
    except Exception as exc:
        summary_md = ""
        synth_status = "warning"
        if on_step:
            on_step("synthesize", "warning", {"error": f"{type(exc).__name__}: {str(exc)[:80]}"})
    if on_step and synth_status == "done":
        on_step("synthesize", "done")

    if on_step:
        on_step("persist", "running")
    persist_academic_layer(session, topic.id, papers, edges)
    if on_step:
        on_step("persist", "done")

    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "paper_count": len(papers),
        "edge_count": len(edges),
        "papers": papers,
        "graph": {"nodes": graph_nodes(papers), "edges": edges},
        "literature_network": literature_network(papers, edges),
        "schools": schools_data["schools"],
        "foundational_papers": schools_data["foundational_papers"],
        "summary_md": summary_md,
        "sort_strategy": "OpenAlex + Crossref search results are merged by DOI; OpenAlex relevance is preserved where available, and cited_by_count is used only for local foundation ranking.",
    }


CJK_RE = re.compile(r"[\u3400-\u9fff]")


def fetch_academic_papers(search_query: str, top_n: int = 30) -> list[dict[str, Any]]:
    openalex_papers = safe_search(openalex.search_works, search_query, top_n)
    crossref_papers = safe_search(crossref.search_works, search_query, top_n)
    return merge_paper_sources(openalex_papers, crossref_papers)[:top_n]


def safe_search(search_fn: Any, search_query: str, top_n: int) -> list[dict[str, Any]]:
    try:
        return list(search_fn(search_query, top_n=top_n))
    except Exception:
        return []


def merge_paper_sources(*paper_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for group in paper_groups:
        for paper in group:
            key = paper_merge_key(paper)
            if not key:
                merged.append(with_source_defaults(paper))
                continue
            existing = by_key.get(key)
            if existing:
                merge_paper(existing, paper)
            else:
                normalized = with_source_defaults(paper)
                by_key[key] = normalized
                merged.append(normalized)
    return merged


def paper_merge_key(paper: dict[str, Any]) -> str:
    doi = normalize_doi(paper.get("doi", "")).lower()
    if doi:
        return f"doi:{doi}"
    title = normalize_text(paper.get("title", ""))
    year = str(paper.get("year") or "")
    first_author = normalize_text((paper.get("authors") or [""])[0])
    if title:
        return f"title:{title}|{first_author}|{year}"
    return ""


def with_source_defaults(paper: dict[str, Any]) -> dict[str, Any]:
    result = dict(paper)
    sources = [str(source).lower() for source in result.get("sources") or [] if source]
    if not sources and result.get("openalex_id", "").startswith("crossref:"):
        sources = ["crossref"]
    if not sources:
        sources = ["openalex"]
    result["sources"] = sorted(dict.fromkeys(sources))
    links = list(result.get("source_links") or [])
    if "openalex" in result["sources"] and (result.get("openalex_url") or result.get("openalex_id")):
        url = result.get("openalex_url") or result.get("openalex_id")
        if url and not any(str(link.get("source", "")).lower() == "openalex" for link in links):
            links.append({"source": "openalex", "url": url})
    if "crossref" in result["sources"] and result.get("doi"):
        doi = normalize_doi(result.get("doi", "")).removeprefix("https://doi.org/")
        crossref_url = f"https://api.crossref.org/works/{doi}" if doi else ""
        if crossref_url and not any(str(link.get("source", "")).lower() == "crossref" for link in links):
            links.append({"source": "crossref", "url": crossref_url})
    result["source_links"] = links
    result["source_count"] = len(result["sources"])
    return result


def merge_paper(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    incoming = with_source_defaults(incoming)
    for field in ("title", "abstract", "venue", "doi", "url", "openalex_url"):
        if not target.get(field) and incoming.get(field):
            target[field] = incoming[field]
    for field in ("year",):
        if not target.get(field) and incoming.get(field):
            target[field] = incoming[field]
    target["cited_by_count"] = max(int(target.get("cited_by_count") or 0), int(incoming.get("cited_by_count") or 0))
    if not target.get("authors") and incoming.get("authors"):
        target["authors"] = incoming["authors"]
    if not target.get("concepts") and incoming.get("concepts"):
        target["concepts"] = incoming["concepts"]
    if not target.get("referenced_works") and incoming.get("referenced_works"):
        target["referenced_works"] = incoming["referenced_works"]
    sources = list(target.get("sources") or []) + list(incoming.get("sources") or [])
    target["sources"] = sorted(dict.fromkeys(str(source).lower() for source in sources if source))
    links = list(target.get("source_links") or []) + list(incoming.get("source_links") or [])
    deduped_links = []
    seen_links = set()
    for link in links:
        key = (str(link.get("source", "")).lower(), str(link.get("url", "")))
        if key in seen_links:
            continue
        seen_links.add(key)
        deduped_links.append(link)
    target["source_links"] = deduped_links
    target["source_count"] = len(target["sources"])


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def academic_search_query(topic_name: str) -> str:
    if not contains_cjk(topic_name):
        return topic_name
    try:
        translated = llm.chat(
            config.SYNTH_MODEL,
            f"把以下事件主题转成一个适合学术论文检索的英文查询词，只返回查询词本身：{topic_name}",
            max_tokens=80,
            system="You convert event topics into concise English academic search queries.",
        )
    except Exception:
        return topic_name
    translated = str(translated).strip().strip("\"'")
    return translated or topic_name


def contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    return openalex.reconstruct_abstract(inverted_index)


def build_citation_graph(papers: list[dict[str, Any]]) -> list[dict[str, str]]:
    return openalex.converged_citation_edges(papers)


def analyze_schools(
    papers: list[dict[str, Any]],
    edges: list[dict[str, str]],
) -> dict[str, Any]:
    indegree = Counter(edge["cited_openalex_id"] for edge in edges)
    papers_by_id = {paper["openalex_id"]: paper for paper in papers if paper.get("openalex_id")}
    ranked = sorted(
        papers,
        key=lambda paper: (
            indegree.get(paper.get("openalex_id"), 0),
            int(paper.get("cited_by_count") or 0),
            -(paper.get("year") or 9999),
        ),
        reverse=True,
    )
    foundational = [
        {
            "openalex_id": paper.get("openalex_id", ""),
            "title": paper.get("title", ""),
            "year": paper.get("year"),
            "cited_by_count": paper.get("cited_by_count", 0),
            "internal_citations": indegree.get(paper.get("openalex_id"), 0),
        }
        for paper in ranked[:8]
    ]

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        concept = primary_concept(paper)
        groups[concept].append(paper)

    schools = []
    for name, group in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        schools.append({
            "name": name,
            "paper_count": len(group),
            "years": sorted({paper.get("year") for paper in group if paper.get("year")}),
            "top_papers": [
                {
                    "openalex_id": paper.get("openalex_id", ""),
                    "title": paper.get("title", ""),
                    "year": paper.get("year"),
                    "cited_by_count": paper.get("cited_by_count", 0),
                }
                for paper in sorted(group, key=lambda paper: int(paper.get("cited_by_count") or 0), reverse=True)[:5]
            ],
            "concepts": common_concepts(group),
        })

    return {
        "foundational_papers": foundational,
        "schools": schools,
        "indegree": dict(indegree),
        "papers_by_id": papers_by_id,
    }


def synthesize_academic(
    topic: Topic,
    papers: list[dict[str, Any]],
    edges: list[dict[str, str]],
    schools_data: dict[str, Any],
) -> str:
    return synthesize_academic_consensus(topic, papers, edges, schools_data)


def synthesize_academic_consensus(
    topic: Topic,
    papers: list[dict[str, Any]],
    edges: list[dict[str, str]],
    schools_data: dict[str, Any],
) -> str:
    compact_papers = [compact_paper_for_prompt(paper) for paper in papers[:25]]
    compact_schools = {
        "foundational_papers": schools_data.get("foundational_papers", [])[:8],
        "schools": schools_data.get("schools", [])[:8],
    }
    source_label = academic_source_label(papers)
    prompt = f"""请基于以下 {source_label} 学术论文样本，为专题「{topic.name}」生成中文学界视角综述。

要求:
1. 标题使用“学界综述”。
2. 引用每一条判断；每一条实质判断都要引用给定论文，使用 [W123] 这类 citation_key，不允许无出处断言。
3. 总结主要学派/研究路径、学术共识、分歧、证据缺口与方法争议。
4. 按时间说明共识如何演变。
5. 末尾必须有“参考文献”小节，列出被引用论文的作者、年份、题名、期刊/会议、DOI 或 OpenAlex 链接。
6. 明确说明样本来源为 {source_label}，引用图只使用样本内部互引。
7. 如果给定样本不足以支持结论，直接写“不足以判断”，不要补写外部文献。

论文样本:
{compact_papers}

内部引用边:
{edges[:80]}

学派和奠基文献:
{compact_schools}
"""
    return llm.chat(
        config.SYNTH_MODEL,
        prompt,
        max_tokens=1800,
        system="你是严谨的学术综述助手，只根据给定论文样本归纳，不编造文献。引用每一条判断。",
    )


def academic_source_label(papers: list[dict[str, Any]]) -> str:
    sources: list[str] = []
    for paper in papers:
        for source in paper.get("sources") or []:
            normalized = str(source).strip().lower()
            if normalized:
                sources.append(normalized)
    if not sources:
        sources = ["crossref" if str(paper.get("openalex_id", "")).startswith("crossref:") else "openalex" for paper in papers]
    labels = {
        "openalex": "OpenAlex",
        "crossref": "Crossref",
    }
    unique_sources = list(dict.fromkeys(sources))
    order = {"openalex": 0, "crossref": 1}
    ordered = [
        labels.get(source, source.title())
        for source in sorted(unique_sources, key=lambda source: (order.get(source, 99), source))
    ]
    return " + ".join(ordered) if ordered else "OpenAlex + Crossref"


def compact_paper_for_prompt(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": paper.get("openalex_id", ""),
        "citation_key": citation_key(paper.get("openalex_id", "")),
        "citation_ref": f"[{citation_key(paper.get('openalex_id', ''))}]",
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "cited_by_count": paper.get("cited_by_count", 0),
        "venue": paper.get("venue", ""),
        "authors": (paper.get("authors") or [])[:3],
        "doi": paper.get("doi", ""),
        "openalex_url": paper.get("openalex_url") or paper.get("openalex_id", ""),
        "sources": paper.get("sources") or ["crossref" if str(paper.get("openalex_id", "")).startswith("crossref:") else "openalex"],
        "source_links": paper.get("source_links") or default_source_links(paper),
        "citation": citation_string(paper),
        "concepts": common_concepts([paper], limit=5),
        "abstract_excerpt": (paper.get("abstract") or "")[:280],
    }


def persist_academic_layer(
    session: Session,
    topic_id: int,
    papers: list[dict[str, Any]],
    edges: list[dict[str, str]],
) -> None:
    paper_by_openalex_id: dict[str, Paper] = {}
    for paper_data in papers:
        openalex_id = paper_data.get("openalex_id", "")
        if not openalex_id:
            continue
        paper = session.exec(select(Paper).where(Paper.openalex_id == openalex_id)).first()
        if not paper:
            paper = Paper(openalex_id=openalex_id)
        paper.title = paper_data.get("title", "")
        paper.abstract = paper_data.get("abstract", "")
        paper.year = paper_data.get("year")
        paper.cited_by_count = int(paper_data.get("cited_by_count") or 0)
        paper.authors = paper_data.get("authors", [])
        paper.venue = paper_data.get("venue", "")
        paper.concepts = paper_data.get("concepts", [])
        paper.doi = normalize_doi(paper_data.get("doi", ""))
        paper.openalex_url = paper_data.get("openalex_url") or openalex_id
        paper.url = paper_data.get("url", "")
        paper.sources = paper_data.get("sources") or ["crossref" if str(openalex_id).startswith("crossref:") else "openalex"]
        paper.source_links = paper_data.get("source_links") or default_source_links(paper_data)
        session.add(paper)
        session.commit()
        session.refresh(paper)
        paper_by_openalex_id[openalex_id] = paper

        link = session.get(TopicPaper, (topic_id, paper.id))
        if not link:
            session.add(TopicPaper(topic_id=topic_id, paper_id=paper.id, relevance=1.0))

    session.commit()

    existing_edges = {
        (citation.citing_paper_id, citation.cited_paper_id)
        for citation in session.exec(select(PaperCitation)).all()
    }
    for edge in edges:
        citing = paper_by_openalex_id.get(edge["citing_openalex_id"])
        cited = paper_by_openalex_id.get(edge["cited_openalex_id"])
        if not citing or not cited or citing.id is None or cited.id is None:
            continue
        pair = (citing.id, cited.id)
        if pair in existing_edges:
            continue
        session.add(PaperCitation(citing_paper_id=citing.id, cited_paper_id=cited.id))
        existing_edges.add(pair)
    session.commit()


def academic_payload(session: Session, topic: Topic, summary_md: str = "") -> dict[str, Any]:
    rows = session.exec(
        select(TopicPaper, Paper)
        .where(TopicPaper.paper_id == Paper.id)
        .where(TopicPaper.topic_id == topic.id)
    ).all()
    papers = [paper_to_dict(paper) for _, paper in rows]
    paper_db_by_id = {paper.id: paper for _, paper in rows}
    openalex_by_db_id = {paper.id: paper.openalex_id for _, paper in rows}
    citations = session.exec(select(PaperCitation)).all()
    edges = [
        {
            "citing_openalex_id": openalex_by_db_id[citation.citing_paper_id],
            "cited_openalex_id": openalex_by_db_id[citation.cited_paper_id],
        }
        for citation in citations
        if citation.citing_paper_id in paper_db_by_id and citation.cited_paper_id in paper_db_by_id
    ]
    schools_data = analyze_schools(papers, edges)
    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "papers": papers,
        "graph": {"nodes": graph_nodes(papers), "edges": edges},
        "literature_network": literature_network(papers, edges),
        "schools": schools_data["schools"],
        "foundational_papers": schools_data["foundational_papers"],
        "summary_md": summary_md,
    }


def paper_to_dict(paper: Paper) -> dict[str, Any]:
    source_labels = paper.sources or ["crossref" if str(paper.openalex_id).startswith("crossref:") else "openalex"]
    source_links = paper.source_links or default_source_links({
        "openalex_id": paper.openalex_id,
        "openalex_url": paper.openalex_url,
        "doi": paper.doi,
        "sources": source_labels,
    })
    return {
        "id": paper.id,
        "openalex_id": paper.openalex_id,
        "title": paper.title,
        "abstract": paper.abstract,
        "year": paper.year,
        "cited_by_count": paper.cited_by_count,
        "authors": paper.authors,
        "venue": paper.venue,
        "concepts": paper.concepts,
        "doi": normalize_doi(paper.doi),
        "openalex_url": paper.openalex_url or paper.openalex_id,
        "citation_key": citation_key(paper.openalex_id),
        "citation": citation_string({
            "authors": paper.authors,
            "year": paper.year,
            "title": paper.title,
            "venue": paper.venue,
            "doi": paper.doi,
            "openalex_url": paper.openalex_url or paper.openalex_id,
        }),
        "url": paper.url,
        "sources": source_labels,
        "source_count": len(source_labels),
        "source_links": source_links,
    }


def graph_nodes(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": paper.get("openalex_id", ""),
            "citation_key": citation_key(paper.get("openalex_id", "")),
            "title": paper.get("title", ""),
            "year": paper.get("year"),
            "cited_by_count": paper.get("cited_by_count", 0),
        }
        for paper in papers
    ]


def literature_network(papers: list[dict[str, Any]], edges: list[dict[str, str]]) -> dict[str, Any]:
    by_id = {paper.get("openalex_id", ""): paper for paper in papers}
    return {
        "nodes": [
            {
                "id": paper.get("openalex_id", ""),
                "citation_key": citation_key(paper.get("openalex_id", "")),
                "title": paper.get("title", ""),
                "year": paper.get("year"),
                "venue": paper.get("venue", ""),
                "cited_by_count": paper.get("cited_by_count", 0),
            }
            for paper in papers
        ],
        "edges": [
            {
                "citing_openalex_id": edge["citing_openalex_id"],
                "cited_openalex_id": edge["cited_openalex_id"],
                "citing_title": by_id.get(edge["citing_openalex_id"], {}).get("title", ""),
                "cited_title": by_id.get(edge["cited_openalex_id"], {}).get("title", ""),
                "relation": "cites",
            }
            for edge in edges
        ],
    }


def citation_key(openalex_id: str) -> str:
    raw = str(openalex_id or "").rstrip("/").split("/")[-1]
    return raw or "unknown"


def normalize_doi(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("https://doi.org/"):
        return raw
    if raw.startswith("http://doi.org/"):
        return "https://doi.org/" + raw.removeprefix("http://doi.org/")
    if raw.lower().startswith("doi:"):
        return "https://doi.org/" + raw[4:].strip()
    if raw.startswith("10."):
        return f"https://doi.org/{raw}"
    return raw


def default_source_links(paper: dict[str, Any]) -> list[dict[str, str]]:
    links = []
    sources = [str(source).lower() for source in paper.get("sources") or []]
    if "openalex" in sources:
        url = paper.get("openalex_url") or paper.get("openalex_id") or ""
        if url and not str(url).startswith("crossref:"):
            links.append({"source": "openalex", "url": str(url)})
    if "crossref" in sources:
        doi = normalize_doi(paper.get("doi", "")).removeprefix("https://doi.org/")
        if doi:
            links.append({"source": "crossref", "url": f"https://api.crossref.org/works/{doi}"})
    return links


def citation_string(paper: dict[str, Any]) -> str:
    authors = paper.get("authors") or []
    author_text = ", ".join(str(author) for author in authors[:3]) or "Unknown authors"
    year = paper.get("year") or "n.d."
    title = paper.get("title") or "Untitled"
    venue = paper.get("venue") or "Unknown venue"
    locator = normalize_doi(paper.get("doi")) or paper.get("openalex_url") or paper.get("openalex_id") or ""
    suffix = f" {locator}" if locator else ""
    return f"{author_text} ({year}). {title}. {venue}.{suffix}"


def primary_concept(paper: dict[str, Any]) -> str:
    concepts = paper.get("concepts") or []
    if not concepts:
        return "Unclassified"
    return str(concepts[0].get("name") or concepts[0].get("display_name") or "Unclassified")


def common_concepts(papers: list[dict[str, Any]], limit: int = 6) -> list[str]:
    counts: Counter[str] = Counter()
    for paper in papers:
        for concept in paper.get("concepts") or []:
            name = concept.get("name") or concept.get("display_name")
            if name:
                counts[str(name)] += 1
    return [name for name, _count in counts.most_common(limit)]
