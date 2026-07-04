# 14-Point Sprint Remaining Decisions - 2026-07-04

This document turns the remaining blockers in the 14-point feedback repair sprint into explicit decisions.

It does not replace `spec/14-point-acceptance-2026-07-04.md`. The acceptance matrix remains the source of truth for evidence and final status.

## Human Decision Brief

To close the current integration tree without starting a new feature direction, the remaining decisions and implementation choices are:

1. #2 freshness automation:
   - Human decision recorded: `B`
   - Meaning: auto refresh news/frontier while the backend is running. The backend auto-refresh implementation and Codex frontend status UI/e2e are now present and verified; Claude still needs to explicitly confirm `#2 ready for human final review: yes/no`.
2. #3/#13 source ingestion scope:
   - Human decision recorded for #3: expand mainstream news sources, especially WSJ, The Guardian, AFP, Xinhua, and similar high-quality outlets.
   - Meaning: source registry, source status explanation, and RSS/newsletter/Google Alerts import remain useful, but #3 cannot close as V1 limitation until Claude implements classified mainstream-source expansion and verifies it. #13 video/web/newsletter ingestion scope remains separate.
3. #6/#7/#8 semantic review:
   - Recommended reply from Claude: `V1 acceptable`
   - Meaning: media/community trends are sample signals, and event network edges are local evidence links, not causal proof.
4. #10/#11 academic source breadth:
   - Choice needed: `implement second academic source now` or `accept OpenAlex-only V1 limitation`
   - If the sprint must fully answer the user's OpenAlex concern, choose `implement second academic source now`; otherwise accept OpenAlex-only for this sprint and schedule Crossref/Semantic Scholar as the next backend slice.

Do not mark the sprint complete until these decisions are recorded, any chosen implementation is verified, and the full gate is rerun.

## Current Proven State

Fresh full gate evidence after auto-refresh frontend wiring and GitNexus reindex is green:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings in 39.31s`.
- `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 460ms).
- `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
- `git diff --check` -> pass, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
- `node .gitnexus/run.cjs analyze` -> repository indexed successfully; FTS extension unavailable warning only.
- `node .gitnexus/run.cjs status` -> index up-to-date at current commit `d028496`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `medium`, `16 files`, `45 symbols`, `1` affected execution flow (`RunCrossSynthesis -> FetchCrossSynthesis`).

The sprint is still open because several user-facing requirements need a scope decision or Claude-owned backend/source review.

## Final Status Projection

If no further implementation is chosen, the current matrix can only close after the remaining decisions are explicitly accepted. This projection is not a completion claim.

| Item | Current finalizable status | What prevents final closure |
|---|---|---|
| #1 | `Done` | Nothing item-specific. |
| #2 | `Done` for parent-context drilldown, stale/manual fallback, backend-running auto-refresh, and frontend status UI/e2e. | Claude must explicitly confirm no remaining backend blocker before human final review. |
| #3 | Not final-green while mainstream source expansion is unimplemented. | Human requested broader mainstream sources; Claude needs classified source expansion and tests. |
| #4 | `Done` | Nothing item-specific. |
| #5 | `Done` for Windows runner/diagnostics; external platform login/API may be `Blocked by external account/API`. | Real platform login/API failures remain environment-dependent. |
| #6 | `V1 Done with known limitation` if accepted. | Claude semantic review for pseudo-trend risk. |
| #7/#8 | `V1 Done with known limitation` if accepted. | Claude/human acceptance that this is a local evidence network, not a causal graph. |
| #9 | `Done` | Nothing item-specific. |
| #10 | Not final-green as `Done` while OpenAlex-only. | Claude implements a second academic source, or human accepts OpenAlex-only V1 limitation. |
| #11 | `V1 Done with known limitation`, tied to #10. | Source hygiene follows #10. |
| #12 | `V1 Done with known limitation` | Nothing item-specific for this sprint. |
| #13 | `V1 Done with known limitation` if accepted. | Claude/human must accept docs/import V1 or request ingestion entry implementation. |
| #14 | `Done` | Nothing item-specific. |

## Codex Read-Only Evidence Audit

Codex reviewed the current source/academic implementation without changing code. GitNexus MCP context was unavailable in this session due to MCP startup handshake failure, so this audit uses source files and tests as evidence.

### #3 News/Source Quality Evidence

Current implementation evidence:

- `backend/config/feeds.json` includes wire/mainstream/professional/newsletter/research feeds.
- `backend/app/feed_registry.py` validates curated feeds and exposes only enabled RSS registry rows for collection.
- `backend/app/services/source_registry.py` supports list/create/import/update and records source metadata.
- `backend/tests/test_source_registry.py` covers:
  - seeded source registry defaults;
  - enabled sources being used and disabled sources being skipped;
  - successful and failed source fetch status updates;
  - source API list/update/create/import validation;
  - evidence package output with no-LLM article evidence.
- `frontend/tests/e2e/source-registry.spec.ts` covers source manager status summary, failed-source reason visibility, Google Alerts RSS add, and newsletter/Google Alerts bulk import.

Codex read-only conclusion:

- The implemented #3 scope is no longer enough for final closure because the human explicitly requested broader mainstream source coverage after the earlier V1-limitation proposal.
- Current `feeds.json` already includes some mainstream/professional sources, so the next work is not "add any source"; it is classified source expansion with honest coverage limits.
- Quick source audit from Codex on 2026-07-04:
  - WSJ World RSS `https://feeds.a.dj.com/rss/RSSWorldNews.xml` was reachable but showed `lastBuildDate` / item dates around 2025-01-27, so it must not be treated as freshness-reliable without further validation.
  - AFP configured RSS `https://www.afp.com/en/rss.xml` returned AFP.com site/agency items rather than a fresh AFP newswire stream; treat AFP news coverage as API/license or Google-News-proxy-limited unless a fresh public feed is found.
  - Xinhua official RSS index `https://english.news.cn/rss/index.htm` exists, but linked `xinhuanet.com/english/rss/*rss.xml` samples were stale, mostly 2017-2020; do not enable as a fresh news source without a newer feed.
  - Guardian public RSS parsed successfully with the project-style `feedparser` check: 45 entries, feed updated `2026-07-04T11:52:59Z`; treat it as a direct fresh public RSS candidate, while still recording runtime source status normally.
- Full crawler, paywalled exclusives, and same-event G20 coverage remain outside this sprint unless the human explicitly expands scope again.

### #10 Academic Source Breadth Evidence

Current implementation evidence:

- `backend/app/pipeline/academic.py` calls `openalex.search_works(search_query, top_n=top_n)` directly in `run_academic_analysis`.
- No second academic collector is wired into `run_academic_analysis`.
- The synthesis prompt explicitly names OpenAlex top-N search and tells the LLM not to invent outside literature.
- `backend/tests/test_academic_layer.py` covers metadata, citation formatting, DOI normalization, readable literature network payload, academic job API, CJK topic translation, and LLM timeout degradation.
- `frontend/tests/e2e/academic-panel.spec.ts` covers authors, venue, DOI, OpenAlex link, priority-reading signals, and readable literature network.

Codex read-only conclusion:

- Academic metadata and review-discipline UI are V1-ready.
- Academic source breadth is not final-green: the collector is still OpenAlex-only.
- #10 needs either Claude implementation of a second source path, or a human decision to accept OpenAlex-only as `V1 Done with known limitation`.

### #11 Literature Network Evidence

Current implementation evidence:

- `AcademicPanel.vue` renders readable literature nodes and explicit `引用` edges.
- `academic.literature_network()` builds nodes and `relation: "cites"` edges from sample-internal citation edges.
- E2E asserts the readable network and checks the old `.academic-edge-list` is not rendered.

Codex read-only conclusion:

- #11 UI readability is V1-ready.
- Source hygiene depends on #10. If #10 is accepted as OpenAlex-only V1, #11 should inherit that limitation explicitly.

### #13 Source-Ingestion Lead Evidence

Current implementation evidence:

- The user-provided Bilibili/newsletter/Google Alerts method is recorded in `spec/2026-07-03-frontend-feedback.md`.
- Newsletter/RSS/Google Alerts import is implemented through source registry create/import.
- Tests cover Google Alerts RSS add and newsletter/Google Alerts bulk import.
- Bilibili remains documentation/lead only; no transcript, video URL ingestion, or platform-specific video collector is implemented.

Codex read-only conclusion:

- #13 can be accepted as `V1 Done with known limitation` if "source-ingestion lead" means documented method plus RSS/newsletter/Google Alerts import.
- #13 is not final-green if the sprint requires a first-class video/web/newsletter ingestion workflow.

## Decision 1: #2 Freshness Automation

Problem:

- Old topics can remain on an old `latest_published_at` because they were not re-collected.
- Frontend now labels stale dates as local last-collected time and offers a manual refresh fallback.
- The user preference has moved toward automatic updates.

Options:

- A. Keep stale warning plus one-click refresh only.
  - Pros: already implemented, lowest risk.
  - Cons: does not satisfy the new "do not make me remember to refresh" preference.
  - Final status if accepted: `V1 Done with known limitation`.
- B. Add backend-running auto refresh for news/frontier only.
  - Pros: directly addresses old topics going stale while backend is open.
  - Cons: needs backend scheduler/status implementation and careful non-overlap with manual jobs.
  - Final status if implemented: `Done` for freshness automation while backend is running.
- C. Auto refresh news/frontier plus visible stale state and manual fallback.
  - Pros: best product fit; combines automation, explainability, and recovery.
  - Cons: largest of the three, still local-process only.
  - Recommended decision: C.

Required owner if B/C: Claude backend implementation, Codex frontend review/e2e if new status fields are exposed.

Do not auto-run:

- OpenCLI community collection.
- LLM deep analysis.
- Three-side comparison.
- Academic refresh by default in this sprint.

## Decision 2: #3 News Source Quality

Current proof:

- Source registry exists.
- Source manager shows total/enabled/failed sources, latest successful fetch time, and failure reasons.
- Evidence package/local pre-analysis tests exist.
- Newsletter/RSS and Google Alerts import paths have frontend e2e coverage.

Human decision:

- Expand mainstream source coverage in this sprint.

Recommended implementation:

- Use classified expansion instead of blind enablement:
  - directly enable public RSS sources that are fresh and collector-compatible;
  - add visible limited entries for important sources that are paywalled, API/license-only, stale-RSS, summary-only, or Google-News-proxy-only;
  - keep disabled/limited sources out of collection while showing the user why they are not fully usable.

Known limitation to state:

- Full crawler, paywalled exclusives, AFP licensed wire access, and same-event G20 coverage are not guaranteed in this sprint.

Required owner: Claude for backend source registry/feed implementation and tests; Codex for source-manager UI/e2e if coverage metadata changes.

## Decision 3: #6 Media and Community Trend Semantics

Current proof:

- Media stance timeline shows count delta, share delta, turning period, sources, and representative reports.
- Small media samples degrade to distribution-only.
- Community sentiment timeline shows platform, time bucket, representative posts, confidence, and tiny-sample markers.
- Codex semantic scan found the UI frames this as samples, not truth:
  - `报道样本`
  - `不代表民间舆论`
  - `当前样本只能显示立场分布`
  - `样本趋势，非事实时间线`
  - `小样本线索`
- Fresh Codex self-audit command:
  - `rg -n "报道样本|不代表民间舆论|当前样本只能显示立场分布|样本趋势，非事实时间线|小样本线索|情绪样本，非事实来源" frontend/src/components frontend/tests/e2e`
  - Confirmed matching boundary copy in `MediaPanel.vue`, `SentimentPanel.vue`, `source-matrix.spec.ts`, and `sentiment-panel.spec.ts`.
- Current pseudo-trend risk assessment:
  - Media trend cards only render trend deltas when sample size and changed counts are sufficient.
  - Small samples explicitly show distribution-only language.
  - Community posts/comments are labeled `情绪样本，非事实来源`.

Recommended decision:

- Accept `V1 Done with known limitation` if Claude agrees the wording avoids pseudo-trend risk.

Known limitation to state:

- This is sample-level media/community signal, not a measurement of whole public opinion.

Required owner if copy/data semantics need more changes: Codex for frontend copy/e2e, Claude for backend data semantics.

## Codex Frontend Closure Note: #12 Cognition Expansion Cards

Current proof:

- Cognition boundary cards show a visible summary, report connection, deep-dive reason, recommendation reason, suggested path, profile evidence, and analysis workflow.
- The discovery cognition e2e asserts the core card fields:
  - `摘要`
  - `相关日报线索`
  - `深入理由`
  - `建议路径`
- Fresh Codex self-audit command:
  - `rg -n "摘要|相关日报线索|深入理由|建议路径|本地相似信号，不代表因果链" frontend/src/components/DiscoveryPanel.vue frontend/tests/e2e/discovery-cognition.spec.ts`
  - Confirmed matching UI copy and e2e assertions.

Recommended decision:

- Keep #12 as `V1 Done with known limitation`.

Known limitation to state:

- Long-term cognition profile calibration remains future work; current cards are evidence-linked prompts, not proof that the system fully understands the user's blind spots.

## Decision 4: #7/#8 Event Development Network

Current proof:

- Event structure tree and event-development flow are merged into an event network surface.
- Selected node details stay inline.
- Edge types distinguish chronology, shared articles, shared entities, and shared sources.
- Codex semantic scan found no unqualified causal wording; UI says local evidence edge and no LLM causal hypothesis.
- Fresh Codex self-audit command:
  - `rg -n "本地证据边，不显示 LLM 因果假设|本地相似信号，不代表因果链|导致|证明|根因|真因" frontend/src/components frontend/tests/e2e`
  - Confirmed the positive boundary copy exists in `MediaPanel.vue`, `DiscoveryPanel.vue`, and e2e assertions. Any `导致/证明/根因/真因` matches should be treated as suspect; current event-network UI does not use these words as causal claims.
- Current pseudo-causality risk assessment:
  - Edge labels are evidence-relation labels: `时间顺序`, `同组报道`, `共享对象`, `共同来源`.
  - The network explicitly says it does not show LLM causal hypotheses.
  - The cognition timeline tree explicitly says local similarity is not causality.

Recommended decision:

- Accept `V1 Done with known limitation`.

Known limitation to state:

- This is a local evidence network, not a historical causal graph.
- The user's long causal-chain vision remains a later product direction, not this sprint's closure criterion.

Required owner if more semantic work is needed: Codex, after Claude/human specifies exact copy or data-structure change.

## Decision 5: #10 Academic Source Breadth

Current proof:

- Academic UI shows authors, year, venue, DOI/OpenAlex links, priority-reading signals, and readable literature network.
- Academic prompt asks for review discipline and source citation.
- Backend tests pass.

Open problem:

- Academic collector is still OpenAlex-only.
- The user explicitly asked whether one academic source is too thin.

Options:

- A. Add a second academic source in this sprint.
  - Recommended source: Crossref or Semantic Scholar.
  - Pros: satisfies the user's source-breadth concern directly.
  - Cons: backend collector/merge/dedup work and new tests required.
  - Required owner: Claude.
- B. Ask the human to accept OpenAlex-only as V1 limitation.
  - Pros: closes the sprint without expanding backend scope.
  - Cons: does not fully satisfy the user's stated concern.
  - Final status if accepted: `V1 Done with known limitation`.

Recommended decision:

- If this sprint must fully answer the user's "OpenAlex-only too thin" concern, choose A.
- If the priority is to close the current broad integration tree, choose B and schedule the second source as the next backend slice.

## Decision 6: #11 Literature Network Source Hygiene

Current proof:

- The old unreadable citation chips have been replaced by readable nodes and explicit citation/reference edges.
- Frontend e2e covers metadata and network readability.

Open problem:

- Network semantics are only as strong as the source data.
- If #10 remains OpenAlex-only, #11 should inherit the same limitation.

Recommended decision:

- Accept `V1 Done with known limitation` only after #10 is either implemented with a second source or explicitly accepted as OpenAlex-only V1.

Required owner:

- Claude for source semantics.
- Codex only for UI regression if backend data shape changes.

## Decision 7: #13 Bilibili / Newsletter / Google Alerts Source-Ingestion Lead

Current proof:

- Original video/link feedback is recorded in `spec/2026-07-03-frontend-feedback.md`.
- Newsletter/RSS and Google Alerts source import have tests.
- Bilibili remains a documented lead, not a full transcript ingestion pipeline.
- Fresh Codex self-audit command:
  - `rg -n "情报源导入路径|RSS / Newsletter / Google Alerts|B站视频 / 网页线索|V1 不做视频转录" frontend/src/App.vue frontend/tests/e2e/source-registry.spec.ts`
  - Confirmed visible UI copy and e2e assertions for the source-ingestion path.

Options:

- A. Accept source registry/import/docs as V1.
  - Pros: honest closure; avoids starting a video-transcript feature inside the repair sprint.
  - Cons: Bilibili is not a first-class ingestion workflow yet.
  - Final status: `V1 Done with known limitation`.
- B. Implement a clearer video/web/newsletter ingestion entry now.
  - Pros: more directly addresses the user's "信息搜集方法" feedback.
  - Cons: new feature surface and likely backend/UI changes.
  - Required owner: Claude for ingestion design/source pipeline; Codex for frontend review if UI changes.

Recommended decision:

- Choose A for this sprint. Track B as a future source-ingestion feature.

## Recommended Closure Path

For fastest safe closure of the current 47-file integration tree:

1. Claude confirms #2 is ready for human final review, or names the exact remaining backend blocker.
2. Claude implements #3 classified mainstream-source expansion.
3. Claude marks #6/#7/#8 semantic review as acceptable or names exact copy changes.
4. Human chooses #10:
   - implement second academic source now, or
   - accept OpenAlex-only V1 limitation.
5. #11 follows the #10 decision.
6. Human accepts #13 as `V1 Done with known limitation`, unless a new ingestion feature is explicitly approved.
7. Rerun the full gate before any final completion claim or commit.

## Final Status Mapping After Decisions

| Item | If recommended decision is accepted |
|---|---|
| #2 | `Done` after Claude confirms no remaining backend blocker and human final review accepts the line |
| #3 | `Done` or `V1 Done with known limitation` only after classified mainstream-source expansion is implemented and limitations are visible |
| #6 | `V1 Done with known limitation` |
| #7/#8 | `V1 Done with known limitation` |
| #10 | `Done` if second source is added; `V1 Done with known limitation` if OpenAlex-only is accepted |
| #11 | `V1 Done with known limitation`, tied to #10 |
| #13 | `V1 Done with known limitation` |
