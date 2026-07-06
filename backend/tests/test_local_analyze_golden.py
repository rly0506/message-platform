from datetime import datetime, timedelta
import hashlib
import json

from app.pipeline import local_analyze


EXPECTED_GOLDEN_SHA256 = "422a7b3bf7bd9d522936588abcaa230b9896df97a548f2b385d410fcf25349a1"


def _row(
    idx: int,
    title: str,
    source: str,
    day_offset: int = 0,
    snippet: str = "",
    relevance: float = 1.0,
    stance: str = "",
) -> local_analyze.ArticleRow:
    return local_analyze.ArticleRow(
        id=idx,
        title=title,
        source=source,
        published_at=datetime(2026, 6, 1, 8, 0) + timedelta(days=day_offset),
        snippet=snippet,
        relevance=relevance,
        stance=stance,
    )


def _golden_rows() -> list[local_analyze.ArticleRow]:
    return [
        _row(
            101,
            "Trump says US strike on Iran is possible",
            "Reuters",
            snippet=(
                "White House and Islamic Revolutionary Guard Corps are cited as oil markets "
                "watch Hormuz Strait."
            ),
            relevance=0.96,
        ),
        _row(
            102,
            "Trump says US strike on Iran could expand",
            "BBC",
            day_offset=1,
            snippet="White House officials discuss Iran strike risks and market impact near Hormuz Strait.",
            relevance=0.91,
        ),
        _row(
            103,
            "Iran warns retaliation after US strike threat",
            "AP News",
            day_offset=1,
            snippet="Islamic Revolutionary Guard Corps warns of military retaliation after US strike threat.",
            relevance=0.88,
        ),
        _row(
            104,
            "Oil market rises as Hormuz Strait risk grows",
            "Financial Times",
            day_offset=2,
            snippet="Oil market impact and sanctions risks dominate analysis after Iran warnings.",
            relevance=0.84,
        ),
        _row(
            105,
            "United Nations urges ceasefire talks on Iran crisis",
            "Al Jazeera",
            day_offset=4,
            snippet="United Nations diplomats call for ceasefire talks and diplomacy.",
            relevance=0.78,
        ),
    ]


def test_analyze_topic_golden_snapshot(monkeypatch):
    monkeypatch.setattr(local_analyze, "pseg", None)
    monkeypatch.setattr(
        local_analyze,
        "_spacy_entities",
        lambda text: [
            ("Donald Trump", "person"),
            ("White House", "organization"),
            ("Islamic Revolutionary Guard Corps", "organization"),
            ("Hormuz Strait", "place"),
            ("United Nations", "organization"),
        ],
    )

    result = local_analyze.analyze_topic("Iran crisis golden sample", _golden_rows(), max_events=4)

    canonical = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == EXPECTED_GOLDEN_SHA256

    assert list(result) == [
        "events",
        "framing",
        "analysis_md",
        "stance_evolution",
        "keywords",
        "entities",
        "entity_groups",
        "criteria",
    ]
    assert len(result["events"]) == 3
    lead_event = result["events"][0]
    assert lead_event["title_zh"] == "Trump says US strike on Iran is possible"
    assert lead_event["score"] == 0.622
    assert lead_event["article_ids"] == [101, 102, 103]
    assert lead_event["source_tiers"] == [
        {"key": "wire", "label": "通讯社", "count": 2},
        {"key": "mainstream", "label": "主流媒体", "count": 1},
    ]
    assert {entry["source"] for entry in lead_event["source_matrix"]} == {"Reuters", "BBC", "AP News"}
    assert lead_event["score_breakdown"]["impact"]["reason"] == "strike"

    assert result["stance_evolution"] == [
        {
            "period": "2026-06",
            "dominant_stance": "冲突/安全",
            "counts": {"冲突/安全": 3, "竞争/商业": 1, "风险/审慎": 1},
            "article_ids": [101, 102, 103, 104, 105],
        }
    ]
    framing_by_party = {item["party"]: item["article_ids"] for item in result["framing"]}
    assert framing_by_party["冲突/安全"] == [101, 103, 105]
    assert framing_by_party["竞争/商业"] == [102]
    assert framing_by_party["风险/审慎"] == [104]
    assert [item["term"] for item in result["keywords"][:5]] == ["iran", "strike", "us", "on", "oil"]
    grouped = {group["kind"]: group["items"] for group in result["entity_groups"]}
    assert grouped["person"][0]["term"] == "特朗普"
    assert {item["term"] for item in grouped["organization"]} >= {"白宫", "联合国", "伊斯兰革命卫队"}
    assert {item["term"] for item in grouped["place"]} >= {"伊朗", "美国", "Hormuz Strait"}
    assert result["criteria"] == local_analyze.SIGNIFICANCE_CRITERIA
