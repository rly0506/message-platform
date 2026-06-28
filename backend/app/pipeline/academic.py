"""Academic-layer analysis: OpenAlex papers, converged citations, schools."""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any

from sqlmodel import Session, select

from app import config, llm
from app.collectors import openalex
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
    papers = openalex.search_works(search_query, top_n=top_n)
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
    summary_md = synthesize_academic(topic, papers, edges, schools_data)
    if on_step:
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
        "schools": schools_data["schools"],
        "foundational_papers": schools_data["foundational_papers"],
        "summary_md": summary_md,
        "sort_strategy": "OpenAlex relevance_score default; cited_by_count is used only for local foundation ranking.",
    }


CJK_RE = re.compile(r"[\u3400-\u9fff]")


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
    prompt = f"""请基于以下 OpenAlex 学术论文样本，为专题「{topic.name}」生成中文学界视角综述。

要求:
1. 总结主要学派/研究路径。
2. 提炼学术共识。
3. 指出分歧、证据缺口与方法争议。
4. 按时间说明共识如何演变。
5. 明确说明样本来自 OpenAlex top-N 相关性搜索，引用图只使用样本内部互引。

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
        system="你是严谨的学术综述助手，只根据给定论文样本归纳，不编造文献。",
    )


def compact_paper_for_prompt(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": paper.get("openalex_id", ""),
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "cited_by_count": paper.get("cited_by_count", 0),
        "venue": paper.get("venue", ""),
        "authors": (paper.get("authors") or [])[:3],
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
        paper.url = paper_data.get("url", "")
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
        "schools": schools_data["schools"],
        "foundational_papers": schools_data["foundational_papers"],
        "summary_md": summary_md,
    }


def paper_to_dict(paper: Paper) -> dict[str, Any]:
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
        "url": paper.url,
    }


def graph_nodes(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": paper.get("openalex_id", ""),
            "title": paper.get("title", ""),
            "year": paper.get("year"),
            "cited_by_count": paper.get("cited_by_count", 0),
        }
        for paper in papers
    ]


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
