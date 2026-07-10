from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import api
from app.db import Article, Event, Topic, TopicArticle, engine, init_db
from app.services.event_contrast import SourceBundle, _coverage_gaps, _source_payload


def test_event_contrast_returns_multi_source_payload_with_neutral_gaps():
    topic_id, event_id = _seed_contrast_topic(tag="main")

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{event_id}/contrast")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is False
    assert "未观察" in payload["note"]
    assert "蓄意" in payload["note"]
    assert payload["event"]["id"] == event_id
    assert payload["event"]["source_count"] == 3
    assert payload["event"]["article_count"] == 3

    sources = {source["source"]: source for source in payload["sources"]}
    assert set(sources) == {"Reuters", "BBC", "Financial Times"}
    assert sources["Reuters"]["tier"] == "wire"
    assert sources["Reuters"]["tier_label"] == "通讯社"
    assert sources["Reuters"]["stance"] == "冲突/安全"
    assert sources["Reuters"]["stance_summary"] == "强调军事行动"
    assert sources["Reuters"]["substance_score"] == 82
    assert sources["Reuters"]["substance_note"] == "含具体时间地点"
    assert sources["Reuters"]["emotion_score"] == 18
    assert sources["Reuters"]["emotion_note"] == "措辞克制"
    assert sources["Reuters"]["representative_title"] == "Reuters: Iran strike near Hormuz"
    assert sources["Reuters"]["url"] == "https://example.com/reuters-main"
    assert sources["Reuters"]["article_ids"]
    iran = next(item for item in sources["Reuters"]["emphasized_entities"] if item["term"] == "伊朗")
    assert iran["count"] == 2
    assert iran["evidence_article_ids"] == sources["Reuters"]["article_ids"]
    assert all("count" in item for item in sources["Reuters"]["emphasized_keywords"])

    gaps = payload["coverage_gaps"]
    assert gaps
    assert all("not_observed_in" in gap for gap in gaps)
    assert all("missing_from" not in gap for gap in gaps)
    hormuz = next(gap for gap in gaps if gap["term"] == "霍尔木兹海峡")
    assert hormuz["kind"] == "entity"
    assert hormuz["covered_by"] == ["Reuters"]
    assert set(hormuz["not_observed_in"]) == {"BBC", "Financial Times"}
    assert hormuz["evidence_article_ids"] == sources["Reuters"]["article_ids"]
    assert hormuz["salience"] > 1
    white_house = next(gap for gap in gaps if gap["term"] == "白宫")
    assert white_house["salience"] == 1


def test_event_contrast_degrades_with_fewer_than_two_sources():
    topic_id, event_id = _seed_single_source_topic()

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{event_id}/contrast")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is True
    assert "至少需要 2 个来源" in payload["note"]
    assert len(payload["sources"]) == 1
    assert payload["coverage_gaps"] == []


def test_event_contrast_rejects_event_outside_topic():
    first_topic_id, _ = _seed_single_source_topic(name="Contrast Topic A")
    _, other_event_id = _seed_single_source_topic(name="Contrast Topic B")

    response = TestClient(api.app).get(f"/api/topics/{first_topic_id}/events/{other_event_id}/contrast")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found in topic"


def test_event_contrast_missing_enrichment_does_not_block_payload():
    topic_id, event_id = _seed_contrast_topic(tag="missing", with_missing_enrichment=True)

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{event_id}/contrast")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is False
    bbc = next(source for source in payload["sources"] if source["source"] == "BBC")
    assert bbc["substance_score"] == -1
    assert bbc["substance_note"] == "未评分"
    assert bbc["emotion_score"] == -1
    assert bbc["emotion_note"] == "未评分"


def test_event_contrast_normalizes_terms_before_gap_detection():
    topic_id, event_id = _seed_contrast_topic(tag="normalize")

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{event_id}/contrast")

    assert response.status_code == 200
    gaps = response.json()["coverage_gaps"]
    iran_gap = [gap for gap in gaps if gap["term"] == "伊朗"]
    assert iran_gap == []


def test_event_contrast_ranks_and_limits_gaps_by_salience():
    weak_terms = [
        {"term": f"a-weak-{index:02d}", "count": 1, "evidence_article_ids": [101]}
        for index in range(35)
    ]
    sources = [
        {
            "source": "Reuters",
            "emphasized_entities": [
                *weak_terms,
                {"term": "z-strong", "count": 5, "evidence_article_ids": [101]},
            ],
            "emphasized_keywords": [],
            "article_ids": [101],
        },
        {
            "source": "BBC",
            "emphasized_entities": [],
            "emphasized_keywords": [],
            "article_ids": [102],
        },
    ]

    gaps = _coverage_gaps(sources)

    assert len(gaps) == 30
    assert gaps[0]["term"] == "z-strong"
    assert gaps[0]["salience"] == 5
    assert all(gap["salience"] == 1 for gap in gaps[1:])


def test_source_payload_tracks_evidence_articles_for_each_emphasized_term():
    matching = Article(
        id=101,
        url="https://example.com/reuters-hormuz",
        title="Reuters: Iran keeps Hormuz shipping open 伊朗",
        source="Reuters",
        snippet="Shipping continues through Hormuz after the announcement.",
        published_at=datetime(2026, 6, 1, 8, 0),
    )
    unrelated = Article(
        id=102,
        url="https://example.com/reuters-oil",
        title="Reuters: Oil prices edge higher",
        source="Reuters",
        snippet="Energy markets moved in early trading.",
        published_at=datetime(2026, 6, 1, 9, 0),
    )
    rows = [
        (TopicArticle(topic_id=1, article_id=101, relevance=0.9), matching),
        (TopicArticle(topic_id=1, article_id=102, relevance=0.8), unrelated),
    ]

    source = _source_payload(SourceBundle(source="Reuters", rows=rows))

    hormuz = next(item for item in source["emphasized_keywords"] if item["term"] == "hormuz")
    assert hormuz["evidence_article_ids"] == [101]
    iran = next(item for item in source["emphasized_entities"] if item["term"] == "伊朗")
    assert iran["evidence_article_ids"] == [101]


def test_source_payload_does_not_truncate_entity_evidence_per_article(monkeypatch):
    def fake_entities(text: str, *, limit: int, **_kwargs):
        if 'first-marker' in text and 'second-marker' in text:
            return [{'term': 'Shared Entity', 'count': 2}]
        decoys = [{'term': f'Decoy {index}', 'count': 1} for index in range(10)]
        if limit > 10:
            decoys.append({'term': 'Shared Entity', 'count': 1})
        return decoys

    monkeypatch.setattr('app.services.event_contrast.local_analyze._entities_for_text', fake_entities)
    rows = [
        (
            TopicArticle(topic_id=1, article_id=101, relevance=0.9),
            Article(
                id=101,
                url='https://example.com/reuters-first',
                title='first-marker',
                source='Reuters',
                snippet='',
                published_at=datetime(2026, 6, 1, 8, 0),
            ),
        ),
        (
            TopicArticle(topic_id=1, article_id=102, relevance=0.8),
            Article(
                id=102,
                url='https://example.com/reuters-second',
                title='second-marker',
                source='Reuters',
                snippet='',
                published_at=datetime(2026, 6, 1, 9, 0),
            ),
        ),
    ]

    source = _source_payload(SourceBundle(source='Reuters', rows=rows))

    entity = next(item for item in source['emphasized_entities'] if item['term'] == 'Shared Entity')
    assert entity['evidence_article_ids'] == [101, 102]


def test_coverage_gaps_use_term_evidence_instead_of_every_source_article():
    sources = [
        {
            "source": "Reuters",
            "emphasized_entities": [],
            "emphasized_keywords": [
                {"term": "hormuz", "count": 2, "evidence_article_ids": [101]},
            ],
            "article_ids": [101, 102],
        },
        {
            "source": "BBC",
            "emphasized_entities": [],
            "emphasized_keywords": [],
            "article_ids": [201],
        },
    ]

    gaps = _coverage_gaps(sources)

    assert gaps[0]["evidence_article_ids"] == [101]


def test_coverage_gaps_skip_terms_without_article_evidence():
    sources = [
        {
            "source": "Reuters",
            "emphasized_entities": [],
            "emphasized_keywords": [{"term": "hormuz", "count": 2, "evidence_article_ids": []}],
            "article_ids": [101],
        },
        {
            "source": "BBC",
            "emphasized_entities": [],
            "emphasized_keywords": [],
            "article_ids": [201],
        },
    ]

    assert _coverage_gaps(sources) == []


def _seed_contrast_topic(tag: str, with_missing_enrichment: bool = False) -> tuple[int, int]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=f"Event Contrast {tag}", queries=["Iran"])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        rows = [
            (
                Article(
                    url=f"https://example.com/reuters-{tag}",
                    title="Reuters: Iran strike near Hormuz",
                    source="Reuters",
                    snippet="Iran says the Strait of Hormuz remains open after the strike.",
                    published_at=datetime(2026, 6, 1, 8, 0),
                ),
                TopicArticle(
                    topic_id=topic.id,
                    article_id=0,
                    relevance=0.9,
                    stance="冲突/安全",
                    stance_summary="强调军事行动",
                    substance_score=82,
                    substance_note="含具体时间地点",
                    emotion_score=18,
                    emotion_note="措辞克制",
                ),
            ),
            (
                Article(
                    url=f"https://example.com/bbc-{tag}",
                    title="BBC: Iran response draws diplomacy calls",
                    source="BBC",
                    snippet="  Iran  officials and the White House call for talks.",
                    published_at=datetime(2026, 6, 1, 9, 0),
                ),
                TopicArticle(
                    topic_id=topic.id,
                    article_id=0,
                    relevance=0.85,
                    stance="外交降温",
                    stance_summary="强调外交沟通",
                    substance_score=-1 if with_missing_enrichment else 64,
                    substance_note="" if with_missing_enrichment else "含具名表态",
                    emotion_score=-1 if with_missing_enrichment else 24,
                    emotion_note="" if with_missing_enrichment else "情绪较低",
                ),
            ),
            (
                Article(
                    url=f"https://example.com/ft-{tag}",
                    title="FT: Oil traders watch market risk",
                    source="Financial Times",
                    snippet="Oil markets weigh Iran sanctions after the regional escalation.",
                    published_at=datetime(2026, 6, 1, 10, 0),
                ),
                TopicArticle(
                    topic_id=topic.id,
                    article_id=0,
                    relevance=0.8,
                    stance="市场影响",
                    stance_summary="强调市场后果",
                    substance_score=70,
                    substance_note="含市场价格",
                    emotion_score=30,
                    emotion_note="风险措辞中等",
                ),
            ),
        ]

        article_ids = []
        for article, link in rows:
            session.add(article)
            session.commit()
            session.refresh(article)
            link.article_id = article.id
            session.add(link)
            article_ids.append(article.id)
        event = Event(
            topic_id=topic.id,
            date=datetime(2026, 6, 1),
            title="Iran event",
            title_zh="伊朗相关事件",
            summary_zh="多家媒体报道伊朗相关事件。",
            article_ids=article_ids,
            sources=["Reuters", "BBC", "Financial Times"],
            entities=["伊朗"],
            source_count=3,
            article_count=3,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return topic.id, event.id


def _seed_single_source_topic(name: str = "Single Source Contrast") -> tuple[int, int]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, queries=["Iran"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        article = Article(
            url=f"https://example.com/{name}",
            title="Reuters: Iran update",
            source="Reuters",
            snippet="Iran update.",
            published_at=datetime(2026, 6, 1, 8, 0),
        )
        session.add(article)
        session.commit()
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
        event = Event(
            topic_id=topic.id,
            date=datetime(2026, 6, 1),
            title="Single source event",
            title_zh="单源事件",
            summary_zh="只有一个来源。",
            article_ids=[article.id],
            sources=["Reuters"],
            entities=["伊朗"],
            source_count=1,
            article_count=1,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return topic.id, event.id
