from app.pipeline import prefilter


def test_normalize_url_removes_tracking_params_and_fragment():
    url = "https://example.com/news/1/?utm_source=x&keep=1&fbclid=abc#section"

    assert prefilter.normalize_url(url) == "https://example.com/news/1?keep=1"


def test_dedup_and_score_filters_known_url_duplicate_title_and_low_relevance():
    incoming = [
        {
            "url": "https://example.com/a?utm_campaign=x",
            "title": "美伊战争 最新进展",
            "snippet": "伊朗和美国局势升级",
        },
        {
            "url": "https://example.com/b",
            "title": "美伊战争最新进展",
            "snippet": "同一标题的转载",
        },
        {
            "url": "https://example.com/c",
            "title": "完全无关的体育新闻",
            "snippet": "比赛结果",
        },
        {
            "url": "https://known.example.com/old",
            "title": "美伊战争 旧报道",
            "snippet": "重复链接",
        },
    ]

    kept = prefilter.dedup_and_score(
        incoming,
        queries=["美伊战争"],
        known_urls={"https://known.example.com/old"},
        known_titles=[],
        min_relevance=0.5,
    )

    assert [item["norm_url"] for item in kept] == ["https://example.com/a"]
    assert kept[0]["relevance"] == 1.0
