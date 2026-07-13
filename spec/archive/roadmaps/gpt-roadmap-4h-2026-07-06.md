# GPT 4 小时路线图 · P1 证据链 + value_lens 生产者（2026-07-06）

状态：**交 GPT 执行**。这是 `.agent-bridge/TO_CODEX.md` 里"任务 A + B"的时间盒版本，机制经二次源码探查核实（file:line 准确、未漂移）。人类审后 GPT 按块执行。

**总原则**：每块独立小提交 + 独立门禁；只碰 `backend/` + `docs/` + `spec/CHANGELOG`（别碰 `frontend/`，Claude 地盘）；不合并 master、不推 origin（人类决定）；不写真实库；改符号前 GitNexus impact。

**关键风险（决定排序）**：P1.1 和 P1.2 都改动 `test_local_analyze_golden.py:8` 的单一 SHA-256（还有 :117 和 :124 两处断言）。**这两块必须连做、最后一起重生成哈希一次**，否则会连环撞两次 golden。P1.4 和 value_lens 不碰 golden，可独立验证、风险低。

---

## 块 0（~10 分钟）· 起点门禁基线
不改码。跑一遍确认起点绿，作为后续对照：
- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` → 应 `235 passed`
- `node .gitnexus/run.cjs status`
任一红 → 停，写明什么红。

---

## 块 1（~25 分钟）· P1.4 OpenAlex 降级留痕【热身，trivial，不碰 golden】
**为什么先做**：最轻、完全独立、立刻一个干净提交建立节奏。
- 病症：`collectors/openalex.py:88-89` 无 key 就 `raise`（其实匿名可用）；`pipeline/academic.py:81-85` `safe_search` 用 `except Exception: return []` 静默吞掉 → 默认只剩 Crossref，但 payload `academic.py:68` 仍宣称 "OpenAlex + Crossref merged"。
- 修：
  1. `openalex.py` 去掉强制 key 的 raise，无 key 走匿名 + mailto 礼貌池（保留网络失败的 raise）。
  2. `academic.py` 的 `safe_search`：**降级必须留痕**——返回结构带一个 `degraded`/`source_error` 标记，别再无声返回 `[]`（工程红线：任何管线降级在 payload 留痕）。
  3. `academic.py:68` 的 `sort_strategy` 文案改成反映实际贡献源（OpenAlex 空时别宣称有它）。
- 验证：`pytest tests/test_academic_layer.py -q` + `pytest -q` 全绿。GitNexus impact on `academic.py`。
- **提交**：`fix(academic): openalex anonymous access + surface degraded source in payload`

---

## 块 2（~90 分钟）· P1.1 词边界 + P1.2 framing【golden 连做，最后一起重生成哈希】
**这两块共享一次 golden 重生成，务必连做。**

### 2a. P1.1 英文词边界（moderate）
- 5 个静态调用点全是 `term.lower() in text` 同款：`categorization.py:27`(infer_stance)、`:41`(_event_category)、`:50`(_event_category_reason)、`scoring.py:410`(_impact_hits)、`:413`(_matched_impact_terms)。另 `prefilter.py:46`(relevance) 同病但词来自运行时 query。
- 做一个共用 helper `_term_hit(term, text)`：
  - **ASCII 纯字母数字词** → 用 `\b` 词边界正则（`re.search(r'\b'+re.escape(term)+r'\b', text)`）。
  - **含 CJK 字符 或 含连字符的 ASCII 词**（如 `gpt-4`、`open-source`）→ 走子串 `in`（CJK 无词边界；`\b` 会在连字符处错误切分）。
  - 判据：`term` 是否全 ASCII 且 `term.isalnum()` 之类——含 `-`/CJK 走子串分支。
- 五处（含 prefilter 视情况）改为调 `_term_hit`。放 helper 到合适公共位置（如 categorization 或一个小 util，两文件都 import）。
- 加单元断言："Iran warns retaliation" 不命中 `war`、"bank" 不命中 `ban`、但 "war" 词本身命中 `war`；`gpt-4` 仍子串命中。

### 2b. P1.2 framing article_ids 不串桶（moderate）
- 病症：`_stance_evolution`(`scoring.py:200-221`) 每期 `article_ids[bucket]` = 该期**全部** row id 不分立场；`_framing_from_evolution`(`scoring.py:222-252`) line 237 对每个立场 `extend(item["article_ids"])` → **每个立场继承全期 id**（golden 里 1 篇的 `竞争/商业` 被挂上全部 5 篇）。
- 修：`_stance_evolution` 增加 per-(period, stance) id 结构（如 `article_ids_by_stance: dict[period][stance] -> list[int]`），在 line 208-209 计数处同步填。`_framing_from_evolution` line 237 改读 `item["article_ids_by_stance"][stance]` 而非全期扁平表。
- **关键**：保留 evolution item 原有的**全期** `article_ids` 字段不变（golden `test:124` 断言它），只**新增**一个 per-stance 结构给 framing 用。这样 stance_evolution 断言不动、framing 修好。

### 2c. golden 一次性重生成
- P1.1 改后 `test:117` 的 `impact.reason=="war、strike"` 会变（war 是 warns 假阳，修完消失）；SHA-256(`test:8`) 也变。
- 跑 `pytest tests/test_local_analyze_golden.py -q` → 读失败输出里的新 digest → 更新 `test:8` 的 `EXPECTED_GOLDEN_SHA256` + `test:117` 断言为**正确**值（用真实命中的 impact 词）。
- 输入是纯静态 fixture（`_golden_rows`），可复现、低风险。**提交信息写明"移除 war/warns 假证据，golden 重生成"**。
- 验证：`pytest -q` 全绿。GitNexus impact on scoring.py/categorization.py（HIGH 预期，行为改变是有意的）。
- **提交（2 笔或 1 笔连提均可，信息分清）**：`fix(analyze): word-boundary term matching, regen golden` + `fix(scoring): per-stance framing evidence ids`

---

## 块 3（~50 分钟）· P1.3 情绪层 external_id【moderate，独立，不碰 golden】
- 病症：`SentimentPost`(`db.py:134-149`) 无稳定平台 id 列。内存路径 `compact_posts_by_platform`(`sentiment.py:138`) 用 `post["id"]`=平台字符串匹配评论 `parent_post_id`（对）；DB 路径落库丢平台 id、`id` 变自增整数，回读 `sentiment_post_to_dict:310` emit DB 整数 → 评论 `parent_post_id`(平台串) 对不上 → **刷新后评论全失联**。
- 修（触 3 函数 + model + 迁移）：
  1. `db.py:134-149` `SentimentPost` 加 `external_id: str = ""` 字段。
  2. `db.py:246-247` `sentimentpost` 迁移列表追加 `("external_id", "VARCHAR DEFAULT ''")`（项目用手写 `_migrate` + `create_all`，无 Alembic；这就是全部 schema 迁移）。
  3. `sentiment.py:163` `sentiment_post_from_dict` 落库时写入 `external_id`=平台 id。
  4. `sentiment.py:308` `sentiment_post_to_dict` emit `external_id`。
  5. `sentiment.py:138` `compact_posts_by_platform` 的 join key 从 `post.get("id")` 改用 `external_id`，让内存/DB 两路都用同一稳定串。
  6. 顺带：空 url 帖每次重跑重复插入 → 去重键用 `platform+external_id`。
- 验证：`pytest tests/test_sentiment_layer.py -q` + 加"落库再回读评论仍关联到帖"的测试（内存 SQLite，不碰真实库）。`pytest -q` 全绿。
- **提交**：`fix(sentiment): add external_id so comments survive DB reload`

---

## 块 4（~70 分钟）· value_lens.py 后端生产者【喂活前端 chip，依赖块 2 已修】
**为什么排最后**：依赖 P1.1 词边界修完（否则透镜建在假证据上）。
- 新模块 `backend/app/pipeline/value_lens.py`，纯函数、无 LLM，复用现有信号（探查确认全是 plain data）：
  - `suspected_hype`/`availability_high`：pickup 代理（`scoring.py:143-147`/event 上 `source_count`/`article_count`）高 + substance 低。
  - `suspected_herding`：`narrative_signals.detect_narrative_signals`(`narrative_signals.py:17`) 多家同报 → 标为**可能信息瀑布不是证据增强**。
  - `small_sample`：复用"样本不足"(`scoring.py:256-258` total<6) + sentiment confidence(`sentiment.py:247`)。
- **前端契约（Claude 已上线，严格对齐别改字段名）**：
  `info_value_labels: [{code, label, note, severity}]`
  - `severity` 恒 `"hint"`。
  - `code` 前端已有配色：`suspected_hype`(疑似造势)/`availability_high`(可得性偏高)/`suspected_herding`(疑似羊群)；`small_sample`(样本不足) 走中性默认色也 OK。
  - `label` 中文短词，`note` 一句话（前端 tooltip）。
- **挂载点（避开 golden，探查确认安全）**：
  - `payloads.py:82-105` `article_payload` 加 `info_value_labels` 键（模仿现有 `category`/`category_reason` 追加方式）。
  - `report.collect_seeds`(`report.py:204-215`) 加键 → 流向报告/邮件日报。
  - **别碰 `analyze_topic` 返回 dict**（触发 golden 重算）。
- 红线：阅读提示不是真理裁决、不做投资建议、降级留痕。
- 验证：`pytest` 加 value_lens 纯函数单测（直接喂输入断标签）+ 一个 article_payload 带标签的断言。`pytest -q` 全绿。**注意字段形状要能对上 `frontend/src/types/dossier.ts:315` 的 `InfoValueLabel`**（GPT 别改 frontend，只对齐形状）。
- **提交**：`feat(value-lens): local behavioral-finance info-value labels on articles and seeds`

---

## 时间盒总览与落后预案

| 块 | 预计 | 累计 | 难度 | golden |
|---|---|---|---|---|
| 0 基线 | 10m | 0:10 | — | — |
| 1 OpenAlex | 25m | 0:35 | trivial | 否 |
| 2 词边界+framing | 90m | 2:05 | moderate×2 | **是（一次重生成）** |
| 3 情绪 external_id | 50m | 2:55 | moderate | 否 |
| 4 value_lens | 70m | 4:05 | moderate-involved | 否 |

**落后预案（时间不够就停在整块边界，绝不留半块未验证）**：
- 若 2:05 时块 2 还没干净收尾（golden 没重生成成功）→ 优先把块 2 做完并绿，**块 3/4 留给下一轮**。证据链正确性 > 新功能。
- 块 4 value_lens 若开头发现信号组合比预期复杂 → 先只做 `suspected_herding`（最直接，narrative_signals 现成）一个标签打通全链路（后端产出→payload→前端 chip 真实显示），其余标签留下轮。**打通一条真链路 > 铺四个半成品。**

## 收尾（每块都做）
- 每块提交前：`pytest -q` 全绿 + 相关 targeted 测试红→绿留痕。
- 每块结果写 `spec/CHANGELOG.md`。
- 全部完成后在 `.agent-bridge/TO_CLAUDE.md` 汇报：哪些块完成、value_lens 产出的 code 集（Claude 核对是否和前端 chip 配色对上）、golden 新 sha、剩余风险。
- **不合并 master、不推 origin**——人类晨审决定。
