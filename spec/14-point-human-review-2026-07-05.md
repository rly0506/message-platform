# 14-Point Human Review Packet - 2026-07-05

This packet summarizes the current **14 点反馈验收修复 Sprint** state for human final review.

It is not a completion claim. The source of truth remains `spec/14-point-acceptance-2026-07-04.md`; this file is the shorter decision view.

Update after Claude final review on 2026-07-05:

- #3 accepted as `V1 Done with known limitation`.
- #10 accepted as `Done`.
- #11 accepted as `V1 Done with known limitation`.
- #13 accepted as `V1 Done with known limitation`.
- No further source/academic code changes are required before the final gate.

## Latest Gate

Fresh final gate on 2026-07-05 after Claude final review and status-doc updates:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 31.31s`.
- `cd frontend; npm run build` -> passed, built in `565ms`.
- `cd frontend; npm run test:e2e -- --workers=1` -> `88 passed (2.5m)`.
- `git diff --check` -> pass, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`.
- `node .gitnexus/run.cjs analyze` -> indexed current commit `0a9a97b`.
- `node .gitnexus/run.cjs status` -> up-to-date at `0a9a97b`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> `low`, `19 files`, `41 symbols`, `0` affected processes.

## Gate Risk

The earlier pre-final GitNexus `critical` result applied to the full integration tree before commit1 separated backend/source/academic changes. It came from central symbols that fan out into many job flows:

- `SourceRegistry`
- `Paper`
- `_migrate`
- `_seed_source_registry`

Current commit2 frontend/spec surface is lower risk after reindexing: `detect-changes` is `low`, with `0` affected processes. Commit1 still carries the broader backend/source/academic review context and is already separated as `0a9a97b`.

## Human Decisions

### Decision A: #3 First Source Batch V1

Current evidence:

- `backend/config/feeds.json` has `25` curated feeds.
- `8` feeds are classified as `fresh_rss` + `public`:
  - UN News
  - NPR World
  - The Conversation
  - CNBC World
  - The White House
  - Federal Reserve
  - European Central Bank
  - WTO News
- Source registry exposes `coverage/access/last_tested/coverage_reason/state_media`.
- Disabled/limited sources do not silently fall back into collection.

Decision:

- Accepted by Claude as `V1 Done with known limitation`.

Known limitation to approve explicitly:

- WSJ/AFP/Xinhua/paywalled-wire/API-only sources are not fully covered.
- Multilingual source expansion is not done.
- Same-event G20 coverage and full crawler behavior are not guaranteed.

### Decision B: #10 Crossref Academic Second Source

Current evidence:

- Academic layer fetches OpenAlex + Crossref.
- Results merge by DOI, with title/first-author/year fallback.
- Paper payloads preserve `sources/source_count/source_links`.
- Crossref failures fail soft; OpenAlex-only results still survive.
- Prompt and UI no longer describe the sample as OpenAlex-only.

Decision:

- Accepted by Claude as `Done` for V1 academic source breadth.

Known limitation:

- No formal journal ranking.
- No third academic source such as Semantic Scholar yet.

### Decision C: #11 Literature Network Boundary

Current evidence:

- Old unreadable citation chips are replaced by readable nodes and `引用` edges.
- UI states the network is sample-internal.
- Paper cards can show OpenAlex + Crossref provenance links.

Decision:

- Accepted by Claude as `V1 Done with known limitation`.

Known limitation:

- This is not a full bibliometric map.

### Decision D: #13 Source-Ingestion Lead

Current evidence:

- RSS/newsletter/Google Alerts import paths exist.
- Source Manager shows a visible `情报源导入路径`.
- B站/video/web are documented as leads.
- V1 explicitly does not perform video transcript ingestion.

Decision:

- Accepted by Claude as `V1 Done with known limitation`.

Known limitation:

- Bilibili is a source lead, not a first-class video ingestion pipeline.

## 14-Point Table

| # | Proposed final status | Human/Claude action |
|---|---|---|
| 1 | `Done` | Final gate only. |
| 2 | `Done` | Final gate only. |
| 3 | `V1 Done with known limitation` | Final gate only. |
| 4 | `Done` | Final gate only. |
| 5 | `Done` + external failures `Blocked by external account/API` | Final gate only. |
| 6 | `V1 Done with known limitation` | Final gate only. |
| 7 | `V1 Done with known limitation` | Final gate only. |
| 8 | `V1 Done with known limitation` | Final gate only. |
| 9 | `Done` | Final gate only. |
| 10 | `Done` | Final gate only. |
| 11 | `V1 Done with known limitation` | Final gate only. |
| 12 | `V1 Done with known limitation` | Final gate only. |
| 13 | `V1 Done with known limitation` | Final gate only. |
| 14 | `Done` | Final gate only. |

## Commit Strategy

Do not commit:

- `.agent-bridge/`
- `.agents/`
- `backend/.env`
- `backend/dossier.db`

Recommended commit split if the tree can be staged cleanly:

1. `feat(workbench): close 14-point frontend workflow gaps`
2. `feat(sources): classify registry coverage and expand fresh feeds`
3. `feat(academic): add Crossref provenance to academic layer`
4. `fix(opencli): harden Windows runner diagnostics`

If the tree is too tangled for clean staging, one broad commit is acceptable only with an explicit message such as:

```text
feat: integrate 14-point feedback repair sprint
```

The commit body should include the latest gate results and the GitNexus `critical` explanation.

## Stop Conditions

Do not mark the sprint complete if any of these happen:

- Claude requests another source or academic code change.
- Human rejects #3, #10, #11, or #13 V1 boundaries.
- Any code or status-document changes occur after the 2026-07-05 final gate without rerunning the full gate.
- The earlier GitNexus `critical` context for commit1 is not acknowledged in the final human report.
