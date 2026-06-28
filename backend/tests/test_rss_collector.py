from types import SimpleNamespace

from app.collectors import rss


def test_collect_feed_applies_curated_metadata(monkeypatch):
    metadata = {
        "name": "Reuters",
        "url": "https://www.reutersagency.com/feed/",
        "country": "United Kingdom",
        "lang": "en",
        "tier": "wire",
    }

    parsed = SimpleNamespace(
        bozo=False,
        feed={"title": "Fallback Feed Title", "language": "ignored"},
        entries=[
            {
                "link": "https://example.com/story",
                "title": "Iran nuclear talks resume",
                "summary": "A short summary",
            }
        ],
    )

    monkeypatch.setattr(rss.feedparser, "parse", lambda url, agent=None: parsed)

    items = rss.collect_feed(metadata["url"], metadata=metadata)

    assert len(items) == 1
    assert items[0]["source"] == "Reuters"
    assert items[0]["source_lang"] == "en"
    assert items[0]["source_country"] == "United Kingdom"
    assert items[0]["source_tier"] == "wire"
    assert items[0]["collector"] == "rss"
