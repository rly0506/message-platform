from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlsplit

from sqlmodel import Session, select

from app.db import Article, CognitionProfile, Event, Topic, TopicArticle
from app.services import coverage_snapshot, payloads


BRIEFING_NOTE = (
    'Facts use persisted article titles and source snippets; '
    'article bodies are not stored.'
)
APP_BASE_URL_ENV = 'DAILY_DIGEST_APP_URL'
FRESH_DAYS = 14
ITEM_LIMIT = 5

_STYLE_QUESTIONS = {
    'mechanism': '关键机制是什么，哪些物理、技术或制度约束会改变结果？',
    'financial_model': '收入、成本、现金流和激励分别由哪些可核查数据支持？',
    'macro_model': '利率、流动性、汇率和政策传导分别通过什么数据口径观察？',
    'evaluation': '维护者、许可证、活跃度、安全记录和商业边界分别怎样核查？',
    'comparison': '比较对象共享哪些条件，哪些关键差异会使类比失效？',
    'paper_check': '论文、实验阶段、样本规模、复现和监管进度分别到了哪一步？',
    'risk_check': '责任主体、资产或数据边界、流动性与极端情景怎样核查？',
    'multi_angle': '不同参与方的激励、能力约束和证据口径分别是什么？',
}


def build_daily_briefing(
    session: Session,
    *,
    app_base_url: str = '',
    now: datetime | None = None,
    item_limit: int = ITEM_LIMIT,
) -> dict[str, Any]:
    reference_time = _naive_utc(now or datetime.now(timezone.utc))
    return {
        'generated_at': _utc_iso(reference_time),
        'basis': 'persisted_article_metadata',
        'note': BRIEFING_NOTE,
        'items': _briefing_items(
            session,
            app_base_url=app_base_url,
            now=reference_time,
            limit=max(0, int(item_limit)),
        ),
        'domain_today': _domain_today(session, reference_time),
    }


def _briefing_items(
    session: Session,
    *,
    app_base_url: str,
    now: datetime,
    limit: int,
) -> list[dict[str, Any]]:
    cutoff = now - timedelta(days=FRESH_DAYS)
    candidates: list[tuple[datetime, Topic, Article]] = []
    topics = session.exec(select(Topic).where(Topic.status == 'active')).all()
    for topic in topics:
        rows = session.exec(
            select(TopicArticle, Article)
            .where(TopicArticle.article_id == Article.id)
            .where(TopicArticle.topic_id == topic.id)
            .where(TopicArticle.relevant == True)  # noqa: E712
        ).all()
        recent = [
            article
            for _, article in rows
            if article.published_at
            and cutoff <= _naive_utc(article.published_at) <= now
        ]
        if not recent:
            continue
        article = max(
            recent,
            key=lambda row: (_naive_utc(row.published_at), row.id or 0),
        )
        candidates.append((_naive_utc(article.published_at), topic, article))

    candidates.sort(key=lambda item: (item[0], item[1].id or 0), reverse=True)
    return [
        _briefing_item(session, topic, article, app_base_url=app_base_url)
        for _, topic, article in candidates[:limit]
    ]


def _briefing_item(
    session: Session,
    topic: Topic,
    article: Article,
    *,
    app_base_url: str,
) -> dict[str, Any]:
    event = _event_for_article(session, topic.id, article.id)
    event_id = event.id if event else None
    snapshot = coverage_snapshot.build_coverage_snapshot(session, topic.id, event_id)
    deep_link_path = _deep_link_path(topic.id, event_id)
    snippet = payloads.clean_snippet(article.snippet)
    return {
        'topic_id': topic.id,
        'topic_name': topic.name,
        'event_id': event_id,
        'article_id': article.id,
        'title': (article.title or '未命名报道').strip(),
        'fact_summary': snippet or '该条持久化记录目前只有标题；正文未落库。',
        'summary_basis': 'persisted_title_and_snippet' if snippet else 'persisted_title_only',
        'source': article.source.strip() or '来源未知',
        'published_at': payloads.iso(article.published_at),
        'evidence_url': article.url,
        'deep_link_path': deep_link_path,
        'deep_link_url': _absolute_deep_link(app_base_url, deep_link_path),
        'fulltext': snapshot['fulltext'],
        'coverage': _coverage_micro_label(snapshot, event_id is not None),
    }


def _event_for_article(
    session: Session,
    topic_id: int | None,
    article_id: int | None,
) -> Event | None:
    if topic_id is None or article_id is None:
        return None
    events = session.exec(select(Event).where(Event.topic_id == topic_id)).all()
    matches = [event for event in events if article_id in _integer_ids(event.article_ids)]
    if not matches:
        return None
    return max(
        matches,
        key=lambda event: (
            _naive_utc(event.date) if event.date else datetime.min,
            _naive_utc(event.updated_at),
            event.id or 0,
        ),
    )


def _coverage_micro_label(snapshot: dict[str, Any], event_scope: bool) -> dict[str, Any]:
    source_buckets = snapshot.get('source_distribution') or []
    language_buckets = snapshot.get('language_distribution') or []
    known_languages = [
        bucket
        for bucket in language_buckets
        if str(bucket.get('key') or '').strip().casefold() != 'unknown'
    ]
    unknown_language_count = sum(
        int(bucket.get('count') or 0)
        for bucket in language_buckets
        if str(bucket.get('key') or '').strip().casefold() == 'unknown'
    )
    unknown_source_count = sum(
        int(bucket.get('count') or 0)
        for bucket in source_buckets
        if str(bucket.get('key') or '').strip().casefold() == 'unknown'
    )
    sample = snapshot['sample']
    source_count = int(snapshot.get('independent_source_count') or 0)
    known_language_count = len(known_languages)
    scope_label = '事件样本' if event_scope else '专题样本'
    source_label = f'{source_count} 源' if source_count else '来源未知'
    if unknown_source_count and source_count:
        source_label += f'（{unknown_source_count} 篇来源未知）'
    language_label = f'{known_language_count} 语种' if known_language_count else '语种未知'
    label = f"{scope_label} {sample['article_count']} 篇 · {source_label} · {language_label}"
    if unknown_language_count and known_language_count:
        label += f'（{unknown_language_count} 篇语种未知）'
    return {
        'scope': 'event' if event_scope else 'topic',
        'article_count': sample['article_count'],
        'independent_source_count': source_count,
        'unknown_source_article_count': unknown_source_count,
        'known_language_count': known_language_count,
        'unknown_language_article_count': unknown_language_count,
        'article_ids': sample['article_ids'],
        'label': label,
        'note': sample['note'],
    }


def _domain_today(session: Session, now: datetime) -> dict[str, Any] | None:
    profiles = session.exec(select(CognitionProfile)).all()
    if not profiles:
        return None
    level_rank = {'unfamiliar': 0, 'partial': 1, 'strong_partial': 2}
    profiles.sort(
        key=lambda row: (
            level_rank.get(row.level, 3),
            row.domain_key,
        )
    )
    profile = profiles[now.date().toordinal() % len(profiles)]
    label = profile.domain_label or profile.domain_key
    style_question = _STYLE_QUESTIONS.get(
        profile.recommended_seed_style,
        f'{label} 中最值得核查的机制、约束和反例分别是什么？',
    )
    return {
        'date': now.date().isoformat(),
        'domain_key': profile.domain_key,
        'domain_label': label,
        'profile_level': profile.level,
        'profile_confidence': profile.confidence,
        'selection_basis': 'deterministic_local_profile_rotation',
        'questions': [
            f'对照{label}的官方文件、行业媒体、研究资料与社区样本：各自突出什么、遗漏什么？',
            f'找一个{label}的历史先例：机制相似在哪里，技术、制度或市场条件差在哪里？',
            style_question,
        ],
        'note': '这是问题脚手架，不是结论；阅读本卡不会写入或修改认知画像。',
    }


def _deep_link_path(topic_id: int | None, event_id: int | None) -> str:
    params: list[tuple[str, Any]] = [('topic', topic_id)]
    if event_id is not None:
        params.append(('event', event_id))
    params.append(('view', 'contrast'))
    return f'/?{urlencode(params)}'


def _absolute_deep_link(base_url: str, path: str) -> str | None:
    base = str(base_url or '').strip()
    if not base:
        return None
    parsed = urlsplit(base)
    if (
        parsed.scheme.casefold() not in {'http', 'https'}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        return None
    query = path.partition('?')[2]
    return f"{base.rstrip('/')}/?{query}"


def _integer_ids(values: list[Any]) -> set[int]:
    ids: set[int] = set()
    for value in values or []:
        try:
            ids.add(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_iso(value: datetime) -> str:
    return f'{_naive_utc(value).isoformat()}Z'
