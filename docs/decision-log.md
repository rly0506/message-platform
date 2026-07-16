# Decision Log

## 2026-06-21: Current Product Is Event Intelligence Workbench

Decision: Treat the current MVP as an event intelligence workbench, not a map-first product.

Reason: The strongest user need is understanding event evolution across many sources. Map visualization is useful after event structure becomes reliable.

## 2026-06-21: Core Path Must Not Depend On LLM Quota

Decision: Search, collection, local analysis, timeline, source matrix, entity grouping, and evidence display must run without paid model calls.

Reason: The project should remain usable when model quota is unavailable.

## 2026-06-21: Evidence Before Conclusion

Decision: Each event node should expose sources, evidence articles, first sources, source tiers, and selection basis.

Reason: News analysis without traceable evidence is not trustworthy enough for this project.

## 2026-06-21: Use Stable Report Function Categories

Decision: Classify reports with stable labels such as 起因背景、触发事件、行动进展、各方回应、外交降温、影响后果、分析解读、核实澄清、后续处置.

Reason: Users need to read reports by function, not just by source or time.

## 2026-06-21: GitNexus Is Used For Framework Navigation

Decision: Use GitNexus status/context/impact/detect-changes while refactoring framework boundaries.

Reason: The project is beginning to split large files; symbol impact and graph checks reduce accidental breakage.

## 2026-06-21: Superpowers Plans Live Under docs/superpowers/plans (Superseded 2026-07-16)

Decision: Put long implementation plans in `docs/superpowers/plans/`.

Reason: The main roadmap should stay readable, while implementation plans can be detailed and executable.

Superseded by the framework-neutral Agent Work Protocol in `spec/development.md`. Existing files remain as historical evidence; new work is routed by artifact type instead of by plugin name.

## 2026-07-16: Use Small Canonical Indices And Preserve Redirects

Decision: Use the root `README.md` and `docs/README.md` as routing indices. Keep current product, roadmap, development, and acceptance truth under `spec/`; archive superseded architecture and direction prose while retaining compatibility redirects at the old paths.

Reason: Humans and agents need a short deterministic read order, while code comments and historical reports still need old links to resolve.

## 2026-07-16: Retire Superpowers As A Repository Workflow Authority

Decision: Preserve completed files under `docs/superpowers/` as historical implementation evidence, but use `spec/development.md#agent-work-protocol` as the durable workflow contract. Do not manually remove user-level plugin caches as part of repository cleanup.

Reason: The project should not depend on a branded agent framework, and repository documentation governance must not mutate user-level tool installations.
