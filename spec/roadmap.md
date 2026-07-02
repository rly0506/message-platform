# Roadmap

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse.

## Current Priority

Next planned implementation candidate: academic filtering / priority-reading signals.

Goal: make the academic layer answer which papers are better first reads without pretending to rank journals formally.

Design reference: `spec/academic-filtering-design.md`.

Implementation default:

- derive signals from existing OpenAlex fields: venue, year, cited_by_count, concepts, internal citations
- use neutral labels like `高引用`, `新近`, `样本内奠基`, `venue明确`, `低信息`
- do not claim `权威`, `顶刊`, or `中上等刊物` in V1
- prefer frontend-derived labels before changing backend payloads

## Near-Term

- Academic filtering: turn the design into a small UI iteration in the Academic tab.
- Local capability note: write a short product note explaining what the no-LLM path can and cannot do.
- Cognition-boundary cards: continue tuning card wording only after real use.

## Mid-Term

- Community readability: continue improving the sentiment layer as compact evidence cards, while keeping community sentiment clearly labeled as signal rather than fact.
- Narrative convergence: keep the feature framed as topic-local similarity signals with evidence, not as a claim of manipulation.

## Design-First

- Event tree: design a text-first structure for root issue -> branches -> supporting evidence before attempting a visual tree.
- Academic literature graph: design the reading task first, then decide whether a visual graph is useful.
- Cognition map: keep collecting low-friction cognition marks before drawing a map.

## Deferred

- Sentence-level perspective / B: defer unless it becomes fulltext reading assistance or anti-manipulation annotation. Summary-only sentence labels are not currently valuable enough.
- Heavy infrastructure: no vector database, queue system, or new component library until the existing local approach fails by evidence.
- Low-fit reference repos: Budibase, agents-radar, and codebase-memory-mcp stay out of the main plan unless the user names a concrete use.
