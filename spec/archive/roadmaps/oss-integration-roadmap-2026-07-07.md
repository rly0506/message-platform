# 开源项目落地规划(2026-07-07)

状态:**规划,待人类拍板**。回答"推荐的开源项目都没用上"。基于三路真实源码探查(file:line 已核实),把每个项目对到一个真实缺口 + 挂载点 + 工作量。按北极星三支柱(发现/分析/认知)组织,不按项目名。

---

## 先对账:哪些用了、哪些没用(诚实)

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| **taste-skill** | 🟡 **部分用了** | token 系统已定义(style.css:1-70)、DiscoveryPanel 已重排;但 style.css 主体迁移 **<5%**,MediaPanel 等零重排 |
| **行为金融学**(用户课程) | ✅ **用了** | 变成 `value_lens.py`(可得性/羊群/造势/小样本标签),已上 master |
| **SearXNG** | ❌ 零代码 | 全 backend grep 无匹配,只在计划文档 + 一个前端标签 |
| **Scrapling** | ❌ 零代码 | fulltext.py 只有 trafilatura 三方法,无 Scrapling 分支 |
| **last30days-skill** | ❌ 没建 | 发现层有 delta/加速(store.py),但是"相对上次快照"非"固定时间窗研究" |
| **cheat-on-money 校准闭环** | ❌ 没建 | marks 存了(CognitionMark)但只做队列过滤,profile 静态、confidence 从不由行为更新 |
| **logseq/AppFlowy** | ❌ 没碰 | 认知地图交互参考,无实现 |
| **tikhub** | ⏸ 缓 | 民间层采集替代,等使用期证明民间层被用 |
| **ian-xiaohei 插画** | ❌ 没用 | 前端零插画;仅适合空状态/概览头,数据表区会打架 |

**结论**:不是"都没用上",是**贴主线的两个(taste-skill/行金)用了但没做完,剩下的多是独立能力线还没排期**。下面按支柱排。

---

## 支柱一:分析(让已搜到的事更可读、正文更全)

### 1.1 【taste-skill 收尾】MediaPanel 可读性重排 —— 中等,高价值
- **缺口**:token 定义 100% 但 style.css 主体迁移 <5%;**MediaPanel(1021 行、零 scoped 样式、全靠全局 CSS)是最大未重排目标**。时间轴(`.timeline-node` style.css:1363)/来源矩阵(`.source-matrix-*` style.css:1620)/文章行(`.article-row` style.css:1088)/实体组全是密集表格式、硬编码色。
- **做**:延续 DiscoveryPanel 的编辑风原则,给 MediaPanel 加 scoped 样式或迁全局块到 token;主视图拉层次(主信息大、次要折叠),数据表保持信息密度但加呼吸。
- **顺带**:AcademicPanel/SentimentPanel 同样零 scoped、待重排(优先级次于 MediaPanel)。
- **谁**:Claude(前端地盘)。**红线**:保 e2e 类名或同提交改测试;数据表区不塞插画。

### 1.2 【SearXNG + Scrapling】破全文天花板 —— 中等,高杠杆(数据线)
- **缺口**:主源 gnews 给的是 `news.google.com/rss/articles/CBMi...` 跳转链接,无解码代码(探查确认 backend 零 redirect-resolution),`extract_url_proxied` 抓到的是 Google 中间页非正文 → 情绪徽标/单篇透视这类全文功能对主源 100% 失效。
- **做(两段一条线)**:
  - **SearXNG**(docker 服务,不是抄代码):新采集器 `collectors/searxng.py`,`collect_searxng(q)` 打自托管实例 `/search?format=json`,发 rss 同款 dict(`rss.py:93-103` 键、`collector="searxng"`),接 `collect_topic` 每查询循环(`topic_ops.py:77`)。拿**真实文章 URL** 进 `Article.url`,绕开 gnews 跳转。config 加 `SEARXNG_URL`/`USE_SEARXNG`(默认关)。
  - **Scrapling**(`pip install`):`fulltext.py` 加 `extract_url_scrapling(url)`,StealthyFetcher 取 HTML→复用 `extract_from_html`(:75)。接单点 `topic_ops.py:284`,`FULLTEXT_USE_SCRAPLING`(默认关)。**红线:只抓公开/反爬页,不破付费墙**。
- **谁**:GPT(后端)。**先 spike**:起 SearXNG docker 实测一周直链率+正文成功率,再决定接主链路。
- **价值**:抓取成功率↑ → `fulltext_hits`↑ → 能打情绪分的文章↑(现在无 body 强制 emotion=-1)。这是"分析质量天花板"最大单点杠杆。

---

## 支柱二:认知(项目唯一护城河,差异化灵魂)

### 2.1 【cheat-on-money 校准闭环】marks → profile,越用越准 —— 中等,战略级
- **缺口(最值得做的一件)**:`CognitionMark` 存了(api.py:655),但**只被前端当队列过滤器**(DiscoveryPanel.vue:138 掉 known),标完即丢。`CognitionProfile`(db.py:174)**完全静态**——confidence/depth 只由种子默认或手动 PUT 设,**从不由行为更新**。spec 自己承认"profile is not yet continuously calibrated"。
- **cheat-on-money 的可迁移机制**:预期→执行→记录实际→累积 lessons 让推荐越来越准。映射:
  - **预期** = profile 的 confidence/depth(系统对某域"你懂多少"的预测)。
  - **实际** = 用户 mark(对系统判"边界外"的种子点"我懂了" = 预期与实际的 delta)。
  - **缺的循环** = mark 后回写 profile。**挂载点:`upsert_cognition_mark`(api.py:655)** 持久化 mark 后,解析种子 domain→domain_key,微调该 `CognitionProfile` 行的 confidence/depth。
- **做(V1 极简)**:①mark 存 domain(现在只存 target_key=url,后端需补 seed→domain 解析,现只在前端 `profileForSeed` 做);②`upsert_cognition_mark` 后按 label 轻推 confidence(known→该域+、doubtful→标记存疑不加);③`evidence` 字段追加一条"何时因何调整"的 lessons 痕迹。
- **谁**:GPT 后端(回写逻辑)+ Claude 前端(boundaryScore 消费校准后的 confidence)。
- **红线(灵魂,焊死)**:校准目标是**戳盲区、反回音壁**,不是"推你已认同的"。confidence 升不等于"少推这个域",要防滑向回音壁(见 cognitive-map-direction)。**先对话验证机制价值,再产品化**(cognition-test-framework)。

### 2.2 【logseq/AppFlowy】认知地图交互 —— 大件,排后
- **缺口**:marks 累积中但没有"认知地图"可视化;用户看不到自己的认知版图/盲区分布。
- **借**:logseq/AppFlowy 的**本地优先 + `[[双链]]`让图谱从小连接长出来**的交互思想(不接依赖、不装那两个 Electron 应用)。
- **判断**:两位 AI 早共识**排在信息架构稳定 + marks 攒够之后**(#5 关系图同类)。V1 别上大可视化,先让 2.1 的校准闭环把 marks 用起来,地图是它成熟后的表达层。**本轮不做**。

---

## 支柱三:发现(让"叫不出名字的事"冒出来)

### 3.1 【last30days-skill】时间窗研究范式 —— 小-中等,可选增强
- **现状**:发现层已有加速/delta(store.py score),但那是"相对上次快照"的跨run记忆,**不是"某主题最近30天发生了什么"的固定时间窗研究**。两者不同。
- **last30days 的范式**:给定一个主题,研究它在固定时间窗内的动态,成文报告。
- **可能落地**:不是替换发现层,是**给"深入某个种子"加一层**——点种子深入时,除了现有的 distill→搜索,可选跑一次"这个主题最近 30 天"的时间窗汇总。或给追踪话题做"最近 N 天变化"摘要。
- **判断**:**低优先**。发现层日报刚上线自动化,先收几天看内容够不够解渴(见 casual-open-painpoint 的下一步判断),再决定要不要加时间窗研究。别在验证前堆功能。

### 3.2 【tikhub】民间层采集替代 —— 缓,等信号
- **现状**:民间层靠 OpenCLI+Chrome 不稳(WinError 类问题反复)。tikhub 16+ 平台 API、$0.001/请求,能替换 + 补微信公众号。
- **判断**:维持"缓"。**等 30 天使用期证明民间层真的被用**,再充最小档试点。别为没被用的能力接第三方付费依赖。

---

## 独立:ian-xiaohei 插画 —— 条件性,小
- **现状**:前端零插画。探查确认唯一合适位置是**空状态**(MediaPanel.vue:663/788/917 等纯文字空态)和概览头部,数据表区会和极简方向打架(用户已砍花哨)。
- **判断**:**排在 MediaPanel 重排(1.1)之后**。若重排后空状态显得干,再给 2-3 个关键空态加"小黑"黑线插画点缀。费 API、非主线,可选。

---

## 优先级总排(建议)

| 优先 | 项目 | 支柱 | 谁 | 为什么这个位置 |
| --- | --- | --- | --- | --- |
| **P1** | 1.1 MediaPanel 重排 | 分析 | Claude | taste-skill 收尾,直接服务"打开欲";最大未重排面 |
| **P1** | 2.1 校准闭环 V1 | 认知 | GPT+Claude | 唯一护城河;marks 已在流动只差回写 |
| **P2** | 1.2 SearXNG+Scrapling | 分析 | GPT | 全文天花板最大杠杆;但需先 spike 验证 |
| **P3** | 3.1 last30days 时间窗 | 发现 | GPT | 等日报使用验证后再定 |
| **P3** | 插画空状态 | — | Claude | 1.1 之后的点缀 |
| **缓** | 2.2 认知地图 / 3.2 tikhub | 认知/发现 | — | 等 marks 攒够 / 等民间层被用 |

**一句话**:先做 **1.1(前端重排收尾)+ 2.1(校准闭环)**——一个让产品"想打开",一个是差异化灵魂,都建在已有地基上、不需新数据源。SearXNG/Scrapling(1.2)是下一波数据线杠杆,但先 spike。其余等真实使用信号再排。

**红线不变**:无 LLM 可跑 / 结论回证据 / 降级留痕 / 不写真实库 / 反回音壁不做成回音壁。
