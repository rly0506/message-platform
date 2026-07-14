# RM-055 Coverage Observation Pipeline Design

Date: 2026-07-14

Status: Awaiting human spec approval after M1-M5 revision

Roadmap: RM-055

## Goal

Retain real, auditable, post-collection Coverage observations until a gate-ready
RM-055 source/fulltext review, no earlier than 2026-07-27, can make an
evidence-based GO, NO-GO, or continued-HOLD decision.

The pipeline must prove which topic collection transaction committed before a
Coverage snapshot was recorded. It must never infer that a source did not
publish merely because collection did not retrieve it, and it must never turn
`unknown` or `unclassified` metadata into a reason to expand sources.

The user approved the direction and authorized this specification revision and
reviewer communication. That authorization does not approve the revised text,
implementation, or the first real daily invocation. A later explicit
authorization is required before any runner writes the real
`backend/dossier.db`. No stage authorizes LLM calls, source expansion,
schema-heavy infrastructure, pushing, or merging `master`.

## Why The Existing Endpoint Is Insufficient

`GET /api/topics/{topic_id}/coverage` is an honest point-in-time snapshot, but
it does not retain history. The existing auto-refresh status exposes only a
count of refreshed topics. It does not identify those topics, and
`collect_topic()` records individual collector failures in its return value
without necessarily raising an exception.

Consequently, a standalone read-only HTTP scraper could retain a real snapshot
but could not prove that the corresponding topic had just completed collection
or that a collector failure was not being mistaken for a coverage gap.

## Decision And Alternatives

Use an auto-refresh-only post-commit observation hook plus a once-daily Windows
runner. This deliberately chooses review option M1-B.

The hook records Coverage immediately after a topic's auto-refresh transaction
commits. The runner gives the existing no-LLM refresh path one opportunity to
run each day even when the backend is not already open.

The observation scope is exact:

- only `_refresh_due_news` can produce a retained observation;
- manual CLI collection, search jobs, API-triggered search, and frontier
  discovery do not produce or count as Coverage observations;
- an eligible topic must be active, have existing articles, be stale by
  `AUTO_REFRESH_NEWS_INTERVAL_HOURS` (currently 6 hours), and not be protected
  by an active job or topic lock;
- each refresh cycle keeps the existing
  `AUTO_REFRESH_MAX_TOPICS_PER_CYCLE` limit (currently 3);
- the runner invokes `refresh_once` through the existing POST endpoint even
  when the temporary process sets `AUTO_REFRESH_ENABLED=0`; that setting and
  `AUTO_REFRESH_INITIAL_DELAY_SECONDS` control only the background scheduler,
  not the explicit once-daily invocation;
- a scheduled invocation with no due topic produces an empty manifest and no
  successful observation day.

This narrow scope avoids changing the heterogeneous commit boundaries in
`backend/cli.py`, `search_service.py`, and `collect_topic()` itself. The cost is
explicit: the pipeline may not reach 10 successful dates or three topics with
three dates by 2026-07-27. That outcome is continued HOLD, not an implementation
failure and never a reason to count manual or point-in-time snapshots.

Rejected alternatives:

- A pure read-only scheduled scraper cannot establish topic-level
  after-collection provenance and cannot meet the gate reliably while the
  backend is offline.
- Storing only the last auto-refresh result in memory loses earlier cycles and
  loses all provenance on process restart.
- Adding observation tables or a queue to SQLite would expand database and
  migration risk without improving the append-only audit requirement.

GitNexus reports LOW upstream risk for `_refresh_due_news`, `refresh_once`, and
`status_snapshot`: at most one direct caller and no affected indexed execution
flow. The implementation still requires fresh impact checks immediately before
editing those symbols.

## Architecture

### 1. Observation recorder

Add one focused backend service responsible for filesystem evidence only. It
will:

- build the existing Coverage snapshot after the topic transaction commits;
- retain the complete `collect_topic()` result, including request-level errors;
- write one immutable topic observation per committed refresh;
- finish each refresh run with an atomic manifest that lists expected,
  captured, failed, and skipped topic IDs;
- compute SHA-256 and byte length for every retained topic observation;
- verify and summarize retained observations without opening SQLite.

The service does not collect data, call an LLM, choose sources, classify
unknown metadata, or write the database.

### 2. Auto-refresh integration

`_refresh_due_news` will preserve structured outcomes for attempted topics.
After `collect_topic()`, local analysis, and `session.commit()` succeed, it will
retain the returned `collect_topic()` result, close the topic's write Session,
and open a new short-lived read Session against the same engine. The new
Session calls `build_coverage_snapshot()` for the committed topic ID, closes,
and passes the serializable snapshot to the filesystem recorder. An
uncommitted snapshot, a reused dirty write Session, or a Session shared across
topics is invalid by contract.

Observation-file failure is fail-soft for collection: it must not roll back or
pretend that the already committed collection failed. The refresh result and
run manifest must expose the observation failure, and the affected day cannot
be counted as a complete observation day.

The existing constraints remain unchanged:

- only stale, active topics with existing articles are eligible;
- the existing maximum-topics-per-cycle limit remains in force;
- queued/running topic jobs and topic write guards still cause skips;
- GNews plus curated feeds and local analysis remain the only news path;
- LLM, academic, sentiment, OpenCLI, and cross-synthesis paths remain excluded.
- frontier refresh never produces a Coverage observation.

### 3. API compatibility

The existing auto-refresh response fields and meanings remain unchanged:
`enabled`, `running`, `last_started_at`, `last_finished_at`, `last_error`,
`news_refreshed`, `news_errors`, `frontier_refreshed`, and `skipped_active`.

Observation integration may add only these optional top-level fields:

- `observation_run_id`;
- `observation_status` with `complete`, `incomplete`, `empty`, or `not_run`;
- `observation_error`, using an empty string when no recorder error exists.

A successful database commit continues to increment `news_refreshed` even if
filesystem capture later fails. Such a failure sets observation status to
`incomplete`; it does not enter `news_errors`, whose existing collection/
database meaning is preserved. Soft collector errors returned by
`collect_topic()` remain in the local manifest and do not silently disappear.

Per-topic structured outcomes remain in the ignored manifest and read-only CLI;
they do not enlarge the HTTP payload. Frontend and API regressions must prove
that all legacy keys retain their previous type and semantics and that clients
which ignore the additive fields behave unchanged.

### 4. Status CLI

Expose two Typer commands through the existing `backend/cli.py` command
surface:

- `coverage-verify`: validate schemas, manifests, checksums, file membership,
  and observation timestamps;
- `coverage-status`: report valid days, per-topic observation counts,
  collector degradation, metadata debt, repeated raw distributions, and gate
  readiness.

Both commands require an explicit observation window. They do not modify raw
files and do not automatically decide whether to add a source or persist
fulltext.

### 5. Daily Windows runner

Add a PowerShell runner that follows existing scheduled-task conventions:

1. Acquire `backend/coverage_observations/.runner.lock` exclusively so
   overlapping manual/scheduled runs do not create competing backend processes.
2. Reuse the backend only when its health and OpenAPI responses identify the
   expected app and expose both the auto-refresh and Coverage endpoints.
3. If the backend is offline, start a temporary hidden Uvicorn process with its
   background scheduler disabled, wait for health, and remember that exact PID.
4. If an existing auto-refresh is running, wait for it and use the hook evidence
   from that run; otherwise invoke `POST /api/auto-refresh/run` once.
5. Run observation verification and print the gate status.
6. Stop only the temporary backend process started by this invocation.

If port 8000 belongs to an unexpected service, the runner fails without killing
the process. Logs go to the already ignored `backend/logs/` directory. The
Windows task uses `StartWhenAvailable`, `WakeToRun`, and an ignore-new-instance
policy. The default task name is `Personal Intelligence RM055 Coverage
Observation`, its default local schedule is 09:00 Asia/Shanghai, and the runner
accepts explicit window-start/window-end parameters. Registration, inspection,
manual run, and removal commands will be documented.

## Storage Contract

Raw evidence lives under ignored local runtime storage:

```text
backend/coverage_observations/
  .runner.lock
  YYYY-MM-DD/
    <run-id>/
      topic-<topic-id>.json
      manifest.json
```

Adding `backend/coverage_observations/` to the root `.gitignore` is a blocking
implementation DoD and must land before any recorder or runner smoke test. The
lock, temporary files, topic observations, and manifests all live beneath that
single ignored root. Acceptance requires:

- `git check-ignore -v backend/coverage_observations/.runner.lock` identifies
  the new rule;
- `git ls-files backend/coverage_observations` returns no tracked path;
- the following command shows no runtime evidence or secret staged or tracked:

  ```powershell
  git status --short -- backend/coverage_observations backend/logs backend/dossier.db backend/.env
  ```

The observation date uses `Asia/Shanghai`; timestamps also retain UTC ISO-8601.
For example:

```json
{
  "observed_at_utc": "2026-07-14T01:00:00Z",
  "observation_date": "2026-07-14",
  "timezone": "Asia/Shanghai"
}
```

Run IDs contain a UTC timestamp and a collision-resistant suffix. Run
directories are never reused or overwritten.

A topic observation contains:

- schema version, run ID, UTC timestamp, Shanghai observation date;
- topic ID and the topic name retained only in ignored local evidence;
- provenance identifying auto-refresh and successful transaction commit;
- the complete serializable `collect_topic()` result, including requests and
  errors;
- the complete existing Coverage response, including article/evidence IDs,
  distributions, decode evidence, registry classifications, and explicit
  fulltext `unknown`;
- no article body, API key, environment value, proxy address, or credential.

Topic files are written to temporary sibling files, flushed, and atomically
renamed. The manifest is written last and contains:

- run timestamps and refresh-level errors;
- attempted, committed, skipped, failed, and observation-failed topic IDs;
- every expected topic filename, SHA-256, and byte length;
- enough information to prove that every committed topic was either captured
  or explicitly marked as an observation failure.

A run directory without a valid final manifest is incomplete and never counts.

## Counting And Gate Semantics

The status command reports evidence; the human gate review makes the decision.

### Observation window and review date

There is no backfill. The first window begins on the first successful Shanghai
observation date produced by the implemented pipeline and spans that date plus
the next 13 calendar dates. The review date is:

```text
max(2026-07-27, first_successful_observation_date + 13 days)
```

Therefore 2026-07-27 remains the earliest possible review, not a guaranteed
decision date. If the window contains fewer than 10 successful observation
dates, or fewer than three topics with three dates each, the only valid result
is continued HOLD. The next review is moved to the earliest later date on which
a trailing 14-date window can satisfy both thresholds. Empty/no-due runs,
manual collection, old point-in-time Coverage responses, and collector errors
cannot be relabelled or backfilled to make the arithmetic pass.

If no successful observation date exists, no window or review date is inferred;
the gate remains HOLD until a first valid date exists.

### Valid topic observation

A topic observation is valid only when:

- its manifest and checksum validate;
- provenance states that the topic transaction committed before capture;
- the retained Coverage response matches the topic ID;
- explicit `unknown` values remain unchanged;
- the observation falls inside the requested calendar window.

Multiple complete runs for the same topic on one Shanghai calendar date count
as one topic observation. The deterministic representative is the latest valid
topic observation from a complete run on that date; all earlier raw runs remain
retained and remain visible in verification output.

### Successful observation day

A run is complete only when its manifest validates, at least one topic
transaction committed, and every committed topic has a valid retained
observation. A calendar date counts once when it contains at least one complete
run. Incomplete runs remain reported but cannot invalidate or replace a later
complete run. A run with no due topics does not manufacture an observation day.

Collector request errors do not erase real committed evidence. They are exposed
as degradation and make any related absence ineligible as a source-coverage
claim. The status output separately reports capture-valid days and
collector-clean topic observations so the final reviewer cannot overlook the
distinction.

### Gate readiness

For the requested window, status reports:

- count and dates of successful observation days;
- captured active topic IDs with their distinct observation-date counts;
- whether at least three topics have at least three dates each;
- raw recurrence of collector, language, country, source, registry type/tier,
  URL decode, and fulltext statuses;
- collector failures affecting each topic/date;
- all `unknown` and `unclassified` article IDs as metadata debt, never as a
  source-expansion reason.

A proposed named gap may proceed to human review only when it recurs on at
least three observation dates and two topics, or satisfies the gate's explicit
single-topic stakeholder/language exception. The tool does not invent a gap
threshold or candidate feed.

## Source And Fulltext Decisions

The first gate-ready review must produce two separate human decisions:

1. Source expansion: `GO`, evidence-based `NO-GO`, or continued `HOLD`.
2. Fulltext persistence scope: `GO`, evidence-based `NO-GO`, or `DEFER`.

Insufficient days remain `HOLD`, not NO-GO. A source NO-GO can close RM-055 only
if the human explicitly accepts evidence-based non-expansion as satisfying the
conditional M3' outcome; otherwise the original "first batch enters feeds"
wording remains unmet.

Coverage currently reports fulltext as `unknown` because bodies are not
persisted. This observation pipeline cannot turn that unknown into evidence for
a fulltext GO. Without a separately approved, real fulltext probe, the honest
gate-review outcome for that dimension is `DEFER` or `NO-GO`, with the reason
recorded.

If source expansion is approved, the existing gate still limits the first
batch to three feeds and requires three successful probes on separate dates,
lawful public access, registry metadata, duplication checks, tests, and a
post-rollout comparison. The observation pipeline does not bypass those steps.

## Error Handling And Safety

- Capture failures are visible in the manifest, refresh status, runner exit
  code, and ignored log; they never become a successful day.
- Collector failures stay attached to the exact topic/date and cannot be
  rewritten as "source did not publish."
- Schema or checksum mismatch makes the affected run invalid; the tool never
  repairs or rewrites raw evidence automatically.
- Temporary backend startup never enables the background scheduler and never
  stops an unrelated process.
- Tests continue to use the isolated temp database. Passing the implementation
  gates does not itself authorize a real run; the first invocation that may
  update `backend/dossier.db` requires a separate explicit human authorization.
- Raw observations, logs, `.env`, databases, and credentials remain ignored and
  uncommitted.
- No source is added, enabled, or probed merely because the observer exists.
- Before implementation begins, BOARD and `spec/current-state.md` must register
  the observation pipeline as an `ACTIVE-GATE`, record its exact
  auto-refresh-only scope, and retain RM-055 as the sole `CURRENT` product
  roadmap.

## Testing And Acceptance

Implementation follows TDD and includes the smallest tests that prove:

- post-commit capture receives the exact topic and collection result;
- capture opens a fresh read Session only after the topic write Session has
  committed and closed;
- a database failure produces no valid observation;
- an observation write failure does not undo committed collection and makes the
  run incomplete;
- topic files and manifests are atomic, immutable, and checksum-verifiable;
- incomplete, corrupt, mismatched, and out-of-window runs do not count;
- same-topic same-day runs deduplicate deterministically;
- collector errors remain visible and disqualify related absence claims;
- `unknown` and `unclassified` remain metadata debt;
- status calculates the 10-day, three-topic/three-date, and recurrence gates
  without making a GO/NO-GO decision;
- a first-success date after 2026-07-14 moves the earliest review date, and an
  insufficient 14-date window remains HOLD;
- manual CLI/search/API collection and frontier refresh do not create or count
  observations under the selected M1-B scope;
- legacy auto-refresh response keys preserve their types and meanings while
  the three optional observation fields remain additive;
- auto-refresh still excludes LLM/OpenCLI/academic/sentiment/cross paths;
- the PowerShell runner reuses an expected backend, starts/stops only its own
  hidden temporary backend, and fails safely on an unexpected port owner.
- the observation root and `.runner.lock` are ignored, and no observation,
  `.env`, log, or database path is tracked.

Verification for implementation uses targeted backend tests first, then the
full backend suite, PowerShell syntax/smoke checks, `git diff --check`, GitNexus
status and `detect-changes`, and secret/database ignore checks. The first real
capture is run only after the implementation passes those gates and the human
separately authorizes the real daily invocation.

## Operational Completion Evidence

Raw evidence remains local for privacy and database-bound reproducibility. The
gate review commits a compact report containing:

- window and timezone;
- successful dates and per-topic counts;
- degraded/invalid dates and exact reasons;
- recurring named gaps and excluded metadata debt;
- hashes of the reviewed raw manifests;
- the separate source and fulltext decisions;
- candidate acceptance or rejection evidence when applicable;
- final verification and GitNexus scope.

RM-055 remains active until the observation gate and both human decisions are
closed honestly. This design itself does not mark RM-055 complete.
