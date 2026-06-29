from app.db import Article


def test_article_perspective_api_requires_topic_link(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app import api
    from app.db import Topic, TopicArticle, engine, init_db
    from app.services import article_perspective

    init_db()
    with Session(engine) as session:
        topic = Topic(name="Perspective Topic", queries=["Perspective Topic"])
        other = Topic(name="Other Topic", queries=["Other Topic"])
        article = Article(url="https://example.com/p", title="Title", snippet="Snippet")
        session.add(topic)
        session.add(other)
        session.add(article)
        session.commit()
        session.refresh(topic)
        session.refresh(other)
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.8))
        session.commit()
        topic_id = topic.id
        other_id = other.id
        article_id = article.id

    monkeypatch.setattr(article_perspective, "analyze_article", lambda article: {"article_id": article.id, "mode": "summary", "items": [], "error": "", "source_error": ""})
    client = TestClient(api.app)

    assert client.get(f"/api/topics/{topic_id}/articles/{article_id}/perspective").status_code == 200
    assert client.get(f"/api/topics/{other_id}/articles/{article_id}/perspective").status_code == 404


def test_article_perspective_degrades_without_llm(monkeypatch):
    from app.services import article_perspective

    def fail_chat(*args, **kwargs):
        raise RuntimeError("no key")

    monkeypatch.setattr(article_perspective.llm, "chat", fail_chat)
    result = article_perspective.analyze_article(
        Article(id=1, url="https://example.com/a", title="Title", snippet="Short summary")
    )

    assert result["mode"] == "summary"
    assert result["items"] == []
    assert "no key" in result["error"]


def test_article_perspective_uses_fulltext_when_available(monkeypatch):
    from app.pipeline.fulltext import Extracted
    from app.services import article_perspective

    monkeypatch.setattr(
        article_perspective.fulltext,
        "extract_url",
        lambda url: Extracted(url=url, ok=True, full_text="Full body sentence. Another sentence.", word_count=6),
    )
    monkeypatch.setattr(article_perspective.llm, "chat", lambda *a, **k: '[{"sentence":"Full body sentence.","kind":"substance","reason":"checkable"}]')

    result = article_perspective.analyze_article(
        Article(id=1, url="https://example.com/a", title="Title", snippet="Short summary")
    )

    assert result["mode"] == "fulltext"
    assert result["items"] == [{"sentence": "Full body sentence.", "kind": "substance", "reason": "checkable"}]
    assert result["error"] == ""


def test_article_perspective_falls_back_to_summary_when_fulltext_fails(monkeypatch):
    from app.pipeline.fulltext import Extracted
    from app.services import article_perspective

    monkeypatch.setattr(
        article_perspective.fulltext,
        "extract_url",
        lambda url: Extracted(url=url, ok=False, error="fetch failed"),
    )
    monkeypatch.setattr(article_perspective.llm, "chat", lambda *a, **k: '[{"sentence":"Short summary","kind":"emotion","reason":"loaded wording"}]')

    result = article_perspective.analyze_article(
        Article(id=1, url="https://example.com/a", title="Title", snippet="Short summary")
    )

    assert result["mode"] == "summary"
    assert result["items"][0]["kind"] == "emotion"
    assert result["source_error"] == "fetch failed"
