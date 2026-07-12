from fastapi.testclient import TestClient
from sqlmodel import Session

from app import api
from app.db import Article, Event, SourceRegistry, Topic, TopicArticle, engine, init_db


def test_topic_coverage_reports_evidence_linked_distributions():
    topic_id, article_ids, _ = _seed_coverage_topic('topic')

    response = TestClient(api.app).get(f'/api/topics/{topic_id}/coverage')

    assert response.status_code == 200
    payload = response.json()
    assert payload['topic_id'] == topic_id
    assert payload['event_id'] is None
    assert payload['sample']['basis'] == 'persisted_topic_articles'
    assert payload['sample']['article_count'] == 4
    assert payload['sample']['article_ids'] == sorted(article_ids)
    assert 'not proof' in payload['sample']['note']
    assert payload['independent_source_count'] == 2

    assert _bucket_map(payload['collector_distribution']) == {
        'gnews': (2, sorted(article_ids[:2])),
        'rss': (1, [article_ids[2]]),
        'unknown': (1, [article_ids[3]]),
    }
    unknown_ids = sorted([article_ids[1], article_ids[3]])
    assert _bucket_map(payload['language_distribution'])['unknown'] == (2, unknown_ids)
    assert _bucket_map(payload['country_distribution'])['unknown'] == (2, unknown_ids)

    assert payload['url_decoding'] == {
        'eligible_count': 2,
        'decoded_count': 1,
        'rate': 0.5,
        'decoded_article_ids': [article_ids[0]],
        'not_decoded_article_ids': [article_ids[1]],
    }

    registry = payload['source_registry']
    assert _bucket_map(registry['type_distribution']) == {
        'news_agency': (2, sorted(article_ids[:2])),
    }
    assert _bucket_map(registry['tier_distribution']) == {
        'tier_1': (2, sorted(article_ids[:2])),
    }
    assert registry['unclassified_article_ids'] == sorted(article_ids[2:])
    assert payload['fulltext'] == {
        'status': 'unknown',
        'reason': 'article_bodies_not_persisted',
    }


def test_event_coverage_intersects_topic_evidence():
    topic_id, article_ids, event_id = _seed_coverage_topic('event')

    response = TestClient(api.app).get(
        f'/api/topics/{topic_id}/coverage',
        params={'event_id': event_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['event_id'] == event_id
    assert payload['sample']['basis'] == 'persisted_event_articles'
    assert payload['sample']['article_ids'] == sorted(article_ids[1:3])
    assert payload['sample']['article_count'] == 2
    assert payload['url_decoding']['eligible_count'] == 1
    assert payload['url_decoding']['rate'] == 0.0


def test_coverage_returns_empty_honest_sample_and_null_decode_rate():
    init_db()
    with Session(engine) as session:
        topic = Topic(name='RM055 Empty Coverage', queries=[])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        topic_id = topic.id

    payload = TestClient(api.app).get(f'/api/topics/{topic_id}/coverage').json()

    assert payload['sample']['article_count'] == 0
    assert payload['sample']['article_ids'] == []
    assert payload['url_decoding']['rate'] is None
    assert payload['collector_distribution'] == []


def test_coverage_rejects_missing_topic_and_event_outside_topic():
    first_topic_id, _, _ = _seed_coverage_topic('owner-a')
    _, _, other_event_id = _seed_coverage_topic('owner-b')
    client = TestClient(api.app)

    missing_topic = client.get('/api/topics/999999/coverage')
    wrong_event = client.get(
        f'/api/topics/{first_topic_id}/coverage',
        params={'event_id': other_event_id},
    )

    assert missing_topic.status_code == 404
    assert missing_topic.json()['detail'] == 'Topic not found'
    assert wrong_event.status_code == 404
    assert wrong_event.json()['detail'] == 'Event not found in topic'


def _bucket_map(buckets):
    return {
        bucket['key']: (bucket['count'], bucket['article_ids'])
        for bucket in buckets
    }


def _seed_coverage_topic(tag: str) -> tuple[int, list[int], int]:
    init_db()
    registry_name = f'RM055 Wire {tag}'
    with Session(engine) as session:
        session.add(SourceRegistry(
            name=registry_name,
            url=f'https://rm055.example/{tag}/feed',
            source_type='news_agency',
            quality_tier='tier_1',
        ))
        topic = Topic(name=f'RM055 Coverage {tag}', queries=[tag])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        articles = [
            Article(
                url=f'https://rm055.example/{tag}/decoded',
                source=registry_name,
                source_lang='en',
                source_country='US',
                collector='gnews',
                url_decoded=True,
            ),
            Article(
                url=f'https://rm055.example/{tag}/not-decoded',
                source=registry_name,
                collector='gnews',
                url_decoded=False,
            ),
            Article(
                url=f'https://rm055.example/{tag}/unmatched',
                source=f'RM055 Unmatched {tag}',
                source_lang='fr',
                source_country='FR',
                collector='rss',
            ),
            Article(
                url=f'https://rm055.example/{tag}/unknown',
                source='',
                source_lang='',
                source_country='',
                collector='',
            ),
        ]
        article_ids = []
        for article in articles:
            session.add(article)
            session.commit()
            session.refresh(article)
            article_ids.append(article.id)
            session.add(TopicArticle(topic_id=topic.id, article_id=article.id))
        session.commit()

        event = Event(
            topic_id=topic.id,
            title=f'RM055 Event {tag}',
            article_ids=[article_ids[1], article_ids[2], 999999],
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return topic.id, article_ids, event.id
