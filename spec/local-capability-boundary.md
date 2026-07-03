# Local Capability Boundary

This note defines what the workbench can do without an LLM key, what remains an optional LLM enhancement, and where the user should keep evidence limits in mind.

The product goal is not merely "degrade gracefully." The no-LLM path should feel like a usable local intelligence workbench: collect evidence, organize it, search it, and let the user inspect sources before any generated synthesis exists.

## Local Path

The core path should keep working without LLM access:

- collect reports from configured sources
- deduplicate and store article links
- build local event timelines from titles, snippets, sources, and dates
- show source matrices, source tiers, stance/category heuristics, and raw article evidence
- collect academic and community samples when those platform collectors are available
- browse discovery seeds and cognition-boundary cards that are already present locally
- browse historical frontier reports from local archive files
- classify discovery seeds by local fields such as domain, domain label, source/domain, date, and signal
- connect seeds across days with local similarity evidence, clearly labeled as non-causal
- search or filter local reports, seeds, tracked topics, sources, and cognition marks
- preserve partial results when one collector or platform fails

These outputs are signals for reading and triage. They are not full-text fact checks.

## Local UX Target

When LLM is unavailable, the UI should still help the user answer:

- What happened recently?
- What did earlier frontier reports contain?
- Which items are repeated, new, or adjacent to my cognition boundary?
- Which source, report date, or seed supports this label?
- What can I inspect next without waiting for generated prose?

The local UI should avoid blank states that imply "nothing works without AI." If a feature is LLM-only, mark it as enhancement. If a local fallback exists, show the local evidence first.

## LLM Enhancements

These features may improve readability or synthesis when an LLM key is configured, but must degrade gracefully when unavailable:

- deep analysis and synthesis
- per-article enrichment, substance notes, and optional emotion notes
- frontier synthesis / overview writing
- seed-to-query distillation
- any future fulltext reading assistance or narrative explanation
- optional branch naming or "what changed since last report" prose for cognition timeline branches

Failure mode: record an error, warning, or empty optional result; do not break collection, local analysis, or browsing.

## Boundaries

The local path does not guarantee:

- full-text fact verification
- causal attribution for complex events
- proof of manipulation or propaganda
- reliable judgement of user cognition
- complete platform coverage when a source blocks scraping, times out, or requires browser/login state

When a local or LLM-derived judgement matters, the UI should keep the original evidence reachable.
