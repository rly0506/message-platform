from datetime import datetime, timedelta

from app.pipeline import local_analyze


def row(
    idx: int,
    title: str,
    source: str,
    day_offset: int = 0,
    snippet: str = "",
    relevance: float = 1.0,
    stance: str = "",
):
    return local_analyze.ArticleRow(
        id=idx,
        title=title,
        source=source,
        published_at=datetime(2026, 6, 1) + timedelta(days=day_offset),
        snippet=snippet,
        relevance=relevance,
        stance=stance,
    )


def test_analyze_topic_returns_event_evidence_and_grouped_entities():
    rows = [
        row(
            1,
            "特朗普称美国将对伊朗发动空袭",
            "Reuters",
            snippet="哈梅内伊、伊斯兰革命卫队和白宫均成为报道焦点。",
        ),
        row(
            2,
            "Trump says US strike on Iran is possible",
            "BBC",
            snippet="The White House and IRGC are cited in the report.",
            day_offset=1,
        ),
        row(
            3,
            "美伊战争影响霍尔木兹海峡油价",
            "Financial Times",
            snippet="美国、伊朗、霍尔木兹海峡、制裁成为核心关键词。",
            day_offset=2,
        ),
    ]

    data = local_analyze.analyze_topic("美伊战争", rows, max_events=5)

    assert data["events"]
    event = data["events"][0]
    assert event["score_breakdown"]
    assert event["sources"]
    assert event["source_matrix"]
    assert event["source_tiers"]
    assert event["category"]
    assert event["category_reason"]
    assert event["importance_label"] in {"高", "中", "低"}
    assert event["coverage_label"]
    assert event["selection_basis"]
    assert event["location_signals"]
    assert event["evidence"]["first_sources"]
    matrix_sources = {item["source"]: item for item in event["source_matrix"]}
    assert "Reuters" in matrix_sources
    assert matrix_sources["Reuters"]["tier_label"] == "通讯社"
    assert matrix_sources["Reuters"]["dominant_stance"]
    assert matrix_sources["Reuters"]["dominant_category"]
    assert matrix_sources["Reuters"]["category_counts"]
    assert matrix_sources["Reuters"]["representative_title"]

    groups = {group["label"]: group["items"] for group in data["entity_groups"]}
    assert "人物" in groups
    assert "组织" in groups
    assert "地点" in groups
    assert any(item["term"] == "特朗普" for item in groups["人物"])
    assert any(item["term"] == "伊斯兰革命卫队" for item in groups["组织"])
    assert any(item["term"] == "伊朗" for item in groups["地点"])


def test_empty_topic_shape_uses_entity_group_list():
    data = local_analyze.analyze_topic("空专题", [])

    assert data["events"] == []
    assert data["entity_groups"] == []


def test_stance_trend_requires_enough_total_samples():
    evolution = [
        {"period": "2026-05", "counts": {}, "article_ids": []},
        {"period": "2026-06", "counts": {"conflict": 3}, "article_ids": [1, 2, 3]},
    ]

    assert local_analyze._trend_for_stance("conflict", evolution) == "样本不足"


def test_stance_trend_compares_first_and_last_period_conservatively():
    evolution = [
        {"period": "2026-04", "counts": {"conflict": 2, "neutral": 2}, "article_ids": [1, 2, 3, 4]},
        {"period": "2026-05", "counts": {"conflict": 8}, "article_ids": [5, 6, 7, 8, 9, 10, 11, 12]},
        {"period": "2026-06", "counts": {"conflict": 2, "neutral": 2}, "article_ids": [13, 14, 15, 16]},
    ]

    assert local_analyze._trend_for_stance("conflict", evolution) == "基本稳定"


def test_framing_article_ids_are_limited_to_matching_stance():
    rows = [
        row(1, "Bank earnings lift market", "Reuters", stance="竞争/商业"),
        row(2, "Iran warns retaliation after strike", "AP News", stance="风险/审慎"),
        row(3, "Ceasefire talks resume", "BBC", day_offset=35, stance="外交降温"),
    ]

    evolution = local_analyze._stance_evolution(rows)
    framing = {item["party"]: item for item in local_analyze._framing_from_evolution(evolution, rows)}

    assert framing["竞争/商业"]["article_ids"] == [1]
    assert framing["风险/审慎"]["article_ids"] == [2]
    assert framing["外交降温"]["article_ids"] == [3]


def test_report_category_inference_uses_stable_product_labels():
    assert local_analyze.infer_report_category("油价上涨，美伊战争影响市场") == "影响后果"
    assert local_analyze.infer_report_category("白宫回应伊朗警告") == "各方回应"
    reason = local_analyze.report_category_reason("影响后果", "油价上涨，美伊战争影响市场")
    assert "命中阶段词" in reason


def test_entity_extraction_falls_back_when_spacy_is_unavailable(monkeypatch):
    monkeypatch.setattr(local_analyze, "_spacy_entities", lambda text: [])

    entities = local_analyze._entities_for_text("特朗普在白宫讨论Iran局势", limit=10)

    assert entities
    assert any(item["term"] == "特朗普" for item in entities)


def test_entity_cloud_filters_article_source_names():
    rows = [
        row(
            1,
            "China Press: Australia weighs Iran response",
            "China Press",
            snippet="Moomoo says the White House and IRGC remain central.",
        ),
        row(
            2,
            "Moomoo: Oil market reacts to Iran sanctions",
            "Moomoo",
            snippet="Australia and Iran are both cited.",
            day_offset=1,
        ),
    ]

    data = local_analyze.analyze_topic("美伊战争", rows, max_events=5)
    terms = {item["term"] for item in data["entities"]}

    assert "China Press" not in terms
    assert "Moomoo" not in terms


def test_entity_cloud_filters_source_alias_before_country_classification():
    entities = local_analyze._entities_for_text(
        "美伊战争经济影响曝光 - 中國報 China Press China Press says Australia and Iran are cited.",
        limit=20,
        source_names=["中國報 China Press"],
    )
    all_terms = {item["term"] for item in entities}
    place_terms = {item["term"] for item in entities if item["kind"] == "place"}

    assert "China Press" not in all_terms
    assert "China Press" not in place_terms
    assert not any("China Press" in term for term in all_terms)


def test_english_country_names_are_classified_as_places(monkeypatch):
    monkeypatch.setattr(local_analyze, "_spacy_entities", lambda text: [])

    entities = local_analyze._entities_for_text("Australia weighs response after Iran talks", limit=10)

    assert any(item["term"] == "Australia" and item["kind"] == "place" for item in entities)


def test_event_level_entities_skip_spacy_for_performance(monkeypatch):
    calls = []

    def fake_spacy(text):
        calls.append(text)
        return [("Netanyahu", "person")]

    monkeypatch.setattr(local_analyze, "_spacy_entities", fake_spacy)
    rows = [
        row(
            1,
            "Trump says Netanyahu will discuss Iran",
            "Reuters",
            snippet="The White House is cited.",
        )
    ]

    data = local_analyze.analyze_topic("美伊战争", rows, max_events=5)

    assert len(calls) == 1
    assert any(item["term"] in {"Netanyahu", "内塔尼亚胡"} for item in data["entities"])
    assert all(item["term"] != "Netanyahu" for event in data["events"] for item in event["entities"])


def test_entity_extraction_ignores_rss_url_noise(monkeypatch):
    monkeypatch.setattr(
        local_analyze,
        "_spacy_entities",
        lambda text: [("WFZhaWxCU294dlMt", "organization"), ("White House", "organization")],
    )

    entities = local_analyze._entities_for_text(
        '<a href="https://news.google.com/rss/articles/WFZhaWxCU294dlMt">White House</a>',
        limit=10,
    )
    terms = {item["term"] for item in entities}

    assert "White House" in terms or "白宫" in terms
    assert "WFZhaWxCU294dlMt" not in terms


def test_entity_extraction_ignores_html_entity_noise(monkeypatch):
    monkeypatch.setattr(
        local_analyze,
        "_spacy_entities",
        lambda text: [("nbsp", "person"), ("White House", "organization")],
    )

    entities = local_analyze._entities_for_text("？ &nbsp;&nbsp; White House", limit=10)
    terms = {item["term"] for item in entities}

    assert "White House" in terms or "白宫" in terms
    assert "nbsp" not in terms


def test_entity_cloud_uses_full_topic_rows_not_only_major_event_subset(monkeypatch):
    def fake_spacy(text):
        out = []
        if "美军" in text:
            out.append(("美军", "organization"))
        if "白宫" in text:
            out.append(("白宫", "organization"))
        return out

    monkeypatch.setattr(local_analyze, "_spacy_entities", fake_spacy)
    rows = [
        row(1, "特朗普宣布美伊战争爆发", "Reuters", relevance=1.0),
        row(2, "油价随美伊战争上涨", "BBC", day_offset=1, relevance=0.9),
        row(
            3,
            "背景报道：美军与白宫正在评估局势",
            "AP News",
            day_offset=90,
            snippet="这篇不是重大事件子集，但应进入全局实体云。",
            relevance=0.1,
        ),
    ]

    data = local_analyze.analyze_topic("美伊战争", rows, max_events=1)
    organizations = {
        item["term"]
        for group in data["entity_groups"]
        if group["label"] == "组织"
        for item in group["items"]
    }

    assert {"美军", "白宫"} <= organizations


def test_spacy_person_place_misclassification_is_reclassified(monkeypatch):
    monkeypatch.setattr(local_analyze, "_spacy_entities", lambda text: [("黎巴嫩", "person"), ("霍尔木兹", "person")])

    entities = local_analyze._entities_for_text("黎巴嫩和霍尔木兹局势升温", limit=10)
    people = {item["term"] for item in entities if item["kind"] == "person"}
    places = {item["term"] for item in entities if item["kind"] == "place"}

    assert "黎巴嫩" not in people
    assert "霍尔木兹" not in people
    assert {"黎巴嫩", "霍尔木兹"} <= places


def test_spacy_person_noise_is_filtered_while_real_people_remain(monkeypatch):
    monkeypatch.setattr(
        local_analyze,
        "_spacy_entities",
        lambda text: [("已达成", "person"), ("伊美军", "person"), ("红艳艳", "person"), ("普京", "person")],
    )

    entities = local_analyze._entities_for_text("普京表示双方已达成协议，伊美军一词是误分词。", limit=10)
    people = {item["term"] for item in entities if item["kind"] == "person"}

    assert "普京" in people
    assert "已达成" not in people
    assert "伊美军" not in people
    assert "红艳艳" not in people


def test_spacy_organization_noise_is_filtered_while_real_orgs_remain(monkeypatch):
    monkeypatch.setattr(
        local_analyze,
        "_spacy_entities",
        lambda text: [
            ("伊朗战争", "organization"),
            ("美以伊战争", "organization"),
            ("谅解备忘录", "organization"),
            ("美伊谅解备忘录", "organization"),
            ("通讯社", "organization"),
            ("美军", "organization"),
            ("白宫", "organization"),
            ("伊朗国家通讯社", "organization"),
            ("联合国", "organization"),
        ],
    )

    entities = local_analyze._entities_for_text(
        "美军、白宫、伊朗国家通讯社和联合国被报道；伊朗战争、谅解备忘录和通讯社是噪声。",
        limit=20,
    )
    organizations = {item["term"] for item in entities if item["kind"] == "organization"}

    assert {"美军", "白宫", "伊朗国家通讯社", "联合国"} <= organizations
    assert "伊朗战争" not in organizations
    assert "美以伊战争" not in organizations
    assert "谅解备忘录" not in organizations
    assert "美伊谅解备忘录" not in organizations
    assert "通讯社" not in organizations
