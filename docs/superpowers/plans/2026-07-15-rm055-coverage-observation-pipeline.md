# RM-055 Coverage Observation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist honest post-commit Coverage evidence from the existing no-LLM refresh path, expose filesystem-only verification/status commands, and start the approved longitudinal observation window without changing the HTTP/frontend contract.

**Architecture:** A new pure-filesystem service owns immutable topic JSON, final manifests, verification, and gate arithmetic. `_refresh_due_news` remains the only producer: it commits and closes its write Session, keeps the topic guard, opens a fresh read Session for `build_coverage_snapshot`, then hands serializable data to the recorder. The existing Typer CLI chooses one online POST or one offline synchronous refresh, and the existing daily script calls it once between discovery and email.

**Tech Stack:** Python 3.11+, SQLModel, Typer, standard-library `json/hashlib/pathlib/urllib`, pytest, PowerShell, GitNexus.

**Authoritative design:** `docs/superpowers/specs/2026-07-14-rm055-coverage-observation-pipeline-design.md` at commit `1190aca`.

---

### Task 1: Activate the gate and protect runtime evidence

**Files:**
- Modify: `.gitignore`
- Modify: `spec/current-state.md`
- Modify: `spec/roadmap-ledger.md`
- Modify locally, never stage: `.agent-bridge/BOARD.md`

- [ ] **Step 1: Record the active gate without creating a second product roadmap**

Add one compact current-truth entry to `spec/current-state.md` and `spec/roadmap-ledger.md`: RM-055 remains the sole `CURRENT` roadmap; the slim Coverage observation pipeline is an `ACTIVE-GATE`; implementation and the first real run are authorized; source expansion remains HOLD; the Grok/OpenCode topic-load race remains outside scope.

- [ ] **Step 2: Add the blocking ignore rule**

Add exactly this runtime rule near the existing backend local-output rules:

```gitignore
backend/coverage_observations/
```

- [ ] **Step 3: Update the local board checkpoint**

Record HEAD, `ACTIVE-GATE`, accepted no-lock/no-fingerprint residual risk, and the current execution order in `.agent-bridge/BOARD.md`. Do not stage `.agent-bridge/`.

- [ ] **Step 4: Verify ignore and staged scope**

Run:

```powershell
git check-ignore -v backend/coverage_observations/2099-01-01/test-run/manifest.json
git ls-files backend/coverage_observations
git diff --check
git add -- .gitignore spec/current-state.md spec/roadmap-ledger.md
git diff --cached --name-only
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
```

Expected: the first command cites the new rule; `git ls-files` is empty; staged paths are exactly the three tracked files; GitNexus reports documentation/config-only scope and zero product flows.

- [ ] **Step 5: Commit the active gate**

```powershell
git commit -m "docs: activate RM-055 coverage observation gate"
```

---

### Task 2: Build immutable observation storage

**Files:**
- Create: `backend/app/services/coverage_observation.py`
- Create: `backend/tests/test_coverage_observation.py`

- [ ] **Step 1: Write failing storage tests**

Add tests named `test_finish_run_writes_topic_before_manifest_with_hash_and_size`,
`test_atomic_write_never_replaces_existing_topic_or_manifest`,
`test_expected_is_derived_and_terminal_outcomes_are_disjoint`, and
`test_topic_capture_failure_can_finalize_as_observation_failed`.

Use only `tmp_path`; assert deterministic JSON bytes, SHA-256, byte length, exact file membership, `expected == captured | observation_failed`, and pairwise-disjoint `captured/observation_failed/failed/skipped`.

- [ ] **Step 2: Run tests and confirm RED**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation.py -q
```

Expected: collection error because `app.services.coverage_observation` does not exist.

- [ ] **Step 3: Implement the minimal filesystem model**

Create a focused module with no SQLModel or database imports. Use an
`ObservationRun` dataclass with `root`, `run_dir`, `run_id`,
`observed_at_utc`, `observation_date`, `captured`, `observation_failed`,
`failed`, and `skipped`. Expose these exact call signatures:

- `start_run(*, observed_at_utc: datetime, root: Path | None = None) -> ObservationRun`
- `record_topic(run: ObservationRun, *, topic_id: int, collect_result: dict[str, Any], coverage: dict[str, Any]) -> None`
- `mark_observation_failed(run: ObservationRun, *, topic_id: int, error: str) -> None`
- `mark_failed(run: ObservationRun, *, topic_id: int, error: str) -> None`
- `mark_skipped(run: ObservationRun, *, topic_id: int, reason: str) -> None`
- `finish_run(run: ObservationRun) -> Path`

Set `DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "coverage_observations"`.

Use one private `_atomic_write_new(path, payload)` helper: deterministic UTF-8 JSON, sibling temporary file, flush + `os.fsync`, and Windows no-replace rename semantics. Clean only the helper's own temporary file on failure. Do not create a reusable storage framework.

- [ ] **Step 4: Run storage tests and confirm GREEN**

```powershell
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation.py -q
```

Expected: all storage tests pass; no `backend/coverage_observations/` is created.

- [ ] **Step 5: Commit storage**

```powershell
cd ..
git add -- backend/app/services/coverage_observation.py backend/tests/test_coverage_observation.py
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
git commit -m "feat: add immutable coverage observation storage"
```

---

### Task 3: Verify evidence and calculate HOLD readiness

**Files:**
- Modify: `backend/app/services/coverage_observation.py`
- Modify: `backend/tests/test_coverage_observation.py`

- [ ] **Step 1: Write failing verifier/status tests**

Add tests named `test_verify_rejects_missing_unfinalized_corrupt_mismatched_and_extra_files`,
`test_status_counts_only_complete_nonempty_runs`,
`test_status_uses_latest_valid_topic_observation_per_shanghai_day`,
`test_status_preserves_collector_errors_as_degradation`,
`test_status_treats_unknown_and_unclassified_as_metadata_debt`,
`test_status_uses_first_success_and_maximum_review_date`,
`test_status_returns_hold_without_ten_days_and_three_topics_three_dates`, and
`test_verify_and_status_never_open_sqlmodel_session`.

The fixture must create all evidence under `tmp_path`. A legitimate HOLD is valid status, not an exception.

- [ ] **Step 2: Run tests and confirm RED**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation.py -q
```

Expected: failures for missing verification/status functions.

- [ ] **Step 3: Implement pure-filesystem verification and status**

Add exact call signatures
`verify_observations(*, root: Path, start_date: date, end_date: date) -> dict[str, Any]`
and
`build_observation_status(*, root: Path, start_date: date, end_date: date) -> dict[str, Any]`.

Return structured `valid`, `errors`, valid/invalid runs, successful dates, per-topic distinct dates, degradation, metadata debt, `first_successful_date`, `review_date`, `gate_ready`, and `hold_reasons`. Use `ZoneInfo("Asia/Shanghai")`. Never emit GO/NO-GO, repair files, import `app.db`, or open SQLite. Missing/unreadable/unfinalized evidence is invalid; insufficient but valid evidence is HOLD with a successful function return.

- [ ] **Step 4: Run tests and confirm GREEN**

```powershell
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation.py -q
```

- [ ] **Step 5: Commit verifier/status**

```powershell
cd ..
git add -- backend/app/services/coverage_observation.py backend/tests/test_coverage_observation.py
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
git commit -m "feat: verify coverage observation history"
```

---

### Task 4: Capture only committed auto-refresh topics

**Files:**
- Modify: `backend/app/services/auto_refresh.py`
- Modify: `backend/tests/test_auto_refresh.py`

- [ ] **Step 1: Refresh impact evidence before symbol edits**

```powershell
node .gitnexus/run.cjs status
node .gitnexus/run.cjs impact refresh_once -d upstream --include-tests --repo message-platform
node .gitnexus/run.cjs impact _refresh_due_news -d upstream --include-tests --repo message-platform
```

Expected current risk: LOW; `refresh_once` has direct caller `_loop`; `_refresh_due_news` has direct caller `refresh_once`; zero indexed flows. Stop and report if HIGH/CRITICAL.

- [ ] **Step 2: Write failing integration tests**

Add tests named `test_refresh_records_exact_collect_result_after_commit_in_fresh_session`,
`test_topic_guard_is_held_until_snapshot_session_closes`,
`test_commit_failure_creates_no_expected_observation`,
`test_topic_capture_failure_preserves_commit_and_finalizes_incomplete_run`,
`test_root_create_failure_preserves_commit_and_logs_invalid_run`,
`test_manifest_finalize_failure_preserves_commit_and_logs_invalid_run`,
`test_refresh_contract_remains_exactly_nine_fields`, and
`test_frontier_and_ordinary_collection_never_record_observations`.

Inject every observation root with `tmp_path`. Assert the write Session exits before the fresh read Session opens and that the outer `claim_topic` guard releases only after snapshot Session close.

- [ ] **Step 3: Run focused tests and confirm RED**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_auto_refresh.py tests/test_coverage_observation.py -q
```

- [ ] **Step 4: Implement the post-commit hook without changing the API result**

Change only the existing signatures to
`refresh_once(now: datetime | None = None, *, observation_root: Path | None = None) -> dict[str, Any]`
and
`_refresh_due_news(now: datetime, *, observation_root: Path | None = None) -> tuple[int, int, list[str]]`.

Start one observation run per `_refresh_due_news` invocation. The candidate universe is only stale active topics with persisted articles. Fresh, empty, and archived topics never enter the manifest. Record `skipped` reasons only for stale candidates: `guard`, `active_job`, or `cycle_limit` after the existing successful-refresh limit is reached.

Inside the existing topic guard: retain `collect_topic()`'s exact result; analyze; commit; exit the write Session; increment `refreshed`; open/close a fresh `Session(engine)` and build the snapshot by `topic_id`; then record the topic. Topic capture failures become `observation_failed` only if final manifest writing succeeds. Root creation or finalization failures log an invalid run and do not enter `_state`, `news_errors`, or the nine-field response. `_refresh_due_frontier` remains unchanged.

- [ ] **Step 5: Run focused tests and confirm GREEN**

```powershell
..\venv\Scripts\python.exe -m pytest tests/test_auto_refresh.py tests/test_coverage_observation.py -q
```

- [ ] **Step 6: Commit integration**

```powershell
cd ..
git add -- backend/app/services/auto_refresh.py backend/tests/test_auto_refresh.py
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
git commit -m "feat: record post-commit coverage observations"
```

---

### Task 5: Add the three read/trigger CLI commands

**Files:**
- Modify: `backend/cli.py`
- Create: `backend/tests/test_coverage_observation_cli.py`

- [ ] **Step 1: Write failing Typer tests**

Use `typer.testing.CliRunner` and add
`test_refresh_once_posts_once_after_valid_health`,
`test_refresh_once_runs_local_once_only_after_connection_refused`,
`test_refresh_once_rejects_bad_post_protocol_without_local_fallback` (parameterized
with missing-key, extra-key, and wrong-type payloads),
`test_refresh_once_rejects_timeout_bad_health_and_post_transport_failure`,
`test_coverage_verify_requires_window_and_uses_injected_root`, and
`test_coverage_status_returns_zero_for_hold_and_nonzero_for_invalid_evidence`.

- [ ] **Step 2: Run tests and confirm RED**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation_cli.py -q
```

- [ ] **Step 3: Implement strict standard-library HTTP and filesystem commands**

Add a nine-field validator that rejects bool-as-int, missing/extra keys, non-string error entries, and wrong nullable timestamp types. `refresh-once` performs health GET then exactly one POST; only `URLError` rooted in connection-refused/no-listener selects `init_db(); auto_refresh.refresh_once()`. Timeout, reachable bad health, wrong POST protocol, and POST errors exit nonzero with no fallback.

Add required `--start` and `--end` ISO dates plus injectable `--root` to `coverage-verify` and `coverage-status`. Print deterministic JSON. Invalid evidence exits 1; valid HOLD exits 0.

- [ ] **Step 4: Run CLI tests and confirm GREEN**

```powershell
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation_cli.py -q
```

- [ ] **Step 5: Commit CLI**

```powershell
cd ..
git add -- backend/cli.py backend/tests/test_coverage_observation_cli.py
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
git commit -m "feat: add coverage observation commands"
```

---

### Task 6: Attach refresh to the existing daily script

**Files:**
- Modify: `scripts/send_daily_digest.ps1`
- Modify: `backend/tests/test_daily_email.py`

- [ ] **Step 1: Write the failing script-order regression**

Add `test_daily_digest_script_orders_discover_refresh_once_before_email` that reads the script, asserts exactly one `'refresh-once'`, verifies index order `discover < refresh-once < daily-email`, and verifies the refresh nonzero branch logs a warning without throwing before email.

- [ ] **Step 2: Run the test and confirm RED**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_daily_email.py -q
```

- [ ] **Step 3: Add the one fail-soft invocation**

Insert after successful discovery and before email:

```powershell
Write-Log "Running RM-055 coverage refresh."
& $python 'cli.py' 'refresh-once' *>&1 | Tee-Object -FilePath $logPath -Append
if ($LASTEXITCODE -ne 0) {
    Write-Log "WARNING: coverage refresh failed with exit code $LASTEXITCODE; continuing daily email."
}
```

Do not add a task, process manager, port fingerprint, lock, or retry.

- [ ] **Step 4: Verify script syntax and tests**

```powershell
..\venv\Scripts\python.exe -m pytest tests/test_daily_email.py tests/test_coverage_observation_cli.py -q
cd ..
[scriptblock]::Create((Get-Content -Raw scripts/send_daily_digest.ps1)) | Out-Null
```

- [ ] **Step 5: Commit daily integration**

```powershell
git add -- scripts/send_daily_digest.ps1 backend/tests/test_daily_email.py
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
git commit -m "feat: observe coverage in daily digest task"
```

---

### Task 7: Run full gates, document reality, and start the real window

**Files:**
- Modify: `spec/current-state.md`
- Modify: `spec/roadmap-ledger.md`
- Modify: `spec/CHANGELOG.md`
- Create: `docs/operations/rm055-coverage-observation-task-report-2026-07-15.md`
- Modify locally, never stage: `.agent-bridge/BOARD.md`, `.agent-bridge/TO_CLAUDE.md`, `.agent-bridge/TO_OPENCODE.md`

- [ ] **Step 1: Run focused and full backend gates**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_coverage_observation.py tests/test_coverage_observation_cli.py tests/test_auto_refresh.py tests/test_daily_email.py -q
..\venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 2: Run frontend regression gates**

```powershell
cd ..\frontend
npm run build
npm run test:e2e
```

If the already-diagnosed Windows Playwright-owned Vite shutdown hang recurs only after every test passes, rerun the exact suite with one controlled PowerShell `Start-Job` Vite server so Playwright reuses it, stop/remove that job in `finally`, and record both the standard-command timeout and the successful controlled result. Do not change frontend code or config in this batch.

- [ ] **Step 3: Run scope and safety gates before completion claims**

```powershell
cd ..
git diff --check
node .gitnexus/run.cjs status
node .gitnexus/run.cjs detect-changes --scope compare --base-ref master --repo message-platform
git status --short -- backend/.env backend/dossier.db backend/coverage_observations backend/logs
git check-ignore -v backend/.env backend/dossier.db backend/coverage_observations/probe
git ls-files backend/coverage_observations backend/.env backend/dossier.db
```

Expected: changed symbols/flows match the recorder, auto-refresh, CLI, and daily script; secrets/database/evidence remain ignored and untracked.

- [ ] **Step 4: Run the already-authorized first real refresh**

From `backend/`, run only the refresh command, not an unsolicited email:

```powershell
..\venv\Scripts\python.exe cli.py refresh-once
..\venv\Scripts\python.exe cli.py coverage-verify --start 2026-07-15 --end 2026-07-15
..\venv\Scripts\python.exe cli.py coverage-status --start 2026-07-15 --end 2026-07-15
```

Record whether the run was complete, empty/no-due, degraded, or invalid. An empty run does not start the window; do not backfill or alter staleness to manufacture a success. Never stage `backend/dossier.db`, logs, or observation files.

- [ ] **Step 5: Write the evidence report and current truth**

Record changed files, test commands/results, GitNexus risk/flows, real-run Shanghai date, manifest hashes/counts, HOLD reasons, accepted offline race risk, and secret/database safety. Update current-state/ledger/changelog and local mailboxes without claiming source/fulltext GO.

- [ ] **Step 6: Commit only tracked reports/state**

```powershell
git add -- spec/current-state.md spec/roadmap-ledger.md spec/CHANGELOG.md docs/operations/rm055-coverage-observation-task-report-2026-07-15.md
git diff --cached --check
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform
git commit -m "docs: record RM-055 observation pipeline evidence"
```

- [ ] **Step 7: Retry the approved feature-branch backup once**

```powershell
git push origin feature/academic-reading-signals
```

If `github.com:443` remains unreachable, report the external backup blocker and continue retaining all local commits; never push or merge `master`.
