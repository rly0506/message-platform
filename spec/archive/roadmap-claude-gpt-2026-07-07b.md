# Claude × GPT 分工路线图(2026-07-07 第二版)—— 待人类审

状态:**Claude 拟,plan-mode 产出,待人类拍板**。基于本轮四路源码探查(file:line 核实),修正前两版路线图两处过时假设。承接 `direction-plan-2026-07-07.md`。

**北极星(锚)**:反回音壁认知拓展(护城河)· 诚实有证据的数据 · 补打开欲 · 不做成瘾 feed。

---

## 零、探查修正:两处路线图过时假设(必读)

### 修正 1 —— 事件影响网络**已经建好、已上线、e2e 已覆盖**(不是待办)
前两版和我自己的 direction-plan 都把"事件影响网络 V1"当未来大件。**错**。它是 live Vue 组件:
- `MediaPanel.vue:130-201` `eventNetwork` computed:建 node + edge(时间顺序/共享 cluster/共享对象/共同来源),封顶 24 边。
- `MediaPanel.vue:665-697` 模板渲染(`.event-network-panel/-node/-edge`)。
- `MediaPanel.vue:671` 硬编码护栏文案:"本地证据边,不显示 LLM 因果假设"——**已经就是"结构视图/无因果箭头"版**,正是我上一版想加的红线,它早已在。
- e2e `source-matrix.spec.ts:764-818` 断言 node/edge 渲染;CSS `style.css:2680-2826` 已 token 化(c047749)。
- **结论:事件网络不排新工作,至多 polish。它已守住反回音壁红线。**

### 修正 2 —— MediaPanel 重排已完成,但走的是全局 CSS token 收敛,非 scoped
`c047749` 迁了 ~89 硬编码色进全局 `style.css`,**没加 scoped `<style>` 块**(grep 确认 MediaPanel.vue 无 `<style>`)。可读性目标达成(token 化 + 层次 + 呼吸),build + 40 e2e 绿。**判断:够用,不为 scoped 而 scoped**。AcademicPanel/SentimentPanel 同样零 scoped、待同法重排。

---

## 一、本轮头号(我立刻做):校准闭环前端半 + confidence 方向定音

GPT 后端半已落地(domain 列 + 映射表 + 轻推回写 + 反回音壁守卫,见 TO_CLAUDE)。前端接线小而清,但含一个方向决策(人类已授权我拍:**中性化**)。

**探查确认的现状**:
- `saveCognitionMark`(dossierApi.ts:141-148)payload **无 domain**;调用点 `App.vue:804` `markSeedCognition` 也没传。
- `CognitionMark` 类型(dossier.ts:338-347)**无 domain**;后端现在会回传 domain。
- `seed.domain` / `seed.domain_label` **前端现成**(DiscoverySeed 类型 dossier.ts:583/621;DiscoveryPanel 已用)。
- 标记后**不 refetch profile**——`markSeedCognition` 只更新本地 mark 缓存,confidence 回写后前端看不到,要整页重载才刷新。
- `boundaryScore`(DiscoveryPanel.vue:290-302)有 `confidenceBoost`:confidence≥70→+8、≥55→+4。**这是回音壁隐患**:标"已懂"抬 confidence → 该域种子排更前。

**做(逐步,独立可提交)**:
1. **传 domain**:`saveCognitionMark` payload 类型加可选 `domain?: string`(dossierApi.ts:141);`markSeedCognition` 调用点传 `domain: seed.domain`(App.vue:804)。
2. **类型补 domain**:`CognitionMark` 加 `domain?: string`(dossier.ts:338)——后端回传,类型对齐。
3. **闭环 refetch**:`markSeedCognition` 成功后 `await fetchCognitionProfile()` 刷新 `cognitionProfile.value`,让画像证据(confidence)即时反映回写。**不整页重载**。
4. **confidence 方向 = 中性化**(人类授权,我拍):**去掉 `confidenceBoost`**(DiscoveryPanel.vue:301-302),保留 `interestBoost`(想看→+16,干净的"想要更多"信号)。confidence 仍在 `profileEvidenceText` 显示("confidence 70%"),只是**不再暗中重排 feed**。
   - **理由**:confidence(懂多少)≠ interest(想不想看),你们画像 V1 已见"深度≠兴趣"。让 confidence 回到"透明告知",不做"越懂越推"的回音壁闭环。方向留给认知测试验证后再定要不要回排序。**最可逆**。
5. **测试**:扩 `discovery-cognition.spec.ts`——①`savedMark` 断言加 `domain: 'energy'`(锁交接契约,现用 toMatchObject 部分匹配不会破);②加一条"标记 known 后 refetch、画像 confidence 更新可见"的断言(mock 第二次 profile 返回升后的值)。
   - **e2e 安全性已核**:去 confidenceBoost 不破现有排序断言——energy(边界外、signal 88)仍排 finance(signal 65)前;且去 boost 对已懂的 finance(78→−8)扣得比 energy(58→−4)多,反而强化反回音壁,`boundary-list.first()===energy` 保持绿。

**红线**:保 e2e 类名;confidence 方向改动写进 commit body 说明"中性化、可逆";不碰后端。

---

## 二、分工原则(按目录切死,并行不阻塞)

- **Claude 主责**:前端体验 · 产品语义 · 视觉可读性 · 排序/推荐的产品判断(如 confidence 方向) · 反回音壁的前端表达。地盘 `frontend/`。
- **GPT 主责**:后端链路 · 测试门禁 · 证据正确性 · 降级留痕 · 集成风险。地盘 `backend/` + `docs/` + `spec/CHANGELOG`。
- 每阶段互审;不混提交;不提交 `.agent-bridge/`/`.agents/`/真实 `.env`·`dossier.db`/gitnexus 幽灵(AGENTS.md·CLAUDE.md)。
- 硬约束:不合并 master/不推 origin(人类决定);每步独立提交+门禁;改符号前 GitNexus impact;无 LLM 也能跑;结论回证据;降级留痕;不写真实库。

---

## 三、阶段路线(本轮 → 下轮)

| 阶段 | 内容 | 谁 | 依赖/状态 |
| --- | --- | --- | --- |
| **本轮 P1** | 校准闭环前端半 + confidence 中性化(第一节) | Claude | GPT 后端已就位,立刻做 |
| **本轮 P1** | 校准闭环后端半复审 + 独立提交 | GPT(Claude 审) | 后端已写,等我审 domain 契约/映射/幅度 |
| **本轮 P2** | 阶段0 债务清扫(int 500/空白query/改名综述丢失/daily-email WinError) | GPT | 低危热身,不碰 golden;清单在 gpt-next-iteration:12-32 |
| **下轮 P2** | AcademicPanel + SentimentPanel token 重排(同 MediaPanel 法) | Claude | 无后端依赖,MediaPanel 法已验证,可随时起 |
| **下轮 P3** | SearXNG + gnews 解码 + Scrapling(破全文天花板) | GPT | **阻塞**:需人类先起 SearXNG docker 才能 spike;默认关、仅代码就位 |
| **polish** | 事件网络细节打磨(已上线,非新建) | Claude | 可选,低优先 |
| **缓** | 认知地图可视化 / tikhub / last30days 时间窗 | — | 等 marks 攒够 / 民间层被用 / 日报验证 |

**起手建议**:
- **Claude**:立刻做第一节(校准闭环前端半 + confidence 中性化),一个独立 commit。做完可无缝接 AcademicPanel/SentimentPanel 重排(不等任何人)。
- **GPT**:先把已写的校准闭环后端半整成独立 commit 等我审;然后阶段0 债务热身。SearXNG 等人类起 docker。

---

## 四、待人类拍板(两问)
1. **confidence 中性化**(去 confidenceBoost、保 interestBoost、confidence 仅显示不排序)—— 认不认?(我已按授权拍为默认,写进计划;你若要"翻转"或"维持",现在说。)
2. **下轮 Claude 是否接 AcademicPanel/SentimentPanel 重排**作为校准闭环之后的默认下一件?(无依赖、同法、直接服务打开欲。)
