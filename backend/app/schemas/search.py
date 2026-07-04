from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    collect: bool = True
    gdelt: bool = False
    years: int = Field(default=1, ge=1, le=10)
    min_relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    decompose: bool = True  # LLM 把宏观主题拆成子线索 (下钻) + 历史先例; 无 LLM 自动退回原行为


class DeepAnalysisRequest(BaseModel):
    enrich_limit: int = Field(default=30, ge=0, le=200)


class AcademicAnalysisRequest(BaseModel):
    top_n: int = Field(default=30, ge=1, le=50)


class SentimentAnalysisRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)


class CrossSynthesisRequest(BaseModel):
    # False(默认): 只用已落库的三声部合成, 不重跑(避免刷新单板块后重复消耗 LLM)。
    # True: 用户显式请求全刷新时, 先重跑媒体/学界/民间三声部再合成。
    refresh_voices: bool = False


class DiscoveryDistillRequest(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    domain: str = Field(default="", max_length=40)


class CognitionMarkRequest(BaseModel):
    target_type: Literal["topic", "article", "event", "seed"]
    target_id: int = Field(default=0, ge=0)
    target_key: str = Field(default="", max_length=500)
    label: Literal["known", "unexpected", "doubtful", "unfamiliar"]
    topic_id: int | None = Field(default=None, ge=1)
    note: str = Field(default="", max_length=300)


class SearchStep(BaseModel):
    key: str
    label: str
    status: str


class CollectionRequestStats(BaseModel):
    id: str
    collector: str
    query: str
    raw_count: int
    kept_count: int
    status: str
    error: str = ""
    source_id: int | None = None
    source_name: str = ""
    source_type: str = ""
    quality_tier: str = ""


class CollectionTimeSpan(BaseModel):
    start: str | None = None
    end: str | None = None


class CollectionStats(BaseModel):
    raw: int = 0
    kept: int = 0
    new_articles: int = 0
    new_links: int = 0
    source_count: int = 0
    collector_counts: dict[str, int] = {}
    time_span: CollectionTimeSpan = CollectionTimeSpan()
    requests: list[CollectionRequestStats] = []
    errors: list[str] = []


class SearchJobPayload(BaseModel):
    id: str
    query: str
    status: str
    steps: list[dict[str, str]]
    created_at: str | None
    updated_at: str | None
    result: dict[str, Any] | None
    error: str
