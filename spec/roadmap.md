# Roadmap

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse.

## Current Priority

Next planned design candidate: event tree / academic literature graph.

Goal: design how the workbench can show topic structure before implementing another visual feature. The next code iteration should choose either text-first event tree V1 or academic reading-map V1, not both at once.

Reference notes: `spec/event-tree-literature-graph-design.md` for the design boundary, `spec/local-capability-boundary.md` for no-LLM limits, and `spec/academic-filtering-design.md` for academic priority-reading signals.

Implementation default:

- text-first before visual canvas
- keep every branch or group linked back to evidence
- avoid causal claims such as "root cause" unless evidence supports a weaker label
- do not add a graph library, vector database, or backend dependency in V1

## Near-Term

- Event tree V1 candidate: collapsed Media-tab structure showing root issue, triggers, branches, consequences, and unresolved questions from existing local analysis data.
- Academic reading-map V1 candidate: collapsed Academic-tab structure grouping foundational, recent, high-citation, school/concept, and low-information papers from existing OpenAlex fields.
- Community readability: observe the platform coverage and sentiment sample cards in real use before adding another redesign pass.
- Academic filtering: observe the new priority-reading signals in real use before adding sorting.
- Cognition-boundary cards: continue tuning card wording only after real use.

## Mid-Term

- Community readability: continue improving the sentiment layer as compact evidence cards, while keeping community sentiment clearly labeled as signal rather than fact.
- Narrative convergence: V1 evidence cards are implemented; revisit only if real topics show unreadable or misleading clusters.

## Design-First

- Event tree / academic literature graph: captured in `spec/event-tree-literature-graph-design.md`; implementation must pick one small V1.
- Cognition map: keep collecting low-friction cognition marks before drawing a map.
- Local capability boundary: documented in `spec/local-capability-boundary.md`; revise only when the no-LLM core path changes.

## Deferred

- Sentence-level perspective / B: defer unless it becomes fulltext reading assistance or anti-manipulation annotation. Summary-only sentence labels are not currently valuable enough.
- Heavy infrastructure: no vector database, queue system, or new component library until the existing local approach fails by evidence.
- Low-fit reference repos: Budibase, agents-radar, and codebase-memory-mcp stay out of the main plan unless the user names a concrete use.
