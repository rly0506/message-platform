from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import SearchJob, SentimentPost, Topic, engine, init_db
from app.services import search_service


def test_rank_posts_sorts_by_score_descending():
    from app.pipeline import sentiment

    posts = [
        {"id": "low", "score": 3, "num_comments": 100},
        {"id": "high", "score": 42, "num_comments": 2},
        {"id": "mid", "score": 15, "num_comments": 10},
    ]

    assert [post["id"] for post in sentiment.rank_posts(posts)] == ["high", "mid", "low"]


def test_summarize_sentiment_prompt_frames_reddit_as_suspect_corner(monkeypatch):
    from app.pipeline import sentiment

    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        captured["system"] = system
        return "## 民间情绪\n高赞不是事实，只有少量上游观察值得追踪。"

    monkeypatch.setattr(sentiment.llm, "chat", fake_chat)
    topic = Topic(id=10, name="美伊战争")
    posts = [
        {
            "platform": "reddit",
            "subreddit": "worldnews",
            "title": "US Iran war thread",
            "author": "observer42",
            "score": 128,
            "num_comments": 37,
            "url": "https://reddit.com/r/worldnews/comments/abc123/test",
            "created_utc": "1760000000",
            "selftext_snippet": "Mostly vibes, but one useful tanker note.",
        }
    ]

    summary = sentiment.summarize_sentiment(topic, posts)

    assert "高赞不是事实" in summary
    assert "最该被批判怀疑的一角" in captured["prompt"]
    assert "不要把高赞当事实" in captured["prompt"]
    assert "情绪/站队/看热闹" in captured["prompt"]
    assert "聪明的、上游的民间观察" in captured["prompt"]


def test_summarize_sentiment_prompt_groups_multiple_platforms_and_warns_about_filters(monkeypatch):
    from app.pipeline import sentiment

    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        captured["system"] = system
        return "## 多平台民间情绪\n平台滤镜不同，高赞不等于事实。"

    monkeypatch.setattr(sentiment.llm, "chat", fake_chat)
    topic = Topic(id=10, name="美伊战争")
    posts = [
        {"platform": "reddit", "subreddit": "worldnews", "title": "US Iran thread", "score": 12, "num_comments": 3},
        {"platform": "bilibili", "subreddit": "bilibili", "title": "B站讲解", "score": 30, "num_comments": 8},
        {"platform": "xiaohongshu", "subreddit": "xiaohongshu", "title": "小红书留学讨论", "score": 9, "num_comments": 2},
        {"platform": "xueqiu", "subreddit": "xueqiu", "title": "雪球油价讨论", "score": 18, "num_comments": 6},
    ]

    sentiment.summarize_sentiment(topic, posts)

    assert "按平台分组" in captured["prompt"]
    assert "B站偏年轻科技" in captured["prompt"]
    assert "小红书偏消费" in captured["prompt"]
    assert "雪球偏金融" in captured["prompt"]
    assert "不能跨平台直接当共识" in captured["prompt"]
    assert "'bilibili'" in captured["prompt"]
    assert "'xiaohongshu'" in captured["prompt"]
    assert "'xueqiu'" in captured["prompt"]


def test_summarize_sentiment_prompt_nests_comments_under_parent_posts(monkeypatch):
    from app.pipeline import sentiment

    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        return "summary"

    monkeypatch.setattr(sentiment.llm, "chat", fake_chat)
    topic = Topic(id=10, name="美伊战争")
    posts = [
        {
            "platform": "reddit",
            "kind": "post",
            "id": "abc123",
            "subreddit": "worldnews",
            "title": "Parent post",
            "score": 100,
            "num_comments": 20,
        },
        {
            "platform": "reddit",
            "kind": "comment",
            "id": "c1",
            "parent_post_id": "abc123",
            "subreddit": "worldnews",
            "title": "High-value comment",
            "score": 42,
            "num_comments": 0,
        },
    ]

    sentiment.summarize_sentiment(topic, posts)

    assert "高赞评论" in captured["prompt"]
    assert "parent_post_id" in captured["prompt"]
    assert "High-value comment" in captured["prompt"]


def test_run_sentiment_analysis_job_fetches_summarizes_and_persists(monkeypatch):
    from app.pipeline import academic
    from app.collectors import reddit_sentiment
    from app.pipeline import sentiment

    topic_id = _seed_topic(name="美伊战争")
    monkeypatch.setattr(academic, "academic_search_query", lambda name: "US Iran war")
    monkeypatch.setattr(
        reddit_sentiment,
        "search_all_platforms",
        lambda reddit_query, chinese_query, limit=25: {
            "posts": [
                {
                    "platform": "reddit",
                    "id": "abc123",
                    "subreddit": "worldnews",
                    "title": "US Iran war thread",
                    "author": "observer42",
                    "score": 128,
                    "num_comments": 37,
                    "url": "https://reddit.com/r/worldnews/comments/abc123/test",
                    "created_utc": "1760000000",
                    "selftext_snippet": "Mostly vibes, one useful tanker note.",
                },
                {
                    "platform": "bilibili",
                    "id": "bv123",
                    "subreddit": "bilibili",
                    "title": "中文平台样本",
                    "author": "up",
                    "score": 88,
                    "num_comments": 11,
                    "url": "https://www.bilibili.com/video/BV123",
                    "created_utc": "1760000001",
                    "selftext_snippet": "中文查询结果。",
                },
            ],
            "errors": [],
            "queries": {"reddit": reddit_query, "chinese": chinese_query},
        },
    )
    monkeypatch.setattr(sentiment, "summarize_sentiment", lambda topic, posts: "## 民间情绪\n高赞不等于事实。")

    job = SearchJob(
        id="sentiment-job",
        query="sentiment:美伊战争",
        status="queued",
        steps=search_service.sentiment_analysis_steps(),
        payload={"topic_id": topic_id, "limit": 25, "kind": "sentiment_analysis"},
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()

    search_service.run_sentiment_analysis_job("sentiment-job", topic_id, 25)

    with Session(engine) as session:
        saved_job = session.get(SearchJob, "sentiment-job")
        posts = session.exec(select(SentimentPost).where(SentimentPost.topic_id == topic_id)).all()

    assert saved_job.status == "done"
    assert saved_job.result["query"] == "US Iran war"
    assert saved_job.result["queries"] == {"reddit": "US Iran war", "chinese": "美伊战争"}
    assert saved_job.result["summary_md"].startswith("## 民间情绪")
    assert len(posts) == 2
    assert posts[0].subreddit == "worldnews"
    assert posts[1].platform == "bilibili"


def test_sentiment_api_endpoints_use_background_job_and_return_payload(monkeypatch):
    topic_id = _seed_topic(name="Sentiment API Topic")
    started = []

    class DummyThread:
        def __init__(self, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started.append((self.target, self.args, self.daemon))

    monkeypatch.setattr(search_service, "Thread", DummyThread)
    client = TestClient(api.app)

    response = client.post(f"/api/topics/{topic_id}/sentiment/jobs", json={"limit": 12})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert [step["key"] for step in body["steps"]] == ["fetch", "summarize", "persist"]
    assert started == [(search_service.run_sentiment_analysis_job, (body["id"], topic_id, 12), True)]

    with Session(engine) as session:
        session.add(
            SentimentPost(
                topic_id=topic_id,
                platform="reddit",
                subreddit="worldnews",
                title="Thread title",
                author="observer42",
                score=9,
                num_comments=3,
                url="https://reddit.com/thread",
                created_utc="1760000000",
                selftext_snippet="A noisy comment.",
            )
        )
        session.add(
            SearchJob(
                id="sentiment-summary",
                query="sentiment:Sentiment API Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "sentiment_analysis"},
                result={"summary_md": "latest sentiment summary"},
                created_at=datetime(2026, 1, 1, 10, 0, 0),
                updated_at=datetime(2026, 1, 1, 10, 5, 0),
            )
        )
        session.commit()

    payload = client.get(f"/api/topics/{topic_id}/sentiment").json()

    assert payload["topic_id"] == topic_id
    assert payload["warning"].startswith("多平台民间情绪")
    assert payload["summary_md"] == "latest sentiment summary"
    assert payload["posts"][0]["title"] == "Thread title"


def test_sentiment_view_returns_latest_sentiment_job_summary():
    topic_id = _seed_topic(name="Sentiment Summary Topic")
    older = datetime(2026, 1, 1, 10, 0, 0)
    newer = older + timedelta(minutes=5)

    with Session(engine) as session:
        session.add(
            SearchJob(
                id="sentiment-old",
                query="sentiment:Sentiment Summary Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "sentiment_analysis"},
                result={"summary_md": "old sentiment"},
                created_at=older,
                updated_at=older,
            )
        )
        session.add(
            SearchJob(
                id="sentiment-new",
                query="sentiment:Sentiment Summary Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "sentiment_analysis"},
                result={"summary_md": "new sentiment"},
                created_at=newer,
                updated_at=newer,
            )
        )
        session.commit()

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/sentiment").json()

    assert payload["summary_md"] == "new sentiment"


def _seed_topic(name: str = "Sentiment Topic") -> int:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, description="民间情绪测试", queries=[name])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        return topic.id
