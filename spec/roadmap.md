# Roadmap

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse. For a complete context reset, read `spec/current-state.md` first.

## Current Priority

Current working-tree implementation: cognition-profile calibration V1 and profile-driven boundary cards.

Goal: finish human review of the current working tree, then observe whether profile evidence and local workflow prompts make frontier-report recommendations feel more like cognition expansion.

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
