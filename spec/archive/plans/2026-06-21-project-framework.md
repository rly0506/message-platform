# Project Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前可运行的事件情报分析 MVP 收敛成清晰、可扩展、可测试的项目框架，为后续 Phase 1-5 持续开发建立稳定边界。

**Architecture:** 当前系统已经跑通“搜索任务 -> 新闻采集 -> 去重入库 -> 本地规则分析 -> 前端时间轴/来源矩阵”的主链路，但后端 API、任务编排、分析返回结构和前端工作台仍集中在少数大文件中。框架化目标不是重写业务，而是把现有能力按边界拆成 service、schema、analysis、frontend api、composable、component 和 docs，让每次迭代有明确落点。

**Tech Stack:** FastAPI, SQLModel, SQLite, pytest, Vue 3, TypeScript, Vite, Playwright, GitNexus, Superpowers.

---

## 0. Tool-Assisted Review Record

本计划基于 Superpowers 的 `writing-plans` 工作流和 GitNexus 索引结果。

GitNexus 当前索引状态：

```text
Repository: D:\意向项目
Indexed: 2026-06-21 20:07
Status: up-to-date
Stats: 39 files, 630 symbols, 1293 edges, 30 clusters, 54 flows
Structural cycles: 0
```

GitNexus 关键发现：

- 后端搜索主链路集中在 `backend/app/api.py::_run_search`。
- 采集与入库集中在 `backend/app/topic_ops.py::collect_topic`。
- 主题分析桥接集中在 `backend/app/topic_ops.py::analyze_topic`。
- 本地规则分析集中在 `backend/app/pipeline/local_analyze.py::analyze_topic`。
- 前端工作台集中在 `frontend/src/App.vue::runEventSearch` 和 `frontend/src/App.vue::finishSearchJob`。
- GitNexus keyword query 受 FTS 扩展缺失影响较大，但 `context`、`check --cycles`、索引状态和符号级浏览可用。

当前主要框架问题：

- `backend/app/api.py` 同时承担路由、任务编排、搜索服务、序列化、证据挂载、任务状态管理。
- `backend/app/topic_ops.py` 同时承担查询扩展、采集、诊断统计、数据库写入、分析持久化。
- `backend/app/pipeline/local_analyze.py` 是核心规则引擎，但输出结构没有正式 schema。
- `frontend/src/App.vue` 同时承担类型定义、API 调用、任务轮询、状态派生、工作台布局、来源矩阵、报道分组和实体展示。
- README 仍停留在早期状态，和当前事件情报分析台不完全一致。

---

## Target Framework

### Backend Target Shape

```text
backend/app/
  api.py                         # FastAPI app wiring only
  schemas/
    search.py                    # SearchRequest/SearchJobResponse/CollectStats
    analysis.py                  # LocalEvent/SourceMatrix/EvidenceArticle DTO
  services/
    search_service.py            # run/enqueue/rerun/search job orchestration
    topic_service.py             # topic summary, article listing, local events
    collection_service.py        # collection diagnostics and source execution
  repositories/
    topic_repository.py          # SQLModel query helpers
    search_job_repository.py     # SearchJob persistence helpers
  pipeline/
    local_analyze.py             # pure local analysis rules
    prefilter.py                 # relevance and dedup
  config/
    rule_config.json             # current combined rule config
```

### Frontend Target Shape

```text
frontend/src/
  App.vue                        # page composition only
  api/
    dossierApi.ts                # axios client and typed endpoints
  types/
    dossier.ts                   # shared frontend DTOs
  composables/
    useSearchJob.ts              # submit, poll, rerun
    useTopicData.ts              # topics/detail/articles/local events loading
    useEventWorkbench.ts         # derived selected event, matrix, article groups
  components/
    SearchPanel.vue
    EventTimeline.vue
    EventDetail.vue
    SourceMatrix.vue
    ArticleGroups.vue
    EntityPanel.vue
    StancePanel.vue
```

### Documentation Target Shape

```text
docs/
  architecture.md                # system data flow and module boundaries
  decision-log.md                # dated product/technical decisions
  operations.md                  # run, test, install, known tool limitations
  superpowers/plans/
    2026-06-21-project-framework.md
```

---

## Task 1: Backend Schema Boundary

**Files:**

- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/search.py`
- Create: `backend/app/schemas/analysis.py`
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_api_helpers.py`

- [ ] **Step 1: Create schema package**

Create `backend/app/schemas/__init__.py`:

```python
"""Typed API payload shapes used by the FastAPI surface."""
```

- [ ] **Step 2: Extract search request and job DTOs**

Create `backend/app/schemas/search.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    collect: bool = True
    gdelt: bool = False
    years: int = Field(default=1, ge=1, le=10)
    min_relevance: float = Field(default=0.0, ge=0.0, le=1.0)


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
```

- [ ] **Step 3: Extract analysis DTO documentation types**

Create `backend/app/schemas/analysis.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EvidenceArticlePayload(BaseModel):
    id: int
    url: str
    title: str
    source: str
    published_at: str | None
    snippet: str
    collector: str
    relevance: float
    stance: str
    category: str
    category_reason: str


class SourceMatrixPayload(BaseModel):
    source: str
    tier: str
    tier_label: str
    article_count: int
    first_published_at: str | None
    latest_published_at: str | None
    dominant_stance: str
    stance_counts: dict[str, int]
    dominant_category: str
    category_counts: dict[str, int]
    representative_title: str
    article_ids: list[int]


class LocalEventPayload(BaseModel):
    date: str | None
    title_zh: str
    summary_zh: str
    article_ids: list[int]
    score: float
    importance_label: str
    coverage_label: str
    selection_basis: list[str]
    source_count: int
    article_count: int
    sources: list[dict[str, Any]]
    source_matrix: list[SourceMatrixPayload]
    source_tiers: list[dict[str, Any]]
    category: str
    category_reason: str
    stance: str
    score_breakdown: dict[str, Any]
    evidence: dict[str, Any]
    keywords: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    location_signals: list[dict[str, Any]]
    evidence_articles: list[EvidenceArticlePayload] = []
```

- [ ] **Step 4: Update API imports**

Modify `backend/app/api.py`:

```python
from app.schemas.search import SearchRequest
```

Remove the existing local `SearchRequest` class and unused `BaseModel, Field` import.

- [ ] **Step 5: Run backend tests**

Run:

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
```

Expected:

```text
16 passed
```

- [ ] **Step 6: Re-index GitNexus**

Run:

```powershell
gitnexus analyze
gitnexus status
```

Expected:

```text
Repository indexed successfully
Status: up-to-date
```

---

## Task 2: Backend Service Boundary

**Files:**

- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/search_service.py`
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_api_helpers.py`

- [x] **Step 1: Run GitNexus impact before moving search functions**

Run:

```powershell
gitnexus impact _run_search
gitnexus impact _enqueue_search_job
gitnexus impact _run_search_job
```

Expected:

```text
Impact result includes callers search_and_collect/create_search_job/get_search_job/rerun_search_job.
No HIGH or CRITICAL warning should be ignored.
```

- [x] **Step 2: Create service package**

Create `backend/app/services/__init__.py`:

```python
"""Application services that coordinate API requests, persistence, and pipelines."""
```

- [x] **Step 3: Move search orchestration into service**

Create `backend/app/services/search_service.py` with the current search job orchestration functions from `backend/app/api.py`:

```python
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Thread
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app import topic_ops
from app.db import Article, SearchJob, Topic, TopicArticle, engine, init_db
from app.pipeline import local_analyze
from app.schemas.search import SearchRequest

MAX_SEARCH_JOBS = 50


def enqueue_search_job(payload: SearchRequest) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        job = SearchJob(
            id=job_id,
            query=payload.query.strip(),
            status="queued",
            steps=search_steps(payload.collect),
            payload=request_payload(payload),
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=run_search_job, args=(job_id, payload), daemon=True).start()
    return job_snapshot(job_id)
```

Continue by moving the existing implementations of:

- `_run_search`
- `_run_search_job`
- `_search_steps`
- `_set_step`
- `_sync_job_steps`
- `_update_job`
- `_job_snapshot`
- `_trim_search_jobs`
- `_mark_interrupted_search_jobs`
- `_interrupted_steps`
- `_search_job_payload`
- `_request_payload`
- `_search_request_from_job`

Rename them without leading underscores where they are called by `api.py`:

```python
run_search
run_search_job
search_steps
set_step
sync_job_steps
update_job
job_snapshot
trim_search_jobs
mark_interrupted_search_jobs
interrupted_steps
search_job_payload
request_payload
search_request_from_job
```

Keep helper functions private when they are only used inside `search_service.py`.

- [x] **Step 4: Update API route handlers**

Modify `backend/app/api.py`:

```python
from app.services import search_service
from app.schemas.search import SearchRequest
```

Route handlers should become thin:

```python
@app.post("/api/search")
def search_and_collect(payload: SearchRequest) -> dict[str, Any]:
    return search_service.run_search(payload)


@app.post("/api/search/jobs")
def create_search_job(payload: SearchRequest) -> dict[str, Any]:
    return search_service.enqueue_search_job(payload)


@app.get("/api/search/jobs/{job_id}")
def get_search_job(job_id: str) -> dict[str, Any]:
    return search_service.job_snapshot(job_id)
```

Update startup:

```python
@app.on_event("startup")
def on_startup() -> None:
    init_db()
    search_service.mark_interrupted_search_jobs()
```

- [x] **Step 5: Preserve tests by importing service functions**

Modify `backend/tests/test_api_helpers.py` where it directly calls search helper functions.

Replace:

```python
from app import api
```

with:

```python
from app import api
from app.services import search_service
```

Replace calls:

```python
api._search_steps(True)
api._set_step(...)
api._job_snapshot(...)
api._mark_interrupted_search_jobs(...)
api._search_request_from_job(...)
```

with:

```python
search_service.search_steps(True)
search_service.set_step(...)
search_service.job_snapshot(...)
search_service.mark_interrupted_search_jobs(...)
search_service.search_request_from_job(...)
```

- [x] **Step 6: Run tests and GitNexus change detection**

Run:

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
gitnexus detect-changes
gitnexus analyze
```

Expected:

```text
Backend tests pass.
GitNexus reports affected symbols in API/search service only.
Repository re-indexes successfully.
```

Execution note:

- Created `backend/app/services/search_service.py` for search execution, background jobs, step updates, job snapshots, reruns, interruption marking, and job trimming.
- Created `backend/app/services/payloads.py` so `api.py` and `search_service.py` can share topic summaries, evidence article payloads, event evidence attachment, and date serialization without a circular import.
- `backend/app/api.py` now delegates search routes to `search_service` and topic/article payload shaping to `payloads`.
- `gitnexus detect-changes` still reports `No changes detected` because the repository has no tracked baseline, but `gitnexus analyze`, `gitnexus status`, and `gitnexus check --cycles --json` passed.

---

## Task 3: Frontend Type and API Boundary

**Files:**

- Create: `frontend/src/types/dossier.ts`
- Create: `frontend/src/api/dossierApi.ts`
- Modify: `frontend/src/App.vue`
- Test: `frontend/tests/e2e/source-matrix.spec.ts`

- [ ] **Step 1: Create shared frontend types**

Create `frontend/src/types/dossier.ts` by moving the current TypeScript types from `frontend/src/App.vue`:

```ts
export type TopicSummary = {
  id: number
  name: string
  description: string
  queries: string[]
  status: string
  article_count: number
  source_count: number
  enriched_count: number
  relevant_count: number
  latest_published_at: string | null
}
```

Continue moving all current `type` definitions:

- `TopicDetail`
- `Article`
- `TimelineEvent`
- `SourceFraming`
- `Analysis`
- `ScoreBreakdown`
- `Keyword`
- `EntityGroup`
- `Criterion`
- `EvidenceArticle`
- `SourceMatrixItem`
- `LocalEvent`
- `StanceEvolution`
- `LocalEventsPayload`
- `SearchResponse`
- `SearchJob`

- [ ] **Step 2: Create API client**

Create `frontend/src/api/dossierApi.ts`:

```ts
import axios from 'axios'
import type {
  Article,
  LocalEventsPayload,
  SearchJob,
  TopicDetail,
  TopicSummary,
} from '../types/dossier'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export async function fetchTopics() {
  const res = await axios.get<TopicSummary[]>(`${API_BASE}/api/topics`)
  return res.data
}

export async function fetchTopic(id: number) {
  const res = await axios.get<TopicDetail>(`${API_BASE}/api/topics/${id}`)
  return res.data
}

export async function fetchArticles(id: number, limit: number) {
  const res = await axios.get<{ total: number; items: Article[] }>(
    `${API_BASE}/api/topics/${id}/articles`,
    { params: { limit } },
  )
  return res.data
}

export async function fetchLocalEvents(id: number) {
  const res = await axios.get<LocalEventsPayload>(`${API_BASE}/api/topics/${id}/local-events`)
  return res.data
}

export async function createSearchJob(query: string) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/search/jobs`, {
    query,
    collect: true,
    gdelt: false,
    min_relevance: 0,
  })
  return res.data
}

export async function fetchSearchJob(jobId: string) {
  const res = await axios.get<SearchJob>(`${API_BASE}/api/search/jobs/${jobId}`)
  return res.data
}

export async function rerunSearchJob(jobId: string) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/search/jobs/${jobId}/rerun`)
  return res.data
}

export function isNetworkError(err: unknown) {
  return axios.isAxiosError(err) && err.code === 'ERR_NETWORK'
}

export function errorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message
  }
  return err instanceof Error ? err.message : '未知错误'
}
```

- [ ] **Step 3: Update App imports**

Modify `frontend/src/App.vue`:

```ts
import {
  createSearchJob,
  errorMessage,
  fetchArticles,
  fetchLocalEvents,
  fetchSearchJob,
  fetchTopic,
  fetchTopics,
  isNetworkError,
  rerunSearchJob,
} from './api/dossierApi'

import type {
  Article,
  EntityGroup,
  EvidenceArticle,
  Keyword,
  LocalEvent,
  LocalEventsPayload,
  SearchJob,
  SearchResponse,
  SourceFraming,
  SourceMatrixItem,
  StanceEvolution,
  TopicDetail,
  TopicSummary,
} from './types/dossier'
```

Remove local type definitions and direct `axios` import from `App.vue`.

- [ ] **Step 4: Replace direct axios calls**

Replace:

```ts
const res = await axios.get<TopicSummary[]>(`${API_BASE}/api/topics`)
topics.value = res.data
```

with:

```ts
const data = await fetchTopics()
topics.value = data
```

Apply the same pattern for topic, articles, local events, create search job, get search job, rerun search job.

- [ ] **Step 5: Update readableError**

Replace `readableError` body with:

```ts
function readableError(err: unknown) {
  if (isNetworkError(err)) {
    return '无法连接到后端服务'
  }
  return errorMessage(err)
}
```

- [ ] **Step 6: Verify frontend**

Run:

```powershell
cd frontend
npm run build
npm run test:e2e
```

Expected:

```text
build passes
6 passed
```

---

## Task 4: Frontend Component Boundary

**Files:**

- Create: `frontend/src/components/SearchPanel.vue`
- Create: `frontend/src/components/SourceMatrix.vue`
- Create: `frontend/src/components/ArticleGroups.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/tests/e2e/source-matrix.spec.ts`

- [ ] **Step 1: Extract SearchPanel props and emits**

Create `frontend/src/components/SearchPanel.vue`:

```vue
<script setup lang="ts">
import type { SearchJob, SearchResponse } from '../types/dossier'

defineProps<{
  eventSearch: string
  searching: boolean
  activeJobId: string
  searchMessage: string
  searchWarnings: string[]
  searchSteps: { key: string; label: string; status: string }[]
  terminalJob: SearchJob | null
  collectDiagnostics: SearchResponse['collect'] | null
  stepStatusText: (status: string) => string
  canRerunJob: (job: SearchJob | null) => boolean
  collectSummary: (collect: SearchResponse['collect'] | null) => string
}>()

defineEmits<{
  'update:eventSearch': [value: string]
  search: []
  rerun: []
}>()
</script>
```

Move the current search panel template from `App.vue` into this component.

- [ ] **Step 2: Extract SourceMatrix**

Create `frontend/src/components/SourceMatrix.vue` with props:

```ts
defineProps<{
  sources: SourceMatrixItem[]
  visibleSources: SourceMatrixItem[]
  sourceTierOptions: { key: string; label: string }[]
  sourceTierFilter: string
  sourceMatrixSort: string
  fmtDate: (value: string | null, withTime?: boolean) => string
}>()
```

Emits:

```ts
defineEmits<{
  'update:sourceTierFilter': [value: string]
  'update:sourceMatrixSort': [value: string]
  authority: []
  earliest: []
  covered: []
}>()
```

Move only the source matrix block from `App.vue`.

- [ ] **Step 3: Extract ArticleGroups**

Create `frontend/src/components/ArticleGroups.vue` with props:

```ts
defineProps<{
  showArticles: boolean
  totalArticles: number
  articleLoading: boolean
  filteredCount: number
  stanceGroups: { name: string; count: number }[]
  articleCategoryGroups: { category: string; items: Article[] }[]
  visibleArticleGroups: { category: string; items: Article[] }[]
  articleCategoryOptions: { key: string; label: string }[]
  articleCategoryFilter: string
  fmtDate: (value: string | null, withTime?: boolean) => string
  percent: (value: number) => string
  titleFor: (article: Article) => string
  snippetFor: (article: Article) => string
}>()
```

Move the original reports block from `App.vue`.

- [ ] **Step 4: Keep App.vue as page composition**

After extraction, `App.vue` should retain:

- refs and computed state
- API calls
- top-level layout
- component composition
- formatting helper functions

`App.vue` should no longer own the full markup for search panel, source matrix, and article groups.

- [ ] **Step 5: Run frontend verification**

Run:

```powershell
cd frontend
npm run build
npm run test:e2e
```

Expected:

```text
build passes
6 passed
```

---

## Task 5: Documentation Framework

**Files:**

- Create: `docs/architecture.md`
- Create: `docs/decision-log.md`
- Create: `docs/operations.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`

- [ ] **Step 1: Create architecture document**

Create `docs/architecture.md`:

```markdown
# Architecture

## Product Shape

当前产品主线是事件情报分析台。ChinaNewsMap 是长期地图化表达目标。

## Main Data Flow

1. 用户在前端输入事件关键词。
2. 前端调用 `POST /api/search/jobs` 创建搜索任务。
3. 后端创建或复用 `Topic`。
4. 后端通过 Google News RSS / GDELT 采集报道。
5. `prefilter` 做 URL 规范化、标题去重和相关性评分。
6. `TopicArticle` 记录专题与报道关系。
7. `local_analyze` 生成事件节点、来源矩阵、报道分类、关键实体、地点线索。
8. API 为事件节点挂载证据报道。
9. 前端展示时间轴、来源矩阵、实体面板和原始报道分组。

## Current Boundaries

- `backend/app/api.py`：HTTP route and payload serialization.
- `backend/app/topic_ops.py`：topic collection and analysis bridge.
- `backend/app/pipeline/local_analyze.py`：local no-LLM analysis rules.
- `backend/config/rule_config.json`：media/entity/stopword rules.
- `frontend/src/App.vue`：current event workbench page.

## Target Boundaries

- API routes stay thin.
- Services coordinate business flows.
- Repositories isolate SQLModel queries.
- Pipeline modules stay pure and testable.
- Frontend API/types/composables/components are split by responsibility.
```

- [ ] **Step 2: Create decision log**

Create `docs/decision-log.md`:

```markdown
# Decision Log

## 2026-06-21: Current Product Is Event Intelligence Workbench

Decision: Treat the current MVP as an event intelligence workbench, not a map-first product.

Reason: The strongest user need is understanding event evolution across many sources. Map visualization is useful after event structure becomes reliable.

## 2026-06-21: Core Path Must Not Depend On LLM Quota

Decision: Search, collection, local analysis, timeline, source matrix, entity grouping, and evidence display must run without paid model calls.

Reason: The project should remain usable when model quota is unavailable.

## 2026-06-21: Evidence Before Conclusion

Decision: Each event node should expose sources, evidence articles, first sources, source tiers, and selection basis.

Reason: News analysis without traceable evidence is not trustworthy enough for this project.

## 2026-06-21: GitNexus Is Used For Framework Navigation

Decision: Use GitNexus status/context/impact/detect-changes while refactoring framework boundaries.

Reason: The project is beginning to split large files; symbol impact and graph checks reduce accidental breakage.
```

- [ ] **Step 3: Create operations document**

Create `docs/operations.md`:

```markdown
# Operations

## Backend

```powershell
uvicorn app.api:app --app-dir backend --reload
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm run build
npm run test:e2e
```

## GitNexus

```powershell
gitnexus status
gitnexus analyze
gitnexus doctor
gitnexus check --cycles --json
```

Known limitation: FTS/BM25 search may be unavailable on this Windows environment. Use `gitnexus context <symbol>` and `gitnexus check --cycles --json` when query results are degraded.

## Installed Agent Tools

- Agent Reach skill: `C:\Users\任锂帅\.agents\skills\agent-reach`
- GitNexus skills: `C:\Users\任锂帅\.agents\skills\gitnexus-*`
- Superpowers plugin: `C:\Users\任锂帅\.codex\plugins\cache\openai-api-curated\superpowers`
```

- [ ] **Step 4: Update backend README**

Modify `backend/README.md` to say:

```markdown
# Dossier Intelligence Workbench Backend

后端提供事件搜索、新闻采集、去重入库、本地规则分析、搜索任务状态和事件证据 API。

当前核心入口：

- `POST /api/search/jobs`
- `GET /api/search/jobs/{job_id}`
- `POST /api/search/jobs/{job_id}/rerun`
- `GET /api/topics/{topic_id}/local-events`
```

- [ ] **Step 5: Update frontend README**

Modify `frontend/README.md` to say:

```markdown
# Dossier Intelligence Workbench Frontend

Vue 3 + TypeScript + Vite 前端，用于事件关键词搜索、搜索任务轮询、事件时间轴、来源矩阵、关键实体和原始报道分组展示。

```powershell
npm install
npm run dev
npm run build
npm run test:e2e
```
```

- [ ] **Step 6: Verify docs paths**

Run:

```powershell
rg -n "Event Intelligence|事件情报|GitNexus|Superpowers|POST /api/search/jobs" docs backend/README.md frontend/README.md
```

Expected:

```text
Matches in architecture, decision-log, operations, backend README, frontend README.
```

---

## Task 6: GitNexus Framework Workflow

**Files:**

- Modify: `.gitignore`
- Modify: `docs/operations.md`

- [ ] **Step 1: Decide whether GitNexus index stays in repo**

Current GitNexus generated:

```text
.gitnexus/
AGENTS.md
CLAUDE.md
.claude/
```

Recommended policy:

- Keep `AGENTS.md` and `CLAUDE.md` if the project will rely on GitNexus agent instructions.
- Keep `.claude/skills/gitnexus/` only if Claude Code compatibility matters.
- Ignore heavyweight index cache if it should not be committed.

- [ ] **Step 2: Ignore heavy GitNexus cache if needed**

If the repo should not commit local graph binaries, add to `.gitignore`:

```gitignore
.gitnexus/lbug
.gitnexus/parse-cache/
.gitnexus/parsedfile-cache/
```

Do not ignore `.gitnexus/run.cjs` if you want a stable local runner.

- [ ] **Step 3: Add GitNexus pre-refactor habit to operations**

Append to `docs/operations.md`:

```markdown
## GitNexus Refactor Workflow

Before editing a function/class/method:

```powershell
gitnexus impact <symbol>
```

After refactor:

```powershell
gitnexus detect-changes
gitnexus analyze
gitnexus check --cycles --json
```
```

- [ ] **Step 4: Run verification**

Run:

```powershell
gitnexus status
gitnexus check --cycles --json
```

Expected:

```text
Status: up-to-date
cycleCount: 0
```

---

## Task 7: Final Verification Gate

**Files:**

- No code changes expected.

- [ ] **Step 1: Backend tests**

Run:

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 2: Frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected:

```text
vite build succeeds.
```

- [ ] **Step 3: Frontend e2e**

Run:

```powershell
cd frontend
npm run test:e2e
```

Expected:

```text
All Playwright tests pass on desktop and mobile projects.
```

- [ ] **Step 4: GitNexus graph check**

Run:

```powershell
gitnexus analyze
gitnexus check --cycles --json
gitnexus status
```

Expected:

```text
Repository indexed successfully.
cycleCount: 0.
Status: up-to-date.
```

- [ ] **Step 5: Update project roadmap**

Modify `# 🇨🇳 ChinaNewsMap - 中国新闻地图平台.md` and add a short execution record:

```markdown
## 16. Framework Construction Plan（2026-06-21）

已使用 Superpowers `writing-plans` 和 GitNexus 索引结果生成项目框架计划：

- 后端目标：schema / service / repository / pipeline 边界清晰化。
- 前端目标：types / api / composables / components 拆分。
- 文档目标：architecture / decision-log / operations 三件套。
- GitNexus 工作流：改函数前看 impact，改完跑 detect-changes、analyze、check。

计划文件：`docs/superpowers/plans/2026-06-21-project-framework.md`
```

---

## Self-Review

Spec coverage:

- 使用 Superpowers 重新审视项目代码：已按 `writing-plans` 输出可执行计划。
- 使用 GitNexus 构建项目框架：已基于 GitNexus 索引、context、check 结果建立后端/前端/文档目标框架。
- 保留当前 MVP 能力：计划以拆边界为主，不要求重写主链路。
- 可验证：每个任务都包含测试或 GitNexus 验证命令。

Known constraints:

- GitNexus FTS/BM25 当前不可用，所以 keyword query 结果降级；本计划使用 `context`、`status`、`check --cycles` 和符号扫描补足。
- 计划中涉及函数搬移的任务必须在执行时先跑 `gitnexus impact`。
- 目前不建议立即做地图 UI，先完成框架拆分和文档边界。
