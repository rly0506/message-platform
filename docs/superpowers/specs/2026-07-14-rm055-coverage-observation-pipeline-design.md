# RM-055 Coverage Observation Pipeline Design

Date: 2026-07-14

Slim revision approved: 2026-07-15

Status: Approved for implementation planning, TDD implementation, and the first
real daily run after all implementation gates pass

Roadmap: RM-055

## Goal And Authorization

Retain auditable Coverage observations after real no-LLM news refreshes so the
RM-055 source gate can distinguish repeated collection evidence from missing or
unknown metadata.

The 2026-07-15 revision is already human-approved. It does not require another
human, Claude, or OpenCode review before an implementation plan and TDD
implementation. After implementation is fully green, the first real daily run
is also authorized; report that run to the agent mailbox. This authorization
does not permit source expansion, LLM work, or a merge to `master`. The
independently approved fulltext-probe batch remains outside this specification
and must be implemented separately.

The smallest sufficient design is a post-commit filesystem recorder, three
Typer commands on the existing CLI, and one added call in the existing daily
PowerShell script. It adds no dependency, database table, frontend contract,
service process, or scheduled task.

## Scope Boundary

The sole observation trigger is a successful per-topic commit inside
`_refresh_due_news`. This is true regardless of how `refresh_once` was
reached:

- the existing background scheduler;
- `POST /api/auto-refresh/run`;
- the new offline `refresh-once` CLI path.

Ordinary collect commands, search jobs, API search/collection, point-in-time
Coverage reads, discovery, and frontier refresh never create or count as
observations. A run with no due topic may retain an empty manifest for
diagnostics, but it never creates a successful observation day.

Existing eligibility and safety behavior remains in force: active topics with
persisted articles must be stale, topic/job guards still skip competing work,
the per-cycle maximum remains unchanged, and the path stays no-LLM. Academic,
sentiment, OpenCLI, enrichment, synthesis, and frontier work remain outside the
news observation.

## Committed Observation Flow

For each eligible topic, implementation must use this exact order:

1. Run `collect_topic()` and retain its complete serializable result,
   including every `requests` entry and every `errors` entry.
2. Run local analysis with persistence enabled.
3. Commit the topic transaction.
4. Fully exit and close the write `Session`.
5. Open a new short-lived read `Session` against the same engine.
6. Load/call `build_coverage_snapshot` only by the committed `topic_id`;
   do not pass a detached topic object or reuse state from the write Session.
7. Close the read Session completely.
8. Pass the collection result and Coverage snapshot to the filesystem writer.

There is no valid observation before step 3 succeeds. A commit exception rolls
back through the existing refresh path, contributes no expected observation,
and remains an existing `news_errors` failure.

A topic snapshot or topic-file failure after the commit is fail-soft for the
refresh:

- it never rolls back the committed database work;
- it never decrements `news_refreshed`;
- it never enters `news_errors`;
- when the final manifest can still be written, it is recorded as local
  `observation-failed` evidence and exposed by `coverage-verify` /
  `coverage-status`.

Failure to create the observation root or atomically finalize the manifest is
a run-level failure: the whole run is invalid or unfinalized. Normal backend/
command logging must retain the in-memory committed topic IDs and exact error,
but a nonexistent final manifest cannot be claimed as topic-level audit
evidence. The Coverage commands exit nonzero for missing, unreadable, or
unfinalized evidence; they do not pretend to reconstruct facts that were never
persisted. Silence is not a valid fail-soft outcome.

## HTTP And Frontend Contract

The auto-refresh HTTP response remains exactly these nine top-level fields,
with their current types and meanings:

- `enabled`
- `running`
- `last_started_at`
- `last_finished_at`
- `last_error`
- `news_refreshed`
- `news_errors`
- `frontier_refreshed`
- `skipped_active`

No observation detail enters HTTP. `frontend/src/types/dossier.ts` does not
change.

## Filesystem Evidence Contract

Before any recorder smoke test or real invocation,
`backend/coverage_observations/` must be covered by the root `.gitignore`.
That ignore rule is a blocking implementation DoD.

```text
backend/coverage_observations/
  YYYY-MM-DD/
    <run-id>/
      topic-<topic-id>.json
      manifest.json
```

The date is the `Asia/Shanghai` calendar date at capture time. Each record also
keeps a UTC ISO-8601 timestamp. Run IDs are collision-resistant, and a run
directory is never reused.

Each topic JSON contains:

- schema version, run ID, UTC timestamp, Shanghai date, and topic ID;
- provenance naming `_refresh_due_news` and the successful commit;
- the complete `collect_topic()` result;
- the complete existing Coverage snapshot, including evidence IDs,
  distributions, registry classifications, decode evidence, and explicit
  fulltext `unknown`;
- no body text, credential, environment value, API key, or proxy detail.

Topic JSON is encoded deterministically to bytes, written to a sibling
temporary file, flushed, and atomically installed with create-if-absent
semantics. An existing destination is an error and is never replaced. The
manifest records the SHA-256 and byte length of the exact final bytes.
One small standard-library helper implements this Windows runtime boundary;
the feature does not introduce a general storage abstraction.

The manifest is written atomically and last, also without replacement. It
records these topic-ID sets and counts:

- `expected`: the derived set of topic transactions that committed and
  therefore require capture;
- `captured`: expected topics with a valid immutable topic JSON;
- `failed`: refresh attempts that failed before commit;
- `skipped`: topics not attempted because eligibility or concurrency rules
  excluded them;
- `observation-failed`: expected topics whose post-commit capture failed.

The terminal outcome sets `captured`, `observation-failed`, `failed`, and
`skipped` are pairwise disjoint. `failed` means an attempted refresh failed
before commit; `skipped` means the candidate was not attempted because an
eligibility or concurrency guard excluded it. The verifier must prove:

```text
expected = captured ∪ observation-failed
captured ∩ observation-failed = ∅
failed ∩ expected = ∅
skipped ∩ (expected ∪ failed) = ∅
manifest bytes/checksums/file membership match the retained topic files
```

Unlisted, partial, checksum-mismatched, replaced, or manifest-less evidence is
invalid. Raw run directories and all earlier topic files remain append-only.

## CLI Contract

All commands live on the existing Typer surface in `backend/cli.py`.

### `refresh-once`

`refresh-once` uses only Python's standard-library HTTP client and follows
one decision tree:

1. `GET http://127.0.0.1:8000/api/health`.
2. If and only if the response is HTTP 200 and its JSON object has
   `status == "ok"`, send exactly one
   `POST http://127.0.0.1:8000/api/auto-refresh/run`. This reuses the
   backend process's existing in-process lock. Treat the POST as successful
   only when its JSON object has the exact existing nine-field key set and
   compatible value types.
3. Only an explicit connection-refused/no-listener result may select the
   offline path. That path calls `init_db()`, then synchronously calls
   `refresh_once()` exactly once in the CLI process.
4. A health timeout, reachable non-200 response, malformed JSON, wrong health
   value, other transport error, or failed POST exits nonzero and never falls
   back locally.

The command never starts the scheduler or a web server, manages another
process, creates its own lock, or retries a refresh. A successfully returned
existing fail-soft result is printed once; `last_error` or `news_errors`
must not trigger a second run.

The approved slim design accepts two local operational residual risks instead
of rebuilding the removed runner: the loopback health response is not a strong
application identity, and a backend that starts immediately after a refused
health connection (or two simultaneous offline CLI invocations) can race the
offline call across processes. The supported unattended topology is one
existing Windows daily task. Reachable-but-unexpected responses fail closed,
run IDs never overwrite evidence, and any incomplete/corrupt result is
ineligible for counting. Do not reintroduce a cross-process lock, OpenAPI/port
fingerprint, or temporary backend under this specification.

### `coverage-verify` and `coverage-status`

Both commands are filesystem-only:

- `coverage-verify` validates schemas, atomic-completion markers, manifest
  membership, SHA-256 values, byte lengths, topic identity, and timestamps;
- `coverage-status` summarizes valid dates, per-topic dates, collector
  degradation, metadata debt, and gate arithmetic.

They never open SQLite, call `init_db()`, repair or rewrite raw evidence, or
emit an automatic source/fulltext GO or NO-GO. Invalid or inaccessible evidence
produces a nonzero exit.

## Existing Daily Script

`scripts/send_daily_digest.ps1` adds exactly one `refresh-once` invocation
and keeps one scheduled workflow:

```text
discover -> refresh-once -> daily-email
```

The new command's stdout/stderr goes to the script's existing daily log. A
`refresh-once` infrastructure/protocol nonzero result is logged as a warning
and the script continues to `daily-email`; it does not invoke refresh again.
Existing discover and email failure behavior is unchanged.

## Counting And Review Semantics

All day arithmetic uses `Asia/Shanghai`. There is no backfill.

A complete run has a valid final manifest, at least one captured committed
topic, and no `observation-failed` expected topic. Pre-commit `failed` and
`skipped` entries remain visible but do not fabricate evidence. Empty,
incomplete, corrupt, or out-of-window runs never count.

A Shanghai date is successful when it contains at least one complete run. For
the same topic and Shanghai date, the latest valid observation is the
deterministic counting representative; every earlier raw observation remains
retained and visible.

Collector errors remain attached to the exact topic/date. They do not erase a
committed snapshot, but any related absence is ineligible as evidence of a
source gap. `unknown` and `unclassified` are reported only as metadata debt,
never converted into source absence.

The first window starts on the first real successful Shanghai observation date
and covers that date plus 13 calendar dates. The earliest review is:

```text
max(2026-07-27, first_successful_observation_date + 13 days)
```

Before a first success there is no inferred window. If a review has fewer than
10 successful dates, fewer than three topics represented on three distinct
dates each, or otherwise insufficient recurring evidence under the canonical
RM-055 gate, the only result is `HOLD`. Do not loosen validity, count empty
days, or backfill snapshots to reach a threshold.

The commands report evidence and arithmetic; a human makes the source decision.

## Separate Fulltext Evidence Batch

The approved fulltext probe is an independent B batch and is not designed or
implemented here. Coverage observations do not fetch bodies and cannot turn
fulltext `unknown` into a fulltext GO. The later review may consider both
batches, but each keeps its own evidence and acceptance boundary.

## Implementation And Test Gate

Implementation uses TDD. Before editing any function, class, or method, rerun
GitNexus upstream impact analysis against the current index for that exact
symbol. Report HIGH or CRITICAL blast radius before editing. No historical
risk label in an earlier document substitutes for this check.

Tests must prove at least:

- online `refresh-once`: valid health causes exactly one POST and no local
  call;
- offline `refresh-once`: explicit refusal causes one `init_db()` and one
  synchronous local call;
- timeout, malformed/reachable health, other transport errors, and POST failure
  exit nonzero with zero local fallback;
- GET, POST, and lock-busy HTTP responses have exactly the existing nine
  fields; the unchanged frontend DTO is verified by diff/review rather than a
  brittle source-text runtime test;
- collect -> local analyze -> commit -> closed write Session -> fresh same-
  engine read Session -> snapshot by topic ID -> closed read Session -> file
  ordering, with the complete collection result retained;
- commit failure creates no observation; injected topic-file failure preserves
  the commit and `news_refreshed`, avoids `news_errors`, and is manifest-visible;
  injected root-create and manifest-finalize failures instead invalidate the
  whole run and remain explicit in normal logging;
- topic/manifest atomicity, no-overwrite immutability, SHA-256, byte length,
  membership, the derived `expected` set, and pairwise-disjoint terminal
  outcomes;
- corrupt, partial, mismatched, empty, and out-of-window data does not count;
- same-topic same-day selection, Shanghai boundaries, first-success review
  arithmetic, insufficient-window HOLD, collector-error exclusions, and
  metadata-debt treatment;
- both Coverage commands work without opening or mutating SQLite and never
  repair evidence or decide GO/NO-GO;
- the PowerShell script calls refresh exactly once, preserves
  discover -> refresh -> email order, captures output in the existing log, and
  continues email after refresh infrastructure failure;
- scheduler, POST, and offline CLI all observe only successful
  `_refresh_due_news` commits, while ordinary collect/search/frontier paths
  never do.

Run the focused tests first, then the full project gate:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
npm run test:e2e

cd ..
git diff --check
node .gitnexus/run.cjs status
node .gitnexus/run.cjs detect-changes --scope all
```

Safety checks must additionally prove:

- tests use only the isolated temporary database;
- `backend/.env`, `backend/dossier.db`, logs, and observation evidence are
  ignored and untracked;
- `git check-ignore -v backend/coverage_observations/probe` resolves to the
  intended root rule;
- no observation evidence is staged.

Only after every gate is green may the already-authorized first real daily run
execute. Its Shanghai date, command result, manifest verification, counts, and
any warning are reported to the agent mailbox. That run begins the window only
if it satisfies the validity rules above.
