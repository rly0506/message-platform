# Spec Changelog

## 2026-07-02

### Added

- Added platform coverage status to the Sentiment tab:
  - shows attempted community platforms as compact chips: `有样本`, `暂不可用`, or `已尝试无样本`;
  - labels Hacker News as public API and Chinese OpenCLI platforms as requiring Chrome login state;
  - keeps community samples framed as sentiment signals, not facts, with no backend/API changes.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/SentimentPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- sentiment-panel` -> RED before implementation, missing `.sentiment-platform-coverage`
- `cd frontend && npm run test:e2e -- sentiment-panel` -> `2 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `20 passed`

### Added

- Documented the no-LLM local capability boundary:
  - added `spec/local-capability-boundary.md`;
  - linked it from `spec/README.md`;
  - added a compact local capability note to the LLM tab when no LLM analysis exists.
- Updated `spec/roadmap.md` so the next planned candidate is community readability / sentiment evidence cards.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/LlmPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- llm-panel` -> RED before implementation, missing `.local-capability-note`
- `cd frontend && npm run test:e2e -- llm-panel` -> `2 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `20 passed`

### Added

- Implemented academic priority-reading signals in the Academic tab:
  - added a compact `优先阅读信号` summary for high-citation, recent, sample-foundational, and low-information paper counts;
  - added neutral paper badges: `高引用`, `新近`, `样本内奠基`, `venue明确`, `低信息`;
  - kept the logic frontend-derived from existing OpenAlex payload fields, with no backend/API/LLM changes and no paper hiding or ranking claims.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/AcademicPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- academic-panel` -> `2 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `18 passed`

### Planning

- Added `spec/academic-filtering-design.md`:
  - frames academic filtering as neutral priority-reading signals, not formal journal ranking;
  - uses existing OpenAlex fields (`venue`, `year`, `cited_by_count`, concepts, internal citations);
  - defines V1 labels: `高引用`, `新近`, `样本内奠基`, `venue明确`, `低信息`;
  - keeps V1 frontend-derived and avoids backend/API changes unless later reuse needs them.
- Updated `spec/roadmap.md` so academic filtering is the next planned implementation candidate.
- Linked the design from `spec/README.md`.

### Verification

- `git diff --check` -> exit 0
- `git status --short` -> only `spec/` documents changed before commit

### Added

- Enhanced the cognition-boundary queue cards in the intelligence desk:
  - each boundary seed now shows `推荐原因`, `挑战点`, and `下一步`;
  - the boundary card reuses existing seed/profile data and does not change backend APIs;
  - the boundary card now includes a visible `深入` action that reuses the existing seed analysis flow.

### Verification

- `node .gitnexus/run.cjs impact boundaryReason -d upstream --include-tests` -> risk LOW
- `node .gitnexus/run.cjs impact -u "Function:frontend/src/components/DiscoveryPanel.vue:boundaryQueue" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- discovery-cognition` -> `4 passed`
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk MEDIUM, 2 files, 2 symbols, 1 expected boundary queue flow
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Planning

- Added `spec/roadmap.md` to record the next iteration direction:
  - near-term priority is cognition-boundary card enhancement in the intelligence desk;
  - #5 event tree / academic literature graph is now captured as design-first work;
  - #7 no-LLM local capability note is now captured as near-term documentation work;
  - sentence-level perspective remains deferred unless upgraded into fulltext reading assistance or anti-manipulation annotation.
- Linked `spec/roadmap.md` from `spec/README.md`.

### Frontend收口

- Committed `be5afaf` (`refactor(discovery): calm rest seed browsing`):
  - rest seeds are default-collapsed;
  - rest seeds exclude cognition-boundary queue items and already-known seeds;
  - social-feed style emoji clutter was removed;
  - e2e coverage now checks collapsed rest seeds and no duplicate boundary seeds.

### Verification

- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- discovery-cognition` -> `4 passed`
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk LOW, 2 files, 3 symbols, 0 affected processes
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Added

- Reliability + discovery-layer round (human-approved "A" plan, Claude impl / GPT review):
  - **#9 academic LLM-synthesis timeout no longer strands the job.** `run_academic_analysis`
    wraps `synthesize_academic` in try/except: on timeout/failure the summary degrades to ""
    and the synthesize step reports `warning`, while `persist` still runs so fetched papers +
    citation graph are not lost. `run_academic_analysis_job` uses `mark_running_steps_done()`
    (not `mark_all_steps_done()`) so the `warning` is not masked as `done`. `fail_job` untouched
    (avoids its CRITICAL blast radius).
  - **#2/#3 discovery layer stops reading like a social feed.** Removed the `🔥 signal` heat
    badge from seeds (signal still drives ranking, just not shown). The cognition-boundary queue
    now has a one-click `我懂了` (marks `known`, reuses existing seed mark) that filters the item
    out of the queue — a visible closure — plus an auxiliary `存疑`. Removed the four-way
    classification buttons and the free-text "reason" editor from the seed stream (the friction
    the user flagged). Empty queue shows "今天都过了一遍 👍".
  - **#6 deep-analysis now includes cross-synthesis without double-running voices.** The
    cross-synthesis job gained a `refresh_voices: bool = True` flag. The standalone 三方对照 button
    keeps the full-refresh 6-step path (re-runs media/academic/sentiment then synthesizes). The
    LLM bundle calls it with `refresh_voices=false` — a lite 3-step path (gather/synthesize/persist)
    that reuses the just-persisted voices instead of re-running all three. `cross_synthesis_steps`,
    payload and args all split on the flag so the UI never shows 6 steps for a 3-step run. Missing
    voices still synthesize (handled by `gather_voices`).

### Two cross-synthesis semantics (by design)

- Standalone 「三方对照」button = full refresh (re-runs all three voices, then synthesizes).
- 「深度分析（LLM · 媒体+学界+民间+三方对照）」= reuses the voices just persisted by the bundle
  (`refresh_voices=false`), so nothing runs twice.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `164 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `14 passed` (run twice, stable)
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs impact run_cross_synthesis_job -d upstream` -> risk LOW
- `node .gitnexus/run.cjs impact run_academic_analysis -d upstream` -> risk LOW

## 2026-06-30

### Added

- Added a fulltext-assisted emotion-manipulation badge to the media article feed,
  rendered next to the substance-density badge (`6281282`):
  - `fulltext.extract_url_proxied` reuses the proven httpx + SOCKS5/trust_env path
    from `rss.py` to fetch HTML, then feeds `extract_from_html` — bypassing
    trafilatura's proxy-less downloader;
  - `enrich_topic_articles` concurrently fetches article bodies before each LLM
    batch (8s timeout, falls back to title+snippet on failure, never blocks);
  - the enrich LLM call emits two extra fields `emotion_score` / `emotion_note`
    in the same pass (zero extra calls);
  - pending re-enrichment includes `emotion_score < 0` only when fulltext is on,
    so disabling fulltext does not re-run the LLM for un-scorable emotion;
  - frontend shows `情绪 N` only when `emotion_score >= 0` (red=high manipulation).
- Config `FULLTEXT_FETCH_TIMEOUT=8`, `ENRICH_FETCH_FULLTEXT=1` (off → title+snippet only).

### Fixed

- Forced `emotion_score=-1` at the code level when no fulltext was fetched,
  ignoring whatever the LLM returns (`803b7d1`). Real-data validation showed the
  LLM ignores the prompt's "return -1 without body" instruction and scores
  emotion from title+snippet alone — a pseudo-judgement leak. The red line is now
  enforced in code, not by trusting the prompt. `substance_score` is left
  unchanged (title/snippet conservative estimate is acceptable; evidence bar differs).

### Reason

Emotion manipulation is a whole-article rhetorical pattern, so it must be judged
from body text, not the opening hook in a snippet. Fulltext is an *assist*, not a
dependency: when extraction fails, substance scoring continues and the emotion
badge simply does not show — never a fabricated judgement.

### Known limitation

- The emotion badge (and any fulltext-dependent feature) is only effective for
  sources whose body can be extracted (direct links / native RSS). The primary
  source — Google News RSS — yields `news.google.com/rss/articles/CBMi...` redirect
  URLs that trafilatura cannot extract, so those articles keep `emotion_score=-1`
  and show no badge. Resolving Google News redirect/encoded URLs is intentionally
  out of scope this round (redirect-following and `CBMi` base64 decoding are both
  fragile, and the resolved target may still block scraping). Fulltext-class
  features need a direct-link / better source to be broadly useful.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `162 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `14 passed`
- `git diff --check` -> exit 0
- `git check-ignore backend/.env backend/dossier.db` -> both ignored
- `node .gitnexus/run.cjs impact enrich_topic_articles -d upstream` -> risk LOW
- Real-data run (topic 1, enrich_limit=10): `fulltext_hits=0` (confirms the Google
  News limitation); 4 pseudo emotion scores leaked pre-hotfix were reset to -1 in
  the live DB with human approval (dry-run → UPDATE → recount 0).

## 2026-06-29

### Added

- Moved cognition marking from the media article feed to today's intelligence desk:
  - added a local cognition profile initialized from the user's 10 boundary-test answers;
  - added seed-level cognition marks with stable `target_key` URLs and optional notes;
  - added a small cognition-boundary queue in `DiscoveryPanel`;
  - removed article-level cognition sorting from the original article feed while keeping substance-score visibility;
  - allowed `PUT` in local CORS so browser saves can pass preflight.

### Reason

The cognition labels are useful for new frontier items, not for forcing the user to classify 100+ raw reports. V1 now collects low-friction judgement data from a small queue before any larger cognition map exists.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_cognition_marks.py -q` -> `5 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `153 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `14 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk medium, affected processes 3

### Added

- Implemented the readable-cognition roadmap in five small commits:
  - surfaced article substance-score coverage in the media feed;
  - rendered community sentiment as compact readable sample cards;
  - added on-demand article perspective for summary/fulltext sentence inspection;
  - added topic-local narrative convergence signals;
  - added one-click cognition marks and a lightweight cognition accumulation panel.

### Reason

Prioritize reading experience before larger cognition-map work: make substance, signals, and personal judgement markers visible without making LLM or heavy infrastructure part of the core path.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_cognition_marks.py -q` -> `2 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `150 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- tests/e2e/source-matrix.spec.ts -g "groups original articles"` -> `2 passed`
- `cd frontend && npm run test:e2e` -> `10 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk medium, affected processes 5

### Added

- Created the spec harness:
  - `spec/README.md`
  - `spec/project.md`
  - `spec/development.md`
  - `spec/acceptance.md`
- Extended `AGENTS.md` with project map, one-sentence goal, project structure, non-negotiable constraints, verification commands, and spec links.
- Added this changelog and linked it from `AGENTS.md` and `spec/README.md`.

### Reason

Give future agents a stable project map and reproducible acceptance standard before they edit code or claim work is complete.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `140 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `8 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk low, affected processes 0
