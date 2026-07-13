# 双方方向草稿(2026-07-07)—— Claude 拟,待人类拍板

状态:**Claude 起草,人类审后才进 `.agent-bridge/TO_CODEX.md` 交 GPT**。承接 `spec/archive/roadmaps/oss-integration-roadmap-2026-07-07.md` / `spec/archive/roadmaps/gpt-next-iteration-2026-07-07.md`,但按本轮两路源码探查(file:line 已核实)**修正两处路线图错误**、并**重排头号**。

**北极星(不许跑偏的锚)**:反回音壁的认知拓展(护城河)· 诚实、有证据链的数据(不造可信假象)· 补"打开欲"低意图入口 · **不做成瘾 feed**。任何一步偏离这四条,停下来问人。

---

## 一、先纠两处地基事实(探查实证,推翻旧计划假设)

### 纠错 A — 校准闭环有个隐藏死结:两套 domain 词表不通
- 种子 payload 的 `domain` = `tech/finance/geopolitics/science/society/other`(report.py:32-39,`_DOMAIN_LABELS`)。
- `CognitionProfile.domain_key` = `ai_infra/finance/macro_finance/...`(api.py:34+)。
- **两套只有 `finance` 重合**。旧路线图"domain 现成、落到 mark 上就能回写"**不成立**——没有可 join 的键。
- **修正**:校准闭环的**第 0 步 = 建一张 seed-domain → profile-domain_key 的映射表**(GPT 后端),映射不上的落 `other`/不回写并留痕。这一步不做,后面回写逻辑全是空转。

### 纠错 B — value_lens 只发 4 维,没有"框架"
- 实际发出:`疑似造势 / 可得性偏高 / 疑似羊群 / 样本不足`(value_lens.py:9-40),两个 key 撞同一 `availability_high` code。**无 framing 标签**。
- **修正**:事件网络的"共享维度边"**按现存 4 维设计**,不按想象的 6 维。要不要补 framing 是独立小任务(GPT),不阻塞网络图。

### 已实证为真(维持旧判断)
- **全文天花板是结构性的、不是配置事故**:gnews 发 `news.google.com/rss/articles/CBMi...` 跳转链,rss.py:83/94 原样存、零解码;唯一正文抓取器是 trafilatura 系(fulltext.py),跟着跳转进 Google 中间页抓不到正文;无 body → `emotion_score` 被代码强制 -1(topic_ops.py:378)→ MediaPanel 隐藏徽标(MediaPanel.vue:817)。数据缺口一路传到 UI。
- **校准闭环确实零行为回写**:CognitionProfile 只有两个写入者(api.py:840 默认 / api.py:722 手动 PUT),都不读 marks;CognitionMark 无 domain 列,只存 target_key=url。

---

## 二、头号之争:我(Claude)的诚实反对与重排建议

**你上轮选了"事件影响网络"当头号。基于实证,我反对把它当头号,理由是结构性的:**

事件网络是**建在数据之上的展示层**。现在喂它的东西是:主源正文 100% 抓不到、无 body 文章 emotion 一律 -1。拿这种残缺信号连出来的"影响网络",会产出**看着可信、实则错**的关系图——这正是北极星第二条("不造可信假象")最怕的。

**先把喂它的东西喂对、喂全,再画图。** 所以重排:

| 位置 | 内容 | 支柱 | 谁 | 为什么 |
| --- | --- | --- | --- | --- |
| **头号** | 校准闭环 V1(含纠错 A 的映射表) | 认知(护城河) | GPT 后端 + Claude 前端 | 唯一护城河;marks 已在流动,只差回写;是北极星第一条的本体 |
| **并列头号** | 全文天花板 spike(SearXNG + gnews 解码 + Scrapling) | 数据线 | GPT | "分析质量天花板最大单点杠杆";喂对数据是一切展示层的前提 |
| **次** | MediaPanel 可读性重排(taste-skill 收尾) | 打开欲 | Claude | 最大未重排面;直接服务低意图入口 |
| **降级** | 事件影响网络 V1 | 展示 | Claude | 建在数据之上;锁死"结构视图"版,不冒充因果 |

**我不拦你坚持先画网络图**——但若坚持,焊死在下面的约束里。

---

## 三、并行分工(按目录切死,两边不互相阻塞)

**GPT = `backend/` + `docs/` + `spec/CHANGELOG`;Claude = `frontend/`。** 硬约束不变:不合并 master / 不推 origin(人类决定)· 不写真实库 · 每步独立提交+门禁 · 改符号前 GitNexus impact · 降级留痕 · 无 LLM 可跑 · 结论回证据。

### GPT 轨 A —— 数据线(破全文天花板,先 spike)
1. **SearXNG 采集器**:新 `collectors/searxng.py`,`collect_searxng(q)` 打自托管实例 `/search?format=json`,发 rss 同款 dict(`collector="searxng"`);接 `collect_topic` 每查询循环(topic_ops.py:77,仿 `gdelt_on` 加 `searxng_on` 分支);config 加 `SEARXNG_URL`/`USE_SEARXNG`(默认关)。拿真实文章 URL 绕开 gnews 跳转。
2. **gnews URL 解码**(spike 的一部分):在 `_fetch_bodies`(topic_ops.py:269)抓 body 前,把 `news.google.com/rss/articles/...` 解到发布方真链;解不出留痕降级。
3. **Scrapling 变体**:`fulltext.py` 加 `extract_url_scrapling(url)`,StealthyFetcher 取 HTML → 复用 `extract_from_html`(:75);接 `_fetch_bodies._one`(topic_ops.py:284),`FULLTEXT_USE_SCRAPLING`(默认关)。**红线:只抓公开/反爬页,不破付费墙。**
4. **先 spike**:起 docker 实测一周直链率 + 正文成功率,再决定接主链路。默认关、仅代码就位。
- **验证信号**:`fulltext_hits`↑ → 能打 emotion 的文章↑(现在无 body 强制 -1)。

### GPT 轨 B —— 校准闭环 V1(护城河,借 cheat-on-money 机制)
0. **(纠错 A,前置必做)** 建 seed-domain(tech/finance/…)→ profile-domain_key(ai_infra/finance/…)映射;映射不上落 `other`、不回写、留痕。
1. **mark 存 domain**:CognitionMark 加 `domain` 列(db.py:162 model + 迁移块);schema 加可选 `domain`;`upsert_cognition_mark`(api.py:655)存它。
2. **回写 profile**:mark 持久化后,按映射后的 domain_key 找 CognitionProfile 行,按 label **轻推**:`known`→confidence 小幅+(如 +5,clamp≤100);`doubtful`→不加分(标存疑);`unfamiliar`→小幅-。幅度小、可累积。
3. **lessons 留痕**:`evidence` 追加一句"何时因何调整"(对应 cheat-on-money 的 lessons)。
4. 测试:内存 SQLite,验"mark known 后该域 confidence 升 + evidence 有痕",不写真实库。
- **灵魂红线(焊死)**:回写**只更新事实**(用户表示懂了/存疑),**后端绝不加"高 confidence 就少推该域"逻辑**——那是滑向回音壁。boundaryScore 怎么用 confidence 是前端 + 人类的产品判断。**先对话验证机制价值,再产品化。**

### Claude 轨 —— 前端(三件,按序)
1. **校准闭环前端半**(配合 GPT 轨 B):`saveCognitionMark` 带上 `domain`(前端已有 `profileForSeed` + seed.domain 现成);boundaryScore 消费校准后的 confidence。**交接契约:前端传 `domain` 字段,GPT 只接收存储。**
2. **MediaPanel 可读性重排**(taste-skill 收尾):延续 DiscoveryPanel 编辑风,给 MediaPanel(1021 行、零 scoped)加 scoped 样式 / 迁全局块到 token;主视图拉层次,数据表保密度加呼吸。**红线:保 e2e 类名或同提交改测试;数据表区不塞插画。**
3. **事件影响网络 V1 —— 锁死"结构视图"**(降级项,数据线见效后再重):
   - **只做"标签 + 共享维度边"**:边 = "这两件事共享某个结构特征(如都被标可得性偏高)",**不是**"A 导致 B"。**绝不画因果箭头。**
   - **维度用现存 4 个**(造势/可得性/羊群/样本不足),不用想象的 6 个;标不出的维度不画边——宁可 3 条真边,不要 14 条凑数。
   - **纯本地起步可接受,但降级/低置信必须在 payload + UI 上标出**——糊的标签不能和硬证据长一样。

---

## 四、待人类拍板(三问)
1. **头号**:认我的重排(校准闭环 + 数据线并列头号,事件网络降级为结构视图)?还是坚持事件网络当头号(那就锁死结构视图版)?
2. **纠错 A 的映射表**:认"校准闭环前置先建 domain 映射"这一步?(不做则回写空转)
3. **起手**:GPT 从轨 A(数据线 spike)还是轨 B(校准闭环)先起?我的建议:**轨 B 先起**(护城河、不需新数据源、风险最低),轨 A 的 SearXNG 需要你先起 docker 实例才能 spike。

拍板后我把它整理进 `TO_CODEX.md` 交 GPT。
