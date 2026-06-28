from datetime import datetime

from app import topic_ops
from app.db import (
    Analysis,
    Article,
    SourceFraming,
    TimelineEvent,
    Topic,
    TopicArticle,
    engine,
    init_db,
)
from sqlmodel import Session, select


def test_remove_topic_dry_run_keeps_data_and_reports_counts():
    topic_id, _shared_id, exclusive_id = _seed_remove_topic_case()

    with Session(engine) as session:
        result = topic_ops.remove_topic(session, topic_id, dry_run=True)

        assert result == {
            "found": True,
            "topic_id": topic_id,
            "topic_name": "删除测试主主题",
            "links": 2,
            "exclusive_articles": 1,
            "timeline": 1,
            "framing": 1,
            "analysis": 1,
            "deleted": False,
        }
        assert session.get(Topic, topic_id) is not None
        assert session.get(Article, exclusive_id) is not None
        assert len(session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic_id)).all()) == 2


def test_remove_topic_deletes_topic_outputs_and_links():
    topic_id, _shared_id, _exclusive_id = _seed_remove_topic_case()

    with Session(engine) as session:
        result = topic_ops.remove_topic(session, topic_id, dry_run=False)

        assert result["deleted"] is True
        assert session.get(Topic, topic_id) is None
        assert session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic_id)).all() == []
        assert session.exec(select(TimelineEvent).where(TimelineEvent.topic_id == topic_id)).all() == []
        assert session.exec(select(SourceFraming).where(SourceFraming.topic_id == topic_id)).all() == []
        assert session.exec(select(Analysis).where(Analysis.topic_id == topic_id)).all() == []


def test_remove_topic_keeps_shared_articles():
    topic_id, shared_id, _exclusive_id = _seed_remove_topic_case()

    with Session(engine) as session:
        topic_ops.remove_topic(session, topic_id, dry_run=False)

        assert session.get(Article, shared_id) is not None
        links = session.exec(select(TopicArticle).where(TopicArticle.article_id == shared_id)).all()
        assert len(links) == 1
        assert links[0].topic_id != topic_id


def test_remove_topic_deletes_exclusive_articles():
    topic_id, _shared_id, exclusive_id = _seed_remove_topic_case()

    with Session(engine) as session:
        topic_ops.remove_topic(session, topic_id, dry_run=False)

        assert session.get(Article, exclusive_id) is None


def _seed_remove_topic_case() -> tuple[int, int, int]:
    init_db()
    with Session(engine) as session:
        primary = Topic(name="删除测试主主题", queries=["删除测试主主题"])
        other = Topic(name="删除测试共享主题", queries=["删除测试共享主题"])
        shared = Article(
            url=f"https://example.com/shared-{datetime.utcnow().timestamp()}",
            title="共享文章",
        )
        exclusive = Article(
            url=f"https://example.com/exclusive-{datetime.utcnow().timestamp()}",
            title="独占文章",
        )
        session.add(primary)
        session.add(other)
        session.add(shared)
        session.add(exclusive)
        session.commit()
        session.refresh(primary)
        session.refresh(other)
        session.refresh(shared)
        session.refresh(exclusive)

        session.add(TopicArticle(topic_id=primary.id, article_id=shared.id, relevance=0.9))
        session.add(TopicArticle(topic_id=other.id, article_id=shared.id, relevance=0.7))
        session.add(TopicArticle(topic_id=primary.id, article_id=exclusive.id, relevance=0.8))
        session.add(TimelineEvent(topic_id=primary.id, title_zh="测试时间线"))
        session.add(SourceFraming(topic_id=primary.id, party="测试来源", stance="中立"))
        session.add(Analysis(topic_id=primary.id, content_md="测试分析"))
        session.commit()
        return primary.id, shared.id, exclusive.id
