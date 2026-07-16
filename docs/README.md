# Documentation Map

`docs/` 保存使用说明、运维证据、外部参考和历史快照。产品目标、当前状态、路线图与开发约束以 [`spec/`](../spec/README.md) 为准。

## 当前文档

| 内容 | 入口 |
| --- | --- |
| 本地运行与运维 | [`operations.md`](operations.md) |
| 认知前沿发现流程 | [`discovery.md`](discovery.md) |
| 已执行任务与审计报告 | [`operations/`](operations/) |
| 外部产品和架构参考 | [`references/`](references/) |

架构的当前机器可读地图在 [`AGENTS.md`](../AGENTS.md)，产品与边界在 [`spec/project.md`](../spec/project.md)，当前方向在 [`spec/roadmap.md`](../spec/roadmap.md)。旧兼容入口 [`architecture.md`](architecture.md) 与 [`future-directions.md`](future-directions.md) 只负责重定向。

## 历史材料

- [`archive/`](archive/)：过时但仍有证据价值的架构与方向快照。
- [`superpowers/`](superpowers/)：已完成任务的历史设计/计划证据；不再是当前工作流权威。
- `operations/` 中带日期的报告保留当时验证结果，不代表本会话已复跑。

## 事实优先级

1. `AGENTS.md`：执行约束与代码地图。
2. `spec/current-state.md`、`spec/roadmap-ledger.md`：当前状态与唯一路线事实。
3. `spec/project.md`、`spec/development.md`、`spec/acceptance.md`：产品、开发与验收规范。
4. `docs/`：使用说明和证据。
5. `docs/archive/`：只读历史，不可直接重新开工。
