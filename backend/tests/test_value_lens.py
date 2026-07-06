from app.discovery.sources import DiscoveryItem
from app.discovery.store import ScoredItem
from app.pipeline import value_lens


def _codes(labels):
    return [label["code"] for label in labels]


def test_article_labels_flag_hype_and_availability_without_judging_truth():
    labels = value_lens.article_info_value_labels(
        substance_score=24,
        emotion_score=82,
        source="Example",
        title="Markets panic over alleged breakthrough",
        snippet="Heavy rhetoric with little verifiable detail.",
    )

    assert _codes(labels) == ["suspected_hype", "availability_high"]
    assert all(label["severity"] == "hint" for label in labels)
    assert "提示" in labels[0]["note"]


def test_article_labels_keep_unknown_scores_empty():
    assert value_lens.article_info_value_labels(
        substance_score=-1,
        emotion_score=-1,
        source="Example",
        title="",
        snippet="",
    ) == []


def test_seed_labels_flag_high_delta_and_small_sample():
    item = DiscoveryItem(
        source="hackernews",
        external_id="1",
        title="New infra idea",
        url="https://example.com/seed",
        signal=38,
    )
    scored = ScoredItem(
        item=item,
        is_new=True,
        prev_signal=None,
        delta=38,
        runs_seen=1,
        age_hours=1.0,
    )

    labels = value_lens.seed_info_value_labels(scored)

    assert _codes(labels) == ["availability_high", "small_sample"]
    assert all(label["severity"] == "hint" for label in labels)


def test_narrative_labels_flag_possible_information_cascade():
    labels = value_lens.narrative_info_value_labels(
        {"claim": "ai capex boom", "source_count": 3, "article_count": 4}
    )

    assert labels == [
        {
            "code": "suspected_herding",
            "label": "疑似羊群",
            "note": "多家来源集中复述同一说法，提示可能是信息瀑布，不等于证据增强。",
            "severity": "hint",
        }
    ]
