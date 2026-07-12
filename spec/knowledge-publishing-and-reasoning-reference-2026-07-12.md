# Knowledge Publishing And Reasoning References

Checked: 2026-07-12.

Status: `REFERENCE`. This note records reusable patterns from external projects. It is not a roadmap and does not authorize dependencies or implementation work.

## Sources

- Knowledge-base content repository: <https://github.com/Mr-Salticidae/knowledge-base>
- Astro display repository: <https://github.com/Mr-Salticidae/above-the-web>
- OpenSPG/KAG repository: <https://github.com/OpenSPG/KAG>
- KAG paper: <https://arxiv.org/abs/2409.13731>

## Astro And Pagefind Pattern

### Verified implementation

- The knowledge repository is an Obsidian-style content vault; the Astro application lives in the separate `above-the-web` repository.
- A content push sends a repository-dispatch event to the display repository.
- The display site also has a scheduled rebuild fallback, so a missing dispatch token does not permanently stop publication.
- The build pipeline syncs and sanitizes content, builds Astro, then generates a static Pagefind index over `dist`.
- Publication uses a whitelist rather than exposing the entire content vault.
- The daily AIGC workflow writes a dated artifact, checks for an existing artifact for idempotency, and triggers deployment explicitly.

### Borrow now

- Keep authoring/content ownership separate from any future public presentation layer.
- Use explicit publication whitelists and build-time sanitization for exported material.
- Prefer dated, idempotent generated artifacts for scheduled outputs.
- If public publishing is later approved, combine push dispatch with a scheduled fallback.

### Defer

- A small Astro/Pagefind read-only archive can be evaluated after RM-050 for public or static historical material.
- Pagefind could serve exported static pages without adding a search backend.

### Reject for the current product core

- Do not replace the FastAPI operational workbench with Astro.
- Do not use Pagefind as the search layer for live private data, mutable jobs, or operational topic state.
- Do not make AIGC generation mandatory for publication or for the no-LLM core path.

## OpenSPG And KAG Pattern

### Verified concepts

- KAG is built around OpenSPG plus LLM-assisted knowledge construction and reasoning.
- It combines schema-constrained knowledge construction with knowledge/chunk mutual indexing.
- Its solver uses logical forms to coordinate exact retrieval, text retrieval, graph reasoning, language reasoning, and numerical calculation.
- The approach aims to reduce ambiguous vector-only retrieval and noisy open information extraction in domain knowledge bases.
- Product deployment introduces OpenSPG/Docker and LLM operational requirements; this is materially heavier than the current SQLite architecture.

### Borrow now as design constraints

- Maintain mutual links between structured `Event`/`Entity`/relation records and their source article or evidence IDs.
- Define evidence relation schemas explicitly instead of allowing arbitrary graph edges.
- Keep observed evidence relations separate from hypotheses, inferences, and optional LLM-generated relations.
- Make future query plans inspectable: label exact lookup, graph traversal, text retrieval, calculation, and optional LLM reasoning as different steps.
- Return multi-hop answers with a visible evidence path rather than only a synthesized conclusion.

### Defer

- Run a small no-LLM spike over the existing SQLite event graph before considering any graph-platform migration.
- Candidate spike: answer a bounded multi-hop question using existing event, entity, relation, and article IDs, then show every hop and supporting source.
- Revisit KAG only if measured product needs exceed the current relational/event-graph approach.

### Reject during RM-050

- Do not add OpenSPG, KAG, a graph database, or a mandatory LLM reasoning service during the active stabilization gate.
- Do not import claims from the paper as product guarantees without local evaluation.
- Do not blur retrieved facts, graph-derived links, and LLM hypotheses into one confidence score.

## Decision Summary

| Pattern | Decision | Reason |
|---|---|---|
| Content/display separation | Borrow | Supports controlled future publishing without coupling it to the workbench. |
| Repository dispatch plus scheduled fallback | Borrow later | Reliable static deployment pattern. |
| Build-time whitelist and sanitization | Borrow | Protects private or non-publishable material. |
| Pagefind for exported archive | Defer | Useful for static pages, not live operational state. |
| Evidence-to-source mutual index | Borrow | Matches the project's evidence-first boundary. |
| Explicit graph/query operators | Borrow conceptually | Improves inspectability and prevents opaque reasoning. |
| KAG/OpenSPG integration | Reject for now | Too much platform and LLM complexity during RM-050. |

## Non-Negotiable Project Boundaries

- Core collection and local analysis remain usable without an LLM key.
- Optional LLM work fails soft and cannot corrupt or replace the core evidence path.
- Every published or reasoned claim must retain inspectable source provenance.
- External references enter the roadmap only after human approval and a scoped acceptance gate.
