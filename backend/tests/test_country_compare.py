from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import api
from app.db import Article, Topic, TopicArticle, engine, init_db
from app.services import country_compare


def test_country_of_source_uses_normalized_config_mapping():
    assert country_compare.country_of_source("Reuters") == {"code": "GB", "name": "英国"}
    assert country_compare.country_of_source("Thomson Reuters") == {"code": "GB", "name": "英国"}
    assert country_compare.country_of_source("BBC News") == {"code": "GB", "name": "英国"}
    assert country_compare.country_of_source("纽约时报中文网") == {"code": "US", "name": "美国"}
    assert country_compare.country_of_source("新华社") == {"code": "CN", "name": "中国"}
    assert country_compare.country_of_source("第一财经") == {"code": "CN", "name": "中国"}
    assert country_compare.country_of_source("Unknown Outlet") is None
    assert country_compare.country_of_source("Tom's Hardware") is None
    assert country_compare.country_of_source("Asharq Al-Awsat English") is None
    assert country_compare.country_of_source("kingandwood.com") is None


def test_country_of_place_maps_aliases_and_capitals():
    assert country_compare.country_of_place("德黑兰") == {"code": "IR", "name": "伊朗"}
    assert country_compare.country_of_place("Washington") == {"code": "US", "name": "美国"}
    assert country_compare.country_of_place("霍尔木兹海峡") == {"code": "IR", "name": "伊朗"}
    assert country_compare.country_of_place("discuss") is None


def test_build_country_compare_includes_g20_party_unmapped_and_first_reporters():
    topic_id, included_id, excluded_id = _seed_country_compare_case()

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = country_compare.build_country_compare(session, topic, article_ids=[included_id])

    anchor_codes = {item["code"] for item in result["anchor_countries"]}
    country_codes = {item["code"] for item in result["countries"]}
    assert "US" in anchor_codes
    assert "IR" in anchor_codes
    assert "CN" in anchor_codes
    assert "QA" not in anchor_codes
    assert "IR" in country_codes
    assert "US" in country_codes
    assert "CN" in country_codes
    assert "QA" in country_codes
    assert result["unmapped_count"] == 0

    iran = next(item for item in result["countries"] if item["code"] == "IR")
    assert iran["is_party"] is True
    assert iran["article_count"] == 0

    qatar = next(item for item in result["countries"] if item["code"] == "QA")
    assert qatar["article_count"] == 1
    assert qatar["stance_distribution"] == {"冲突/安全": 1}
    assert qatar["first_report"]["outlet"] == "Al Jazeera"
    assert qatar["sample_titles"] == ["德黑兰称霍尔木兹谈判继续"]

    assert result["first_reporters"][0]["country_code"] == "QA"
    assert all(item["article_id"] != excluded_id for item in result["first_reporters"])


def test_build_country_compare_prefers_source_country_and_keeps_source_fallback():
    topic_id, gdelt_id, gnews_id = _seed_source_country_case()

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = country_compare.build_country_compare(session, topic, article_ids=[gdelt_id, gnews_id])

    assert result["article_scope_count"] == 2
    assert result["unmapped_count"] == 0

    iran = next(item for item in result["countries"] if item["code"] == "IR")
    assert iran["article_count"] == 1
    assert iran["first_report"]["outlet"] == "presstv.ir"

    france = next(item for item in result["countries"] if item["code"] == "FR")
    assert france["article_count"] == 1
    assert france["first_report"]["outlet"] == "RFI"

    assert {item["country_code"] for item in result["first_reporters"][:2]} == {"IR", "FR"}


def test_nonempty_unknown_source_country_does_not_fall_back_to_source_name():
    topic_id, article_id = _seed_unknown_source_country_case()

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = country_compare.build_country_compare(session, topic, article_ids=[article_id])

    assert result["article_scope_count"] == 1
    assert result["unmapped_count"] == 1
    france = next(item for item in result["countries"] if item["code"] == "FR")
    assert france["article_count"] == 0
    assert result["first_reporters"] == []


def test_country_compare_api_is_read_only_and_accepts_article_ids():
    topic_id, included_id, _excluded_id = _seed_country_compare_case()
    client = TestClient(api.app)

    response = client.get(f"/api/topics/{topic_id}/country-compare", params={"article_ids": str(included_id)})

    assert response.status_code == 200
    body = response.json()
    assert body["topic_id"] == topic_id
    assert body["article_scope_count"] == 1
    assert body["countries"]
    assert any(country["code"] == "CN" and country["is_g20"] for country in body["countries"])


def test_country_compare_rejects_invalid_article_ids_without_server_error():
    topic_id, _included_id, _excluded_id = _seed_country_compare_case()
    client = TestClient(api.app)

    response = client.get(f"/api/topics/{topic_id}/country-compare", params={"article_ids": "abc"})

    assert response.status_code == 422
    assert response.json()["detail"] == "article_ids must be integers"


def _seed_country_compare_case() -> tuple[int, int, int]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name="国家对比测试", queries=["国家对比测试"])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        included = Article(
            url=f"https://example.com/country/{datetime.utcnow().timestamp()}-1",
            title="Tehran says Hormuz talks continue",
            title_zh="德黑兰称霍尔木兹谈判继续",
            source="Al Jazeera",
            source_lang="en-US",
            published_at=datetime(2026, 6, 1, 8, 0),
            snippet="Iran and Washington discuss the Strait of Hormuz.",
        )
        excluded = Article(
            url=f"https://example.com/country/{datetime.utcnow().timestamp()}-2",
            title="Beijing market watches war risk",
            title_zh="北京市场关注战争风险",
            source="新华社",
            source_lang="zh-CN",
            published_at=datetime(2026, 6, 1, 9, 0),
            snippet="中国关注地区风险。",
        )
        session.add(included)
        session.add(excluded)
        session.commit()
        session.refresh(included)
        session.refresh(excluded)

        session.add(TopicArticle(
            topic_id=topic.id,
            article_id=included.id,
            relevance=0.9,
            relevant=True,
            stance="冲突/安全",
        ))
        session.add(TopicArticle(
            topic_id=topic.id,
            article_id=excluded.id,
            relevance=0.8,
            relevant=True,
            stance="影响后果",
        ))
        session.commit()
        return topic.id, included.id, excluded.id


def _seed_source_country_case() -> tuple[int, int, int]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name="GDELT国家字段测试", queries=["GDELT国家字段测试"])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        gdelt_article = Article(
            url=f"https://example.com/gdelt/{datetime.utcnow().timestamp()}-1",
            title="Iran source country should override domain mapping",
            title_zh="GDELT来源国家应优先于域名映射",
            source="presstv.ir",
            source_lang="English",
            source_country="Iran",
            published_at=datetime(2026, 6, 1, 8, 0),
            snippet="Iran outlet reports on talks.",
            collector="gdelt",
        )
        gnews_article = Article(
            url=f"https://example.com/gdelt/{datetime.utcnow().timestamp()}-2",
            title="RFI tracks regional diplomacy",
            title_zh="RFI关注地区外交",
            source="RFI",
            source_lang="zh-CN",
            source_country="",
            published_at=datetime(2026, 6, 1, 9, 0),
            snippet="France-based outlet reports on diplomacy.",
            collector="rss",
        )
        session.add(gdelt_article)
        session.add(gnews_article)
        session.commit()
        session.refresh(gdelt_article)
        session.refresh(gnews_article)

        session.add(TopicArticle(
            topic_id=topic.id,
            article_id=gdelt_article.id,
            relevance=0.9,
            relevant=True,
            stance="官方表态",
        ))
        session.add(TopicArticle(
            topic_id=topic.id,
            article_id=gnews_article.id,
            relevance=0.8,
            relevant=True,
            stance="中性观察",
        ))
        session.commit()
        return topic.id, gdelt_article.id, gnews_article.id


def _seed_unknown_source_country_case() -> tuple[int, int]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name="未知GDELT国家字段测试", queries=["未知GDELT国家字段测试"])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        article = Article(
            url=f"https://example.com/gdelt/{datetime.utcnow().timestamp()}-unknown",
            title="Unknown source country should stay unmapped",
            title_zh="未知来源国不应回退媒体名",
            source="RFI",
            source_lang="English",
            source_country="Atlantis",
            published_at=datetime(2026, 6, 1, 8, 0),
            snippet="Synthetic GDELT row.",
            collector="gdelt",
        )
        session.add(article)
        session.commit()
        session.refresh(article)

        session.add(TopicArticle(
            topic_id=topic.id,
            article_id=article.id,
            relevance=0.9,
            relevant=True,
            stance="中性观察",
        ))
        session.commit()
        return topic.id, article.id
