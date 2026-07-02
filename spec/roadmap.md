# Roadmap

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse.

## Current Priority

Next planned implementation candidate: community readability / sentiment evidence cards.

Goal: keep improving the community layer as readable sentiment samples while preserving the boundary that community sentiment is signal, not fact.

Reference notes: `spec/local-capability-boundary.md` for no-LLM boundaries, and `spec/academic-filtering-design.md` for the completed academic-filtering design.

Implementation default:

- keep failures as compact warnings, not dominant content
- keep HN / Reddit / Chinese platform samples visually distinct
- do not turn sentiment samples into factual claims
- avoid new backend dependencies unless existing collector output is insufficient

## Near-Term

- Community readability: tune the sentiment tab around platform coverage, failure clarity, and compact evidence cards.
- Academic filtering: observe the new priority-reading signals in real use before adding sorting.
- Cognition-boundary cards: continue tuning card wording only after real use.

## Mid-Term

- Community readability: continue improving the sentiment layer as compact evidence cards, while keeping community sentiment clearly labeled as signal rather than fact.
- Narrative convergence: keep the feature framed as topic-local similarity signals with evidence, not as a claim of manipulation.

## Design-First

- Event tree: design a text-first structure for root issue -> branches -> supporting evidence before attempting a visual tree.
- Academic literature graph: design the reading task first, then decide whether a visual graph is useful.
- Cognition map: keep collecting low-friction cognition marks before drawing a map.
- Local capability boundary: documented in `spec/local-capability-boundary.md`; revise only when the no-LLM core path changes.

## Deferred

- Sentence-level perspective / B: defer unless it becomes fulltext reading assistance or anti-manipulation annotation. Summary-only sentence labels are not currently valuable enough.
- Heavy infrastructure: no vector database, queue system, or new component library until the existing local approach fails by evidence.
- Low-fit reference repos: Budibase, agents-radar, and codebase-memory-mcp stay out of the main plan unless the user names a concrete use.
