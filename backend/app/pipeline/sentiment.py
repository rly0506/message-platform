"""民间情绪层: Reddit/OpenCLI posts and critical synthesis."""
from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app import config, llm
from app.collectors import reddit_sentiment
from app.db import SentimentPost, Topic
from app.pipeline import academic


SENTIMENT_LAYER_WARNING = "多平台民间情绪是最该被批判怀疑的一角；高赞不等于事实。"


def run_sentiment_analysis(
    session: Session,
    topic: Topic,
    *,
    limit: int = 25,
    on_step: Any | None = None,
) -> dict[str, Any]:
    if on_step:
        on_step("fetch", "running")
    reddit_query = academic.academic_search_query(topic.name)
    chinese_query = topic.name
    collection = reddit_sentiment.search_all_platforms(
        reddit_query=reddit_query,
        chinese_query=chinese_query,
        limit=limit,
    )
    posts = collection["posts"]
    posts = rank_posts(posts)
    if on_step:
        on_step(
            "fetch",
            "done",
            {
                "post_count": len(posts),
                "queries": collection.get("queries", {}),
                "errors": collection.get("errors", []),
            },
        )

    if on_step:
        on_step("summarize", "running")
    summary_md = summarize_sentiment(topic, posts) if posts else ""
    if on_step:
        on_step("summarize", "done")

    if on_step:
        on_step("persist", "running")
    persist_sentiment_layer(session, topic.id, posts)
    if on_step:
        on_step("persist", "done")

    return sentiment_payload(
        topic,
        posts,
        summary_md=summary_md,
        query=reddit_query,
        queries=collection.get("queries", {"reddit": reddit_query, "chinese": chinese_query}),
        errors=collection.get("errors", []),
    )


def rank_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        posts,
        key=lambda post: (int(post.get("score") or 0), int(post.get("num_comments") or 0)),
        reverse=True,
    )


def summarize_sentiment(topic: Topic, posts: list[dict[str, Any]]) -> str:
    grouped_posts = compact_posts_by_platform(posts)
    prompt = f"""请为专题「{topic.name}」总结多平台民间情绪层。

定位必须钉死:
- 这是 Reddit / B站 / 小红书 / 雪球等平台的民间情绪，是最该被批判怀疑的一角。
- 它以情绪、站队、看热闹和平台偏见为主，绝非事实源。
- 不要把高赞当事实，也不要把评论区共识当现实共识。
- 请区分 (a) 情绪/站队/看热闹/阴谋论/梗图式噪声，和 (b) 偶尔的、聪明的、上游的民间观察或早期信号。
- 对任何民间信号都要标注“待核实/仅作线索”。
- 按平台分组比较，但不同平台有不同立场滤镜: Reddit 偏英语社区，B站偏年轻科技，小红书偏消费/生活经验，雪球偏金融/市场交易，不能跨平台直接当共识。
- 帖子样本下可能带有高赞评论；评论只是更细的情绪/线索，不代表事实。

输出要求:
1. 用中文 markdown。
2. 先给一句总评，明确可信度边界。
3. 分成“平台分布”“主要情绪”“站队与叙事”“可能有价值的信号”“明显噪声/偏见”“需要回到媒体/学界/一手资料核验的问题”。

按平台分组的帖子样本（帖子下挂“高赞评论”，含 parent_post_id）:
{grouped_posts}
"""
    return llm.chat(
        config.SYNTH_MODEL,
        prompt,
        max_tokens=1400,
        system="你是谨慎的舆情分析助手。民间平台只代表样本情绪，不能当事实源。",
    )


def compact_post_for_prompt(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": post.get("platform", "reddit"),
        "kind": post.get("kind", "post"),
        "id": post.get("id", ""),
        "parent_post_id": post.get("parent_post_id", ""),
        "subreddit": post.get("subreddit", ""),
        "title": post.get("title", ""),
        "score": post.get("score", 0),
        "num_comments": post.get("num_comments", 0),
        "author": post.get("author", ""),
        "created_utc": post.get("created_utc", ""),
        "selftext_excerpt": (post.get("selftext_snippet") or "")[:300],
        "url": post.get("url", ""),
    }


def compact_posts_by_platform(posts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    comments_by_parent: dict[str, list[dict[str, Any]]] = {}
    top_posts: list[dict[str, Any]] = []
    for post in rank_posts(posts):
        platform = str(post.get("platform") or "unknown")
        if post.get("kind") == "comment":
            parent_id = str(post.get("parent_post_id") or "")
            comments_by_parent.setdefault(parent_id, []).append(post)
        else:
            top_posts.append(post)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for post in top_posts[:25]:
        platform = str(post.get("platform") or "unknown")
        compact = compact_post_for_prompt(post)
        parent_id = str(post.get("id") or "")
        compact["高赞评论"] = [
            compact_post_for_prompt(comment)
            for comment in rank_posts(comments_by_parent.get(parent_id, []))[:10]
        ]
        grouped.setdefault(platform, []).append(compact)
    return grouped


def persist_sentiment_layer(session: Session, topic_id: int, posts: list[dict[str, Any]]) -> None:
    existing_urls = {
        row.url
        for row in session.exec(select(SentimentPost).where(SentimentPost.topic_id == topic_id)).all()
        if row.url
    }
    for post in posts:
        url = str(post.get("url") or "")
        if url and url in existing_urls:
            continue
        session.add(sentiment_post_from_dict(topic_id, post))
        if url:
            existing_urls.add(url)
    session.commit()


def sentiment_post_from_dict(topic_id: int, post: dict[str, Any]) -> SentimentPost:
    return SentimentPost(
        topic_id=topic_id,
        platform=str(post.get("platform") or "reddit"),
        kind=str(post.get("kind") or "post"),
        parent_post_id=str(post.get("parent_post_id") or ""),
        subreddit=str(post.get("subreddit") or ""),
        title=str(post.get("title") or ""),
        author=str(post.get("author") or ""),
        score=int(post.get("score") or 0),
        num_comments=int(post.get("num_comments") or 0),
        url=str(post.get("url") or ""),
        created_utc=str(post.get("created_utc") or ""),
        selftext_snippet=str(post.get("selftext_snippet") or ""),
    )


def sentiment_payload_from_db(session: Session, topic: Topic, summary_md: str = "") -> dict[str, Any]:
    rows = session.exec(
        select(SentimentPost)
        .where(SentimentPost.topic_id == topic.id)
        .order_by(SentimentPost.score.desc(), SentimentPost.num_comments.desc())
    ).all()
    return sentiment_payload(
        topic,
        [sentiment_post_to_dict(row) for row in rows],
        summary_md=summary_md,
        query="",
        queries={},
    )


def sentiment_payload(
    topic: Topic,
    posts: list[dict[str, Any]],
    *,
    summary_md: str = "",
    query: str = "",
    queries: dict[str, str] | None = None,
    errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    ranked_posts = rank_posts(posts)
    platforms = sorted({str(post.get("platform") or "unknown") for post in ranked_posts})
    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "query": query,
        "queries": queries or {},
        "platform": "multi",
        "platforms": platforms,
        "warning": SENTIMENT_LAYER_WARNING,
        "posts": ranked_posts,
        "errors": errors or [],
        "summary_md": summary_md,
    }


def sentiment_post_to_dict(post: SentimentPost) -> dict[str, Any]:
    return {
        "id": post.id,
        "platform": post.platform,
        "kind": post.kind,
        "parent_post_id": post.parent_post_id,
        "subreddit": post.subreddit,
        "title": post.title,
        "author": post.author,
        "score": post.score,
        "num_comments": post.num_comments,
        "url": post.url,
        "created_utc": post.created_utc,
        "selftext_snippet": post.selftext_snippet,
    }
