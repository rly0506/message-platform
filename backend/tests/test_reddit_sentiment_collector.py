import subprocess
from datetime import datetime

import pytest
from sqlmodel import Session, select


def test_search_reddit_parses_opencli_yaml(monkeypatch):
    from app.collectors import reddit_sentiment

    sample_yaml = """
- id: abc123
  title: US Iran tensions are escalating
  subreddit: worldnews
  author: observer42
  score: 128
  comments: 37
  url: https://reddit.com/r/worldnews/comments/abc123/test
  created_utc: 1760000000
  selftext: |
    People are mostly arguing from vibes here, but one useful comment links tanker data.
"""
    calls = []

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=sample_yaml, stderr="")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)
    monkeypatch.setattr(reddit_sentiment.config, "OPENCLI_COMMAND", "D:\\npm-global\\opencli")

    posts = reddit_sentiment.search_reddit("US Iran war", limit=25)

    assert calls == [["D:\\npm-global\\opencli", "reddit", "search", "US Iran war", "-f", "yaml"]]
    assert posts == [
        {
            "platform": "reddit",
            "kind": "post",
            "id": "abc123",
            "parent_post_id": "",
            "subreddit": "worldnews",
            "title": "US Iran tensions are escalating",
            "author": "observer42",
            "score": 128,
            "num_comments": 37,
            "url": "https://reddit.com/r/worldnews/comments/abc123/test",
            "created_utc": "1760000000",
            "selftext_snippet": "People are mostly arguing from vibes here, but one useful comment links tanker data.",
        }
    ]


def test_chinese_platform_collectors_parse_opencli_yaml(monkeypatch):
    from app.collectors import reddit_sentiment

    samples = {
        "bilibili": """
- id: bv123
  title: 美伊局势讲解
  author: 军事观察员
  score: 4200
  comments: 310
  url: https://www.bilibili.com/video/BV123
  created_utc: 1760000001
  desc: 从能源和军事部署看这次冲突。
""",
        "xiaohongshu": """
- id: xhs123
  title: 美伊冲突会影响留学吗
  author: 小红薯用户
  likes: 88
  comments: 19
  url: https://www.xiaohongshu.com/explore/xhs123
  created_at: 2026-06-27
  content: 评论区多数是在问旅行和签证风险。
""",
        "xueqiu": """
- id: xq123
  title: 油价和军工怎么看
  author: 雪球用户
  likes: 128
  comment_count: 42
  url: https://xueqiu.com/status/xq123
  created_at: 2026-06-27
  text: 市场更关心油价和避险资产。
""",
    }
    calls = []

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=samples[cmd[1]], stderr="")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)
    monkeypatch.setattr(reddit_sentiment.config, "OPENCLI_COMMAND", "D:\\npm-global\\opencli.cmd")

    posts = reddit_sentiment.search_chinese_platforms("美伊战争", limit=5)

    assert calls == [
        ["D:\\npm-global\\opencli.cmd", "bilibili", "search", "美伊战争", "-f", "yaml"],
        ["D:\\npm-global\\opencli.cmd", "xiaohongshu", "search", "美伊战争", "-f", "yaml"],
        ["D:\\npm-global\\opencli.cmd", "xueqiu", "search", "美伊战争", "-f", "yaml"],
    ]
    assert [post["platform"] for post in posts] == ["bilibili", "xiaohongshu", "xueqiu"]
    assert posts[0]["subreddit"] == "bilibili"
    assert posts[0]["score"] == 4200
    assert posts[0]["num_comments"] == 310
    assert posts[0]["selftext_snippet"] == "从能源和军事部署看这次冲突。"
    assert posts[1]["title"] == "美伊冲突会影响留学吗"
    assert posts[1]["score"] == 88
    assert posts[2]["num_comments"] == 42


def test_search_all_platforms_degrades_when_one_platform_fails(monkeypatch):
    from app.collectors import reddit_sentiment

    sample_yaml = """
- id: ok1
  title: 中文平台样本
  author: user
  score: 9
  comments: 2
  url: https://example.com/ok1
"""
    calls = []

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        calls.append(cmd)
        if cmd[1] == "xiaohongshu":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="AUTH_REQUIRED")
        return subprocess.CompletedProcess(cmd, 0, stdout=sample_yaml, stderr="")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    result = reddit_sentiment.search_all_platforms(
        reddit_query="US Iran war",
        chinese_query="美伊战争",
        hackernews=False,
        limit=5,
        platforms=("reddit", "bilibili", "xiaohongshu", "xueqiu"),
        comment_post_limit=0,
    )

    assert [post["platform"] for post in result["posts"]] == ["reddit", "bilibili", "xueqiu"]
    assert len(result["errors"]) == 1
    assert result["errors"][0]["platform"] == "xiaohongshu"
    assert "AUTH_REQUIRED" in result["errors"][0]["error"]
    assert calls[0] == ["opencli", "reddit", "search", "US Iran war", "-f", "yaml"]
    assert calls[1] == ["opencli", "bilibili", "search", "美伊战争", "-f", "yaml"]


def test_search_all_platforms_fetches_limited_comments(monkeypatch):
    from app.collectors import reddit_sentiment

    search_yaml = """
- id: abc123
  title: Reddit post
  subreddit: worldnews
  score: 20
  comments: 3
  url: https://reddit.com/r/worldnews/comments/abc123/test
- id: def456
  title: Reddit post 2
  subreddit: worldnews
  score: 10
  comments: 2
  url: https://reddit.com/r/worldnews/comments/def456/test
"""
    read_yaml = """
comments:
  - id: c1
    author: commenter
    score: 42
    body: This is a highly upvoted comment.
    created_utc: 1760000100
  - id: c2
    author: commenter2
    score: 9
    text: Second comment.
    created_utc: 1760000200
"""
    calls = []

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        calls.append(cmd)
        if cmd[2] == "search":
            return subprocess.CompletedProcess(cmd, 0, stdout=search_yaml, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=read_yaml, stderr="")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    result = reddit_sentiment.search_all_platforms(
        reddit_query="US Iran war",
        chinese_query="美伊战争",
        hackernews=False,
        limit=5,
        platforms=("reddit",),
        comment_post_limit=1,
        comments_per_post=1,
    )

    assert [cmd for cmd in calls if cmd[2] == "read"] == [["opencli", "reddit", "read", "abc123", "-f", "yaml"]]
    assert [item["kind"] for item in result["posts"]] == ["post", "post", "comment"]
    comment = result["posts"][2]
    assert comment["platform"] == "reddit"
    assert comment["parent_post_id"] == "abc123"
    assert comment["title"] == "This is a highly upvoted comment."
    assert comment["score"] == 42


def test_comment_fetch_failure_keeps_parent_post(monkeypatch):
    from app.collectors import reddit_sentiment

    search_yaml = """
- id: bv123
  title: B站视频
  author: up
  score: 30
  comments: 8
  url: https://www.bilibili.com/video/BV123
"""
    calls = []

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        calls.append(cmd)
        if cmd[2] == "search":
            return subprocess.CompletedProcess(cmd, 0, stdout=search_yaml, stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="COMMENT_API_DOWN")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    result = reddit_sentiment.search_all_platforms(
        reddit_query="US Iran war",
        chinese_query="美伊战争",
        hackernews=False,
        limit=5,
        platforms=("bilibili",),
        comment_post_limit=5,
        comments_per_post=10,
    )

    assert [item["kind"] for item in result["posts"]] == ["post"]
    assert result["posts"][0]["id"] == "bv123"
    assert result["errors"][0]["platform"] == "bilibili"
    assert "COMMENT_API_DOWN" in result["errors"][0]["error"]


def test_comment_command_unavailable_degrades_to_posts_only(monkeypatch):
    from app.collectors import reddit_sentiment

    search_yaml = """
- id: xhs123
  title: 小红书笔记
  author: user
  likes: 9
  comments: 2
  url: https://www.xiaohongshu.com/explore/xhs123
"""

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        if cmd[2] == "search":
            return subprocess.CompletedProcess(cmd, 0, stdout=search_yaml, stderr="")
        raise FileNotFoundError("opencli")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    result = reddit_sentiment.search_all_platforms(
        reddit_query="US Iran war",
        chinese_query="美伊战争",
        hackernews=False,
        limit=5,
        platforms=("xiaohongshu",),
        comment_post_limit=5,
        comments_per_post=10,
    )

    assert [item["kind"] for item in result["posts"]] == ["post"]
    assert result["posts"][0]["id"] == "xhs123"
    assert result["errors"][0]["platform"] == "xiaohongshu"
    assert "OpenCLI is not available" in result["errors"][0]["error"]


def test_comment_fetch_respects_top_k_limit(monkeypatch):
    from app.collectors import reddit_sentiment

    search_yaml = "\n".join(
        [
            f"- id: p{i}\n  title: Post {i}\n  score: {100 - i}\n  comments: 10\n  url: https://example.com/p{i}"
            for i in range(7)
        ]
    )
    comment_yaml = """
- id: c
  author: user
  score: 1
  body: comment
"""
    calls = []

    def fake_run(cmd, capture_output, text, encoding, errors, timeout, check):
        calls.append(cmd)
        if cmd[2] == "search":
            return subprocess.CompletedProcess(cmd, 0, stdout=search_yaml, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=comment_yaml, stderr="")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    reddit_sentiment.search_all_platforms(
        reddit_query="US Iran war",
        chinese_query="美伊战争",
        hackernews=False,
        limit=7,
        platforms=("reddit",),
        comment_post_limit=5,
        comments_per_post=10,
    )

    read_calls = [cmd for cmd in calls if cmd[2] == "read"]
    assert len(read_calls) == 5
    assert [cmd[3] for cmd in read_calls] == ["p0", "p1", "p2", "p3", "p4"]


def test_search_reddit_reports_opencli_unavailable(monkeypatch):
    from app.collectors import reddit_sentiment

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("opencli")

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    with pytest.raises(reddit_sentiment.RedditSentimentError, match="OpenCLI is not available"):
        reddit_sentiment.search_reddit("US Iran war", limit=5)


def test_search_reddit_reports_opencli_timeout(monkeypatch):
    from app.collectors import reddit_sentiment

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["opencli"], timeout=30)

    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fake_run)

    with pytest.raises(reddit_sentiment.RedditSentimentError, match="timed out"):
        reddit_sentiment.search_reddit("US Iran war", limit=5)


def test_sentiment_post_table_round_trips_in_isolated_db():
    from app.db import SentimentPost, engine, init_db

    init_db()
    created = datetime(2026, 6, 27, 12, 0, 0)
    with Session(engine) as session:
        row = SentimentPost(
            topic_id=10,
            platform="reddit",
            subreddit="worldnews",
            title="US Iran thread",
            author="observer42",
            score=128,
            num_comments=37,
            url="https://reddit.com/r/worldnews/comments/abc123/test",
            created_utc="1760000000",
            selftext_snippet="Mostly vibes, one useful signal.",
            fetched_at=created,
        )
        session.add(row)
        session.commit()

    with Session(engine) as session:
        rows = session.exec(select(SentimentPost).where(SentimentPost.topic_id == 10)).all()

    assert len(rows) == 1
    assert rows[0].platform == "reddit"
    assert rows[0].subreddit == "worldnews"
    assert rows[0].score == 128
