from app.collectors import searxng


def test_collect_searxng_normalizes_json_results(monkeypatch):
    class DummyClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, path, params):
            assert path == "/search"
            assert params["q"] == "OpenAI"
            assert params["format"] == "json"
            assert params["categories"] == "news"

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "results": [
                            {
                                "url": "https://example.com/story",
                                "title": "OpenAI story",
                                "content": "publisher summary",
                                "engine": "google news",
                            },
                            {"url": "", "title": "missing url"},
                        ]
                    }

            return Response()

    monkeypatch.setattr(searxng.httpx, "Client", DummyClient)
    monkeypatch.setattr(searxng.config, "SEARXNG_URL", "http://localhost:8080")

    items = searxng.collect("OpenAI")

    assert items == [
        {
            "url": "https://example.com/story",
            "title": "OpenAI story",
            "source": "example.com",
            "source_lang": "",
            "source_country": "",
            "source_tier": "",
            "published_at": None,
            "snippet": "publisher summary",
            "collector": "searxng",
            "engine": "google news",
        }
    ]


def test_collect_searxng_degrades_on_network_error(monkeypatch):
    class BoomClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, path, params):
            raise RuntimeError("service down")

    monkeypatch.setattr(searxng.httpx, "Client", BoomClient)

    try:
        searxng.collect("OpenAI")
    except searxng.SearxngError as exc:
        assert "service down" in str(exc)
    else:
        raise AssertionError("expected SearxngError")
