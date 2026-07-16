# Personal Intelligence Workbench

这是一个面向个人使用的国际事件情报工作台：聚合多源证据、比较报道差异，并在不依赖 LLM 的核心路径上帮助用户扩展认知。

## 从这里开始

| 目的 | 权威入口 |
| --- | --- |
| 快速了解当前状态 | [`spec/current-state.md`](spec/current-state.md) |
| 查看唯一当前路线与候选方向 | [`spec/roadmap-ledger.md`](spec/roadmap-ledger.md) |
| 理解产品目标与架构边界 | [`spec/project.md`](spec/project.md) |
| 开发、审计或修改代码 | [`AGENTS.md`](AGENTS.md) → [`spec/development.md`](spec/development.md) |
| 验收一项工作 | [`spec/acceptance.md`](spec/acceptance.md) |
| 查找运维记录、历史说明和参考资料 | [`docs/README.md`](docs/README.md) |
| 查看用户反馈与想法 | [`spec/feedback-and-ideas/README.md`](spec/feedback-and-ideas/README.md) |

本地多代理协作时再读取 `.agent-bridge/BOARD.md` 和自己的 `TO_*.md`。该目录被 Git 忽略，不是可提交的产品事实源。

## 当前快照（非权威摘要）

权威状态以 [`spec/current-state.md`](spec/current-state.md) 和 [`spec/roadmap-ledger.md`](spec/roadmap-ledger.md) 为准；若有冲突，以二者为准。`CURRENT`、观察闸或候选状态变化时必须同步更新本节。

- `RM-055` 是唯一 `CURRENT`；Coverage observation 已实现并处于 `ACTIVE-GATE`。
- 尚无成功真实观察日，来源扩展继续 `HOLD`，不得伪造窗口或缺口证据。
- `RM-065` 是 `CANDIDATE`：历史收口之后，按话题加载正确性、检视阅读、实测性能、本地聚类/去重和证据驱动扩源推进；它不自动取代 RM-055。

## 目录

- `backend/`：FastAPI、SQLModel、SQLite、采集与本地分析。
- `frontend/`：Vue 3、TypeScript、Vite 与 Playwright。
- `spec/`：产品事实、路线图、开发约束和验收门禁。
- `docs/`：运维证据、使用说明、参考资料与历史归档。

## 不可突破的边界

- 核心采集与本地分析不能依赖 LLM key；LLM 增强必须 fail-soft。
- 测试和审阅不得写入 `backend/dossier.db`。
- 不提交密钥、真实代理端口、本地数据库或 `.agent-bridge/`。
- 情绪与社区内容是信号，不是事实；推断必须与证据分开。
- 小步、可逆、先测量；不因“算法更先进”或“来源更多”本身判定成功。
