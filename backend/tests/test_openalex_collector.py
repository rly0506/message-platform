from app.collectors import openalex


def test_reconstruct_abstract_from_inverted_index():
    inverted = {
        "This": [0],
        "deal": [3],
        "nuclear": [2],
        "Iran": [1],
        "matters": [4, 6],
        "because": [5],
    }

    assert openalex.reconstruct_abstract(inverted) == "This Iran nuclear deal matters because matters"


def test_normalize_work_extracts_confirmed_openalex_fields():
    work = {
        "id": "https://openalex.org/W1",
        "title": "The Iran Nuclear Deal",
        "doi": "https://doi.org/10.123/example",
        "publication_year": 2015,
        "cited_by_count": 42,
        "referenced_works": ["https://openalex.org/W2"],
        "abstract_inverted_index": {"Iran": [0], "deal": [1]},
        "authorships": [
            {"author": {"display_name": "Researcher A"}},
            {"author": {"display_name": "Researcher B"}},
        ],
        "concepts": [
            {"display_name": "International relations", "score": 0.95},
            {"display_name": "Nuclear proliferation", "score": 0.88},
        ],
        "primary_location": {
            "source": {"display_name": "Journal of Security Studies"},
            "landing_page_url": "https://doi.org/10.123/example",
        },
    }

    normalized = openalex.normalize_work(work)

    assert normalized["openalex_id"] == "https://openalex.org/W1"
    assert normalized["title"] == "The Iran Nuclear Deal"
    assert normalized["abstract"] == "Iran deal"
    assert normalized["year"] == 2015
    assert normalized["cited_by_count"] == 42
    assert normalized["authors"] == ["Researcher A", "Researcher B"]
    assert normalized["venue"] == "Journal of Security Studies"
    assert normalized["doi"] == "https://doi.org/10.123/example"
    assert normalized["openalex_url"] == "https://openalex.org/W1"
    assert normalized["url"] == "https://doi.org/10.123/example"
    assert normalized["concepts"][0]["name"] == "International relations"
    assert normalized["referenced_works"] == ["https://openalex.org/W2"]


def test_converged_citation_edges_use_only_top_n_internal_references():
    papers = [
        {"openalex_id": "W1", "referenced_works": ["W2", "W9"]},
        {"openalex_id": "W2", "referenced_works": ["W3"]},
        {"openalex_id": "W3", "referenced_works": ["W1", "W404"]},
    ]

    edges = openalex.converged_citation_edges(papers)

    assert edges == [
        {"citing_openalex_id": "W1", "cited_openalex_id": "W2"},
        {"citing_openalex_id": "W2", "cited_openalex_id": "W3"},
        {"citing_openalex_id": "W3", "cited_openalex_id": "W1"},
    ]


def test_search_works_uses_relevance_default_sort_and_api_key(monkeypatch):
    calls = []

    class DummyResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "id": "W1",
                        "title": "Relevant work",
                        "publication_year": 2020,
                        "cited_by_count": 3,
                        "referenced_works": [],
                        "abstract_inverted_index": {"Relevant": [0]},
                        "authorships": [],
                        "concepts": [],
                        "primary_location": {},
                    }
                ]
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            calls.append((url, params))
            return DummyResponse()

    monkeypatch.setattr(openalex.config, "OPENALEX_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(openalex.httpx, "Client", DummyClient)

    papers = openalex.search_works("Iran nuclear deal", top_n=1)

    assert papers[0]["title"] == "Relevant work"
    assert calls[0][0] == "https://api.openalex.org/works"
    assert calls[0][1]["search"] == "Iran nuclear deal"
    assert calls[0][1]["per-page"] == 1
    assert calls[0][1]["api_key"] == "test-key"
    assert "sort" not in calls[0][1]
