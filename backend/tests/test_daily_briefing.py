from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app import api
from app.db import Article, CognitionProfile, Event, Topic, TopicArticle, init_db
from app.services import daily_briefing


def test_briefing_endpoint_returns_local_fact_contract():
    init_db()

    response = TestClient(api.app).get('/api/briefing/latest')

    assert response.status_code == 200
    payload = response.json()
    assert payload['basis'] == 'persisted_article_metadata'
    assert isinstance(payload['items'], list)
    assert 'article bodies are not stored' in payload['note']
    assert 'domain_today' in payload


def test_briefing_uses_latest_persisted_fact_and_event_coverage():
    now = datetime(2026, 7, 14, 12, 0, 0)
    with _isolated_session() as session:
        topic = Topic(name='Ceasefire monitoring', queries=['ceasefire'])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        articles = [
            Article(
                url='https://brief.example/reuters',
                title='Earlier monitoring report',
                source='Reuters',
                source_lang='en',
                snippet='Observers reported the first inspection.',
                published_at=now - timedelta(hours=3),
                collector='rss',
            ),
            Article(
                url='https://brief.example/afp',
                title='Latest inspection window confirmed',
                source='AFP',
                source_lang='fr',
                snippet='<p>Officials confirmed the next inspection window.</p>',
                published_at=now - timedelta(hours=1),
                collector='rss',
            ),
            Article(
                url='https://brief.example/unknown',
                title='Additional local notice',
                source='',
                source_lang='',
                snippet='A local notice listed the same inspection date.',
                published_at=now - timedelta(hours=2),
                collector='gnews',
            ),
        ]
        article_ids = []
        for article in articles:
            session.add(article)
            session.commit()
            session.refresh(article)
            article_ids.append(article.id)
            session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevant=True))
        session.commit()

        event = Event(
            topic_id=topic.id,
            date=now - timedelta(days=1),
            title='Inspection window',
            article_ids=article_ids,
        )
        session.add(event)
        session.commit()
        session.refresh(event)

        payload = daily_briefing.build_daily_briefing(
            session,
            app_base_url='https://desk.example/workbench',
            now=now,
        )

    assert len(payload['items']) == 1
    item = payload['items'][0]
    assert item['topic_id'] == topic.id
    assert item['event_id'] == event.id
    assert item['article_id'] == article_ids[1]
    assert item['title'] == 'Latest inspection window confirmed'
    assert item['fact_summary'] == 'Officials confirmed the next inspection window.'
    assert item['summary_basis'] == 'persisted_title_and_snippet'
    assert item['source'] == 'AFP'
    assert item['evidence_url'] == 'https://brief.example/afp'
    assert item['deep_link_path'] == f'/?topic={topic.id}&event={event.id}&view=contrast'
    assert item['deep_link_url'] == (
        f'https://desk.example/workbench/?topic={topic.id}&event={event.id}&view=contrast'
    )
    assert item['fulltext'] == {
        'status': 'unknown',
        'reason': 'article_bodies_not_persisted',
    }
    assert item['coverage']['scope'] == 'event'
    assert item['coverage']['article_count'] == 3
    assert item['coverage']['independent_source_count'] == 2
    assert item['coverage']['known_language_count'] == 2
    assert item['coverage']['unknown_language_article_count'] == 1
    assert item['coverage']['article_ids'] == sorted(article_ids)
    assert item['coverage']['label'] == '事件样本 3 篇 · 2 源 · 2 语种（1 篇语种未知）'
    assert 'absence is not proof' in item['coverage']['note']


def test_briefing_keeps_topic_fallback_and_unknowns_honest_and_excludes_stale_items():
    now = datetime(2026, 7, 14, 12, 0, 0)
    with _isolated_session() as session:
        fresh = Topic(name='Fresh metadata only', queries=['fresh'])
        stale = Topic(name='Stale topic', queries=['stale'])
        session.add(fresh)
        session.add(stale)
        session.commit()
        session.refresh(fresh)
        session.refresh(stale)

        fresh_article = Article(
            url='https://brief.example/title-only',
            title='Title-only verified record',
            source='',
            source_lang='',
            snippet='',
            published_at=now - timedelta(hours=2),
        )
        stale_article = Article(
            url='https://brief.example/stale',
            title='Old record',
            source='Old Wire',
            source_lang='en',
            snippet='Old summary.',
            published_at=now - timedelta(days=20),
        )
        session.add(fresh_article)
        session.add(stale_article)
        session.commit()
        session.refresh(fresh_article)
        session.refresh(stale_article)
        session.add(TopicArticle(topic_id=fresh.id, article_id=fresh_article.id, relevant=True))
        session.add(TopicArticle(topic_id=stale.id, article_id=stale_article.id, relevant=True))
        session.commit()

        payload = daily_briefing.build_daily_briefing(session, now=now)

    assert [item['topic_id'] for item in payload['items']] == [fresh.id]
    item = payload['items'][0]
    assert item['event_id'] is None
    assert item['summary_basis'] == 'persisted_title_only'
    assert item['fact_summary'] == '该条持久化记录目前只有标题；正文未落库。'
    assert item['source'] == '来源未知'
    assert item['deep_link_path'] == f'/?topic={fresh.id}&view=contrast'
    assert item['deep_link_url'] is None
    assert item['coverage']['scope'] == 'topic'
    assert item['coverage']['label'] == '专题样本 1 篇 · 来源未知 · 语种未知'
    assert item['coverage']['known_language_count'] == 0
    assert item['coverage']['unknown_language_article_count'] == 1


def test_domain_today_rotates_profile_questions_without_mutating_profile_rows():
    first_day = datetime(2026, 7, 14, 8, 0, 0)
    with _isolated_session() as session:
        session.add(CognitionProfile(
            domain_key='energy',
            domain_label='能源',
            level='unfamiliar',
            interest='medium',
            confidence=55,
            recommended_seed_style='mechanism',
        ))
        session.add(CognitionProfile(
            domain_key='finance',
            domain_label='金融',
            level='partial',
            interest='high',
            confidence=70,
            recommended_seed_style='financial_model',
        ))
        session.commit()
        before = _profile_snapshot(session)

        first = daily_briefing.build_daily_briefing(session, now=first_day)['domain_today']
        second = daily_briefing.build_daily_briefing(
            session,
            now=first_day + timedelta(days=1),
        )['domain_today']
        after = _profile_snapshot(session)

    assert first['domain_key'] != second['domain_key']
    assert first['selection_basis'] == 'deterministic_local_profile_rotation'
    assert first['date'] == '2026-07-14'
    assert len(first['questions']) == 3
    assert '官方' in first['questions'][0]
    assert '历史先例' in first['questions'][1]
    assert '不是结论' in first['note']
    assert before == after


def _isolated_session() -> Session:
    isolated_engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(isolated_engine)
    return Session(isolated_engine)


def _profile_snapshot(session: Session) -> list[tuple]:
    rows = session.exec(select(CognitionProfile).order_by(CognitionProfile.domain_key)).all()
    return [
        (
            row.domain_key,
            row.domain_label,
            row.level,
            row.interest,
            row.confidence,
            row.recommended_seed_style,
            row.updated_at,
        )
        for row in rows
    ]
