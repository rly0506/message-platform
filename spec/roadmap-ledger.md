# 路线图总账

> 本文件是路线图状态的唯一索引。路线图正文保留当时的判断和历史语境，不因后续进展反复改写；状态变化只更新这里、`spec/roadmap.md` 和 `.agent-bridge/BOARD.md`。

## 状态定义

- `CURRENT`：当前唯一产品主线。
- `ACTIVE-GATE`：正在执行的稳定化、审计或验收关口；它可以暂时阻挡主线，但不取代主线。
- `COMPLETED`：完成了该路线图承诺的阶段目标，残余优化进入新路线图。
- `SUPERSEDED`：历史方案或草稿，已被后续路线图替代，不再直接执行。
- `REFERENCE`：成果或决策记录，不是待执行计划。
- `CANDIDATE`：已记录但尚未经过人类拍板，不得自动插入当前主线。

## 当前定位

截至 2026-07-14，当前唯一产品主线是 **RM-055 可审计信息供应链 · C 先行**，**接替 RM-050**（非并列）。RM-050 的双模式入口 M1 已完成，其未完成的 M2/M3/M4 由 RM-055 完整承接。

为什么切换主线：用户几轮"扩源"迭代后仍反馈"信息源不够、不广、不权威"。诊断表明症结不是源不够多，而是增强能力（SearXNG / gnews 解码 / Scrapling）默认全关、无真实数据验收、界面不显示本轮用了什么——"代码存在"被当成了"产品拥有能力"。因此新主线先做 C（可审计覆盖仪表 + 证据反证可见），再用真实缺口数据决定补源（A）和落正文（B）。详见 `spec/roadmap-supply-chain-2026-07-12.md`。

实际进度：

1. RM-050 `M1` 双模式入口 V1a 已由提交 `3327008` 完成：深挖队列、本地标记带、头版/事件深链和证据定位已进入基线。
2. 后端 P1 审计批已由提交 `f5bed82` 独立落地（认知画像保值、rerun 类型、自动刷新事务与互斥、类比候选新鲜度、本地分析不覆盖 LLM），全量 `308 passed, 1 warning`；未 push、未合并。
3. RM-055 `M2'` 已完成：U1 后端契约 `7922021`、前端类比卡带 `69ca3aa`，并由 `29f9cf8` 修正事件身份、异步串台和证据回链。
4. RM-055 主线 C 的 Phase 0/1/2 已完成：Phase 0 量化报告、Coverage API `dfdb9c1`、前端覆盖仪表 `4532d02`，跨层审计收口为 `29f9cf8`。
5. RM-055 `M3'` 的 `dig_later` 跨设备落库由 `98efa59` 完成，`4723b0b` 进一步加入 revision/tombstone、原子并发写、逐操作 outbox、跨标签页与崩溃恢复加固；完整测试继续证明不改变任何 CognitionProfile/CognitionMark。源扩展首批因两周纵向 Coverage 数据尚未形成，进入 `docs/operations/rm055-source-expansion-gate-2026-07-13.md` 的证据闸；不得为完成里程碑而伪造扩源理由。
6. RM-055 下一可执行产品阶段是 `M4'`（事实优先早报 + 覆盖标签 + 深链 + 今日一个领域）；源扩展观察可并行运行。

因此，项目目前处在 **RM-055 M4' 开工点**：可审计覆盖闭环与跨设备好奇心队列已经落地，源扩展在数据闸中并行观察。

## 路线图编号

| ID | 文档 | 状态 | 结论 |
|---|---|---|---|
| RM-000 | `spec/roadmap.md` | CURRENT INDEX | 当前方向摘要；必须与本总账和 BOARD 同步。 |
| RM-010 | `spec/archive/direction-plan-2026-07-05.md` | SUPERSEDED | 季度方向提案，提供北极星和单主线原则，已被后续执行路线图接管。 |
| RM-011 | `spec/archive/overnight-plan-2026-07-05.md` | SUPERSEDED | P0/P1 止血和夜间执行计划，相关修复已分批落地，不能继续按原任务表执行。 |
| RM-012 | `spec/archive/gpt-roadmap-4h-2026-07-06.md` | COMPLETED | P1 证据链与 value-lens 生产者阶段已完成，后续问题进入新的审计批。 |
| RM-013 | `spec/archive/oss-integration-roadmap-2026-07-07.md` | SUPERSEDED | SearXNG、Scrapling 和 URL 解码已形成默认关闭的数据线；其余项目仍是候选，不代表已集成。 |
| RM-014 | `spec/archive/direction-plan-2026-07-07.md` | SUPERSEDED | Claude 方向草稿，已由第二版分工路线图修正。 |
| RM-015 | `spec/archive/roadmap-claude-gpt-2026-07-07b.md` | COMPLETED | 可读性、认知校准、稳定性和默认关闭的数据线阶段已经执行。 |
| RM-016 | `spec/archive/roadmap-2026-07-07b-execution-summary.md` | REFERENCE | RM-015 的收官证据和提交记录，不是新的路线图。 |
| RM-030 | `spec/archive/roadmaps/roadmap-event-graph-2026-07-09.md` | COMPLETED | 事件图 V1 的 F1、B1-B3、F2 已提交；事件图仍有架构债务，但 V1 已收官。 |
| RM-040 | `spec/archive/roadmaps/roadmap-understanding-layer-2026-07-09.md` | SUPERSEDED | U2 多源对照完成、U1 后端完成；未完成的前端消费和 U3 假设层已并入 RM-050 或继续延期。 |
| RM-050 | `spec/roadmap-dual-mode-2026-07-09.md` | SUPERSEDED | 双模式入口 M1 已完成（`3327008`）；未完成的 M2/M3/M4 由 RM-055 完整承接。指向接替者 RM-055。 |
| RM-055 | `spec/roadmap-supply-chain-2026-07-12.md` | CURRENT | 当前主线。可审计信息供应链 · C 先行；接替 RM-050 并承接其 M2/M3/M4。 |
| RM-060 | `spec/ai-collaboration-and-source-boundary-2026-07-12.md` | CANDIDATE | AI 可控性与博客/播客/视频/授权私域资料方向，只记录问题和边界，尚未立项。 |

## 非路线图但必须保留的历史轨道

- 14 点意见修复：已经形成可用的阶段性基线，但不是“永不再优化”。后续残余问题按新审计批和新路线图处理，不重开原始 14 点清单。
- Fable 5 bug audit：属于稳定性治理依据，详见 `spec/bug-audit-2026-07-05.md`，不是产品路线图。
- 浏览器控制与 OpenCLI：属于运行边界决策，详见 `spec/browser-control-decision-2026-07-10.md`，不等同于产品采集路线图。
- Astro/Pagefind 与 OpenSPG/KAG：属于外部架构参考，详见 `spec/feedback-and-ideas/references/`；未经人类立项，不进入 RM-055，也不代表已集成。

## 更新规则

1. 任何时刻只有一个 `CURRENT` 产品路线图。
2. 新想法先登记为 `CANDIDATE`，只有人类拍板后才能升级为 `CURRENT` 或并入当前路线图。
3. 路线图完成时写清完成判据和提交证据；“测试全绿”不能单独等于产品完成。
4. 被替代的文件不删除、不重写历史，只改为 `SUPERSEDED` 并指向接替者。
5. Claude 和 Codex 每次规划前先读本总账，再读当前路线图，避免从旧文件重新开工。
