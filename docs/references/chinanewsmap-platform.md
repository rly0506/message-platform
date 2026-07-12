# ChinaNewsMap / Dossier Intelligence 项目路径规划

最后更新：2026-06-28

## 1. 项目重新定位

本项目最初设想是 **ChinaNewsMap：中国新闻地图平台**，核心界面是地图，目标是让用户按地理位置浏览新闻热点。

经过近期开发和讨论后，项目的真实主线已经演进为：

> **事件情报分析台**：用户输入一个事件关键词，系统自动收集多源报道，整理事件时间轴、关键节点、来源矩阵、证据报道、关键人物与机构，帮助用户理解同一事件在不同媒体中的发展脉络。

因此，当前阶段不应急于回到地图。更合理的路径是：

1. 先把“事件搜索 → 多源采集 → 本地分析 → 时间轴 → 来源证据 → 关键实体”这条主链路做稳。
2. 再把已经结构化的事件投射到地图上，形成真正有信息密度的 ChinaNewsMap。
3. 最后再考虑 AI 摘要、观点对比、事实核查、长期监控等增强能力。

## 2. 当前产品定义

当前 MVP 的产品名可以暂定为：

- 中文名：事件情报分析台
- 英文名：Dossier Intelligence Workbench
- 长期品牌：ChinaNewsMap

三者关系：

| 名称 | 当前定位 |
| --- | --- |
| 事件情报分析台 | 当前 MVP，聚焦事件理解和多源报道分析 |
| Dossier Intelligence Workbench | 当前产品的英文/技术名 |
| ChinaNewsMap | 长期愿景，未来在事件结构化能力稳定后回归地图化表达 |

## 3. 核心用户问题

项目要解决的问题不是“把新闻堆出来”，而是帮助用户回答：

- 这件事最早是谁报道的？
- 哪些媒体跟进了？
- 事件经过了哪些关键阶段？
- 哪些报道是关键节点，为什么它们关键？
- 不同来源关注的是起因、经过、影响、责任、回应，还是后续处置？
- 事件中的关键人物、机构、地点和概念是什么？
- 当前结果有哪些证据支撑，又有哪些不能被系统确认？

## 4. 当前已完成能力

> 说明：本节描述截至 2026-06-28 的真实代码状态。项目已从单一"媒体"分析，扩展为**三方对照情报台**：同一事件同时从 **媒体 / 学界 / 民间** 三个声音采集、分析，再做交叉综合。核心链路在无 LLM 时仍可运行；LLM 仅作增强。06-21 之后的逐项进展见第 21 节。

### 4.1 后端能力

当前后端位于 `backend/`，FastAPI 入口 `backend/app/api.py`，SQLite 存储 `backend/app/db.py`。

实际 API 端点（17 个）：

- 基础：`GET /api/health`、`GET /api/topics`、`GET /api/topics/{id}`、`GET /api/topics/{id}/articles`
- 媒体分析：`GET /api/topics/{id}/local-events`（本地规则时间轴 + 关键节点）、`GET /api/topics/{id}/country-compare`（多国对比）
- 学界：`GET /api/topics/{id}/academic`
- 民间：`GET /api/topics/{id}/sentiment`
- 三方对照：`GET /api/topics/{id}/cross-synthesis`
- 同步搜索：`POST /api/search`
- 后台任务（统一经 `JobRunner` 生命周期）：`POST /api/search/jobs`、`POST /api/topics/{id}/deep-analysis/jobs`、`POST /api/topics/{id}/academic/jobs`、`POST /api/topics/{id}/sentiment/jobs`、`POST /api/topics/{id}/cross-synthesis/jobs`、`POST /api/search/jobs/{id}/rerun`、`GET /api/search/jobs/{id}`

采集层 `backend/app/collectors/`：

- `gnews` Google News RSS、`rss.py`（11 个策展源，带 country/lang/tier 元数据，见 `backend/config/feeds.json`）
- `gdelt.py`（多国对比数据，当前 IP 被 429 封）
- `openalex.py`（学术论文，2026-02 起需 API key，relevance 排序）
- `reddit_sentiment.py`（多平台民间声音：B站 / 小红书 / 雪球 / Reddit，经 OpenCLI 驱动真实 Chrome 采集，含帖子 + 评论）

分析管线 `backend/app/pipeline/`（本地规则为主）：

- `local_analyze.py`（门面，183 行）入口 `analyze_topic()`，内部已拆分为：`clustering.py`（聚类/标题清洗/jaccard）、`scoring.py`（事件装配/评分/来源矩阵/分析）、`entities.py`（关键词/实体/spaCy/jieba 分组）、`categorization.py`（立场/报道功能分类）
- `academic.py`（CJK→英文查询翻译、摘要重建、引用收敛图、学界综合）
- `sentiment.py`（民间情绪分析）
- `cross_synthesis.py`（三方对照：共识/矛盾/各自盲区/机制重建/批判提示）
- `enrich.py` / `synthesize.py`（LLM 增强层）

服务层 `backend/app/services/`：`search_service.py`（`JobRunner` 统一 5 类任务生命周期）、`payloads.py`（序列化）、`country_compare.py`（按国家归类报道）。

LLM 层 `backend/app/llm.py`：双协议（OpenAI-compatible / Anthropic-compatible），当前走 Pixel API（`ai-pixel.online`），`HAIKU_MODEL=gpt-5.4-mini`、`SYNTH_MODEL=gpt-5.4`。

特性：搜索任务持久化 `SearchJob`；服务重启将遗留 `queued/running` 标记为 `interrupted`，可重跑；事件节点带 `evidence_articles`、`source_matrix`、`importance_label`、`coverage_label`、`location_signals`；规则配置外置 `backend/config/rule_config.json`。

### 4.2 前端能力

当前前端位于 `frontend/`（Vue 3 + TS + Vite，`App.vue` 639 行，已从 2057 行拆薄）。

工作台按 Tab 分为 5 个面板（`frontend/src/components/`，组件只收 props/发 emits，不自拉数据）：

- `MediaPanel.vue`：事件时间轴、关键节点详情、证据报道、来源矩阵（层级筛选/排序/快捷按钮）、关键实体分组、原始报道折叠分组、多国对比视图
- `AcademicPanel.vue`：学界论文、引用收敛图、学界综合
- `SentimentPanel.vue`：民间多平台帖子 + 评论
- `CrossPanel.vue`：三方对照综合（共识/矛盾/盲区/机制/批判）
- `LlmPanel.vue`：LLM 深度分析

数据获取集中在 composable（`useTopicData.ts` / `useJobRunner.ts` / `useEventWorkbench.ts`）：搜索提交、任务轮询、状态/失败/中断展示、重跑入口、markdown 渲染（marked + DOMPurify 统一封装）。

### 4.3 测试与验证

- 后端 pytest 回归（含 `test_local_analyze_golden.py` 黄金快照，保护 `analyze_topic` 输出逐字段不变）
- 前端生产构建验证
- Playwright 端到端测试
- 来源矩阵桌面端/移动端基础检查

常用验证命令（注意：必须用项目虚拟环境的 Python，系统 Python 没装 pytest）：

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm run build
npm run test:e2e
```

## 5. 当前限制与技术债

### 5.1 数据采集限制

- 采集主要依赖 Google News RSS / GDELT，可用性会受网络、地区和源质量影响。
- 当前结果更适合作为“事件导航”和“线索整理”，不能视为完整新闻库。
- 目前没有稳定的全文抓取、正文清洗、网页正文抽取和反爬处理。
- 没有真正的引用网络，所谓“扩散/引用”仍是来源数、报道数和时间分布的近似判断。

### 5.2 事件理解限制

- 时间线基于标题、摘要、来源、发布时间和链接生成，不等同于全文事实核查。
- 事件聚类仍可能误合并相似标题，也可能拆散同一事件。
- 关键节点评分是本地启发式评分，不是真实概率，也不是权威性证明。
- 实体识别依赖词典、别名、规则和分词后备，不是严格 NER。
- 新事件中的关键人物、机构和概念需要持续补充规则配置。

### 5.3 产品体验限制

- 时间轴仍需要更明确地表达阶段、证据来源和节点原因。
- 来源矩阵需要更强的快速筛选，例如“只看权威来源”“只看首发来源”“只看影响分析”。
- 原始报道流如果全部展开，会造成阅读负担，应默认折叠并按类别聚合。
- 当前还没有地图视图，ChinaNewsMap 的原始地图愿景尚未落地。

### 5.4 工程限制

- 当前后台任务是进程内线程 + SQLite 状态记录，适合 MVP，不适合作为长期生产队列。
- 服务重启后可以标记中断和重跑，但尚不能自动断点恢复。
- 规则配置已外置，但仍是单个 JSON 文件，后续应拆分为多份配置。
- 缺少配置管理页面，非开发者维护实体别名和媒体层级仍不方便。

## 6. 关键产品原则

### 6.1 不依赖付费模型额度

核心链路必须在无 LLM 的情况下可运行：

- 搜索
- 采集
- 去重
- 本地规则分析
- 时间轴
- 来源矩阵
- 实体分组
- 证据报道

LLM 可以作为后续增强，但不能成为项目继续推进的前置条件。

### 6.2 每个判断都要能回到来源

前端展示的关键节点、阶段、来源矩阵、人物机构和事件分类，都应该尽量能追溯到：

- 哪几篇报道支撑了这个判断
- 报道来自哪些来源
- 来源首次出现时间
- 系统为什么认为这个节点重要

### 6.3 明确“系统能做什么”和“不能做什么”

当前系统可以做：

- 多源报道收集
- 标题/摘要级别的事件整理
- 来源层级和报道分布展示
- 初步时间线和关键实体导航

当前系统不能声称已经完成：

- 全文事实核查
- 报道真假判定
- 媒体偏见定量证明
- 完整引用链复原
- 官方级事件定性

## 7. 报道分类体系建议

用户希望把报道按“起因、影响、发起”等类别归类。建议采用更稳定的事件报道功能分类：

| 类别 | 含义 | 示例问题 |
| --- | --- | --- |
| 起因背景 | 解释事件为什么发生 | 历史矛盾、政策背景、冲突源头是什么？ |
| 触发事件 | 直接引爆本轮事件的动作 | 哪个袭击、声明、制裁、判决或事故成为导火索？ |
| 行动进展 | 事件正在发生的事实推进 | 谁采取了什么行动？战事、谈判、调查、救援进展如何？ |
| 各方回应 | 当事方、政府、组织、公众表态 | 谁回应了？态度是否变化？ |
| 影响后果 | 事件造成的政治、经济、社会、安全影响 | 市场、能源、外交、民生受到什么影响？ |
| 分析解读 | 媒体、专家、评论员给出的解释 | 他们如何判断未来走势？ |
| 核实澄清 | 辟谣、修正、事实核查、信息更新 | 哪些说法被否认、修正或补充？ |
| 后续处置 | 调查、制裁、谈判、审判、重建等后续动作 | 事件之后如何处理？ |

近期应优先实现前 6 类；“核实澄清”和“后续处置”可以作为第二轮增强。

## 8. 总体阶段路线图

### Phase 0：项目收敛与文档统一

目标：让项目方向、文档、代码状态保持一致。

已基本完成：

- 确认当前 MVP 是事件情报分析台，而不是地图平台。
- 保留 ChinaNewsMap 作为长期愿景。
- 将旧文档重写为路径规划。
- 明确当前能力、限制、阶段路线和验收标准。

后续补充：

- 为 `backend/`、`frontend/` 各补一份轻量 README。
- 增加一份 `docs/architecture.md`，记录数据流和模块职责。
- 增加一份 `docs/decision-log.md`，记录关键产品决策。

验收标准：

- 新加入项目的人能在 10 分钟内理解当前产品方向。
- 文档不再把地图 MVP 和事件情报 MVP 混在一起。
- 每个阶段都有明确目标和可验证产物。

### Phase 1：数据采集质量提升

目标：让搜索结果更稳定、更少噪声、更可解释。

建议任务：

- 优化查询扩展：
  - 中文关键词
  - 英文关键词
  - 别名
  - 相关人物/地点/组织
- 增加采集源健康检查。
- 在搜索任务中展示逐源采集结果：
  - 哪个源成功
  - 哪个源失败
  - 每个源返回多少条
  - 被过滤多少条
- 强化去重：
  - 标题规范化
  - 来源规范化
  - URL 规范化
  - 同一聚合页面与原始页面合并
- 增加采集质量指标：
  - 总报道数
  - 有效报道数
  - 来源数量
  - 时间跨度
  - 权威来源数量

验收标准：

- 用户搜索“美伊战争”一类事件时，可以看到采集过程和来源覆盖情况。
- 结果中明显无关内容减少。
- 系统能解释“为什么这次搜索结果少/失败/来源不足”。

### Phase 2：事件理解质量提升

目标：让时间轴、关键节点、关键人物和报道分类真正可读。

建议任务：

- 把事件节点百分数改成更清晰的标签：
  - 关键性：高 / 中 / 低
  - 来源覆盖：多少来源、多少报道
  - 权威来源：有 / 无
  - 首发/早期报道：是 / 否
- 每个节点明确显示：
  - 主要来源
  - 首批来源
  - 证据报道
  - 评分原因
  - 所属阶段
  - 报道功能分类
- 引入报道功能分类：
  - 起因背景
  - 触发事件
  - 行动进展
  - 各方回应
  - 影响后果
  - 分析解读
- 改造关键实体展示：
  - 不再使用难读的自由词云作为主视图。
  - 以人物、组织、地点、关键概念分组展示为主。
  - 可以保留一个辅助“实体热度图”，但必须过滤无意义碎片词。
- 优化实体规则：
  - 增补事件相关人物、机构、地点和概念别名。
  - 对短碎片词、半截词、泛化词做强过滤。
  - 对人名、机构名给予更高展示优先级。

验收标准：

- 时间轴每个节点都能回答“为什么它重要”。
- 用户可以清楚看到节点来源，而不是只看到抽象百分数。
- “特朗普、哈梅内伊、伊斯兰革命卫队”等关键实体能优先出现。
- “界影响、影响几、响深远”这类无意义词不会进入主展示区。

### Phase 3：多源对比视图增强

目标：让用户能比较不同媒体如何报道同一事件。

建议任务：

- 来源矩阵增加快捷按钮：
  - 只看权威来源
  - 只看首见来源
  - 按首见时间排序
  - 按报道数量排序
  - 按媒体层级筛选
- 报道列表默认折叠：
  - 按来源折叠
  - 按报道功能分类折叠
  - 按时间段折叠
- 增加“同一节点下不同来源说了什么”对比：
  - 标题
  - 来源
  - 发布时间
  - 摘要
  - 报道分类
  - 原文链接
- 增加来源说明：
  - 通讯社
  - 官方来源
  - 专业媒体
  - 主流媒体
  - 聚合源
  - 其他来源

验收标准：

- 用户不需要展开几十条报道，也能理解各来源覆盖情况。
- 每个来源分类都有明确说明。
- 来源矩阵在桌面和移动端都不溢出。

### Phase 4：任务队列与工程生产化

目标：让系统可以长期运行，而不是只适合本地演示。

建议任务：

- 将进程内线程替换为更可靠的任务执行方式：
  - APScheduler
  - RQ
  - Celery
  - Dramatiq
- 支持任务自动恢复或明确失败重试策略。
- 增加任务取消。
- 增加任务历史列表。
- 增加日志与错误详情。
- 增加 API 参数校验和错误码规范。
- 增加数据库迁移方案。
- 增加环境变量示例文件。

验收标准：

- 后端重启不会让用户误以为任务仍在运行。
- 失败任务可以被诊断和重试。
- 用户不需要依赖命令行才能理解任务状态。

### Phase 5：地图化回归

目标：在事件结构化能力稳定后，回到 ChinaNewsMap 的地图愿景。

建议任务：

- 为文章和事件增加地点抽取：
  - 国家
  - 地区
  - 城市
  - 关键地点
- 增加地点消歧：
  - 同名城市
  - 新闻来源地 vs 事件发生地
  - 涉及地点 vs 核心地点
- 前端增加地图视图：
  - 事件地点标记
  - 地区热度
  - 时间轴播放
  - 从地图进入事件详情
- 优先使用合规和稳定的地图方案：
  - 中国视角：高德地图 / 天地图 / ECharts 中国地图
  - 全球视角：后续单独评估

验收标准：

- 用户可以从地图看到事件发生地和影响范围。
- 用户可以从地图进入事件时间轴和来源矩阵。
- 地图不是装饰，而是基于已结构化事件数据的空间入口。

### Phase 6：AI 增强

目标：在本地规则链路稳定后，用 AI 提升理解质量，但不让 AI 成为项目运行前提。

可选增强：

- 事件摘要
- 时间轴节点合并建议
- 报道功能分类复核
- 人物关系抽取
- 来源差异总结
- 多语言报道对齐
- 矛盾说法提示

原则：

- 无模型额度时系统仍可运行。
- AI 输出必须能回到证据报道。
- AI 只能作为辅助解释，不直接替代来源证据。

验收标准：

- 关闭 AI 后核心功能不受影响。
- 开启 AI 后，结果更易读，但不会失去可追溯性。

## 9. 近期执行优先级

建议下一阶段不要同时做太多方向，优先按以下顺序推进：

1. 前端时间轴改造
   - 去掉让人困惑的百分数主表达。
   - 明确显示关键性、来源覆盖、权威来源、首见来源。
   - 每个节点展示来源和证据入口。

2. 报道功能分类
   - 后端为文章/节点增加分类字段。
   - 前端按分类折叠展示报道。
   - 先用本地规则实现，不依赖 LLM。

3. 关键实体展示重做
   - 主视图使用分组实体列表。
   - 辅助视图可做实体热度条或紧凑标签云。
   - 强过滤无意义碎片词。

4. 来源矩阵快捷筛选
   - 只看权威来源。
   - 只看首见来源。
   - 按报道数量排序。
   - 按首见时间排序。

5. 采集过程可解释
   - 搜索任务步骤展示逐源状态。
   - 明确失败原因和结果数量。

## 10. 前端呈现建议

### 10.1 页面主结构

建议前端以“事件工作台”组织，而不是传统新闻列表：

```text
顶部：搜索栏 + 当前任务状态

左侧/上方：事件概览
- 事件名称
- 时间跨度
- 报道数
- 来源数
- 关键人物/机构/地点

主区域：事件时间轴
- 阶段分段
- 关键节点
- 节点证据

侧栏/下方：来源矩阵
- 来源层级
- 首见时间
- 报道数量
- 主导报道分类

折叠区：原始报道流
- 按分类/来源/时间折叠
```

### 10.2 关键实体呈现

不建议把“词云图”作为主表达。词云容易出现碎片词，也不利于用户判断实体关系。

建议使用：

- 主视图：分组实体面板
  - 人物
  - 组织
  - 地点
  - 关键概念
- 辅助视图：实体热度条
  - 根据出现次数、来源覆盖、是否在标题出现排序
- 可选视图：关系网络图
  - 只在实体质量稳定后再做

### 10.3 原始报道流

原始报道不应默认全部展开。

建议默认折叠为：

- 按报道功能分类折叠
- 按来源折叠
- 按时间段折叠

用户展开后再看到标题、来源、时间、摘要、链接。

## 11. 运行方式

### 11.1 后端

```powershell
uvicorn app.api:app --app-dir backend --reload
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

### 11.2 前端

```powershell
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173/
```

### 11.3 测试

```powershell
python -m pytest backend/tests -q
cd frontend
npm run build
npm run test:e2e
```

## 12. 验收清单

### 当前 MVP 验收

- [ ] 用户可以输入任意事件关键词并启动采集。
- [ ] 搜索任务不会因为长请求造成前端假死。
- [ ] 任务失败或中断时有明确状态。
- [ ] 失败或中断任务可以重新运行。
- [ ] 事件时间轴能展示关键节点。
- [ ] 关键节点能展示来源和证据报道。
- [ ] 来源矩阵能展示各媒体覆盖情况。
- [ ] 关键人物、组织、地点、概念能分组展示。
- [ ] 原始报道流不会默认淹没主要分析结果。
- [ ] 前端在桌面和移动端都可读。

### 事件理解验收

- [ ] 每个关键节点都有阶段说明。
- [ ] 每个关键节点都有重要性原因。
- [ ] 每个关键节点都有支撑报道。
- [ ] 报道能按功能分类。
- [ ] 权威来源和普通来源能区分。
- [ ] 首发/早期来源能被识别。
- [ ] 无意义碎片词不会进入关键实体主展示。

### 地图回归验收

- [ ] 事件能抽取核心发生地。
- [ ] 文章能区分来源地、报道地、事件地。
- [ ] 地图点位能进入事件详情。
- [ ] 地图热度不是单纯文章数量，而能结合事件重要性和来源覆盖。

## 13. 决策记录

### 2026-06-21：当前主线从地图改为事件情报

原因：

- 用户最迫切的问题是信息收集困难、多源报道难以比较、事件脉络不清。
- 地图展示有价值，但前提是事件已经被可靠结构化。
- 如果先做地图，容易变成漂亮但信息解释能力不足的新闻点位系统。

结论：

- 当前主线是事件情报分析台。
- ChinaNewsMap 保留为长期品牌和地图化阶段目标。

### 2026-06-21：核心链路不依赖 LLM

原因：

- 用户已经遇到模型额度不足问题。
- 项目必须能在本地、低成本、可持续的条件下运行。

结论：

- 本地规则、配置和可解释算法是基础。
- AI 只作为后续增强。

### 2026-06-21：来源证据优先于抽象结论

原因：

- 新闻事件分析最容易出现“系统看起来很确定，但用户不知道依据是什么”的问题。
- 用户需要看到来源、时间、报道标题和链接。

结论：

- 每个关键节点都应尽量绑定证据报道。
- 时间轴和来源矩阵必须清晰标注来源。

## 14. 下一步建议

下一轮最适合进入 **Phase 2：事件理解质量提升**，具体从三个改动开始：

1. 重构时间轴节点展示，去掉不清晰的百分数主表达，改成“关键性 + 来源覆盖 + 证据来源”。
2. 增加报道功能分类，让报道能区分起因背景、触发事件、行动进展、各方回应、影响后果和分析解读。
3. 重做关键实体展示，用分组实体和热度条替代难读的词云碎片。

完成这三点后，产品会从“能跑通搜索分析”进入“用户真的能读懂事件”的阶段。

## 15. Phase 1-5 推进记录（2026-06-21）

本轮沿着 Phase 1 到 Phase 5 的路径推进，但优先选择能服务当前主链路的改动。实际完成重点集中在 Phase 1、Phase 2、Phase 3，并为 Phase 5 地图化回归补了一层数据准备。

### 15.1 Phase 1：数据采集质量

已完成：

- 搜索采集结果增加诊断信息：
  - 每个查询/采集器的返回数量。
  - 每个查询/采集器的保留数量。
  - 每个查询/采集器的成功/失败状态。
  - 失败原因。
- 采集汇总增加：
  - 来源数量。
  - 采集器分布。
  - 结果时间跨度。
- 前端搜索完成后展示“采集诊断”，用户可以看到哪些查询返回了结果、哪些结果被保留。

意义：

- 搜索结果少时，不再只表现为空结果。
- 用户能判断是后端不可用、采集源失败、查询词不合适，还是过滤后有效报道太少。

### 15.2 Phase 2：事件理解质量

已完成：

- 将报道功能分类统一为更稳定的产品标签：
  - 起因背景
  - 触发事件
  - 行动进展
  - 各方回应
  - 外交降温
  - 影响后果
  - 分析解读
  - 核实澄清
  - 后续处置
- 事件节点新增可读字段：
  - `importance_label`：高 / 中 / 低关键性。
  - `coverage_label`：多源覆盖 / 权威来源覆盖 / 有限多源 / 单源线索。
  - `selection_basis`：节点入选依据。
  - `location_signals`：地点线索，为地图化回归准备。
- 来源矩阵新增：
  - 主导报道分类。
  - 分类计数。
- 单篇报道和证据报道新增：
  - 报道功能分类。
  - 分类依据。

意义：

- 时间轴不再主要依赖抽象百分数表达。
- 每个节点可以解释“为什么重要”和“属于哪类报道”。
- 原始报道可以按起因、触发、行动、回应、影响等功能阅读。

### 15.3 Phase 3：多源对比视图

已完成：

- 来源矩阵增加快捷按钮：
  - 权威来源。
  - 首见来源。
  - 报道最多。
- 来源矩阵展示“分类/立场”，而不是只展示立场。
- 原始报道流继续默认折叠。
- 展开后按报道功能分类分组。
- 增加报道功能分类筛选。
- 前端补充 Playwright 测试，覆盖：
  - 来源矩阵筛选与排序。
  - 原始报道按分类分组。
  - 移动端没有横向溢出。

意义：

- 用户不必从几十条原始报道里硬读。
- 可以先看事件节点和来源矩阵，再按需要展开某类报道。

### 15.4 Phase 4：任务队列与生产化

本轮未正式推进 Phase 4。

仍保持现状：

- 后台任务仍是 SQLite 状态记录 + 进程内线程。
- 任务中断可见，也可重新运行。
- 尚未引入 APScheduler、RQ、Celery 或其他生产队列。

下一步建议：

- 增加任务历史列表。
- 增加任务取消。
- 增加任务日志详情。
- 再评估是否引入轻量队列。

### 15.5 Phase 5：地图化回归准备

本轮没有实现地图 UI，但补了第一层地图化数据准备：

- 事件节点新增 `location_signals`。
- 地点线索来自当前实体识别结果中的地点类实体。
- 前端在事件节点详情中展示地点线索。

当前限制：

- 这还不是严格地点抽取。
- 尚未区分事件发生地、报道来源地、涉及地点和影响范围。
- 尚未做地理编码，也没有地图点位。

下一步建议：

- 增加地点角色：
  - 事件发生地。
  - 涉及地点。
  - 来源地。
  - 影响范围。
- 增加地点置信度。
- 再进入地图视图开发。

### 15.6 验证结果

本轮验证通过：

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
# 16 passed

cd frontend
npm run build
# passed

npm run test:e2e
# 6 passed
```

注意：

- 直接运行系统 Python 的 `python -m pytest` 会失败，因为系统 Python 环境没有安装 pytest。
- 当前后端测试应使用项目虚拟环境：`venv\Scripts\python.exe -m pytest backend\tests -q`。

## 16. Framework Construction Plan（2026-06-21）

本轮在安装 Agent Reach、GitNexus 和 Superpowers 后，使用 Superpowers 的 `writing-plans` 工作流与 GitNexus 索引结果重新审视项目框架。

已完成：

- GitNexus 已索引当前项目：
  - 39 个文件。
  - 630 个符号。
  - 1293 条关系。
  - 30 个功能聚类。
  - 54 条执行流。
- GitNexus 结构检查通过：
  - `gitnexus check --cycles --json`
  - `cycleCount: 0`
- 识别出当前框架主要问题：
  - `backend/app/api.py` 同时承担路由、搜索编排、任务状态、序列化和证据挂载。
  - `backend/app/topic_ops.py` 同时承担查询扩展、采集、诊断统计、数据库写入和分析持久化。
  - `backend/app/pipeline/local_analyze.py` 是核心规则引擎，但输出结构尚未形成正式 schema。
  - `frontend/src/App.vue` 同时承担类型、API、任务轮询、状态派生、布局和多个业务组件。
- 新增框架执行计划：
  - `docs/superpowers/plans/2026-06-21-project-framework.md`

计划目标：

- 后端拆出 `schemas/`、`services/`、`repositories/`，让 `api.py` 回到薄路由。
- 前端拆出 `types/`、`api/`、`composables/`、`components/`，让 `App.vue` 回到页面编排。
- 文档补齐 `docs/architecture.md`、`docs/decision-log.md`、`docs/operations.md`。
- 后续改函数前使用 GitNexus impact，改完使用 detect-changes、analyze、check 做验证。

注意：

- GitNexus 当前在 Windows 环境下 FTS/BM25 全文搜索扩展不可用，keyword query 会降级。
- 当前仍可使用 GitNexus 的 `context`、`status`、`check --cycles`、`analyze` 和符号级导航能力。

## 17. Framework Execution Record（2026-06-21）

本轮开始执行 `docs/superpowers/plans/2026-06-21-project-framework.md`，优先选择低风险、高收益的框架边界拆分。

已完成：

- 后端新增 schema 边界：
  - `backend/app/schemas/__init__.py`
  - `backend/app/schemas/search.py`
  - `backend/app/schemas/analysis.py`
- `backend/app/api.py` 改为从 `app.schemas.search` 导入 `SearchRequest`，减少路由文件内的类型定义。
- 前端新增类型与 API 边界：
  - `frontend/src/types/dossier.ts`
  - `frontend/src/api/dossierApi.ts`
- `frontend/src/App.vue` 移除内联 DTO 类型和直接 axios 调用，改为使用 typed API client。
- 新增文档三件套：
  - `docs/architecture.md`
  - `docs/decision-log.md`
  - `docs/operations.md`
- 更新 README：
  - `backend/README.md`
  - `frontend/README.md`
- `.gitignore` 增加 GitNexus 本地图缓存忽略：
  - `.gitnexus/lbug`
  - `.gitnexus/parse-cache/`
  - `.gitnexus/parsedfile-cache/`

验证结果：

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
# 16 passed

cd frontend
npm run build
# passed

npm run test:e2e
# 6 passed

gitnexus analyze
# 889 nodes / 1704 edges / 30 clusters / 75 flows

gitnexus check --cycles --json
# cycleCount: 0

gitnexus status
# up-to-date
```

当时说明：

- 本轮没有执行高风险函数搬移，因此当时尚未拆 `backend/app/api.py` 的 search service；该事项已在第 18 节完成。
- `gitnexus detect-changes` 当前显示 `No changes detected`，原因是仓库整体仍处于未跟踪初始状态，没有可靠提交基线可比较。
- 下一阶段如果移动 `_run_search`、`_enqueue_search_job`、`_run_search_job` 等函数，必须先运行 `gitnexus impact`。

当时下一步建议：

1. 执行后端 service 边界拆分：先从搜索任务编排开始，把 `api.py` 中的任务函数移动到 `backend/app/services/search_service.py`。该项已在第 18 节完成。
2. 执行前端组件边界拆分：优先抽出 `SearchPanel.vue`、`SourceMatrix.vue`、`ArticleGroups.vue`。
3. 在第一次大规模搬移前创建一个基线提交，使 GitNexus `detect-changes` 和 git diff 更有意义。

## 18. Backend Service Boundary Execution（2026-06-21）

本轮继续执行 `docs/superpowers/plans/2026-06-21-project-framework.md` 的 Task 2，完成后端搜索服务边界拆分。

已完成：

- 新增服务包：
  - `backend/app/services/__init__.py`
- 新增搜索任务服务：
  - `backend/app/services/search_service.py`
  - 承担同步搜索、后台搜索任务、任务步骤状态、任务快照、任务重跑、中断标记和历史任务裁剪。
- 新增 payload 序列化服务：
  - `backend/app/services/payloads.py`
  - 承担专题摘要、文章 payload、证据文章 payload、事件证据挂载、timeline/framing/analysis 序列化和日期格式化。
- `backend/app/api.py` 已进一步变薄：
  - 搜索相关路由委托给 `search_service`。
  - 专题/文章/事件 payload 组装委托给 `payloads`。
  - 删除原先内联在 API 文件中的搜索任务函数和证据序列化函数。
- `backend/tests/test_api_helpers.py` 已改为直接测试 `payloads` 与 `search_service`，同时保留 `api.rerun_search_job` 的路由层拒绝逻辑检查。

验证结果：

```powershell
venv\Scripts\python.exe -m py_compile backend\app\api.py backend\app\services\payloads.py backend\app\services\search_service.py
# passed

venv\Scripts\python.exe -m pytest backend\tests -q
# 16 passed

cd frontend
npm run build
# passed

npm run test:e2e
# 6 passed

gitnexus analyze
# 883 nodes / 1475 edges / 28 clusters / 60 flows

gitnexus check --cycles --json
# cycleCount: 0

gitnexus status
# up-to-date
```

说明：

- 本轮已执行 `_run_search`、`_enqueue_search_job`、`_run_search_job` 等搜索链路的 GitNexus impact 检查。
- `_topic_summary`、`_article_evidence_lookup`、`_attach_event_evidence` 等共同路径函数的 impact 为 HIGH，原因是它们被列表、详情、同步搜索和后台搜索共同调用；实际改动采用“搬动位置、不改行为”的方式，并通过后端与前端回归验证。
- `gitnexus detect-changes` 仍显示 `No changes detected`，原因同上：当前仓库整体处于未跟踪初始状态，没有可靠提交基线可比较。

下一步建议：

1. 执行前端组件边界拆分：优先抽出 `SearchPanel.vue`、`SourceMatrix.vue`、`ArticleGroups.vue`。
2. 继续收敛 `backend/app/api.py`：下一阶段可把 topic/detail/articles/local-events 查询拆入 `topic_service.py`。
3. 创建一个基线提交，让后续 GitNexus `detect-changes` 与 git diff 能精确描述增量。

## 19. LLM Endpoint Switch To Pixel API（2026-06-21）

本轮根据额度不足后的替代方案，将 LLM 分析端口切换到 Pixel API。

已完成：

- `backend/.env` 中的 `ANTHROPIC_BASE_URL` 已从旧节点改为：
  - `https://ai-pixel.online`
- `backend/.env.example` 增加 Pixel API 端点示例，后续复制配置时不再遗漏 base URL。
- `backend/cli.py` 新增 LLM 冒烟测试命令：
  - `venv\Scripts\python.exe backend\cli.py llm-check`
- `backend/README.md` 和 `docs/operations.md` 增加 LLM 配置、验证、富化和综合命令说明。

验证结果：

```powershell
curl.exe -I -L --max-time 20 https://ai-pixel.online
# HTTP/1.1 200 OK

curl.exe -i --max-time 20 https://ai-pixel.online/v1/models
# 401 API_KEY_REQUIRED

curl.exe -i --max-time 20 -X POST https://ai-pixel.online/v1/messages -H "Content-Type: application/json" -d "{}"
# 401 API_KEY_REQUIRED

venv\Scripts\python.exe backend\cli.py llm-check
# 命中新端点，但返回 INVALID_API_KEY
```

说明：

- Pixel API 域名可达，并且 `/v1/models`、`/v1/messages`、`/v1/chat/completions` 均能返回 API key 相关错误，说明网关路由存在。
- 当前失败点不是代码路径，而是 `backend/.env` 中现有 `ANTHROPIC_API_KEY` 不是 Pixel API 可用 key。
- 更换为 Pixel API 控制台生成的 key 后，应先运行 `llm-check`，再执行 `enrich` / `build`。

下一步建议：

1. 在 Pixel API 控制台生成可用 API key，替换 `backend/.env` 的 `ANTHROPIC_API_KEY`。
2. 运行 `venv\Scripts\python.exe backend\cli.py llm-check` 验证模型调用。
3. 若 `claude-haiku-4-5` 或 `claude-sonnet-4-6` 模型名不被 Pixel API 接受，再根据 Pixel API 模型列表调整 `HAIKU_MODEL` 和 `SYNTH_MODEL`。

## 20. LLM Provider Adaptation And Product Positioning（2026-06-21）

本轮在用户更新 Pixel API key 后，重新检测可用模型并调整 LLM 接入方式。

已完成：

- Pixel API `/v1/models` 已能通过当前 key 返回模型列表。
- 当前账号可用模型中未返回 Claude 模型，主要是 OpenAI-compatible 模型。
- `backend/app/llm.py` 已从单一 Anthropic SDK 路径扩展为双协议：
  - `LLM_PROVIDER=anthropic`：走 Anthropic-compatible `/v1/messages`。
  - `LLM_PROVIDER=openai`：走 OpenAI-compatible `/v1/chat/completions`。
  - `https://ai-pixel.online` 默认推断为 OpenAI-compatible。
- `backend/app/config.py` 固定从 `backend/.env` 加载配置，避免从不同工作目录运行 CLI 或脚本时读不到 key。
- `backend/.env` 当前模型选择：
  - `HAIKU_MODEL=gpt-5.4-mini`
  - `SYNTH_MODEL=gpt-5.4`
- `llm-check`、JSON 输出解析、综合文本生成均已实际验证通过。

验证结果：

```powershell
venv\Scripts\python.exe backend\cli.py llm-check
# gpt-5.4-mini: ok

venv\Scripts\python.exe backend\cli.py llm-check --model gpt-5.4
# gpt-5.4: ok
```

### 项目定位

当前项目不应只是“新闻地图”，而应先定位为：

> 面向复杂公共事件的多源新闻情报工作台。

核心价值不是简单收集新闻，而是把不同语言、不同媒体、不同立场的碎片报道组织成可核查的事件档案：

- 事件如何发生与演进。
- 哪些报道是关键节点证据。
- 不同来源和阵营如何叙述同一事件。
- 哪些人物、组织、地点和概念真正重要。
- 哪些结论有充分来源支撑，哪些仍是信息缺口。

地图仍然重要，但应作为事件档案成熟后的空间表达层，而不是当前阶段的第一优先级。

### 达成路径

#### Phase A：稳定“搜索 -> 本地分析 -> 证据展示”主链路

目标：任何关键词都能生成基础事件档案，即使没有 LLM 也可用。

重点：

- 保持当前搜索任务、来源矩阵、事件轴、报道分组、实体面板稳定。
- 修复前端组件边界，把 `App.vue` 拆成工作台组件。
- 强化关键人物/组织/地点抽取规则，减少无意义词。

#### Phase B：接入 LLM 增强层

目标：让 LLM 只做“解释、归纳、翻译、证据综合”，不替代证据链。

重点：

- `enrich`：对报道做中文标题/摘要、相关性、立场、报道功能分类。
- `build`：对已富化报道生成时间线、各方叙事、批判分析。
- 前端明确区分“本地规则结果”和“LLM 增强结果”。
- 每个 LLM 结论必须挂回 article ids，避免无来源判断。

#### Phase C：产品化事件工作台

目标：让用户能围绕一个事件持续研究，而不是只看一次搜索结果。

重点：

- 搜索任务历史与重跑。
- 事件档案版本记录。
- 手动标注关键报道、关键人物、关键节点。
- 原始报道折叠、筛选、收藏、引用。
- 关键人物/组织/概念改为“实体面板 + 权重列表”，词云只作为辅助视觉。

#### Phase D：空间与时间表达

目标：把事件时间轴与地理线索连接起来，形成 ChinaNewsMap 的长期形态。

重点：

- 地点实体标准化。
- 事件节点关联地点。
- 地图视图展示事件扩散、冲突区域、外交访问、产业影响地点。
- 地图只展示高置信地点，低置信地点进入待确认列表。

### 下一步建议

1. 先执行前端组件拆分，降低 `App.vue` 复杂度。
2. 再设计 LLM 增强结果在前端的呈现方式：不要覆盖本地分析，而是作为可折叠的“AI 综合层”。
3. 最后用一个真实事件做端到端验证：搜索 -> 富化 -> 综合 -> 前端展示 -> 人工评估证据质量。

## 21. 三方对照架构与发现方向（2026-06-28）

本节记录 06-21 之后的进展。核心变化：项目从"媒体单一声音"扩展为**媒体 / 学界 / 民间三方对照**，并完成一轮架构重构、依赖清理、GitHub 备份，且开始探索"事件发现"这一新方向。

### 21.1 三个声音（媒体 / 学界 / 民间）

产品认知升级：同一事件不该只看媒体怎么报，而要三方对照。

- **媒体声音（已有，强化）**：新增**多国对比视图** `country-compare`，按"当事国 + 主权国家（G20 ∪ 涉事方）"归类报道，看谁先报、各国侧重差异。`country_of_source` 用词边界匹配避免媒体名子串误判（dw→DE、aws→US 这类）。
- **学界声音（新增，"重度"层）**：`academic.py` + `openalex.py`。CJK 话题先经 LLM 翻成英文查询（"美伊战争"直译会捞到 0 引用的无关论文，"US Iran war" 才相关），再取论文 + 构建**引用收敛图**。已知特性：新事件引用边稀疏（美伊战争 edges=0 正常），成熟话题才富（亚洲金融危机 12 边）。需 OpenAlex API key（2026-02 起政策变更）。
- **民间声音（新增，"最该被怀疑的一角"）**：`reddit_sentiment.py` 多平台 —— B站 / 小红书 / 雪球 / Reddit，经 OpenCLI 驱动真实 Chrome 采集，绕过沙箱计费网关。采集规则：每平台默认排序取 K=5 帖、每帖 M=10 评论，逐帖 try/except 容错。Reddit 用英文查询、中文平台用原中文名。雪球对非财经话题返回 0 = 正确降级。

### 21.2 三方对照综合（cross-synthesis）

`cross_synthesis.py` 把三个声音喂给 LLM，输出 5 个区块：**三方共识 / 三方矛盾 / 各自盲区 / 机制重建（"分析机制与因果，不做道德归责"）/ 批判提示（"民间情绪是非事实源"）**。

- `gather_voices` 对缺失声音优雅降级（某一路超时不影响其余）。
- 容错链：`run_cross_voice_step` 单声音失败只记录不中断，因 LLM 网关偶发 ReadTimeout/SSL EOF（网络不稳，非代码问题）。
- 实测在真实话题上三方齐发成功（媒体/学界/民间链路均 done，民间含 B站20 + 小红书17 + Reddit30 帖 + 50 评论）。

### 21.3 架构重构（H / I / J 三阶段）

先建基线提交 `2333a53` 保证可回滚，再逐阶段验收、各自独立提交：

- **H 前端组件拆分**（`834af15`）：`App.vue` 2057→639 行，抽出 5 个面板组件，组件零 fetch（数据留在 composable）。
- **I JobRunner 去重**（`185be03`）：5 类任务生命周期统一为 `JobRunner`，`api.py` 零改动（API 契约不变），554→538 行。
- **J local_analyze 拆分**（`8ed7aaa` 黄金测试 + `35db70e` 拆分）：**黄金快照测试先行**（15 处断言锁定输出），再把 1075→183 行的门面拆成 clustering/scoring/entities/categorization 四模块。`analyze_topic` 签名不变。拆分后黄金测试仍过 = 行为逐字段保住。

教训记录：早期 E+F+G 三个任务的 git diff 曾因"验收后未即时提交"缠在一起，之后改为**每个验收通过的任务立即独立提交**。

### 21.4 依赖清理（Ponytail 审视）

用 Ponytail 插件只读审视，GPT 执行：

- `acf3341`：删未用前端依赖（unplugin-auto-import / unplugin-vue-components）+ 死 CSS（.run-hint 等 4 个类）。
- `b85209a`：合并 3 处重复 markdown 渲染为 `renderMarkdown()`、合并 5 个 `waitFor*Job` 轮询。
- 保留 `local_analyze.py` 门面转发函数（被测试和 country_compare 兼容使用，删了不划算）。

> 注：本批清理 GPT 已提交进库，Claude 侧的 K1–K4 逐项复核（删依赖后 build 仍过、CSS 零引用、渲染抽取等价、轮询语义不变）尚未完成。

### 21.5 GitHub 备份

代码已推送至 `https://github.com/rly0506/message-platform`（master）。推送前做了三层密钥扫描（历史文件名 / 全历史 key 模式 / 深度 blob 扫描），确认 `backend/.env`（含真实 ANTHROPIC + OPENALEX key）从未进库，只有空占位的 `.env.example`；`dossier.db` 也已忽略。**当前为公开仓库。**

### 21.6 已知约束（诚实记录）

- **GDELT 429 IP 封锁**：持续，VPN 更糟（数据中心 IP 封得更狠）。需住宅 IP + 冷却，代码已就绪、未恢复。真实格式确认：sourcecountry 为英文全名（"China"/"United States"）。
- **LLM 网关不稳**：偶发 ReadTimeout / SSL EOF / 503，已用容错链兜底。
- **Claude 沙箱网络**：bash 走计费网关，部分外部域名（arXiv export、raw.githubusercontent）被拦，需改走 GitHub API 或 WebFetch 兜底。
- **spaCy**：zh/en 模型手动装（`spacy download` 给 403），不可用时降级 jieba。

### 21.7 新方向：从"搜索"到"发现"

详见 `docs/future-directions.md`。核心问题：现有全部功能都是**搜索**（用户得先叫得出名字），但真正痛点是**发现**（认知之外、叫不出名字的事件）。

- 已认清的硬道理：**零输入下"完全认知之外 + 低噪声"互斥** —— 任何发现系统都需先验（领域/信任源/重要性定义），"扫世界只捞对我重要的"是神谕不是工具。
- 可行解法：**借别人架好的"注意力前沿"**（HN / arXiv / 智库 / GDELT），订阅"圈子里冒头、还没出圈"的东西。
- 关键信号不是"最大"而是"**加速**"（从低基数在长），这要求存**每日快照基线**比 delta —— 发现系统必须有记忆，这是它和无状态的搜索最本质的区别。
- 已做**零成本验证**（HN + arXiv 真实数据）：核心假设成立（技术圈种子确实捞得到），但噪声占快一半（需二级 LLM 分拣折叠），且"加速检测"需多日基线才能验。
- 领域局限（结构性）：HN/arXiv 偏技术圈。换领域需换源 —— 政治时事的对口引擎是 **GDELT**（报道量异常突增 = 政治版加速检测），但受 GDELT 封锁 + 中文敏感议题审查双重约束。

### 21.8 当前待办

- 前端三方对照面板与后端 academic/sentiment/cross 端点的整合复核（确认能点火、能展示）。
- Ponytail 清理 K1–K4 的 Claude 侧复核。
- "事件发现"领域选定（技术 / 金融 / 政治时事），再逐领域验证源可得性与信号质量。
- GDELT 待住宅 IP 冷却后回填。
