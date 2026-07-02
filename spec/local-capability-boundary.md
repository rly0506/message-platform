# Local Capability Boundary

This note defines what the workbench can do without an LLM key, what remains an optional LLM enhancement, and where the user should keep evidence limits in mind.

## Local Path

The core path should keep working without LLM access:

- collect reports from configured sources
- deduplicate and store article links
- build local event timelines from titles, snippets, sources, and dates
- show source matrices, source tiers, stance/category heuristics, and raw article evidence
- collect academic and community samples when those platform collectors are available
- browse discovery seeds and cognition-boundary cards that are already present locally

These outputs are signals for reading and triage. They are not full-text fact checks.

## LLM Enhancements

These features may improve readability or synthesis when an LLM key is configured, but must degrade gracefully when unavailable:

- deep analysis and synthesis
- per-article enrichment, substance notes, and optional emotion notes
- frontier synthesis / overview writing
- seed-to-query distillation
- any future fulltext reading assistance or narrative explanation

Failure mode: record an error, warning, or empty optional result; do not break collection, local analysis, or browsing.

## Boundaries

The local path does not guarantee:

- full-text fact verification
- causal attribution for complex events
- proof of manipulation or propaganda
- reliable judgement of user cognition
- complete platform coverage when a source blocks scraping, times out, or requires browser/login state

When a local or LLM-derived judgement matters, the UI should keep the original evidence reachable.
