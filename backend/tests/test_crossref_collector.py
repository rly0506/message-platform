from app.collectors import crossref


def test_normalize_work_extracts_confirmed_crossref_fields():
    work = {
        "DOI": "10.1234/ABC.DEF",
        "title": ["Academic metadata from Crossref"],
        "abstract": "<jats:p>Crossref abstract.</jats:p>",
        "issued": {"date-parts": [[2021, 5, 1]]},
        "author": [
            {"given": "Ada", "family": "Scholar"},
            {"given": "Bo", "family": "Researcher"},
        ],
        "container-title": ["Journal of Metadata"],
        "publisher": "Fallback Publisher",
        "URL": "https://example.com/work",
    }

    normalized = crossref.normalize_work(work)

    assert normalized["openalex_id"] == "crossref:10.1234/abc.def"
    assert normalized["title"] == "Academic metadata from Crossref"
    assert normalized["abstract"] == "Crossref abstract."
    assert normalized["year"] == 2021
    assert normalized["cited_by_count"] == 0
    assert normalized["authors"] == ["Ada Scholar", "Bo Researcher"]
    assert normalized["venue"] == "Journal of Metadata"
    assert normalized["doi"] == "https://doi.org/10.1234/abc.def"
    assert normalized["url"] == "https://doi.org/10.1234/abc.def"
    assert normalized["sources"] == ["crossref"]
    assert normalized["source_count"] == 1
    assert normalized["source_links"] == [
        {"source": "crossref", "url": "https://api.crossref.org/works/10.1234%2Fabc.def"}
    ]


def test_search_works_uses_bibliographic_query_rows_and_user_agent(monkeypatch):
    calls = []

    class DummyResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/example",
                            "title": ["Relevant Crossref work"],
                            "issued": {"date-parts": [[2020]]},
                            "author": [],
                            "container-title": [],
                        }
                    ]
                }
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            calls.append(("init", args, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            calls.append(("get", url, params))
            return DummyResponse()

    monkeypatch.setattr(crossref.httpx, "Client", DummyClient)

    papers = crossref.search_works("Russia Ukraine war", top_n=3)

    assert papers[0]["title"] == "Relevant Crossref work"
    init_call = calls[0]
    assert init_call[0] == "init"
    assert init_call[2]["timeout"] == 20
    assert "User-Agent" in init_call[2]["headers"]
    assert "mailto:research@example.com" not in init_call[2]["headers"]["User-Agent"]
    get_call = calls[1]
    assert get_call == (
        "get",
        "https://api.crossref.org/works",
        {"query.bibliographic": "Russia Ukraine war", "rows": 3},
    )


def test_search_works_retries_429_before_returning_results(monkeypatch):
    responses = []
    sleep_calls = []

    class RateLimitedResponse:
        status_code = 429

        def raise_for_status(self):
            raise AssertionError("429 should retry before raise_for_status")

    class SuccessResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/retry",
                            "title": ["Retry success"],
                            "issued": {"date-parts": [[2022]]},
                        }
                    ]
                }
            }

    responses.extend([RateLimitedResponse(), SuccessResponse()])

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            return responses.pop(0)

    monkeypatch.setattr(crossref.httpx, "Client", DummyClient)
    monkeypatch.setattr(crossref.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    papers = crossref.search_works("retry topic", top_n=1)

    assert papers[0]["title"] == "Retry success"
    assert sleep_calls == [2]


def test_search_works_caps_rows_to_crossref_limit(monkeypatch):
    calls = []

    class DummyResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"items": []}}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            calls.append(params)
            return DummyResponse()

    monkeypatch.setattr(crossref.httpx, "Client", DummyClient)

    assert crossref.search_works("large request", top_n=999) == []
    assert calls[0]["rows"] == 100
