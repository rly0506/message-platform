# Roadmap

This roadmap records the current product direction after the July 2026 readability and cognition rounds. It is intentionally small: use it to choose the next iteration, not to turn the project into a backlog warehouse.

## Current Priority

Next feature iteration: cognition-boundary card enhancement in the intelligence desk.

Goal: make each frontier seed answer three questions before the user clicks anything:

- why this was recommended to the user
- which cognition profile area it touches or challenges
- what the next useful action is

Implementation default:

- reuse `DiscoverySeed.what`, `DiscoverySeed.why`, `CognitionProfileItem`, and the existing boundary reason logic
- keep one-click `我懂了` and `存疑`
- do not restore four-way classification forms or free-text reason boxes
- do not add backend dependencies, vector storage, or graph infrastructure

## Near-Term

- Cognition-boundary cards: improve seed cards with recommendation reason, challenged knowledge area, and next action.
- Local capability note: write a short product note explaining what the no-LLM path can and cannot do.

## Mid-Term

- Academic filtering: use existing OpenAlex venue, citation, and year fields to make academic results easier to scan and bias toward stronger papers.
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
