"""SQLite 数据模型与连接。

设计要点:
- 文章(Article)全局唯一(按 url)，可同时服务多个主题 -> 不重复采集/富化。
- 主题与文章多对多 (TopicArticle)，每条关联带"该主题下的相关性分"。
- timeline / source_framing / analysis 是 LLM 综合产出 (Phase 1 步骤 5)，
  此处先定义好表结构，采集阶段暂不写入。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel, create_engine

from app import config


class Topic(SQLModel, table=True):
    """一个追踪主题 = 一份会生长的专题档案。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    # 多语种检索词/短语，采集时逐个查询
    queries: list = Field(default_factory=list, sa_column=Column(JSON))
    status: str = "active"          # active / archived
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Article(SQLModel, table=True):
    """单篇报道的元数据 (默认只存标题/摘要/链接，不存全文)。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    title: str = ""
    title_zh: str = ""              # LLM 译文 (富化阶段填充)
    source: str = ""               # 媒体域名/名称
    source_lang: str = ""          # 原文语言
    source_country: str = ""
    published_at: Optional[datetime] = Field(default=None, index=True)
    snippet: str = ""
    snippet_zh: str = ""
    collector: str = ""            # 来源采集器: gdelt / gnews / rss
    enriched: bool = False         # 是否已过 LLM 富化 (缓存键，避免重复花钱)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class TopicArticle(SQLModel, table=True):
    """主题 <-> 文章 关联 (多对多)。富化字段是"主题相关"的，故放这里。"""
    topic_id: int = Field(foreign_key="topic.id", primary_key=True)
    article_id: int = Field(foreign_key="article.id", primary_key=True)
    relevance: float = 0.0         # 该主题下的相关性 [0,1]
    relevant: bool = True          # LLM 是否判定真正相关 (默认 True, 富化后修正)
    stance: str = ""               # 单篇立场标签 (LLM 富化填充)
    stance_summary: str = ""       # 该篇相对主题的一句话立场摘要
    substance_score: int = -1      # 干货密度 0~100 (可证伪事实 vs 空话情绪); -1=未评分
    substance_note: str = ""       # 一句话说明评分依据 (让分数可追溯, 不悬空)
    emotion_score: int = -1        # 情绪操控强度 0~100 (高=煽动/修辞压力重); -1=正文不足未评分
    emotion_note: str = ""         # 一句话说明情绪评分依据 (让分数可追溯, 不悬空)


class Paper(SQLModel, table=True):
    """OpenAlex 学术论文元数据。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    openalex_id: str = Field(unique=True, index=True)
    title: str = ""
    abstract: str = ""
    year: Optional[int] = Field(default=None, index=True)
    cited_by_count: int = 0
    authors: list = Field(default_factory=list, sa_column=Column(JSON))
    venue: str = ""
    concepts: list = Field(default_factory=list, sa_column=Column(JSON))
    url: str = ""
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class PaperCitation(SQLModel, table=True):
    """收敛版引用边: top-N 论文内部互引。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    citing_paper_id: int = Field(foreign_key="paper.id", index=True)
    cited_paper_id: int = Field(foreign_key="paper.id", index=True)


class TopicPaper(SQLModel, table=True):
    """主题 <-> 论文 关联。"""
    topic_id: int = Field(foreign_key="topic.id", primary_key=True)
    paper_id: int = Field(foreign_key="paper.id", primary_key=True)
    relevance: float = 1.0


class SentimentPost(SQLModel, table=True):
    """民间情绪层帖子。Reddit/OpenCLI 是情绪样本，不作为事实源。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", index=True)
    platform: str = "reddit"
    kind: str = "post"
    parent_post_id: str = ""
    subreddit: str = ""
    title: str = ""
    author: str = ""
    score: int = 0
    num_comments: int = 0
    url: str = ""
    created_utc: str = ""
    selftext_snippet: str = ""
    fetched_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CrossSynthesis(SQLModel, table=True):
    """Cross-voice synthesis comparing media, academic, and sentiment layers."""
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", index=True)
    content_md: str = ""
    voices_used: list = Field(default_factory=list, sa_column=Column(JSON))
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CognitionMark(SQLModel, table=True):
    """One-click user cognition marker. Labels are signals, not facts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    target_type: str = Field(index=True)
    target_id: int = Field(default=0, index=True)
    target_key: str = Field(default="", index=True)
    topic_id: Optional[int] = Field(default=None, foreign_key="topic.id", index=True)
    label: str = Field(index=True)
    note: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CognitionProfile(SQLModel, table=True):
    """Local baseline for choosing cognition-boundary seeds."""
    id: Optional[int] = Field(default=None, primary_key=True)
    domain_key: str = Field(unique=True, index=True)
    domain_label: str = ""
    level: str = Field(index=True)
    note: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


# --- 以下为 LLM 综合产出表，Phase 1 步骤 5 才会写入 ---

class TimelineEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", index=True)
    date: Optional[datetime] = None
    title_zh: str = ""
    summary_zh: str = ""
    article_ids: list = Field(default_factory=list, sa_column=Column(JSON))


class SourceFraming(SQLModel, table=True):
    """各家媒体/各方如何报道同一主题 (立场对照)。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", index=True)
    party: str = ""                # 来源/阵营
    stance: str = ""               # 立场标签
    summary_zh: str = ""           # 该方说法摘要
    article_ids: list = Field(default_factory=list, sa_column=Column(JSON))


class Analysis(SQLModel, table=True):
    """批判性综合 (矛盾点 / 信息缺口 / 需警惕的偏差)。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", index=True)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    content_md: str = ""


class SearchJob(SQLModel, table=True):
    """后台搜索任务状态。MVP 阶段用 SQLite 持久化，执行仍由进程内线程完成。"""
    id: str = Field(primary_key=True)
    query: str = Field(index=True)
    status: str = Field(default="queued", index=True)
    steps: list = Field(default_factory=list, sa_column=Column(JSON))
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


engine = create_engine(f"sqlite:///{config.DB_PATH}", echo=False)


def _migrate() -> None:
    """轻量迁移: 给已存在的表补齐新增列 (SQLite 无 IF NOT EXISTS for column)。"""
    adds = {
        "topicarticle": [
            ("relevant", "INTEGER DEFAULT 1"),
            ("stance", "VARCHAR DEFAULT ''"),
            ("stance_summary", "VARCHAR DEFAULT ''"),
            ("substance_score", "INTEGER DEFAULT -1"),
            ("substance_note", "VARCHAR DEFAULT ''"),
            ("emotion_score", "INTEGER DEFAULT -1"),
            ("emotion_note", "VARCHAR DEFAULT ''"),
        ],
        "sentimentpost": [
            ("kind", "VARCHAR DEFAULT 'post'"),
            ("parent_post_id", "VARCHAR DEFAULT ''"),
        ],
        "cognitionmark": [
            ("target_key", "VARCHAR DEFAULT ''"),
            ("note", "VARCHAR DEFAULT ''"),
        ],
    }
    with engine.connect() as conn:
        for table, cols in adds.items():
            existing = {r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, decl in cols:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
        conn.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate()
