# 过夜作战规划 · 交 GPT 执行（2026-07-05）

状态：**方案待人类拍板**。按 8 步流程（Opus 出方案 → GPT 审 → 人类审 → GPT 写码 → 双向简化 → GPT 复查 → 人类终审提交），本文是第 1 步产物。人类批准后，GPT 按阶段顺序执行，**每个任务独立提交 + 独立门禁**。

本规划基于三路真实源码探查（file:line 均已核实），把用户点名的开源项目尽量编排进一晚的工作：
**SearXNG + Scrapling + trafilatura**（全文线）、**taste-skill**（前端重排）、**last30days/邮件日报**（推送）、**行为金融学**（信息价值透镜）。logseq/AppFlowy、tikhub、ECC 本轮不动（理由见末尾）。

---

## 分工（2026-07-05 定）：Claude 前端 / GPT 后端，按目录切死

用户定 Claude 做前端、与 GPT 分工。**按目录切，不按阶段切**，避免两个 agent 编辑同一文件（current-state 明令禁止）：

- **Claude 独占 `frontend/`**：阶段 4 全部（token + 重排 + 头版补卡）+ 阶段 3.3（价值透镜 chip 渲染）+ 阶段 3 的前端 e2e。
- **GPT 独占 `backend/`**：阶段 1（P1 证据链）、阶段 2（SearXNG + Scrapling）、阶段 3.1/3.2（value_lens 后端 + payload 挂载）、阶段 5（配置+文档）。阶段 0 门禁两边各跑各的那一半。
- **交接契约（唯一耦合点）**：GPT 在 `article_payload`/`collect_seeds` 加 `info_value_labels: [...]` 字段（阶段 3.2）；Claude 的 chip（阶段 3.3）消费这个字段。**这是 API 契约交接，不是共享文件**。
- **Claude 不阻塞于 GPT**：前端 e2e 本就 mock 后端（`page.route` fulfill json），Claude 先按约定的 `info_value_labels` 形状写 mock 和 chip，GPT 的真字段落地后自动接上。两边可真并行。
- 冲突面归零核对：Claude 只碰 `frontend/**`，GPT 只碰 `backend/**` + `docs/` + `spec/CHANGELOG`。谁都不碰 `AGENTS.md`/`CLAUDE.md`/`.env`/真实库。

---

## 复用现实：哪些"下载即用"，哪些只是原则（诚实分层）

用户直觉"能复用就下载复用、别重写"——**对工具/库/服务成立，对 skill/提示词/灵感不成立**。逐个说清，免得白下载：

**真·下载即用（GPT 后端线，别自己写）**：
- **SearXNG** = 自托管元搜索**服务**，不是抄代码——`docker run` 起一个实例，打它的 `/search?format=json`。我们写的只是一个薄采集器去调它。
- **Scrapling** = Python **库**——`pip install scrapling`，`import StealthyFetcher`。真库复用，不抄代码。
- **trafilatura** = 已装已用，无需动作。

**不是可下载的代码，是原则/提示词（Claude 前端线要认清）**：
- **taste-skill** = 一组审美 **SKILL.md 提示词**，**没有组件库**。它的价值是"极简/层次/间距"原则，我读了手工应用到我们的 `style.css`/组件上。`npx skills add` 只改 agent 运行环境、不给产品可复用代码——**不装**。
- **last30days-skill** = 研究**范式**，不可嵌进产品。
- **logseq/AppFlowy** = 巨型 Electron/Rust 应用，只借交互灵感，不可当组件复用。
- **ian-xiaohei 插画** = 生图 skill，非前端代码。

**前端唯一真能"下载复用"的点**：设计 token。**人类已定（2026-07-05）：混合方案**——间距/字号/圆角比例复制 Open Props 的值（通用性强、比例经打磨），配色沿用项目现有 teal 冷静基调（品牌识别，从 830+ 硬编码值收敛）。**只复制值进 `:root`、零运行时依赖、不 npm 装**。两套来源在 4.1 对齐一次。

---

## 硬约束（GPT 必须守，违反即回滚）

1. **不自动合并 master / 不推 origin**。feature 分支现领先 master 20 提交、P0 修复只在本分支。合并公开仓库 master 是高影响、难回滚动作 → **留给人类晨审决定**。GPT 只在工作分支上累积提交。
2. **不写 `backend/dossier.db`**（真实库）。测试一律内存 SQLite / mock。`discovery.db` 同样不得污染真实快照。
3. **每个任务独立小提交**，提交前跑门禁（后端 pytest + 前端 build + 相关 e2e）。红/绿留痕写进 `spec/CHANGELOG.md`。
4. **新采集/抓取路径默认关**（env flag off），不改变现有行为，直到人类显式开启。
5. **任何管线降级必须在 payload 留痕**（升格为工程红线）。
6. **改符号前先 GitNexus impact，改完 detect-changes**（CLAUDE.md 规矩）。
7. e2e 无 data-testid，**类名同时是样式钩子和行为钩子**——重排前端必须保留现有类名，或同一提交内改测试。关键类名：`.headline-deck/.headline-card/.boundary-queue/.boundary-list/.rest-seeds/.stream-row/.stream-title/.discovery-report/.discovery-archive-selector/.cognition-timeline-tree/.timeline-go/.boundary-got-it`。

---

## 阶段顺序与依赖

```
阶段 0 门禁基线（不改码，只跑+记录）        —— 解锁一切，确认起点干净
   ↓
阶段 1 P1 证据链修复（含词边界+golden 重生成）—— 透镜的地基，必须先于阶段 3
   ↓                          ↘（阶段 2 与阶段 1 独立，可先可后）
阶段 2 全文线：SearXNG + Scrapling           —— 独立，破全文天花板
   ↓
阶段 3 行为金融学信息价值透镜                 —— 依赖阶段 1 的词边界修复
   ↓（前端与后端独立）
阶段 4 前端：今日头版提升 + 极简 token 重排   —— 独立
   ↓
阶段 5 邮件日报接通（配置+文档，非开发）      —— 最小，收尾
```

GPT 单人过夜建议**严格串行**（避免自身工作互相冲突）。若时间不够，做完哪个阶段就停在哪，绝不留半个未验证的阶段。

---

## 阶段 0 — 门禁基线（预计 15 分钟，不改码）

目的：确认起点绿，作为后续每步的对照。

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q`
- `cd frontend; npm run build`
- `cd frontend; npm run test:e2e -- --workers=1`
- `node .gitnexus/run.cjs status` / `detect-changes --scope all`
- 全部结果写入 `spec/CHANGELOG.md`（当日"过夜基线"条目）。任一红 → 停，写明什么红，不往下做。

---

## 阶段 1 — P1 证据链修复（透镜的地基）

来源 `spec/bug-audit-2026-07-05.md` P1 批。**为什么先做**：阶段 3 的价值透镜复用 `scoring.py:410,413` 的子串匹配器；不修词边界，透镜会继承假证据，"判断信息价值"变成判断噪声。逐条独立提交：

**1.1 英文词表词边界（最关键，牵动 golden）**
- 问题：`_matched_impact_terms`/`_impact_hits`（`scoring.py:408-413`）、`categorization._event_category`/`infer_stance`（`categorization.py:26,42,49`）用裸 `term in text` → "war"命中"warns"、"ban"命中"bank"、"un"命中"under"。`prefilter.py:46` 同病。MSNBC 被"msn"误标聚合源（`scoring.py:390-395`）。
- 修：英文词加 `\b` 正则边界；**CJK 保持子串**（中文无词边界）。给一个共用 helper（如 `_term_hit(term, text)`：ASCII 词走正则、含 CJK 走子串）。
- **golden 会变**：`test_local_analyze_golden.py:117` 现固化 `impact.reason == "war、strike"`（"war"是"warns"假阳）。修完该 reason 变正确值 → **故意重新生成 `EXPECTED_GOLDEN_SHA256`**（`test:8`），并在提交信息里写明"golden 重生成：移除 war/warns 假证据"。这是修复不是回归。
- 测试：加"warns 不命中 war、bank 不命中 ban"的单元断言。

**1.2 framing article_ids 污染**
- 问题：`scoring.py:231-237` 把整月全部文章 id 归给每个立场（`_stance_evolution` 桶不分立场）→ 文案说"共1篇"却挂2篇，还经 `cross_synthesis.py:167-175` 喂 LLM。
- 修：framing 的 evidence ids 只取该立场桶内文章。加"立场证据不串桶"断言。

**1.3 情绪层 external_id（刷新后评论失联）**
- 问题：内存路径 id=外部 id、DB 路径 id=自增 id，评论 `parent_post_id` 存外部 id → 刷新后 `App.vue:890` 匹配不上；空 url 帖每次重跑重复插入（`sentiment.py:147-160`）。`SentimentPost` 缺外部 id 列（`db.py:134-149`）。
- 修：加 `external_id` 列，去重键用 `platform+external_id`，评论按 external_id 关联。**注意 DB schema 变更**——用迁移/建表守卫，不碰真实库。

**1.4 OpenAlex 静默降级 + 留痕**
- 问题：`openalex.py:88-89` 无 key 就 raise（其实匿名可用），`academic.py:81-85` 又吞异常 → 默认只剩 Crossref，payload 却宣称"OpenAlex + Crossref"。
- 修：去掉强制 key（匿名 + mailto 礼貌池）；**降级必须在 payload 留痕**（红线 #5 的第一个落地）。

**阶段 1 门禁**：每条改完跑 `pytest -q` + 受影响 e2e；1.1 提交必须附 golden 重生成说明。

---

## 阶段 2 — 全文线：SearXNG + Scrapling（破全文天花板）

**为什么**：主源 gnews 给的是跳转链接，正文 100% 抓不到（记忆已验证），限制情绪徽标/单篇透视。SearXNG 拿真实 URL，Scrapling 抓反爬公开页。两者默认关，先让能力就位。

**2.1 SearXNG 采集器（查询驱动，像 gnews）**
- 新文件 `backend/app/collectors/searxng.py`，函数 `collect_searxng(query) -> list[dict]`，发 **rss 同款 dict**（`rss.py:93-103` 的键：url/title/source/source_lang/source_country/published_at(datetime)/snippet/collector="searxng"）。
- 走已验证代理配方（`config.RSS_PROXY`/`RSS_USER_AGENT`/httpx），打 SearXNG 实例的 `/search?format=json`。
- 接入：`collect_topic` 每查询循环加分支（`topic_ops.py:77-100`），gated by 新 flag。结果自动过 `prefilter.dedup_and_score`（`topic_ops.py:151`）——真实 URL 直接进 `Article.url`。
- config：`SEARXNG_URL = os.getenv("SEARXNG_URL","").strip()`（`config.py`，空则该采集器跳过），`USE_SEARXNG` truthy-string 开关（仿 `ENRICH_FETCH_FULLTEXT` at `config.py:54`）。
- 测试：`test_searxng_collector.py`，monkeypatch httpx DummyClient（仿 `test_openalex_collector.py:98-113`），断言 dict 键齐、`collector="searxng"`、软失败 `[]`。

**2.2 Scrapling 全文抓取路径（anti_bot 页）**
- 在 `fulltext.py` 加 `extract_url_scrapling(url)`：惰性导入 Scrapling（不可用 → `ok=False` 优雅降级，仿 `_trafilatura()` at `fulltext.py:34-40`），StealthyFetcher 取 HTML → **复用 `extract_from_html`**（`fulltext.py:75`）→ 保持 `Extracted` 契约不变。
- 接入：`_fetch_bodies._one`（单点 `topic_ops.py:284`）按 flag 选 `extract_url_scrapling` 或现有 `extract_url_proxied`。抓取成功率↑ → `fulltext_hits`（`topic_ops.py:340`）↑ → 能打情绪分的文章↑（`topic_ops.py:374-379` 无 body 强制 -1 的红线不变）。
- config：`FULLTEXT_USE_SCRAPLING` truthy-string 开关，默认关。
- **红线**：Scrapling 只抓公开/反爬页，**不破付费墙**（官方明示）。`access="anti_bot"` 已是可采集（`feed_registry.py:21` 未列入 uncollectable）——对齐。
- 测试：`test_fulltext.py` 加 monkeypatch Scrapling 为不可用，验证降级 + HTML 仍走 `extract_from_html`、`ok=False` 软失败。

**阶段 2 门禁**：pytest + build。**不接主链路的真实网络调用**（默认关），仅代码就位 + 单测。人类晨审后自行起 SearXNG docker 做一周 spike 再决定开启。

---

## 阶段 3 — 行为金融学信息价值透镜（智识内核）

**为什么**：回答用户"搜集信息后如何判断有价值"。本地、无 LLM，给种子/文章打**偏差标签 + 用户自查提示**，全部复用已有信号。**依赖阶段 1.1**（词边界修完才不继承假证据）。

**3.1 后端：本地偏差标签器（无 LLM）**
- 新模块 `backend/app/pipeline/value_lens.py`，纯函数，输入已有信号、输出标签数组。映射（全部复用现有函数，不新造检测）：
  - **可得性偏高 / 疑似造势**：`_score_breakdown` 的 pickup 代理（`scoring.py:143-147`，源/文章计数）高但 substance 低 → "关注度高、实质未验证"。
  - **疑似羊群**：`narrative_signals.detect_narrative_signals`（`narrative_signals.py:17`）——多家同报**标为可能的信息瀑布，不是证据增强**（对现有叙事收敛的语义锐化，重要）。
  - **小样本外推**：复用现有先例 `_trend_for_stance` 的"样本不足"（`scoring.py:256-258`，total<6）与 sentiment `confidence=min(1,n/5)`（`sentiment.py:247`）。
  - **干货/情绪**：已有 `substance_score`/`emotion_score`（`db.py:95-98`）直接映射"实质 vs 情绪"。
- 红线：**标签是阅读提示不是真理裁决**；**不做投资建议**（项目非投顾）。每个标签带一句中性说明（学术依据可选注在 tooltip）。

**3.2 挂载点（避开 golden）**
- 文章级：加进 `article_payload`（`payloads.py:82-105`）新键 `info_value_labels: [...]`——**不碰 `analyze_topic` 返回 dict**（否则触发 golden 重算）。
- 话题级：加进 `/api/topics/{id}/local-events` 路由 dict（`api.py:470-481`，紧挨 `narrative_signals`）——也在 golden 之外。
- 发现种子级：加进 `report.collect_seeds`（`report.py:204-215`）——流向报告/sidecar/邮件日报，无 golden 风险。
- 用户自查提示（过度自信/锚定/事后聪明）：作为静态文案，挂在认知层现有提示位（复用 `cognitionProfile` 工作流提示的模式）。

**3.3 前端呈现**
- 文章卡/种子卡加一排克制的标签 chip（复用阶段 4 的 token）。**标签是提示样式，非红色警告**（延续诚实边界美学）。
- e2e 加断言：某造势/羊群样本出现对应 chip；小样本出现"样本不足"提示。

**阶段 3 门禁**：pytest（新 value_lens 单测，纯函数直接喂输入）+ 相关 e2e + build。

---

## 阶段 4 — 前端：今日头版提升 + 极简 token 重排（治打开欲）

**为什么**：用户"没有打开欲"。今日头版已存在（`.headline-frontpage`，`DiscoveryPanel.vue:383-429`），style.css **无 token 系统**（830+ 硬编码色值）——这是极简重排最大杠杆。走 taste-skill 的 minimalist-ui 原则（Notion/Linear 编辑风，**非** premium 动效——用户已砍花哨）。

**4.1 引入 :root 设计 token（最大杠杆，独立提交）**
- `style.css` 顶部加 `:root` token：色阶（收敛现有近重复灰/teal）、间距阶（8/12/16/24）、字号阶、圆角阶。逐步替换字面量。**不改视觉结果**，只把散值收敛成变量——这步应视觉零差（截图对比）。

**4.2 可读性重排两个重灾区（借头版卡片语言）**
- `.rest-seeds .stream-row`（`DiscoveryPanel.vue:567-618`，现在是密集单行索引流）→ 向 `.headline-card` 编辑风靠拢：真标题 + 呼吸间距 + 分组，去掉 `white-space:nowrap` 一行截断。
- `.boundary-card-notes`（`DiscoveryPanel.vue:499-528`，7 字段挤 0.75rem dl 网格）→ 拉开层次，主信息大、次要折叠。
- **保留全部 e2e 类名**（见硬约束 7），或同提交改 spec。

**4.3 今日头版补"追踪话题变化"卡**
- 现头版只有边界队列 top5（`headlineItems = boundaryQueue.slice(0,5)`）。补一类卡：追踪话题的新变化（`useTopicData` 的 `latest_published_at`/`updated_at` 客户端算 delta；`autoRefreshStatus.frontier_refreshed/news_refreshed` 作"有新料"信号）。**无后端新端点**，纯前端派生。
- 打开即见"今天有什么新"，工作台退二层（appMode 已默认 discovery，无需新增 gate）。

**阶段 4 门禁**：build + 全量 e2e（`--workers=1`）。4.1 附前后截图说明视觉零差。

---

## 阶段 5 — 邮件日报接通（配置+文档，非开发，收尾）

**现状**：代码已完整（`daily_email.py` 两路 + CLI `daily-email` + `scripts/send_daily_digest.ps1`）。缺的是配置+调度，GPT 能做到"差最后一个密钥"：

- 跑 `cli.py daily-email --preview`（需先有一次 `discover` 归档报告），确认正文渲染正常，贴进 CHANGELOG。
- 在 `backend/.env.example` 补 `DAILY_DIGEST_*` 全套注释示例（TO/SMTP_HOST/PORT/USER/PASSWORD/FROM/TLS）。
- 写 `docs/operations.md` 一节：如何配 SMTP、如何 `schtasks` 注册 `send_daily_digest.ps1` 每早跑、Agent Mail 两阶段 token 用法。
- **真实密钥 + 注册任务计划 = 人类晨审 5 分钟自己做**（GPT 不接触用户密钥、不写真实 .env）。

---

## 本轮不动的开源项目（诚实说明）

- **logseq / AppFlowy**：认知地图交互参考，属阶段 3 之后的"认知地图 V2"，本轮不接依赖。
- **tikhub.io**：民间层采集替代，按既定决策"缓"——等 30 天使用期证明民间层被用再试点。
- **ECC / mattpocock**：开发工具链，非产品功能；更贴"指挥 AI 的指令体系"另一件事。

---

## 晨审清单（人类醒来看这个）

1. 每阶段 CHANGELOG 的红/绿门禁记录。
2. golden 重生成（阶段 1.1）是否只移除了 war/warns 假证据、无意外字段变动。
3. 情绪层 DB schema 变更（阶段 1.3）是否安全、真实库未被写。
4. SearXNG/Scrapling 是否确实默认关（grep env flag 默认值）。
5. 决定：feature 分支（+ 本轮新提交）是否合并 master 推 origin。
6. 决定：是否起 SearXNG docker 做一周直链率 spike。
