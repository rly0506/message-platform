# Roadmap

> 路线图编号：`RM-000`（当前方向索引）。路线图状态总账见 `spec/roadmap-ledger.md`；当前唯一产品主线是 `RM-055`。

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse. For a complete context reset, read `spec/current-state.md` first.

## Current Priority

可审计信息供应链 · C 先行。完整方案见 `spec/roadmap-supply-chain-2026-07-12.md`。

当前进度（2026-07-14）：Phase 0/1/2、Phase A、`dig_later` 跨设备队列、M4' 事实优先早报与 Phase 3 假设层边界均已闭环。Phase 3 由 `5a53e41` 落地：默认关闭，只显示无数据占位与明确“假设”标识，不生成、不保存因果关系；独立复审最终 `APPROVE`。源扩展因尚无两周纵向缺口数据继续处于证据闸。2026-07-27 前没有新的自动产品开发项，按人类授权转入 correctness-focused code audit。

主线：**先让用户看见 AI 读了什么、漏了什么、有没有反证，再用真实缺口数据决定补哪些源、落哪些正文。** 手机标记好奇心、电脑消化好奇心；省力早报喂事实、硬核台增理解，两模式与认知画像不互相污染。

当前执行：Claude 离线期间由 Codex 按人类授权接管跨层实现；交接仍写入 `.agent-bridge/BOARD.md` 与 `TO_CLAUDE.md`。不 push、不合并 `master`，人类保留最终发布权。

战略判据(2026-07-09 人类读书洞察,不变):区分**获取资讯 vs 增进理解**。新功能优先级先问"这是堆资讯还是增进理解",后者优先。新增红线:早报喂事实不喂结论;两模式不互相污染。

已归档的上一轮:事件关系图 V1(`spec/archive/roadmaps/roadmap-event-graph-2026-07-09.md`,F1/F2/B1-B3 全提交)与理解层透镜2(`spec/archive/roadmaps/roadmap-understanding-layer-2026-07-09.md`,U2 前后端闭环)。

Reference notes: `spec/event-tree-literature-graph-design.md` for the design boundary, `spec/local-capability-boundary.md` for no-LLM limits, `spec/academic-filtering-design.md` for academic priority-reading signals, and `spec/discovery-archive-cognition-timeline-design.md` for discovery history / cross-day cognition-tree planning.

Implementation default:

- repeated lightweight calibration before any large cognition map
- domain universe before fixed hard-coded interests
- confidence and evidence before claims of knowing the user
- local-first before LLM enhancement
- report archive and local query before generated summaries
- text-first before visual canvas
- keep every branch or group linked back to evidence
- keep academic labels as reading signals, not authority claims
- do not add a graph library, vector database, or backend dependency in V1

## Near-Term

- RM-055 Phase 3：已完成（`5a53e41`）。事件图“假设层”默认关闭，以灰/虚线/“假设”角标定死证据与推断的视觉边界；V1 不接生成数据、持久化或后端契约。
- RM-055 M4'：已完成。事实优先早报、覆盖微标签、可核查深链与“今日一个领域”见 `2fd9155` / `8cb9f9b` / `ff85f65`。
- Source expansion observation gate：截至 2026-07-27 收集两周 Coverage 缺口数据；闸门见 `docs/operations/rm055-source-expansion-gate-2026-07-13.md`。
- Autonomous next action：在等待证据闸期间进行 correctness-focused code audit；发现项进入独立小批次，不用未经批准的新功能填空。
- 下列条目是既有观察项或候选方向，不因 RM-055 产品阶段完成而自动开工。
- Context cleanup: implemented in `spec/current-state.md`; keep it updated when a major iteration lands.
- Cognition-profile calibration V1: implemented. Next step is to observe real recommendations and decide whether to add a small editable calibration UI.
- Domain universe V1: implemented as default local profile fields. Tune labels and seed styles only after real use.
- Calibration feedback loop: next candidate; use real behavior after each test (`我懂了`, `存疑`, `深入`, skipped domains, repeated interests) to raise or lower confidence in the profile.
- Event structure tree semantic fix: rename the misleading `触发/行动` node to an evidence/selection label and clarify that nodes are parallel reading slices, not a timeline or causal chain.
- Local-first intelligence desk: strengthen no-LLM classification, collection, archive browsing, query/search, and evidence retrieval so the product still feels coherent when LLM keys are absent.
- Discovery archive V1: expose historical `认知前沿日报` reports already stored under `backend/discovery_reports/`; the frontend currently shows only the latest report.
- Local cognition timeline tree V1: connect seeds/events across previous frontier reports using local similarity evidence such as domain, domain_label, URL/domain reuse, keywords, and repeated signals. Do not claim causality.
- Event tree V1: implemented as a collapsed Media-tab text structure from existing local analysis data; observe real-topic usefulness before adding visual graphing.
- Academic reading-map V1 candidate: collapsed Academic-tab structure grouping foundational, recent, high-citation, school/concept, and low-information papers from existing OpenAlex fields.
- Community readability: observe the platform coverage and sentiment sample cards in real use before adding another redesign pass.
- Academic filtering: observe the new priority-reading signals in real use before adding sorting.
- Cognition-boundary cards: continue tuning card wording only after real use.

## Mid-Term

- Cognition calibration UI: if the dialogue test keeps proving useful, turn it into a small optional calibration flow. Keep it editable, skippable, and local-first; do not grade or personality-type the user.
- Local query layer: search and filter historical reports, seeds, tracked topics, sources, and cognition marks without LLM; generated summaries can later sit on top of this evidence layer.
- Community readability: continue improving the sentiment layer as compact evidence cards, while keeping community sentiment clearly labeled as signal rather than fact.
- Narrative convergence: V1 evidence cards are implemented; revisit only if real topics show unreadable or misleading clusters.

## Design-First

- Product positioning: keep the narrative-calibration frame. The project should not say "people dislike truth"; it should say people use stories to understand the world, and the tool helps evidence-calibrate those stories.
- Cognition domain universe: design the field map as layers, not a flat encyclopedia:
  - intelligence core: AI infrastructure, open-source ecosystems, finance/accounting, macro finance, energy/electricity, geopolitics/industrial policy, media literacy;
  - expansion layer: law/regulation, social structure/demographics, science foundations, biotech/health, cybersecurity/defense, culture/media, organization/management;
  - naturalist layer: geography/resources, history/institutions, philosophy/thought history, anthropology/social psychology, engineering/infrastructure.
  Each calibration round should sample a few core domains, a few chosen expansion domains, and one or two unfamiliar edge domains.
- Event tree / academic literature graph: captured in `spec/event-tree-literature-graph-design.md`; implementation must pick one small V1.
- Cross-day cognition timeline tree: captured in `spec/discovery-archive-cognition-timeline-design.md`; implement report archive first, then local cross-day links, then optional LLM explanations.
- Cognition map: keep collecting low-friction cognition marks and calibrated profile evidence before drawing a map.
- Local capability boundary: documented in `spec/local-capability-boundary.md`; treat it as a product target, not only a warning label. Revise whenever the no-LLM core path gains new collection, classification, query, or archive abilities.

## Deferred

- Sentence-level perspective / B: defer unless it becomes fulltext reading assistance or anti-manipulation annotation. Summary-only sentence labels are not currently valuable enough.
- Heavy infrastructure: no vector database, queue system, or new component library until the existing local approach fails by evidence.
- Low-fit reference repos: Budibase, agents-radar, and codebase-memory-mcp stay out of the main plan unless the user names a concrete use.
