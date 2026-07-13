# Historical Roadmap Consolidation Work Management And Task Report

Status: **COMPLETE**

Branch: `feature/academic-reading-signals`

Commit: `36c2549 docs: consolidate historical roadmaps`

Push/merge policy: do not push; do not merge `master`.

## Delivery Checklist

- [x] Confirm the worktree contained only the prior never-commit set before the
  documentation batch started.
- [x] Inventory every roadmap under `spec/` and `spec/archive/` and search all
  tracked and local coordination references.
- [x] Keep `RM-000`, current `RM-055`, candidate `RM-060`, and the ledger at the
  spec root.
- [x] Move nine scattered historical roadmaps with `git mv` into the existing
  `spec/archive/roadmaps/` directory.
- [x] Preserve all historical body content; only canonical path references were
  changed inside moved documents.
- [x] Add `spec/archive/roadmaps/README.md` as the numbered archive index.
- [x] Register the previously unnumbered GPT continuation as RM-017/SUPERSEDED
  without reopening its task list.
- [x] Update the ledger paths for RM-010..017 and RM-050 while retaining RM-055
  as the single CURRENT product roadmap.
- [x] Correct `spec/README.md` so Current product sprint routes to RM-055 rather
  than the superseded RM-050.
- [x] Update tracked references and local `.agent-bridge/` links to the new
  canonical paths.
- [x] Verify 11 archived roadmap files exist, every indexed ID has an entity,
  ledger IDs are unique, and exactly one roadmap has CURRENT status.
- [x] Verify the spec root contains only `roadmap.md`, `roadmap-ledger.md`, and
  `roadmap-supply-chain-2026-07-12.md` among roadmap-named files.
- [x] Search for all former root/archive paths and obtain zero matches outside
  GitNexus-generated metadata.
- [x] Stage only 19 `spec/` paths; exclude AGENTS, CLAUDE, local tools, databases,
  secrets, and `.agent-bridge/`.
- [x] Run `git diff --cached --check` successfully.
- [x] Refresh the stale GitNexus index and run staged detect-changes with an
  explicit repo and branch: 14 files, 24 symbols, 0 flows, LOW risk.
- [x] Commit the lossless consolidation independently as `36c2549`.
- [x] Update BOARD and TO_CLAUDE with the commit, canonical paths, gate evidence,
  and the next RM-055 stage.

## Evidence And Boundaries

- Git reported five pure 100% renames; the other moved files retained 93-98%
  similarity because one canonical reference line changed.
- The staged batch contained 63 insertions and 22 deletions across 19 files;
  the apparent deletions are path/index line replacements, not removed roadmap
  bodies.
- The first `detect-changes` invocation stopped before analysis because three
  repositories were registered locally. Re-running with `--repo message-platform`
  and `--branch feature/academic-reading-signals` passed at LOW risk.
- GitNexus indexing completed with 4,613 nodes, 8,553 edges, 188 clusters, and
  300 flows. Optional FTS remained unavailable; graph indexing and staged
  change mapping still completed successfully.
- No backend/frontend suite was rerun for this documentation-only batch. The
  immediately preceding M3' full gate remains backend `319 passed, 1 warning`,
  frontend build 98 modules, and desktop/mobile E2E `174 passed`.

## Human Decisions Deferred To The End

None required for this consolidation. The next goal follows the already approved
RM-055 M4' direction; any new product decision discovered there will be collected
at the end rather than interrupting unattended work.
