# GPT 后续迭代路线图(2026-07-07)

状态:**交 GPT 执行,人类审后接**。机制经两路源码探查核实(file:line 准确,反映 P1+value_lens 已上 master 后的现状)。承接 `spec/archive/roadmaps/oss-integration-roadmap-2026-07-07.md` 的 P1/P2。

**分工**:GPT 只碰 `backend/` + `docs/` + `spec/CHANGELOG`;Claude 做前端(校准闭环的前端半 + 继续重排)。按目录切死。
**硬约束**:不合并 master/不推 origin(人类决定);不写真实库;每步独立提交+门禁;改符号前 GitNexus impact;降级留痕。

执行顺序:**阶段 0 债务清扫(热身,低风险) → 阶段 1 校准闭环 V1(头号,战略级) → 阶段 2 SearXNG+Scrapling(数据线,需先 spike)**。时间不够停在整块边界。

---

## 阶段 0 — 债务清扫(约 1 小时,逐条独立提交,都不碰 golden)

热身,清掉探查确认仍在的债。按性价比:

**0.1 未校验 int() 三处 500**(api.py:933/373/779)
- `parse_article_ids` 的 `int(part)`、`update_topic` 的 `int(project_id or 0)`、`project_for_topic_payload` 的 `int(project_id)` 都无 try/except,非数字输入→未处理 500。项目已有 `clamp_int`(api.py:898-903)但这三处没用。
- 修:三处套安全解析(非数字→400 或忽略,按语义)。加测试。

**0.2 空白 query 建空名话题**(schemas/search.py:9)
- 空串已被 `min_length=1` 挡,但**纯空白 `"   "`(len 3)仍过**,`search_service.py:225-229` strip 后建空名话题。
- 修:schema 加 strip 或 search_service strip 后二次校验空则拒。

**0.3 topic 改名后综述丢失**(api.py:941/961/983 + cross_synthesis.py:213)
- `latest_academic_summary` 等按 `SearchJob.query == f"academic:{topic.name}"` 查,job 存的是**建时的名**,改名后新名查不到旧 job;`topic_id` 二次检查救不回已被 name 过滤掉的行。**影响学界+民间+三方对照三处**(比原审计记的更广)。
- 修:按 topic_id 查(job 落 topic_id 或用可稳定关联的键),别按易变的 name。

**0.4 daily-email Windows 崩**(daily_email.py:167)
- `run_agently_cli` 的 `subprocess.run(["agently-cli"...])` 无 shell,Windows 上 `agently-cli.cmd` 找不到→WinError 2。`--send`(Agent Mail)路径崩,`--send-smtp` 不受影响。**修法现成**:`reddit_sentiment.py:37-40` 的 `_opencli_args` 有 `cmd /c` shim,照搬。
- 加 monkeypatch subprocess 的测试验 Windows 分支命令拼对(别真发信)。

**0.5(可选,低危攒批)**:rss.py:62 mktime DST(改 `datetime(*t[:6])`)、rss.py:125 gnews 部分 locale 静默失败(部分失败也该 payload 留痕)、reddit_sentiment cmd 元字符 `&|^` 截断(query 含 `&` 无空格时不被引号包)。时间够才做。

---

## 阶段 1 — 认知校准闭环 V1(头号,marks→profile 回写,借 cheat-on-money 机制)

**为什么是头号**:这是项目唯一护城河(反回音壁认知拓展),且 marks 已在流动、profile 字段齐全,只差"回写"这一步。探查确认:**profile 零行为更新,marks 标完只做前端队列过滤即丢**。

**cheat-on-money 机制映射**:预期(profile.confidence/depth)→ 实际(用户 mark)→ 累积(回写 profile + evidence 留痕)→ 越用越准。

**探查确认的现状与缺口**:
- `CognitionProfile`(db.py:174-186)字段齐全(depth/interest/confidence/evidence/recommended_seed_style),唯一写入是手动 PUT(api.py:722)。
- `CognitionMark`(db.py:162-171)**无 domain 列**,seed mark 只存 `target_key`=URL。
- seed→domain 解析现在**只在前端** `profileForSeed`(DiscoveryPanel.vue:271);但**种子 payload 本身已带 `domain`/`domain_label`**(report.py:203-209)——这是关键,domain 现成、只是没落到 mark 上。
- 迁移:`_migrate`(db.py:234-303)的 adds 字典 + PRAGMA/ALTER 守卫;`cognitionmark` 块在 db.py:251-254。

**做(V1 极简)**:
1. **mark 存 domain**:`CognitionMark` 加 `domain` 列(db.py:162-171 model + db.py:251-254 迁移块加 `("domain","VARCHAR DEFAULT ''")`);`CognitionMarkRequest`(schemas/search.py:40-46)加可选 `domain`;`upsert_cognition_mark`(api.py:655)存它。
2. **交接契约(Claude 前端配合)**:种子 mark 由前端 `saveCognitionMark` 带上 `domain`(前端已有 `profileForSeed` 解析 + seed.domain 现成)。**GPT 只需接收并存 domain 字段名 `domain`,Claude 负责前端传。**
3. **回写 profile**:mark 持久化后(api.py:655 尾部或独立 `recalc_profile_from_mark`),按 domain→domain_key 找到 `CognitionProfile` 行,按 label 轻推:`known`→confidence 小幅+(如 +5,clamp≤100);`doubtful`→不加分(标记存疑);`unfamiliar`→小幅-。**幅度小、可累积,别一次跳大。**
4. **lessons 留痕**:`evidence` 字段追加一句"何时因何调整"(如"2026-07-08 标记 energy 种子已懂 confidence 55→60"),对应 cheat-on-money 的 lessons.md。
5. 测试:内存 SQLite,验"mark known 后该域 confidence 上升 + evidence 有痕",不写真实库。

**红线(灵魂,焊死)**:
- **回写只更新事实(用户表示懂了/存疑),不在后端决定"高 confidence 就少推该域"**。boundaryScore 怎么用 confidence 是前端+人类的产品判断。**反回音壁**:目标是戳盲区,不是喂已认同的——GPT 别在后端加任何"降权已懂域"逻辑。
- 无 LLM 纯规则;可逆可审(evidence 留痕,用户看得到为什么变)。

---

## 阶段 2 — SearXNG + Scrapling 数据线(破全文天花板,需先 spike)

**为什么**:主源 gnews 给跳转链接、正文抓不到(探查确认无解码代码),限制情绪徽标/单篇透视。SearXNG 拿真 URL,Scrapling 抓反爬公开页。**探查确认全新、挂载点干净**。

**2.1 SearXNG 采集器**(docker 服务,非抄代码)
- 新 `collectors/searxng.py`:`collect_searxng(q)` 打自托管实例 `/search?format=json`,发 rss 同款 dict(rss._parse_feed 键、`collector="searxng"`)。
- 接 `collect_topic` 每查询循环第三个分支(topic_ops.py:77-100,仿 gnews/gdelt 块),`collect_topic` 加 `searxng_on: bool=False` 参数(仿 gdelt_on)。
- config 加 `SEARXNG_URL=os.getenv("SEARXNG_URL","").strip()` + `USE_SEARXNG`(truthy-string,默认关,仿 config.py:54)。
- **先 spike**:起 SearXNG docker 实测一周直链率+正文成功率,再决定接主链路。默认关、仅代码就位。

**2.2 Scrapling 全文变体**(`pip install scrapling`)
- `fulltext.py` 加 `extract_url_scrapling(url)`:StealthyFetcher 取 HTML→复用 `extract_from_html`(fulltext.py:75)→保 Extracted 契约。惰性导入不可用则软降级(仿 `_trafilatura`)。
- 接单点 `topic_ops.py:284`(`_fetch_bodies._one`),按 `FULLTEXT_USE_SCRAPLING`(默认关)选变体。
- **红线:只抓公开/反爬页,不破付费墙**。
- 测试:monkeypatch httpx DummyClient(仿 test_openalex_collector.py:72-122)验 dict 键;monkeypatch scrapling 不可用验软降级(仿 test_fulltext.py:45-79)。

**关联 GDELT**:已接默认关(topic_ops.py:88-99,gdelt_on)、429 退避已编码(gdelt.py:40-44)。政治时事"报道量加速"方向要用它时,是开 flag + 住宅 IP 冷却,非新建——本轮不动,记着。

---

## 优先级总排

| 阶段 | 内容 | 难度 | golden | 谁 |
| --- | --- | --- | --- | --- |
| 0.1-0.4 债务 | int 500/空白query/改名综述/daily-email | trivial-moderate | 否 | GPT |
| 1 校准闭环 V1 | marks→profile 回写(+前端传 domain) | moderate | 否 | GPT+Claude |
| 2 SearXNG+Scrapling | 全文天花板(先 spike) | moderate | 否 | GPT |

**一句话**:先清债(阶段0热身)→ 做校准闭环(护城河,和 Claude 前端配合传 domain)→ SearXNG/Scrapling 先 spike 再接。都不碰 golden、风险可控。落后就停在整块边界。

**待 GPT 回**:①校准闭环的 domain 交接(前端传 vs 后端解析)认不认?②回写幅度/反回音壁红线认不认?③从阶段 0 哪条起手?
