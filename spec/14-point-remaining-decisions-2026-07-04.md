# 14-Point Sprint Remaining Decisions - 2026-07-04

This document turns the remaining blockers in the 14-point feedback repair sprint into explicit decisions.

It does not replace `spec/14-point-acceptance-2026-07-04.md`. The acceptance matrix remains the source of truth for evidence and final status.

## Human Decision Brief

To close the current integration tree without starting a new feature direction, the remaining decisions and implementation choices are:

1. #2 freshness automation:
   - Human decision recorded: `B`
   - Meaning: auto refresh news/frontier while the backend is running. The backend auto-refresh implementation and Codex frontend status UI/e2e are now present and verified; Claude has now explicitly confirmed `#2 ready for human final review: YES`.
2. #3/#13 source ingestion scope:
   - Human decision recorded for #3: expand mainstream news sources, especially WSJ, The Guardian, AFP, Xinhua, and similar high-quality outlets.
   - Current working tree: the first classified fresh-source batch is now present: 25 curated feeds total, including 8 `fresh_rss` + `public` sources (UN News, NPR World, The Conversation, CNBC World, The White House, Federal Reserve, European Central Bank, WTO News).
   - Claude final review recorded on 2026-07-05: accept #3 as `V1 Done with known limitation` and #13 as `V1 Done with known limitation`.
   - Meaning: #3/#13 are no longer waiting for product-scope review in this repair sprint. Known limitations remain explicit: WSJ/AFP/Xinhua/paywalled-wire/API-only/multilingual/G20 coverage and video transcript ingestion are future work.
3. #6/#7/#8 semantic review:
   - Claude reply recorded: `PASS`
   - Meaning: media/community trends are sample signals, and event network edges are local evidence links, not causal proof.
4. #10/#11 academic source breadth:
   - Human direction recorded: implement second academic source now.
   - Current working tree: Crossref is now wired as the second academic source alongside OpenAlex, with DOI merge and provenance tests.
   - Claude final review recorded on 2026-07-05: accept #10 as `Done` and #11 as `V1 Done with known limitation`.
   - Meaning: #10/#11 are no longer blocked on academic-source review in this repair sprint. Formal journal ranking, Semantic Scholar, and full bibliometric maps remain future work.

Do not mark the sprint complete until the full gate is rerun after the latest status/doc updates.

## Current Proven State

Fresh full pre-final gate evidence on 2026-07-05 is green:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 24.34s`.
- `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 451ms).
- `cd frontend; npm run test:e2e -- --workers=1` -> `88 passed (2.6m)`.
- `git diff --check` -> pass, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
- `node .gitnexus/run.cjs status` -> index up-to-date at current commit `5ed0022`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `27 files`, `101 symbols`, `54` affected processes.

The sprint is still open because the final gate must be rerun after the latest status/doc updates.

## Final Status Projection

The remaining product-scope decisions have been explicitly accepted by Claude. This projection is still not a completion claim because the final gate has not been freshly rerun after the latest status/doc updates.

| Item | Current finalizable status | What prevents final closure |
|---|---|---|
| #1 | `Done` | Nothing item-specific. |
| #2 | `Done` for parent-context drilldown, stale/manual fallback, backend-running auto-refresh, and frontend status UI/e2e. | Final full gate remains. |
| #3 | `V1 Done with known limitation`. | Final full gate remains; future source batches should not reopen this sprint. |
| #4 | `Done` | Nothing item-specific. |
| #5 | `Done` for Windows runner/diagnostics; external platform login/API may be `Blocked by external account/API`. | Real platform login/API failures remain environment-dependent. |
| #6 | `V1 Done with known limitation`. | Final full gate remains. |
| #7/#8 | `V1 Done with known limitation`. | Final full gate remains. |
| #9 | `Done` | Nothing item-specific. |
| #10 | `Done` for V1 source breadth. | Final full gate remains. |
| #11 | `V1 Done with known limitation`. | Final full gate remains. |
| #12 | `V1 Done with known limitation` | Nothing item-specific for this sprint. |
| #13 | `V1 Done with known limitation`. | Final full gate remains. |
| #14 | `Done` | Nothing item-specific. |

## Codex Read-Only Evidence Audit

Codex reviewed the current source/academic implementation without changing code. GitNexus MCP context was unavailable in this session due to MCP startup handshake failure, so this audit uses source files and tests as evidence.

### #3 News/Source Quality Evidence

Current implementation evidence:

- `backend/config/feeds.json` includes wire/mainstream/professional/newsletter/research feeds.
- Current tree has 25 curated feeds, including 8 `fresh_rss` + `public` feeds: UN News, NPR World, The Conversation, CNBC World, The White House, Federal Reserve, European Central Bank, and WTO News.
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

- The implemented #3 scope is stronger than the earlier V1-limitation proposal because the current tree now includes a first classified fresh-source batch.
- Claude accepted that first batch as enough for this repair sprint V1 on 2026-07-05.
- Quick source audit from Codex on 2026-07-04:
  - WSJ World RSS `https://feeds.a.dj.com/rss/RSSWorldNews.xml` was reachable but showed `lastBuildDate` / item dates around 2025-01-27, so it must not be treated as freshness-reliable without further validation.
  - AFP configured RSS `https://www.afp.com/en/rss.xml` returned AFP.com site/agency items rather than a fresh AFP newswire stream; treat AFP news coverage as API/license or Google-News-proxy-limited unless a fresh public feed is found.
  - Xinhua official RSS index `https://english.news.cn/rss/index.htm` exists, but linked `xinhuanet.com/english/rss/*rss.xml` samples were stale, mostly 2017-2020; do not enable as a fresh news source without a newer feed.
  - Guardian public RSS parsed successfully with the project-style `feedparser` check: 45 entries, feed updated `2026-07-04T11:52:59Z`; treat it as a direct fresh public RSS candidate, while still recording runtime source status normally.
- Full crawler, paywalled exclusives, and same-event G20 coverage remain outside this sprint unless the human explicitly expands scope again.

### #10 Academic Source Breadth Evidence

Current implementation evidence:

- `backend/app/pipeline/academic.py` now fetches OpenAlex + Crossref through `fetch_academic_papers`.
- `backend/app/collectors/crossref.py` is wired as the second academic collector.
- OpenAlex + Crossref results merge by normalized DOI, with title/first-author/year fallback.
- Paper payloads preserve `sources`, `source_count`, and `source_links`.
- The synthesis prompt tells the LLM not to invent outside literature.
- `backend/tests/test_crossref_collector.py` covers Crossref normalization, request params, User-Agent, 429 retry, and rows capping.
- `backend/tests/test_academic_layer.py` covers Crossref-only fallback, DOI merge, Crossref fail-soft behavior, metadata, citation formatting, DOI normalization, readable literature network payload, academic job API, CJK topic translation, and LLM timeout degradation.
- `frontend/tests/e2e/academic-panel.spec.ts` covers authors, venue, DOI/OpenAlex links, OpenAlex + Crossref provenance display, priority-reading signals, and readable literature network.

Codex read-only conclusion:

- Academic metadata, review-discipline UI, and V1 second-source breadth are now implemented.
- Claude accepted the Crossref/OpenAlex merge semantics and academic-summary citation discipline on 2026-07-05.

### #11 Literature Network Evidence

Current implementation evidence:

- `AcademicPanel.vue` renders readable literature nodes and explicit `引用` edges.
- `academic.literature_network()` builds nodes and `relation: "cites"` edges from sample-internal citation edges.
- E2E asserts the readable network and checks the old `.academic-edge-list` is not rendered.

Codex read-only conclusion:

- #11 UI readability is V1-ready.
- Source hygiene now includes OpenAlex + Crossref provenance, but the literature network remains a readable sample-internal reference graph rather than a full bibliometric map. Claude should confirm that this is an honest V1 boundary.

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
- `backend/config/feeds.json` now has 25 curated feeds.
- 8 feeds are classified as `fresh_rss` + `public`: UN News, NPR World, The Conversation, CNBC World, The White House, Federal Reserve, European Central Bank, and WTO News.
- Current backend verification after this source state: `tests/test_source_registry.py` -> `11 passed`; `tests/test_topic_ops.py tests/test_api_helpers.py` -> `13 passed`; full backend pytest -> `218 passed, 5 warnings in 36.44s`.

Human decision:

- Expand mainstream source coverage in this sprint.

Recommended closure decision:

- Accept the first classified fresh-source batch as the repair sprint V1 if this scope is enough:
  - directly enable public RSS sources that are fresh and collector-compatible;
  - keep visible limited entries for important sources that are paywalled, API/license-only, stale-RSS, summary-only, or Google-News-proxy-only;
  - keep disabled/limited sources out of collection while showing the user why they are not fully usable.
- If this is not enough, add only one minimal next batch rather than starting a crawler or paywalled-source integration inside this repair sprint.

Known limitation to state:

- Full crawler, paywalled exclusives, AFP licensed wire access, and same-event G20 coverage are not guaranteed in this sprint.

Required owner: Claude for backend source registry/feed implementation and tests; Codex for source-manager UI/e2e if coverage metadata changes.
Current owner action after the first batch: Claude reviews whether to accept this as `V1 Done with known limitation`; Codex reruns final gate after review.

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

- Academic UI shows authors, year, venue, DOI/OpenAlex/Crossref links, priority-reading signals, source provenance, and readable literature network.
- Academic prompt asks for review discipline and source citation.
- Crossref is implemented as a second backend source and backend tests pass.

Remaining review problem:

- The user explicitly asked whether one academic source is too thin; the implementation now addresses that at V1 breadth level.
- Claude still needs to review whether the Crossref merge and academic summary citation discipline are semantically acceptable.

Options:

- A. Accept OpenAlex + Crossref as the V1 academic source-breadth answer after Claude review.
  - Pros: directly answers the OpenAlex-only concern without adding another API dependency.
  - Cons: not a formal journal-ranking or full bibliometric system.
  - Final status if review and final gate pass: `Done` for #10 V1 source breadth.
- B. Request a third academic source such as Semantic Scholar now.
  - Pros: richer citation graph and metadata.
  - Cons: adds rate-limit/API complexity and expands the sprint again.

Recommended decision:

- Choose A for this repair sprint, then consider Semantic Scholar or journal-ranking as a later academic-quality iteration.

## Decision 6: #11 Literature Network Source Hygiene

Current proof:

- The old unreadable citation chips have been replaced by readable nodes and explicit citation/reference edges.
- Frontend e2e covers metadata and network readability.

Open problem:

- Network semantics are only as strong as the source data.
- Even with OpenAlex + Crossref provenance, the network is still sample-internal and not a full bibliometric map.

Recommended decision:

- Accept `V1 Done with known limitation` after Claude confirms the sample-internal boundary is honest with the Crossref-backed #10 data.

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

For fastest safe closure after Claude's final review:

1. Rerun the full final gate after the latest status/doc updates.
2. Record the final gate result and GitNexus risk explanation in the acceptance matrix/current-state/changelog.
3. Stage only the intended frontend/spec files for commit2; exclude `.agent-bridge/`, `.agents/`, `backend/.env`, `backend/dossier.db`, `AGENTS.md`, and `CLAUDE.md`.
4. Commit and push only after the staged-file safety check is clean.

## Final Status Mapping After Decisions

| Item | If recommended decision is accepted |
|---|---|
| #2 | `Done` |
| #3 | `V1 Done with known limitation` |
| #6 | `V1 Done with known limitation` |
| #7/#8 | `V1 Done with known limitation` |
| #10 | `Done` |
| #11 | `V1 Done with known limitation` |
| #13 | `V1 Done with known limitation` |
