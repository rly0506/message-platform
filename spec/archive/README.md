# Spec Archive

Completed sprint snapshots, superseded roadmaps, audit records, and historical build evidence. Historical material is preserved, but it is not normal AI startup context.

## Structure

- `roadmaps/` - all completed, superseded, or reference roadmaps; `roadmaps/README.md` records their stable IDs.
- `changelog/` - full historical changelog snapshots.
- `plans/` - old implementation plans that are no longer executable.
- `build-logs/` - historical backend construction logs.
- `current-state/` - verbatim snapshots of the former live context reset file.
- archive root - dated sprint ledgers, reviews, audits, and other historical records that are not roadmaps.

## Rules

1. Do not execute an archived plan without revalidating it against `spec/roadmap-ledger.md` and current code.
2. Do not rewrite historical conclusions to match later knowledge; add a new current record instead.
3. Current product truth lives in `spec/current-state.md`, `spec/roadmap-ledger.md`, and `.agent-bridge/BOARD.md`.
4. Generated discovery reports are product data and do not belong here.
