# Architecture

## Product Shape

当前产品主线是事件情报分析台。用户输入事件关键词，系统收集多源报道，生成事件时间轴、来源矩阵、证据报道、报道功能分类、关键实体和地点线索。

ChinaNewsMap 是长期地图化表达目标。地图应建立在事件结构化能力稳定之后，而不是当前 MVP 的第一入口。

## Main Data Flow

1. 用户在前端输入事件关键词。
2. 前端调用 `POST /api/search/jobs` 创建后台搜索任务。
3. 后端创建或复用 `Topic`。
4. 后端通过 Google News RSS / GDELT 采集报道。
5. `prefilter` 做 URL 规范化、标题去重和相关性评分。
6. `TopicArticle` 记录专题与报道关系。
7. `local_analyze` 生成事件节点、来源矩阵、报道分类、关键实体、地点线索。
8. API 为事件节点挂载证据报道。
9. 前端展示时间轴、来源矩阵、实体面板和原始报道分组。

## Current Backend Boundaries

- `backend/app/api.py`：FastAPI 路由、任务状态接口、API payload 序列化。
- `backend/app/db.py`：SQLModel 数据模型和轻量迁移。
- `backend/app/topic_ops.py`：专题创建、采集入库、分析持久化桥接。
- `backend/app/collectors/rss.py`：Google News RSS 与普通 RSS 采集。
- `backend/app/collectors/gdelt.py`：GDELT 历史报道采集。
- `backend/app/pipeline/prefilter.py`：去重和相关性初筛。
- `backend/app/pipeline/local_analyze.py`：无 LLM 的本地规则分析。
- `backend/app/rule_config.py` 与 `backend/config/rule_config.json`：媒体层级、实体别名、停用词等规则配置。
- `backend/app/schemas/`：API 与分析 payload 的类型边界。

## Current Frontend Boundaries

- `frontend/src/App.vue`：事件工作台页面编排、状态派生和主要 UI。
- `frontend/src/api/dossierApi.ts`：后端 API client。
- `frontend/src/types/dossier.ts`：前端共享 DTO 类型。
- `frontend/src/style.css`：当前页面样式。
- `frontend/tests/e2e/source-matrix.spec.ts`：来源矩阵和原始报道分组的 Playwright 验证。

## Target Boundaries

- API routes stay thin.
- Services coordinate business flows.
- Repositories isolate SQLModel queries.
- Pipeline modules stay pure and testable.
- Frontend API/types/composables/components are split by responsibility.

## Known Limits

- 当前搜索任务执行仍是 SQLite 状态记录 + 进程内线程，不是生产级任务队列。
- 事件理解基于标题、摘要、来源、时间和链接，不是全文事实核查。
- GitNexus FTS/BM25 在当前 Windows 环境不可用，keyword query 会降级；符号级 `context`、`status`、`check` 仍可用。
