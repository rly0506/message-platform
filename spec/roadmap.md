# Roadmap

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse.

## Current Priority

Next planned implementation candidate: local-first intelligence desk foundation, after the current event-structure semantic fix is submitted.

Goal: make the intelligence desk useful without LLM access by exposing historical frontier reports, linking cross-day cognition signals, and improving local classification / collection / query paths.

Reference notes: `spec/event-tree-literature-graph-design.md` for the design boundary, `spec/local-capability-boundary.md` for no-LLM limits, `spec/academic-filtering-design.md` for academic priority-reading signals, and `spec/discovery-archive-cognition-timeline-design.md` for discovery history / cross-day cognition-tree planning.

Implementation default:

- local-first before LLM enhancement
- report archive and local query before generated summaries
- text-first before visual canvas
- keep every branch or group linked back to evidence
- keep academic labels as reading signals, not authority claims
- do not add a graph library, vector database, or backend dependency in V1

## Near-Term

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

- Local query layer: search and filter historical reports, seeds, tracked topics, sources, and cognition marks without LLM; generated summaries can later sit on top of this evidence layer.
- Community readability: continue improving the sentiment layer as compact evidence cards, while keeping community sentiment clearly labeled as signal rather than fact.
- Narrative convergence: V1 evidence cards are implemented; revisit only if real topics show unreadable or misleading clusters.

## Design-First

- Event tree / academic literature graph: captured in `spec/event-tree-literature-graph-design.md`; implementation must pick one small V1.
- Cross-day cognition timeline tree: captured in `spec/discovery-archive-cognition-timeline-design.md`; implement report archive first, then local cross-day links, then optional LLM explanations.
- Cognition map: keep collecting low-friction cognition marks before drawing a map.
- Local capability boundary: documented in `spec/local-capability-boundary.md`; treat it as a product target, not only a warning label. Revise whenever the no-LLM core path gains new collection, classification, query, or archive abilities.

## Deferred

- Sentence-level perspective / B: defer unless it becomes fulltext reading assistance or anti-manipulation annotation. Summary-only sentence labels are not currently valuable enough.
- Heavy infrastructure: no vector database, queue system, or new component library until the existing local approach fails by evidence.
- Low-fit reference repos: Budibase, agents-radar, and codebase-memory-mcp stay out of the main plan unless the user names a concrete use.
