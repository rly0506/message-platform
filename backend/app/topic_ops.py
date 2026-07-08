"""Reusable topic collection and local analysis operations."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app import config, feed_registry
from app.collectors import gdelt, rss, searxng
from app.db import Analysis, Article, SourceFraming, SourceRegistry, TimelineEvent, Topic, TopicArticle
from app.pipeline import enrich as enrichp
from app.pipeline import fulltext
from app.pipeline import local_analyze, prefilter
from app.pipeline import synthesize as synthp
from app.services import evidence_package as evidence_service


LLM_ANALYSIS_MARKER = "<!-- analysis-source: llm -->"


def query_variants(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    variants = [text]
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        variants.append(f"{text} 最新 影响")
    else:
        variants.append(f"{text} latest impact")
    return list(dict.fromkeys(variants))


def get_or_create_topic(session: Session, name: str, queries: list[str] | None = None) -> Topic:
    existing = session.exec(select(Topic).where(Topic.name == name)).first()
    if existing:
        if queries:
            merged = list(dict.fromkeys([*(existing.queries or []), *queries]))
            existing.queries = merged
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing

    topic = Topic(
        name=name,
        description=f"由搜索词「{name}」临时创建的事件追踪专题。",
        queries=queries or query_variants(name),
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)
    return topic


def collect_topic(
    session: Session,
    topic: Topic,
    gnews: bool = True,
    gdelt_on: bool = False,
    years: int = 1,
    feeds: list[str] | None = None,
    min_rel: float = 0.0,
    use_curated_feeds: bool = False,
    extra_queries: list[str] | None = None,
) -> dict[str, Any]:
    raw: list[dict] = []
    errors: list[str] = []
    requests: list[dict[str, Any]] = []
    feeds = feeds or []
    # 本次采集用的检索词 = topic 持久化的 queries + 本次临时 extra_queries (如 LLM 拆解的子角度)。
    # extra_queries 不写回 topic, 故只影响这一次采集, 不污染后续 (decompose=False 时干净)。
    search_queries = list(dict.fromkeys([*topic.queries, *(extra_queries or [])]))

    for q in search_queries:
        if gnews:
            request_id = _request_id("gnews", len(requests))
            try:
                items = rss.collect_gnews(q)
                raw += _tag_items(items, request_id)
                requests.append(_request_stats(request_id, "gnews", q, len(items)))
            except Exception as exc:
                error = f"gnews {q!r}: {type(exc).__name__}: {exc}{_gnews_hint(exc)}"
                errors.append(error)
                requests.append(_request_stats(request_id, "gnews", q, 0, error=error))
        if gdelt_on:
            request_id = _request_id("gdelt", len(requests))
            try:
                end = datetime.utcnow()
                start = end - timedelta(days=365 * years)
                items = gdelt.collect(q, start, end)
                raw += _tag_items(items, request_id)
                requests.append(_request_stats(request_id, "gdelt", q, len(items)))
            except Exception as exc:
                error = f"gdelt {q!r}: {type(exc).__name__}: {exc}"
                errors.append(error)
                requests.append(_request_stats(request_id, "gdelt", q, 0, error=error))
        if config.USE_SEARXNG:
            request_id = _request_id("searxng", len(requests))
            try:
                items = searxng.collect(q)
                raw += _tag_items(items, request_id)
                requests.append(_request_stats(request_id, "searxng", q, len(items)))
            except Exception as exc:
                error = f"searxng {q!r}: {type(exc).__name__}: {exc}"
                errors.append(error)
                requests.append(_request_stats(request_id, "searxng", q, 0, error=error))

    feed_requests = [{"url": url, "metadata": None, "source_id": None} for url in feeds]
    if use_curated_feeds:
        registry_feeds = feed_registry.enabled_registry_feeds(session)
        feed_requests.extend(
            {"url": feed["url"], "metadata": feed, "source_id": feed.get("source_id")}
            for feed in registry_feeds
        )
        if not registry_feeds and not feed_registry.has_registry_sources(session):
            feed_requests.extend(
                {"url": feed["url"], "metadata": feed, "source_id": None}
                for feed in feed_registry.curated_feeds()
            )

    for feed_request in feed_requests:
        url = feed_request["url"]
        metadata = feed_request["metadata"]
        source_id = feed_request.get("source_id")
        request_id = _request_id("rss", len(requests))
        try:
            items = rss.collect_feed(url, metadata=metadata)
            raw += _tag_items(items, request_id)
            requests.append(_request_stats(
                request_id,
                "rss",
                url,
                len(items),
                metadata=metadata,
            ))
        except Exception as exc:
            error = f"rss {url!r}: {type(exc).__name__}: {exc}"
            errors.append(error)
            requests.append(_request_stats(
                request_id,
                "rss",
                url,
                0,
                error=error,
                metadata=metadata,
            ))

    known_urls = {prefilter.normalize_url(a.url) for a in session.exec(select(Article)).all()}
    linked_ids = [
        ta.article_id
        for ta in session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic.id)).all()
    ]
    known_titles = (
        [a.title for a in session.exec(select(Article).where(Article.id.in_(linked_ids))).all()]
        if linked_ids
        else []
    )
    kept = prefilter.dedup_and_score(raw, topic.queries, known_urls, known_titles, min_rel)
    decode_stats = _decode_stats(kept)
    kept_by_request = Counter(item.get("_request_id", "") for item in kept)
    for request in requests:
        request["kept_count"] = kept_by_request.get(request["id"], 0)
        if request.get("source_id"):
            _update_source_status(session, int(request["source_id"]), request)

    new_articles = 0
    new_links = 0
    for item in kept:
        art = session.exec(select(Article).where(Article.url == item["norm_url"])).first()
        if not art:
            art = Article(
                url=item["norm_url"],
                original_url=item.get("original_url", ""),
                url_decoded=bool(item.get("url_decoded", False)),
                title=item.get("title", ""),
                source=item.get("source", ""),
                source_lang=item.get("source_lang", ""),
                source_country=item.get("source_country", ""),
                published_at=item.get("published_at"),
                snippet=item.get("snippet", ""),
                collector=item.get("collector", ""),
            )
            session.add(art)
            session.commit()
            session.refresh(art)
            new_articles += 1
        else:
            if item.get("original_url") and not art.original_url:
                art.original_url = item.get("original_url", "")
            if item.get("url_decoded"):
                art.url_decoded = True
            session.add(art)
        link = session.get(TopicArticle, (topic.id, art.id))
        if not link:
            session.add(TopicArticle(topic_id=topic.id, article_id=art.id, relevance=item["relevance"]))
            new_links += 1
    session.commit()

    return {
        "raw": len(raw),
        "kept": len(kept),
        "new_articles": new_articles,
        "new_links": new_links,
        "source_count": len({item.get("source", "") for item in kept if item.get("source")}),
        "collector_counts": dict(Counter(item.get("collector", "unknown") for item in kept)),
        "decode_stats": decode_stats,
        "time_span": _time_span(kept),
        "requests": requests,
        "errors": errors,
    }


def analyze_topic(session: Session, topic: Topic, persist: bool = True) -> dict[str, Any]:
    rows_db = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic.id)
        .where(TopicArticle.relevant == True)  # noqa: E712
    ).all()
    rows = []
    for ta, art in rows_db:
        stance = ta.stance or local_analyze.infer_stance(
            art.title_zh or art.title,
            art.snippet_zh or art.snippet,
        )
        if not ta.stance:
            ta.stance = stance
            ta.stance_summary = f"本地规则根据标题/摘要判定为：{stance}"
        rows.append(local_analyze.ArticleRow(
            id=art.id,
            title=art.title_zh or art.title,
            source=art.source,
            published_at=art.published_at,
            snippet=art.snippet_zh or art.snippet,
            relevance=ta.relevance,
            stance=stance,
        ))

    data = local_analyze.analyze_topic(topic.name, rows)
    if persist:
        _persist_analysis(session, topic.id, data)
    data["article_count"] = len(rows)
    return data


def run_deep_analysis(
    session: Session,
    topic: Topic,
    *,
    enrich_limit: int = 30,
    on_step: Any | None = None,
) -> dict[str, Any]:
    enrich_stats = enrich_topic_articles(
        session,
        topic,
        limit=enrich_limit,
        on_step=on_step,
    )
    if on_step:
        on_step("synthesize", "running")
    data = synthesize_topic(session, topic)
    if on_step:
        on_step("synthesize", "done")
    if on_step:
        on_step("persist", "running")
    persist_synthesis(session, topic.id, data)
    if on_step:
        on_step("persist", "done")
    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "enrich": enrich_stats,
        "synthesize": {
            "input_articles": data.get("input_articles", 0),
            "timeline": len(data.get("timeline", [])),
            "framing": len(data.get("framing", [])),
            "analysis_chars": len(data.get("analysis_md", "")),
            "calls": 3,
        },
        "timeline": data.get("timeline", []),
        "framing": data.get("framing", []),
        "analysis_md": data.get("analysis_md", ""),
    }


def _fetch_bodies(urls: list[str]) -> dict[str, str]:
    """并发抓取一批 URL 的正文, 返回 {url: 正文}。

    软依赖: 任何抓取失败 (墙/超时/无 trafilatura) 都静默跳过, 该 url 不进结果,
    调用方据此回退到标题+摘要。并发 + 短超时 (config.FULLTEXT_FETCH_TIMEOUT),
    避免逐篇串行把深度分析拖垮。ENRICH_FETCH_FULLTEXT=0 时直接返回空 (省钱/省时)。
    """
    if not config.ENRICH_FETCH_FULLTEXT:
        return {}
    urls = [u for u in dict.fromkeys(urls) if u]  # 去重去空
    if not urls:
        return {}
    out: dict[str, str] = {}

    def _one(url: str) -> tuple[str, str]:
        extractor = fulltext.extract_url_scrapling if config.FULLTEXT_USE_SCRAPLING else fulltext.extract_url_proxied
        res = extractor(url)
        return url, (res.full_text if res.ok else "")

    # 并发度收敛: 不超过批大小, 也别开太多连接。
    workers = min(len(urls), max(1, enrichp.BATCH))
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for url, body in pool.map(_one, urls):
                if body:
                    out[url] = body
    except Exception:  # pragma: no cover - 线程池本身异常也不该阻断 enrich
        return out
    return out


def enrich_topic_articles(
    session: Session,
    topic: Topic,
    *,
    limit: int = 30,
    on_step: Any | None = None,
) -> dict[str, Any]:
    # 未富化 / 缺干货分 总是要跑。情绪分仅在"全文抓取开启"时才补 ——
    # 关掉全文时没有 body, emotion 必然返回 -1 永不收敛, 若也纳入 pending 会
    # 每次深度分析白打 LLM, 与"关全文=省钱"自相矛盾。故按开关分流。
    pending_filter = (Article.enriched == False) | (TopicArticle.substance_score < 0)  # noqa: E712
    if config.ENRICH_FETCH_FULLTEXT:
        pending_filter = pending_filter | (TopicArticle.emotion_score < 0)
    pending = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic.id)
        .where(pending_filter)
    ).all()
    pending = pending[: max(0, limit)]
    stats = {
        "limit": limit,
        "pending": len(pending),
        "processed": 0,
        "relevant": 0,
        "batches": 0,
        "calls": 0,
        "errors": [],
    }
    if not pending:
        if on_step:
            on_step("enrich", "done", stats)
        return stats

    for i in range(0, len(pending), enrichp.BATCH):
        if on_step:
            on_step("enrich", "running", stats)
        chunk = pending[i:i + enrichp.BATCH]
        stats["batches"] += 1
        stats["calls"] += 1
        bodies = _fetch_bodies([article.url for _, article in chunk])
        stats["fulltext_hits"] = stats.get("fulltext_hits", 0) + len(bodies)
        items = [
            {
                "id": article.id,
                "lang": article.source_lang,
                "title": article.title,
                "snippet": article.snippet,
                "body": bodies.get(article.url, ""),
            }
            for _, article in chunk
        ]
        try:
            results = enrichp.enrich_batch(topic.name, topic.description, items)
        except Exception as exc:  # pragma: no cover - defensive LLM boundary
            stats["errors"].append(f"batch {stats['batches']}: {type(exc).__name__}: {exc}")
            continue
        for topic_article, article in chunk:
            row = results.get(article.id)
            if not row:
                continue
            if row.get("title_zh") and not article.title_zh:
                article.title_zh = row["title_zh"]
            if row.get("snippet_zh") and not article.snippet_zh:
                article.snippet_zh = row["snippet_zh"]
            article.enriched = True
            topic_article.relevant = bool(row.get("relevant", True))
            topic_article.relevance = float(row.get("relevance", topic_article.relevance) or 0)
            topic_article.stance = row.get("stance") or "中立"
            topic_article.stance_summary = row.get("stance_summary", "")
            topic_article.substance_score = _clamp_score(row.get("substance_score"))
            topic_article.substance_note = str(row.get("substance_note", ""))[:60]
            # 红线兜底: 没抓到正文就强制情绪未评分, 不信任 LLM 自觉返回 -1。
            # 实测 LLM 会无视 prompt 拿标题+摘要硬打情绪分(伪判断), 故在代码层焊死:
            # 无 body -> emotion 一律 -1, 前端不显示徽标。干货分不收紧(标题/摘要可保守估)。
            if bodies.get(article.url):
                topic_article.emotion_score = _clamp_score(row.get("emotion_score"))
                topic_article.emotion_note = str(row.get("emotion_note", ""))[:60]
            else:
                topic_article.emotion_score = -1
                topic_article.emotion_note = ""
            stats["processed"] += 1
            stats["relevant"] += int(topic_article.relevant)
        session.commit()

    if on_step:
        on_step("enrich", "done" if not stats["errors"] else "warning", stats)
    return stats


def synthesize_topic(session: Session, topic: Topic) -> dict[str, Any]:
    package = evidence_service.build_evidence_package(session, topic)
    rows = [
        _synthesis_row_from_evidence_article(article)
        for article in package.get("articles", [])
        if article.get("stance")
    ]
    if not rows:
        raise RuntimeError("没有已富化且相关的文章，请先运行富化。")

    rows.sort(key=lambda row: row["date"])
    data = synthp.synthesize(topic.name, topic.description, rows, evidence_package=package)
    data["input_articles"] = len(rows)
    return data


def _synthesis_row_from_evidence_article(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": article.get("id"),
        "date": (article.get("published_at") or "????-??-??")[:10],
        "source": article.get("source", ""),
        "lang": article.get("source_lang", ""),
        "stance": article.get("stance", ""),
        "title_zh": article.get("title", ""),
        "snippet": article.get("snippet", ""),
        "source_type": article.get("source_type", "unknown"),
        "quality_tier": article.get("quality_tier", "other"),
        "source_country": article.get("source_country", ""),
        "category": article.get("category", ""),
    }


def persist_synthesis(session: Session, topic_id: int, data: dict[str, Any]) -> None:
    analysis_md = data.get("analysis_md", "")
    if analysis_md and LLM_ANALYSIS_MARKER not in analysis_md:
        analysis_md = f"{LLM_ANALYSIS_MARKER}\n{analysis_md}"
    _persist_analysis(
        session,
        topic_id,
        {
            "events": data.get("timeline", []),
            "framing": data.get("framing", []),
            "analysis_md": analysis_md,
        },
    )


def remove_topic(session: Session, topic_id: int, *, dry_run: bool = True) -> dict[str, Any]:
    topic = session.get(Topic, topic_id)
    if not topic:
        return {
            "found": False,
            "topic_id": topic_id,
            "topic_name": "",
            "links": 0,
            "exclusive_articles": 0,
            "timeline": 0,
            "framing": 0,
            "analysis": 0,
            "deleted": False,
        }

    links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic_id)).all()
    article_ids = [link.article_id for link in links]
    exclusive_article_ids = []
    for article_id in article_ids:
        shared_link = session.exec(
            select(TopicArticle)
            .where(TopicArticle.article_id == article_id)
            .where(TopicArticle.topic_id != topic_id)
        ).first()
        if not shared_link:
            exclusive_article_ids.append(article_id)

    timeline = session.exec(select(TimelineEvent).where(TimelineEvent.topic_id == topic_id)).all()
    framing = session.exec(select(SourceFraming).where(SourceFraming.topic_id == topic_id)).all()
    analyses = session.exec(select(Analysis).where(Analysis.topic_id == topic_id)).all()
    result = {
        "found": True,
        "topic_id": topic_id,
        "topic_name": topic.name,
        "links": len(links),
        "exclusive_articles": len(exclusive_article_ids),
        "timeline": len(timeline),
        "framing": len(framing),
        "analysis": len(analyses),
        "deleted": False,
    }
    if dry_run:
        return result

    for row in [*timeline, *framing, *analyses]:
        session.delete(row)
    for link in links:
        session.delete(link)
    for article_id in exclusive_article_ids:
        article = session.get(Article, article_id)
        if article:
            session.delete(article)
    session.delete(topic)
    session.commit()
    result["deleted"] = True
    return result


def _persist_analysis(session: Session, topic_id: int, data: dict[str, Any]) -> None:
    analysis_md = data.get("analysis_md", "")
    incoming_is_llm = LLM_ANALYSIS_MARKER in analysis_md
    existing_analyses = session.exec(select(Analysis).where(Analysis.topic_id == topic_id)).all()
    if not incoming_is_llm and any(LLM_ANALYSIS_MARKER in (row.content_md or "") for row in existing_analyses):
        return

    for model in (TimelineEvent, SourceFraming, Analysis):
        rows = existing_analyses if model is Analysis else session.exec(select(model).where(model.topic_id == topic_id)).all()
        for old in rows:
            session.delete(old)
    session.commit()

    for ev in data.get("events", []):
        session.add(TimelineEvent(
            topic_id=topic_id,
            date=_parse_date(ev.get("date")),
            title_zh=ev.get("title_zh", ""),
            summary_zh=ev.get("summary_zh", ""),
            article_ids=ev.get("article_ids", []),
        ))
    for fr in data.get("framing", []):
        session.add(SourceFraming(
            topic_id=topic_id,
            party=fr.get("party", ""),
            stance=fr.get("stance", ""),
            summary_zh=fr.get("summary_zh", ""),
            article_ids=fr.get("article_ids", []),
        ))
    session.add(Analysis(topic_id=topic_id, content_md=analysis_md))
    session.commit()


def _parse_date(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _request_id(kind: str, index: int) -> str:
    return f"{kind}-{index + 1}"


def _clamp_score(value: object) -> int:
    """把 LLM 返回的分数钳到 0~100; 缺失/非法/负数 -> -1 (未评分, 前端不显示徽标)。

    审核共识: junk 落 -1 而非中性 50, 避免显示一个"没有真依据"的悬空徽标
    (守住"每个判断可追溯")。排序侧把 -1 当中性 50, 故不影响排序。

    负数也映射到 -1: 情绪分约定"正文不足时 LLM 返回 -1"表示未评分, 不能被钳成 0
    (否则会显示一个伪造的"情绪 0"徽标)。
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return -1
    if n < 0:
        return -1
    return min(100, n)


def _gnews_hint(exc: Exception) -> str:
    """gnews 失败时, 若像网络/代理问题, 追加一句可操作的提示。

    Google News 国内直连不通, 必须经代理。连接类错误 (超时/连不上) 多半是
    VPN 没开或 RSS_PROXY 没配, 提示用户怎么办, 而非只抛裸的 traceback。
    """
    text = f"{type(exc).__name__}: {exc}".lower()
    network_signals = ("timeout", "timed out", "connect", "proxy", "10060",
                       "feedfetcherror", "ssl", "网络", "连接")
    if any(sig in text for sig in network_signals):
        return ("　← Google News 国内需经代理。请确认 VPN 已开, 并在 backend/.env 设 "
                "RSS_PROXY (如 socks5://127.0.0.1:10808)。")
    return ""


def _request_stats(
    request_id: str,
    collector: str,
    query: str,
    raw_count: int,
    error: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    return {
        "id": request_id,
        "collector": collector,
        "query": query,
        "raw_count": raw_count,
        "kept_count": 0,
        "status": "failed" if error else "ok",
        "error": error,
        "source_id": metadata.get("source_id"),
        "source_name": metadata.get("name", ""),
        "source_type": metadata.get("source_type", collector),
        "quality_tier": metadata.get("tier", ""),
    }


def _decode_stats(items: list[dict]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for item in items:
        collector = item.get("collector", "unknown")
        if collector != "gnews":
            continue
        bucket = stats.setdefault(
            "gnews",
            {"decoded": 0, "failed": 0, "disabled": 0, "not_gnews": 0},
        )
        method = item.get("url_decode_method", "")
        if item.get("url_decoded"):
            bucket["decoded"] += 1
        elif method == "disabled":
            bucket["disabled"] += 1
        elif method == "not_gnews":
            bucket["not_gnews"] += 1
        else:
            bucket["failed"] += 1
    return stats


def _update_source_status(session: Session, source_id: int, request: dict[str, Any]) -> None:
    source = session.get(SourceRegistry, source_id)
    if not source:
        return
    source.last_status = request["status"]
    source.last_error = request.get("error", "")
    source.last_fetched_at = datetime.utcnow()
    source.article_count += int(request.get("kept_count") or 0)
    source.updated_at = datetime.utcnow()
    session.add(source)
    session.commit()


def _tag_items(items: list[dict], request_id: str) -> list[dict]:
    out = []
    for item in items:
        tagged = dict(item)
        tagged["_request_id"] = request_id
        out.append(tagged)
    return out


def _time_span(items: list[dict]) -> dict[str, str | None]:
    dates = sorted(item.get("published_at") for item in items if item.get("published_at"))
    return {
        "start": dates[0].isoformat() if dates else None,
        "end": dates[-1].isoformat() if dates else None,
    }
