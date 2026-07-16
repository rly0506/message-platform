# RM-065 R1 Inspection Reading Evidence Probe Implementation Plan

> **For agentic workers:** follow `spec/development.md#agent-work-protocol`. Use a fresh implementation subagent per task when available, then perform specification review before quality review. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build a one-time, no-LLM, source-read-only evidence probe that selects 30 persisted article slots, fetches only ordinary public pages, exposes short inspection material for Grok review, and publishes a text-free durable report only after all text/database-bearing temporary evidence is deleted.

**Architecture:** Add an isolated probe service and standalone CLI. Create a marker-owned flat run under the one canonical gitignored runtime root, copy a stable database family without opening the original through SQLite, query only the disposable snapshot, and delete that snapshot before networking. Reuse only `fulltext.extract_from_html()` after a bounded pinned-IP fetch; publish a text-free report only after journaled cleanup removes every temporary text/database byte. Text-free recovery metadata is removed only after the final report is fsynced. The probe adds no table, API, DTO, source, scheduler, UI, LLM call, or Coverage input.

**Tech Stack:** Python 3, SQLModel/SQLAlchemy projection queries over a disposable SQLite filesystem snapshot, existing `trafilatura`, standard-library `sqlite3`/`http.client`/socket/TLS/URL/DNS/hash/robots/atomic-file/OS identity utilities, pytest.

**Status:** `APPROVED; P0-GATED`. Specification and security reviews both returned `APPROVE` with no open findings. The design basis is the human-approved R1 section in `spec/roadmap-inspection-first-local-intelligence-2026-07-15.md`. Code execution still waits for the Opus `topic-load-race` P0 handoff to pass its revised gate. Any real-database preflight or network run remains a separate human-authorized operation.

---

## 1. Locked Boundaries

- Do not modify `Article`, `TopicArticle`, `Topic`, their schema, or migrations. GitNexus reports 45 upstream dependants for both `Article` and `TopicArticle` (`CRITICAL`). R1 reads projections only.
- Do not modify or call `fulltext.extract_url()`, `extract_url_proxied()`, `extract_url_scrapling()`, `topic_ops._fetch_bodies()`, or `article_perspective.analyze_article()`.
- The only existing body helper R1 may call is `fulltext.extract_from_html(html, url)`. Its upstream impact is `LOW` (two direct callers, zero indexed processes), and R1 does not modify it.
- Do not call `init_db()`: it creates tables, runs migrations, backfills projects, and seeds sources.
- The probe service and standalone CLI must not import `app.db` or `app.config`. Importing `app.db` constructs its module-level engine from configured `DB_PATH`, which would give SQLAlchemy the application/real database path before the probe can enforce snapshot isolation. Declare only the required `topic`, `topicarticle`, and `article` columns locally with SQLAlchemy Core `table()` / `column()` projections, and bind every query exclusively to the disposable snapshot engine. Tests may use `app.db` only after `backend/tests/conftest.py` has redirected it to a pytest-temporary database; probe production modules may not.
- Do not read `relevant`, translated fields, or LLM output to choose the sample. Core probe behavior must be identical without any LLM key.
- Do not persist HTML or complete extracted text. Temporary `title`, stored source summary, `lead`, and `tail` are each capped at 600 characters. The disposable database snapshot is removed and its absence verified before DNS/network begins.
- Never give SQLite or SQLAlchemy the real `--database` path. Filesystem copy operations may read the stopped source family; SQLite opens only the run-local snapshot, whose own SHM coordination writes are disposable.
- Do not update Coverage. `fulltext.status` remains `unknown`, and a successful probe is neither an observation day nor a source-expansion reason.
- Do not add retries, browser automation, Scrapling, fingerprint spoofing, paywall/login bypass, CAPTCHA handling, or a new crawler dependency. A failed threshold produces `DEFER`.

## 2. Chosen Approach And Rejected Alternatives

| Approach | Decision | Reason |
| --- | --- | --- |
| Reuse `extract_url_proxied()` | Reject | It trusts environment proxies, follows redirects automatically, reads the whole response, and loses final URL, status, type, size, timing, and closed error semantics. |
| Implement `ArticleInspection` persistence/API now | Reject | That is RM-065 P2, not R1; it would add schema/API/UI before the probe proves public-page usefulness. |
| Isolated read-only probe + `extract_from_html()` | Use | It preserves the approved evidence boundary, isolates risk, produces auditable failures, and can be deleted or promoted without contaminating product state. |

## 3. Exact Contracts

### 3.1 Deterministic sample

1. An active topic is exactly `Topic.status == "active"`.
2. Article count is the count of persisted `TopicArticle` links, including `relevant=False` links. This matches the current `topic_summary.article_count` contract and has no LLM dependency.
3. Sort non-empty active topics by `(article_count ASC, topic_id ASC)`.
4. Pick the first as `minimum`, index `(N - 1) // 2` as `median`, and the last as `maximum`. Require at least three topics; ties remain honest and deterministic.
5. For each selected topic, order projected articles by:
   - non-null `published_at` before null;
   - `published_at DESC`;
   - `fetched_at DESC`;
   - `Article.id DESC`.
6. Static URL eligibility requires absolute HTTP(S), a hostname, no credentials or fragment, and port 80/443 only. Reject localhost, single-label hosts and literal non-public addresses. Percent-decode query keys with strict UTF-8 and casefold them. Reject keys equal to or segmented by `_`/`-` with `token`, `secret`, `signature`, `sig`, `password`, `passwd`, `credential`, `auth`, `session`, `jwt`, `code`, or `key`; also remove non-alphanumerics and reject compact forms containing `apikey`, `accesskey`, `accesstoken`, `idtoken`, `oauthtoken`, `refreshtoken`, `clientsecret`, `sessionid`, `signature`, `credential`, `password`, or `passwd`, plus every `x-amz-*` / `x-goog-*` security key. Fixtures include percent-encoded and camelCase forms. This prevents obvious signed/auth URLs from being fetched or echoed but is not treated as proof that other query values are public. Continue scanning older rows until 10 eligible slots are found.
7. If any selected topic has fewer than 10 eligible slots, stop before DNS/network and return `DEFER` with the exact shortfall. Do not replace the topic or borrow another topic's article.
8. Preserve 30 topic/article slots even when one Article belongs to multiple topics. Derive temporary `canonical_requested_url` by lowercasing scheme/IDNA host, removing a host trailing dot and default port, converting an empty path to `/`, removing RFC 3986 dot segments, decoding only unreserved path escapes, and uppercasing remaining percent escapes. Parse query pairs with strict UTF-8; preserve original pair order, duplicates, blank keys/values, and non-tracking key case; remove decoded tracking keys case-insensitively for `utm_*`, `fbclid`, `gclid`, `mc_cid`, and `mc_eid`; then deterministically re-encode. Fetch the first exact `Article.url` for each canonical requested URL once and fan the result back to all matching slots. Fixtures lock trailing-dot hosts, percent-encoded keys, mixed-case tracking keys, repeated/blank parameters, `%7E` versus `~`, and dot segments.
9. Use `Article.url` as the exact request/provenance input. Never copy exact `Article.original_url` into audit: store only its SHA-256 and, if it independently passes public URL parsing, its queryless display URL plus redaction flag; otherwise store hash plus `original_url_display_status=invalid`. Never substitute it for the requested URL. Durable requested evidence stores SHA-256 of the exact/canonical requested URLs plus queryless `durable_display_url` and `query_redacted`. No query value—known sensitive or otherwise—enters the durable report. The availability denominator uses the temporary canonical requested URL key, not the display URL.

### 3.2 Source database isolation

SQLite may create or update `-shm` reader marks even for a `mode=ro` connection. Therefore the probe never opens the source database family with SQLite:

1. Resolve the explicit source path without URI string interpolation; reject a missing/non-regular main file or any source family member that is a symlink, junction, mount, or reparse point.
2. Create the marker-owned flat run first. Fingerprint the source main, `-wal`, `-shm`, and rollback `-journal` paths by existence, size, `mtime_ns`, and SHA-256. Any non-empty rollback journal is a closed run-level `source_rollback_journal_present` failure; it is never copied or opened. Copy the main file and an existing non-empty WAL into fixed run-local names `snapshot.db` and `snapshot.db-wal`; never copy SHM or a rollback journal. Fingerprint all four source paths again. Any change, appearance, disappearance, or zero-to-nonzero journal transition aborts selection and enters guarded unsealed cleanup.
3. Open only `snapshot.db` through an SQLAlchemy `creator` that calls `sqlite3.connect(str(snapshot_path))`; do not construct a SQLite file URI. The writable run directory lets SQLite rebuild disposable `snapshot.db-shm` when a copied WAL requires it. Attach `PRAGMA query_only=ON` and `PRAGMA temp_store=MEMORY`, assert they read back as `1` and `2`, run `PRAGMA quick_check`, and execute both projection queries in one explicit transaction so SQLite cannot spill query temp files outside the run.
4. Close the session, dispose the engine, remove `snapshot.db`, `snapshot.db-wal`, `snapshot.db-shm`, and any snapshot journal, fsync the run directory where supported, and verify that no `snapshot*` entry remains before DNS/network. The probe may mutate only these disposable snapshot companions; it cannot mutate the source family because SQLite never receives a source path.
5. A WAL-mode test must keep an uncheckpointed committed row in a temporary source WAL, copy it, and prove the row is visible from the snapshot while every source-family hash remains unchanged. A DELETE-journal fixture with no journal must succeed; zero-length journal appearance is fingerprinted but safe only if stable; any non-empty/hot journal must fail before copy/query. A competing-writer or journal injection during copy must abort before snapshot query or network.

### 3.3 Network and compliance

- R1 uses pinned direct transport only. It does not read `RSS_PROXY` or generic proxy environment variables. Existing application collection proxy behavior is unchanged, but proxy-mediated R1 evidence cannot satisfy the public-address proof and therefore is outside this probe.
- Validate the initial URL and every redirect target. Resolve the hostname before each request and require every returned address to be globally routable. Reject private, loopback, link-local, multicast, unspecified, reserved, CGNAT, and IPv4-mapped private IPv6 addresses.
- `socket.getaddrinfo` runs in an isolated spawned resolver process. The parent terminates it when the shared deadline expires; a timed-out resolver cannot keep the CLI alive. Pin the connection to one of the returned validated addresses instead of resolving the hostname again. For HTTPS, connect the socket to that IP and wrap it with the default TLS context using the original hostname for SNI and certificate verification. Send the original hostname in `Host`. For HTTP, connect directly to the IP and still send the original `Host`. Redirects create a new resolved, validated, pinned connection. Tests must prove the connector never receives an address outside the validated set.
- The standard-library transport has no automatic redirect path. Handle only 301/302/303/307/308, at most three hops, in probe code. Reject loops, missing/invalid `Location`, credentials, unsafe targets, non-80/443 ports, and HTTPS-to-HTTP downgrade.
- Check `/robots.txt` once per origin with the exact HTTP user agent `DossierBot/1.0` and robots product token `DossierBot`, using a 256 KiB streaming cap before each page path. A page redirect to a new origin repeats the check; a same-origin redirect applies the cached policy to its new path. Robots may follow at most three same-origin redirects with no HTTPS downgrade; cross-origin, missing/invalid `Location`, or any other redirect violation is `blocked/robots_unavailable`. Robots 404/410 means no policy. Status 200 accepts `text/plain`, `text/x-robots`, or a missing type only when the body is valid UTF-8/ASCII text with no NUL. All other types, 401/403/429, timeout, malformed/oversized content, and 5xx fail closed as `blocked/robots_unavailable`; every other 4xx also fails closed.
- Implement a local parser/matcher for the locked RFC 9309 subset; never call `urllib.robotparser.RobotFileParser.can_fetch()`. Strip comments/blank lines; recognized `user-agent`, `allow`, and `disallow` lines require one colon; user-agent values must be non-empty; rules outside a group are malformed; empty `disallow` has no blocking effect; empty `allow` has no matching effect; unknown well-formed directives are ignored. Match product tokens case-insensitively, combine all groups with the same most-specific matching token, and fall back to `*` only when no specific group matches. Match against normalized path plus query, decode unreserved percent escapes, uppercase remaining escapes, treat `*` as any octet sequence and a terminal `$` as end anchor, reject malformed percent escapes, choose the rule with greatest non-wildcard octet length, and let `Allow` win equal length. Fixtures cover multiple same-name groups, `Mozilla` versus `DossierBot` conflict, wildcard group/pattern, terminal `$`, query matching, longest rule, Allow tie, percent-encoded path, malformed groups/escapes, and redirect behavior.
- Send no cookies, Authorization, Referer, or browser fingerprint headers. Use only `DossierBot/1.0` and `Accept-Encoding: identity`; do not reuse the collection/browser-like user agent.
- Page status must be 200. Stop on 401/403/429 with no retry. Classify a login/paywall page only for a password input inside a login/sign-in form or an element whose `id`/`class` token is exactly one of `paywall`, `subscription-wall`, `login-wall`, `signin-wall`, or `metered-content`. Classify a challenge only for structural tokens `g-recaptcha`, `h-captcha`, `cf-chl-`, `challenge-platform`, or a form containing a CAPTCHA response field. Mere prose mentioning these words does not trigger a block.
- Accept only `text/html` or `application/xhtml+xml`. A missing type is allowed only if the first 1,024 bytes after BOM/ASCII whitespace contain `<!doctype html`, `<html`, `<head`, or `<body`, and the bounded body contains no NUL byte.
- Stream at most 2 MiB; reject a larger `Content-Length` before reading and abort if streamed bytes exceed the cap. Reject non-identity content encoding instead of implementing a decompressor in R1.
- Create one absolute monotonic deadline 20 seconds after each distinct-URL operation starts. DNS, robots, connect, TLS handshake, address fallback, redirects, headers, and every body chunk receive that same deadline. Each blocking socket timeout is `min(stage_cap, remaining)` with 5-second connect/TLS and 10-second read caps. Address fallback may try each validated address once only before an HTTP response exists and only while time remains; HTTP responses are never retried.
- Decode BOM, declared HTTP charset, HTML meta charset, then UTF-8 in that order. Unknown codecs fail. Replacement decoding fails when U+FFFD count exceeds `max(8, decoded_character_count // 200)`; otherwise it is retained. `content_sha256` always hashes the bounded identity-encoded response bytes before character decoding, never decoded text.

### 3.4 Closed outcomes

`status` is one of `success`, `partial`, `blocked`, `failed`.

- `success`: two distinct, non-empty lead/tail paragraphs.
- `partial`: non-empty extracted body but only one usable paragraph; do not duplicate it into both fields.
- `blocked`: policy or access boundary stopped the request.
- `failed`: invalid input, DNS/network/format/extraction/internal failure.

Every `success` or `partial` record must also contain a revalidated public `canonical_final_url`, a lowercase 64-hex `content_sha256` of the bounded raw page bytes, and `body_byte_length > 0`. Missing or malformed fields cannot fall back to the requested URL: orchestration converts the record to `failed/internal_error`, and sealed verification rejects any manifest that still labels it usable.

`error_code` is `null` for success and otherwise one of:

```text
url_invalid, url_credentials, url_port_disallowed, url_sensitive_query,
address_not_public,
dns_unresolved, robots_disallowed, robots_unavailable, redirect_invalid,
redirect_loop, redirect_limit, redirect_downgrade, http_401, http_403,
http_429, http_status, access_login_or_paywall, access_challenge,
content_type_unsupported, content_encoding_unsupported, body_too_large,
body_not_html, decode_failed, timeout, tls_error, network_error,
extractor_unavailable, extraction_empty, extraction_partial, internal_error
```

`source_family_changed`, `source_rollback_journal_present`, and `snapshot_invalid` are run-level preflight failures, not per-slot terminal codes, because network processing never begins.

Every selected slot receives exactly one record. `error_detail` is optional, sanitized, capped at 160 characters, and must never invent a new code or expose credentials, query values, environment/proxy values, or response text.

### 3.5 Field provenance

Temporary audit records use these exact sources:

| Field | Value | Provenance |
| --- | --- | --- |
| `requested_url` | exact `Article.url` in temporary audit only | `article.url` |
| `canonical_requested_url` | normalized, tracking-stripped URL in temporary audit only | `probe.url_canonicalization.v1` |
| `requested_url_sha256` | SHA-256 of exact `Article.url` | `probe.sha256` |
| `canonical_requested_url_sha256` | SHA-256 of canonical requested URL | `probe.sha256` |
| `durable_display_url` | canonical scheme/authority/path with query removed | `probe.url_redaction.v1` |
| `query_redacted` | whether the requested URL contained any query | `probe.url_redaction.v1` |
| `stored_original_url_sha256` | SHA-256 of `Article.original_url` or empty | `article.original_url` + `probe.sha256` |
| `stored_original_display_url` | queryless display URL or empty | `article.original_url` + `probe.url_redaction.v1` |
| `original_url_display_status` | `empty`, `public`, or `invalid` | `probe.url_validation.v1` |
| `title` | capped `Article.title` | `article.title` |
| `publisher_summary` | cleaned, capped `Article.snippet` | `article.snippet:<collector>` |
| `lead` / `tail` | first/last distinct non-empty block from `Extracted.full_text` | `trafilatura.extract_from_html` |
| `final_url` | last validated response URL in temporary audit | `http.redirect_chain` |
| `canonical_final_url` | normalized, tracking-stripped final URL in temporary audit only | `probe.url_canonicalization.v1` |
| `canonical_final_url_sha256` | durable SHA-256 identity for final-page deduplication | `probe.sha256` |

The name `publisher_summary` is retained for the approved probe contract, but provenance must expose that RSS uses entry summary, SearXNG uses result content, and GDELT is normally empty. Never fill a missing summary from body text.

### 3.6 Evidence lifecycle

The only production runtime root is the repository-relative canonical `backend/inspection_probe_runs/`; the CLI exposes no root override. The only production report root is canonical `docs/operations/`; `--report` must be a direct, non-symlink `.json` child of that non-reparse root and must be outside the runtime root, run/tombstone, source family, and pending/claim names. Service tests inject separate `tmp_path` runtime/report roots. A run is flat: no subdirectory is permitted. Fixed payload names are `run-meta.json`, `snapshot.db*`, `audit.jsonl`, `manifest.json`, and `review.json`; atomic temps must match an allowlisted `<target>.<run-id>.<uuid>.tmp` form. Any other name or directory blocks finalization without traversal.

1. Bootstrap in a direct child `.creating-<run-id>-<uuid>`. Atomically install the text-free `run-meta.json`, then atomically rename the staging directory to final `<UTC timestamp>-<uuid>` before writing snapshot/audit bytes. A pre-rename crash can leave only `run-meta.json` and/or a strictly named run-meta temp. `purge-unsealed` may unlink those bootstrap files and remove the staging directory only after `lstat`, regular-file, size-cap, name-pattern, double-enumeration, and no-reparse checks; any snapshot/audit/unknown entry refuses cleanup. Network responses and complete extracted text stay in memory only.
2. After §3.2 snapshot removal, atomically install `audit.jsonl`, one slot per line, containing capped temporary text. Atomically install `manifest.json` last with `status=sealed`, schema version, run id, slot/distinct counts, audit SHA-256, byte length, terminal counts, timings, selected topic identities, canonical URL hashes/metrics, and the review sample. A missing or invalid manifest is unsealed.
3. Build `required_review_record_ids` by first filtering structurally valid records to `status in {success, partial}`, then iterating minimum, median, maximum bands round-robin in stable slot order. Deduplicate strictly by required `canonical_final_url`; no requested-URL fallback exists. Stop at 10. Thus the list contains exactly 10 ids only when 10 distinct usable final pages exist; otherwise it contains all available ids, locks the decision to `DEFER`, and cannot be counted as a passing Grok review. All slots fanned from one canonical requested URL must have identical terminal status, error code, content hash, body length, and canonical final URL.
4. Before any cleanup claim exists, Grok may atomically install `review.json` inside the run. Its closed schema binds `schema_version`, `run_id`, `manifest_sha256`, `audit_sha256`, and unique decisions. Every required id appears exactly once; `clean` is a JSON boolean; notes are capped and do not enter durable output. Extra valid ids never affect the threshold. A possible `PASS` requires 10 required distinct usable pages and at least 9 clean required ids. Review installation refuses once a cleanup claim exists.
5. Calculate availability with integer arithmetic on canonical requested URLs: `canonical_requested_usable_count * 10 >= canonical_requested_total_count * 7`. Slot fan-out never changes numerator or denominator. Lock tests for `7/10` true, `6/10` false, `7/11` false, `14/20` true, and the cross-topic duplicate fixture `7/16` false. Every failed gate yields `DEFER`; `PASS` and `DEFER` are the only durable decisions.
6. Every operation that can write run state—`preflight`, `run`, `install-review`, `finalize`, `purge-unsealed`, `abandon-sealed`, and `recover`—must first acquire one cross-process exclusive owner lock keyed by canonical runtime root plus run id, before checking or writing that run, and hold it until return. The persistent one-byte `.owner-<run-id>.lock` is never replaced or deleted, but it is not created in place. Each contender creates an `O_EXCL|O_NOFOLLOW` / `CREATE_NEW` `.owner-<run-id>.<uuid>.tmp` in the validated root, writes one zero byte, fsyncs, closes, then installs it with the same hard-link/no-replace primitive used by other atomic files. The winner unlinks its temp and fsyncs the root; losers remove their own temp and open the installed lock. On recovery, strict same-inode owner-temp links are enumerated and accounted before locking, then identity-checked and unlinked only while holding the installed lock; unrelated regular size-0/1 owner temps are likewise removed only under that lock and before any run transition. Thus a crash before install leaves no invalid final lock, and a crash after install leaves a recoverable same-inode temp.

   POSIX opens the installed lock relative to the validated root with `O_RDWR|O_NOFOLLOW|O_CLOEXEC`, requires `fstat`/`lstat` identity equality, regular type, current owner, size one, and proves every extra link is an allowlisted same-inode owner temp before applying `flock(LOCK_EX|LOCK_NB)`. Under the lock it removes those temps, requires link count one, and rechecks identity before state mutation. Windows performs the equivalent with `CreateFileW(FILE_FLAG_OPEN_REPARSE_POINT)` while denying delete sharing, validates reparse/type, volume serial/file index/size, accounts same-file temp links, then applies the exclusive byte-range lock and removes them. After acquisition and immediately before every state mutation, path and held handle must still identify the same object; mismatch fails before mutation. Process exit releases the OS lock. A busy/unsafe lock fails closed. The text-free lock file is coordination metadata, not evidence residue; scan reports whether it is actively held.
7. While holding the owner lock, every `finalize`, `purge-unsealed`, or `abandon-sealed` atomically installs deterministic `.cleanup-<run-id>.json` with no replacement. This text-free journal is the exclusive cleanup claim; an existing valid claim directs the caller to `recover`. Claim-temp names are deterministic-prefix plus UUID and contain no evidence text. Read-only scan only reports them; acknowledged purge/recover may remove a regular size-capped claim temp after proving no transition began. Multiprocess tests cover run/purge, install-review/finalize, finalize/finalize, finalize/abandon, and recover/competing command; exactly one writer may proceed.
8. The claim binds operation, run id, a preselected random `.deleting-<run-id>-<uuid>` tombstone, marker/manifest/audit/review hashes, intended decision, pending-envelope identity, report target, and captured directory identity. Finalize order is: validate report target and sealed evidence; construct durable report bytes; install claim; install pending envelope; atomically rename run to the claim-bound tombstone; clean it. Purge/abandon omit pending. `purge-unsealed` refuses a valid sealed manifest; `abandon-sealed` refuses an unsealed run.
9. Cleanup never calls generic recursive deletion. It holds/binds tombstone identity, requires a flat allowlist, and unlinks snapshot/audit/temp payloads first, manifest/review next, `run-meta.json` last, then removes the empty tombstone. POSIX uses `O_DIRECTORY|O_NOFOLLOW` plus descriptor-relative `lstat`/unlink. Windows uses `CreateFileW(FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS)` while denying delete sharing, captures volume serial/file index/reparse attributes, and fails closed if identity locking is unavailable. Entries are unlinked, never followed. File and parent-directory fsync are required where supported; Windows uses `FlushFileBuffers` where supported and treats process-crash and power-loss durability as separate claims.
10. Because the claim is outside the tombstone and the marker is removed last, a crash or permission failure between unlinks remains recoverable. After marker removal, the claim authorizes only the now text-free allowlisted remainder. Cleanup succeeds only when original run/tombstone are absent and a root scan finds no payload for that run.
11. Finalize pending is `<report-name>.<run-id>.<payload-hash>.pending.json` under the fixed report root. Its text-free envelope contains the allowlisted durable `report` plus run id, canonical root/report paths, manifest/audit/review hashes, claim id, decision, and canonical report SHA-256/length. Only nested canonical `report` bytes become durable; local paths and recovery metadata remain temporary. Fewer than 10 distinct usable final pages permits reviewless `DEFER`; otherwise review is mandatory.
12. Recovery acquires the same owner lock and follows an explicit state table. Claim + original run + no pending reconstructs/validates the report from still-sealed evidence, installs missing pending, then continues. Claim + pending + original run performs rename. Claim + pending + tombstone resumes ordered unlink. Claim + pending + no run/tombstone installs or verifies final. Claim + equal final + no pending removes claim. A mismatch, two run locations, missing evidence before pending, or unbound path fails closed. Purge/abandon recovery resumes rename/unlink and removes claim only after original/tombstone absence. Recovery never refetches.
13. After cleanup, reserialize/hash the envelope report and atomically install it without replacement. Its sibling temp is strictly `<report-name>.<run-id>.<payload-hash>.<uuid>.final.tmp`, is bound by claim/pending, and contains only the durable text-free report. Recovery hashes any such temp: a matching temp may complete the no-replace install; an equal final causes temp deletion; a mismatch is removed only by acknowledged recovery and regenerated from the bound pending envelope. Durable output contains display URLs without query values, URL hashes, ids, statuses, codes, content hashes, lengths, timing/redirect metrics, provenance labels, and Grok decisions—never title, summary, lead, tail, HTML, full text, query values, local paths, cleanup metadata, or review notes. Delete pending next and claim last. Pending+equal final and final+claim states close idempotently; unequal final refuses mutation.
14. `scan-residuals` is read-only and scans both fixed roots for bootstrap dirs/temps, owned runs, claim temps/claims, tombstones, bound pending envelopes, and final-report temps by id without printing text fields. Tests terminate child processes with `os._exit` after every atomic install/rename/unlink—including final-temp fsync before install—not only injected exceptions that run `finally`, then recover from a fresh process. All implementation/real-run closeout gates require no active owner and zero payload/tombstone/claim/pending/final-temp residues; inactive persistent owner-lock files are allowed. The contract guarantees bounded explicit recovery, not unattended eventual deletion.

---

## 4. File Map

| File | Responsibility |
| --- | --- |
| Create `backend/app/services/inspection_probe.py` | Data contracts, source-family snapshot isolation, deterministic selection, static/public URL validation, pinned direct transport, robots/manual redirects, bounded fetch, extraction, batch fan-out, audit/manifest/review, claim-journal cleanup, recovery, and residual scan. |
| Create `backend/inspection_probe.py` | Standalone `argparse` CLI with a fixed production runtime root: `preflight`, `run`, `verify`, `install-review`, `finalize`, `recover`, `purge-unsealed`, `abandon-sealed`, `scan-residuals`. No import or call to `init_db()`. |
| Create `backend/tests/test_inspection_probe.py` | Temporary DB, fake DNS/HTTP, extraction, terminal-record, evidence lifecycle, crash recovery, and CLI tests. No external network. |
| Modify `.gitignore` | Add only `backend/inspection_probe_runs/` in the first implementation batch, before any production run helper exists. |
| Modify `spec/CHANGELOG.md` | Record implementation after tests/reviews, without claiming a real run. |
| Create later `docs/operations/rm065-inspection-probe-<date>.json` | Text-free durable report produced only by an authorized real run after Grok review and cleanup. Not part of code implementation. |

---

## 5. Implementation Tasks

### Task 0: Reconfirm Gates Before Code

**Files:** none.

- [ ] **Step 1: Read current coordination state**

Run:

```powershell
Get-Content -Raw -Encoding utf8 .agent-bridge/BOARD.md
Get-Content -Raw -Encoding utf8 .agent-bridge/TO_CODEX.md
git status --short
```

Expected: Opus P0 is explicitly complete/approved; R1 is the next backend stage; unrelated H0 changes are preserved. If P0 is not closed, stop without code changes.

- [ ] **Step 2: Establish isolated execution workspace**

Use the repository's worktree workflow only after the H0/RM-065 documentation is present in the chosen base commit. Do not create a worktree from `bd3693d` and silently lose the uncommitted roadmap/spec files.

- [ ] **Step 3: Re-run candidate-symbol impact**

```powershell
gitnexus impact 'Article' --repo message-platform --file 'backend/app/db.py' --kind Class --direction upstream --depth 2 --include-tests --summary-only
gitnexus impact 'TopicArticle' --repo message-platform --file 'backend/app/db.py' --kind Class --direction upstream --depth 2 --include-tests --summary-only
gitnexus impact 'init_db' --repo message-platform --file 'backend/app/db.py' --kind Function --direction upstream --depth 2 --include-tests --summary-only
gitnexus impact 'extract_from_html' --repo message-platform --file 'backend/app/pipeline/fulltext.py' --kind Function --direction upstream --depth 3 --include-tests
```

Expected: model and `init_db` impacts remain HIGH/CRITICAL and are read-only; `extract_from_html` remains LOW. Any plan to edit/import the models from probe production code or call `init_db` is a specification violation.

### Task 1: Stable Snapshot And Deterministic Selection

**Files:**
- Modify: `.gitignore`
- Create: `backend/app/services/inspection_probe.py`
- Create: `backend/tests/test_inspection_probe.py`

- [ ] **Step 1: Write failing sample-selection tests**

Define tests for odd/even topic counts, all-count ties, fewer than three non-empty active topics, `relevant=False`, null dates, deterministic tie-breaking, static URL shortfall, canonical URL grouping, sensitive query rejection, cross-topic duplicate slots, and source-family isolation. For the full-selection case seed topic counts `10/12/14/16/18`, so minimum/median/maximum can honestly produce 30 slots. Seed only pytest temporary databases.

The core assertions must include:

```python
selection = select_probe_sample(session, per_topic=10)
assert [item.tier for item in selection.topics] == ["minimum", "median", "maximum"]
assert [item.article_count for item in selection.topics] == [10, 14, 18]
assert selection.selected_slot_count == 30
assert selection.fetch_urls == list(dict.fromkeys(slot.canonical_requested_url for slot in selection.slots))
```

For an undersized minimum topic:

```python
with pytest.raises(ProbeDeferred, match="topic_id=.*required=10.*available=9"):
    select_probe_sample(session, per_topic=10)
```

- [ ] **Step 2: Run selection tests and prove red**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_inspection_probe.py -q
```

Expected: collection/import failure because the probe module does not exist.

- [ ] **Step 3: Implement immutable contracts, snapshot isolation, and two projection queries**

Before creating a production run helper, add exactly `backend/inspection_probe_runs/` to `.gitignore` and verify it with `git check-ignore -v backend/inspection_probe_runs/example/audit.jsonl`.

Create frozen dataclasses for `DatabaseFileFingerprint`, `DatabaseFamilyFingerprint`, `TopicBand`, `ProbeSlot`, and `ProbeSelection`, plus `ProbeDeferred`. Define local SQLAlchemy Core `table()` / `column()` clauses for only the required persisted columns; do not import `app.db`, `app.config`, or their SQLModel classes in either probe production module. Use `func.count`, `case`, and projected columns exactly as defined in §3.1. Perform static URL validation/canonicalization in Python before slicing to 10; do not load full ORM Article rows and do not filter `TopicArticle.relevant`.

Expose exactly these typed interfaces: `allocate_run_id() -> str`, `acquire_run_owner(root: Path, run_id: str) -> AbstractContextManager[RunOwner]`, `create_probe_run(owner: RunOwner) -> Path`, `fingerprint_database_family(database: Path) -> DatabaseFamilyFingerprint`, `copy_database_snapshot(owner: RunOwner, database: Path) -> Path`, `create_snapshot_engine(owner: RunOwner, snapshot: Path) -> Engine`, `select_probe_sample(session: Session, *, per_topic: int = 10) -> ProbeSelection`, `select_probe_sample_from_source(owner: RunOwner, database: Path, *, per_topic: int = 10) -> ProbeSelection`, `static_public_url_error(url: str) -> str | None`, and `canonicalize_public_url(url: str) -> str`.

`RunOwner` carries the live locked handle and canonical root/run id; run-mutating helpers validate it before each state transition. `select_probe_sample_from_source` owns the two source-family fingerprints, stable main/WAL copy, snapshot-only engine, `query_only`/memory-temp assertions, `quick_check`, explicit transaction, session closure, engine disposal, and verified snapshot removal. The CLI must not reimplement or weaken that boundary. No function may call `sqlite3.connect`, SQLAlchemy `create_engine`, or `Session` with the source path, and importing the application database module is forbidden because its module-level engine construction would bypass that proof.

- [ ] **Step 4: Run selection tests and prove green**

Use the focused command from Step 2. Expected: all selection/snapshot tests pass and no network mock is called. Tests must prove: clean DELETE-journal and WAL-mode sources both select correctly; an uncheckpointed WAL row is present in the snapshot result; non-empty rollback journal fails closed; zero-length journal and main/WAL/SHM fingerprints remain byte-for-byte stable; source-family/journal mutation during copy aborts; Windows-compatible paths containing spaces, `#`, `%`, and non-ASCII characters open without URI parsing; SQLite receives only `snapshot.db`; a clean subprocess plus a static source-import check prove that importing the service neither directly/lazily imports nor eagerly loads `app.db` or `app.config`; and no `snapshot*` file remains before the network sentinel is invoked. The CLI receives the same proof after it is created in Task 5.

- [ ] **Step 5: Conditional checkpoint commit**

Only with current human commit authorization:

```powershell
git add .gitignore backend/app/services/inspection_probe.py backend/tests/test_inspection_probe.py
node .gitnexus/run.cjs detect-changes --scope compare --base-ref master --repo message-platform
git commit -m "feat(rm065): add isolated deterministic probe sample"
```

Otherwise record the checkpoint in the task report without committing.

### Task 2: Public-Page Fetch And Closed Terminal Results

**Files:**
- Modify: `backend/app/services/inspection_probe.py`
- Modify: `backend/tests/test_inspection_probe.py`

- [ ] **Step 1: Write failing network-boundary tests**

Use injected resolver and pinned-connection fakes only. Set `RM065_TEST_DENY_NETWORK=1` for the entire pytest/CLI-subprocess environment; both the parent transport and spawned resolver entrypoint must check it before real `getaddrinfo` or connect and raise a closed test-only error. Keep an autouse parent monkeypatch as a second guard, but do not rely on monkeypatch inheritance. Resolver timeout tests inject a module-level pickleable sleeping worker. Cover non-public DNS sets; resolver-process timeout/terminate/kill/join; proof that the connector receives only a previously validated IP; DNS rebinding attempts; redirect validation/loop/downgrade/limit; page redirects rechecking robots; robots same-origin redirects, strict local parser groups/ties/malformed input/cache; 401/403/429 zero retry; structural login/paywall/challenge markers versus prose false positives; 1,024-byte HTML sniff; exact replacement-character boundary; raw-byte content hash; type/encoding/body caps; environment proxy variables having no effect; one shared deadline across DNS/robots/TLS/fallback/read; TLS hostname/SNI plus `Host` preservation; and exactly one terminal result per canonical requested URL.

Required assertion shape:

```python
result = fetch_public_page(url, resolver=fake_resolver, transport=fake_transport)
assert (result.status, result.error_code) == ("blocked", "robots_disallowed")
assert fake_transport.article_calls == []
```

```python
results = fetch_distinct_urls(urls, resolver=fake_resolver, transport=fake_transport)
assert list(results) == list(dict.fromkeys(canonicalize_public_url(url) for url in urls))
assert all(item.status in CLOSED_STATUSES for item in results.values())
```

- [ ] **Step 2: Run tests and prove red**

Run the focused test file. Expected: missing fetch functions/enums.

- [ ] **Step 3: Implement validation, robots, manual redirects, and bounded streaming**

Add frozen `Deadline`/`FetchResult`, `Status`/`ErrorCode` literals or enums, `validate_public_url`, `resolve_public_addresses`, `PinnedConnection`, `fetch_robots_policy`, and `fetch_public_page`. Run real `getaddrinfo` in a terminable spawned process. Implement transport with `socket`, `ssl.create_default_context()`, and `http.client`: connect to a selected validated IP, retain the original hostname for TLS SNI/certificate validation and `Host`, and create a fresh validated pinned connection for every redirect origin. Pass one absolute deadline through all phases. Do not read application or environment proxy settings and do not expose a proxy argument. Send no cookies/auth/referer. Sanitize every exception before storing 160 characters.

Use `time.perf_counter_ns()` for elapsed milliseconds. Derive each blocking timeout from the shared deadline and check it before every DNS wait, robots/page redirect, connect/TLS operation, header read, and body chunk. Read at most 2 MiB with `Accept-Encoding: identity`; hash the bounded raw bytes before decoding.

- [ ] **Step 4: Run network tests and prove green**

Expected: all tests pass without DNS or external network access.

- [ ] **Step 5: Conditional checkpoint commit**

```powershell
git add backend/app/services/inspection_probe.py backend/tests/test_inspection_probe.py
node .gitnexus/run.cjs detect-changes --scope compare --base-ref master --repo message-platform
git commit -m "feat(rm065): bound public-page probe fetches"
```

Run only with current human commit authorization.

### Task 3: Inspection Extraction And Batch Fan-Out

**Files:**
- Modify: `backend/app/services/inspection_probe.py`
- Modify: `backend/tests/test_inspection_probe.py`

- [ ] **Step 1: Write failing extraction/provenance tests**

Cover two-paragraph success, one-paragraph partial without duplicated tail, empty extraction, missing trafilatura, navigation/comment/footer contamination fixture, title/summary non-backfill, 600-character caps, collector-specific summary provenance, original-URL hash/queryless-display handling, canonical-requested-URL fan-out, required canonical-final-URL/hash/body-length invariants, stable slot order, shared-result status/hash equality, and one unexpected exception becoming `failed/internal_error` rather than a missing record.

```python
record = inspect_slot(slot, fetched, extractor=fake_extractor)
assert record.status == "partial"
assert record.lead == "only paragraph"
assert record.tail == ""
assert record.provenance["lead"] == "trafilatura.extract_from_html"
assert record.provenance["publisher_summary"] == "article.snippet:rss"
```

- [ ] **Step 2: Run tests and prove red**

Expected: missing `inspect_slot` / batch orchestration.

- [ ] **Step 3: Implement extraction and deterministic fan-out**

Call only `fulltext.extract_from_html`. Split its stripped `full_text` on one-or-more line breaks, normalize whitespace inside each block, discard empty blocks, and choose first/last distinct blocks. Cap title, cleaned stored summary, lead, and tail at 600 characters before constructing the immutable audit record. Immediately release references to HTML/full text after record construction.

Fetch each distinct canonical requested URL once in first-slot order, using that group's first exact stored URL, and fan the immutable fetch/extraction outcome to all slots. Preserve one output record per slot in the original minimum/median/maximum order; validate that fanned terminal status, error code, content hash, and canonical final URL are identical.

- [ ] **Step 4: Run tests and prove green**

Expected: all selection, network, extraction, and fan-out tests pass.

### Task 4: Sealed Audit Evidence, Grok Review, Cleanup, Recovery

**Files:**
- Modify: `backend/app/services/inspection_probe.py`
- Modify: `backend/tests/test_inspection_probe.py`

- [ ] **Step 1: Re-verify the ignored runtime root**

Task 1 already added exactly:

```gitignore
backend/inspection_probe_runs/
```

Verify:

```powershell
git check-ignore -v backend/inspection_probe_runs/example/audit.jsonl
```

- [ ] **Step 2: Write failing lifecycle/crash tests**

Cover staging-directory bootstrap and marker installation before snapshot/audit bytes; cleanup of marker/claim temps with no evidence payload; audit JSONL caps/no full-body sentinel; canonical checksum/length manifest; no overwrite; deterministic usable-only, cross-band, canonical-final-URL-deduplicated `required_review_record_ids`; review schema/hash/run binding with strict booleans and exactly-once required ids; strict durable-report allowlist/query redaction; deterministic exclusive claim; tombstone cleanup-before-publish; cleanup failure; root residual scan; and pending-envelope recovery without refetch.

Add exact decision-boundary tests: `7/10` and `14/20` satisfy the inclusive integer gate while `6/10`, `7/11`, and `7/16` do not; 9 clean of 10 required ids can pass while 8 cannot. The feasible duplicate fixture uses seven successful Articles each linked once to all three selected topics (21 slots) plus nine distinct failed Articles (nine slots), and asserts canonical URL rate `7/16`, not slot rate `21/30`.

Terminate subprocesses with `os._exit` after owner-temp creation, owner-temp fsync, owner-lock install before temp unlink, staging mkdir, marker temp fsync/install, staging rename, snapshot copy, every audit/manifest/review/claim/pending temp and installation, run-to-tombstone rename, each payload/manifest/review/marker unlink, tombstone removal, final-report sibling-temp fsync, final installation, pending removal, and claim removal. Recover in a fresh process. Assert the state table closes each state, same-inode owner temp is repaired to one link, marker is the last in-run file removed, claim-without-pending reconstructs safely, final-temp/final+pending/final+claim states close idempotently, mismatch refuses mutation, and both `PASS` and `DEFER` end with no temporary text.

Add adversarial cleanup tests for an outside/nested run, marker/basename mismatch, unexpected directory or filename, root/run/file symlink, mount/junction/reparse point where supported, identity change after validation, sealed run passed to `purge-unsealed`, and unsealed run passed to `abandon-sealed`. Add owner-lock fixtures for a preexisting symlink/reparse point, hard link, wrong size/owner where supported, outside sentinel, and an identity swap at a hook after acquisition but before mutation. On Windows, also simulate or exercise a junction swap after initial validation and require locked identities to prevent traversal. Every refusal leaves the outside sentinel intact. Test safe bootstrap-temp cleanup and refusal when it contains snapshot/audit/unknown entries. Multiprocess owner-lock tests prove one writer for run/purge, install-review/finalize, finalize/finalize, finalize/abandon, and recover/finalize.

```python
outcome = finalize_reviewed_run(root, report_root, run_dir, durable_report)
assert outcome.status == "published"
assert not run_dir.exists()
payload = json.loads(durable_report.read_text(encoding="utf-8"))
assert not ({"title", "publisher_summary", "lead", "tail", "html", "full_text"} & recursive_keys(payload))
assert FULL_BODY_SENTINEL not in durable_report.read_text(encoding="utf-8")
```

- [ ] **Step 3: Implement atomic no-replace evidence helpers**

Follow the proven coverage-observation atomic no-replace pattern without importing its private helper: sibling unique temp file, `open("xb")`, write, flush, `os.fsync`, no-replace install, finally remove the temp file; fsync the parent where supported. Write `audit.jsonl` first and `manifest.json` last. Implement the flat-run, deterministic external claim-journal, same-root tombstone rename, platform identity lock, ordered unlink, and residual scan exactly as §3.6; never call `shutil.rmtree`.

Implement exactly these typed public interfaces:

- `write_sealed_run(owner: RunOwner, selection: ProbeSelection, records: list[ProbeRecord]) -> VerifiedRun`
- `verify_sealed_run(root: Path, run_dir: Path) -> VerifiedRun`
- `install_grok_review(root: Path, run_dir: Path, review: Mapping[str, object]) -> ReviewResult`
- `validate_grok_review(run: VerifiedRun, review_path: Path) -> ReviewResult`
- `validate_report_target(report_root: Path, durable_report: Path, *, forbidden: Sequence[Path]) -> Path`
- `finalize_reviewed_run(root: Path, report_root: Path, run_dir: Path, durable_report: Path) -> FinalizeResult`
- `purge_unsealed_run(root: Path, run_dir: Path) -> CleanupResult`
- `abandon_sealed_run(root: Path, run_dir: Path) -> CleanupResult`
- `scan_run_residuals(root: Path, report_root: Path, run_id: str | None = None) -> ResidualReport`
- `recover_cleanup(root: Path, report_root: Path, claim_id: str, durable_report: Path | None = None) -> FinalizeResult | CleanupResult`

Durable serialization must use an explicit constructor/allowlist, not dictionary key deletion. All cleanup routes share the claim/tombstone/identity machinery. A valid sealed run cannot be silently treated as crash debris; abandoning it requires the separate acknowledged command. Recovery derives and validates run/tombstone/pending identities from the deterministic claim rather than trusting new arbitrary paths.

- [ ] **Step 4: Run lifecycle tests and prove green**

Expected: no test leaves text outside `tmp_path`; cleanup failure is visible and cannot create the final report; path-escape/symlink fixtures remain untouched; all crash states have one documented non-network recovery action; residual scan is zero after every successful closeout.

### Task 5: Standalone CLI And Fail-Closed Preflight

**Files:**
- Create: `backend/inspection_probe.py`
- Modify: `backend/tests/test_inspection_probe.py`

- [ ] **Step 1: Write failing CLI tests**

Use subprocess or direct `main(argv, runtime_root=tmp_runtime, report_root=tmp_reports)` tests. Assert that production parsing exposes no root override; `--database` is mandatory; `preflight` never calls network and cleans its snapshot/run; `run` requires `--ack-authorized-network-run`; no proxy option exists and proxy-related environment variables have no effect; clean-subprocess and static source-import checks cover both the service and CLI, proving neither has a direct/lazy `app.db` or `app.config` import and their normal import/help paths do not load either module; `init_db` is never imported/called; shortfall exits 2 before network; invalid database/snapshot/cleanup exits 3; and `verify/finalize/recover/purge-unsealed/abandon-sealed` accept validated run/claim ids rather than arbitrary run paths. Report tests reject runtime/run/source targets, nested/non-JSON targets, symlink/reparse parents, and paths outside the injected report root.

- [ ] **Step 2: Run tests and prove red**

Expected: CLI file or parser is missing.

- [ ] **Step 3: Implement an `argparse` CLI**

Commands and exit behavior:

```text
preflight --database PATH
  0 = exactly 30 slots selected, prints text-free selection metrics
  2 = selection shortfall DEFER; temporary run cleaned
  3 = invalid/changed database family, snapshot, or cleanup failure

run --database PATH --ack-authorized-network-run
  0 = sealed run with 30 terminal slot records and no pre-review DEFER
  2 = selection shortfall with no network, or sealed evidence already locks DEFER
  3 = unsealed/infrastructure failure

verify --run-id ID
  0 = checksums/schema/30 terminal slots valid
  3 = invalid/unsafe run

install-review --run-id ID --review PATH
  0 = validated hash-bound review atomically installed as run-local review.json
  3 = schema, binding, duplicate-id, or install failure; sealed evidence unchanged

finalize --run-id ID --report PATH
  0 = text removed, final durable PASS report installed
  2 = review threshold DEFER but cleanup/report still completed
  3 = cleanup/publish failure, no final report

recover --claim-id ID [--report PATH]
  0 = non-decision cleanup completed or pending PASS installed/confirmed
  2 = pending DEFER installed/confirmed
  3 = binding, cleanup, or final/pending mismatch failure

purge-unsealed --run-id ID --ack-delete-temporary-evidence
  0 = marker-owned unsealed run removed and absence verified
  3 = sealed/unsafe path/cleanup failure; nothing outside the run is touched

abandon-sealed --run-id ID --ack-abandon-unreviewed-evidence
  0 = valid sealed run removed and absence verified; no durable probe report
  3 = unsealed/unsafe path/cleanup failure; nothing outside the run is touched

scan-residuals [--run-id ID]
  0 = prints text-free ids/counts; zero payload residue
  2 = recoverable residue exists
  3 = unsafe or unclassifiable entry exists
```

`finalize` requires the bound run-local `review.json` unless the manifest already proves fewer than 10 distinct usable final pages and locks `DEFER`. `--report` must pass the fixed `docs/operations/` direct-child contract. `recover --report` must equal the canonical target bound by its claim; purge/abandon claims reject a report argument. Reconfigure stdout/stderr to UTF-8 as the existing CLI does. Never print title/summary/lead/tail, environment values, response bodies, query values, exact URLs, or unsanitized exception strings.

- [ ] **Step 4: Run all focused tests and prove green**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_inspection_probe.py -q
```

- [ ] **Step 5: Conditional implementation commit**

```powershell
git add .gitignore backend/app/services/inspection_probe.py backend/inspection_probe.py backend/tests/test_inspection_probe.py
node .gitnexus/run.cjs detect-changes --scope compare --base-ref master --repo message-platform
git commit -m "feat(rm065): add auditable inspection-reading probe"
```

Only with current human commit authorization.

### Task 6: Independent Review And Code Verification

**Files:**
- Modify after approval: `spec/CHANGELOG.md`
- Update local ignored files: `.agent-bridge/BOARD.md`, `TO_CLAUDE.md`, `TO_OPENCODE.md`

- [ ] **Step 1: Specification review**

Reviewer checks every §3 contract, especially: no model/schema edit; 30 slot semantics; canonical duplicate URLs fetched once but not weighted; no LLM/API/UI/new source; SQLite never opens the source family; WAL snapshot fidelity and source hashes; every URL terminal; Coverage unchanged; usable-only canonical-final-URL review ids; integer 70% gate; review/pending hash binding; and temporary text cleanup before durable publication.

- [ ] **Step 2: Quality/security review**

Reviewer inspects URL/query privacy, canonicalization, terminable DNS deadline, pinned-IP connection, TLS hostname validation, redirect and robots parser behavior, response/decode/hash thresholds, exception sanitization, atomic file ordering, every per-file cleanup crash boundary, flat-run allowlist, tombstone identity locking, final+pending idempotence, sealed abandonment, residual scan, and the global socket deny guard. Fix and re-review all Critical/Important findings.

- [ ] **Step 3: Run backend gates**

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_inspection_probe.py -q
..\venv\Scripts\python.exe -m pytest -q
cd ..
git diff --check
git status --short -- backend/.env backend/dossier.db
git check-ignore -v backend/.env backend/dossier.db backend/inspection_probe_runs/example/audit.jsonl
node .gitnexus/run.cjs status
node .gitnexus/run.cjs detect-changes --scope compare --base-ref master --repo message-platform
```

Pass criteria: focused and full pytest exit 0; no real DB/env tracked; only intended files changed; GitNexus risk/flows match the new isolated probe and thin CLI. Tests use only pytest temporary source/snapshot databases, include real WAL-mode fixtures, and deny all unmocked sockets.

- [ ] **Step 4: Record implementation truth**

Update the changelog and Bridge with test counts, review outcomes, GitNexus scope, and explicit statements that no real DB/network probe ran and RM-055/RM-065 status did not change.

### Task 7: Authorized Real Probe Operation (Separate HOLD)

**Files:** runtime ignored evidence plus one later text-free `docs/operations/*.json` report.

This task is not authorized by plan implementation or test success. It runs only after P0 handoff, implementation review, and an explicit human instruction naming the real read/network operation.

- [ ] **Step 1: Stop every competing writer; capture main/WAL/SHM/rollback-journal baseline fingerprints; run `scan-residuals` and close any prior known claim before proceeding**
- [ ] **Step 2: With explicit real-read approval, run `preflight`; prove SQLite opened only its disposable snapshot, source fingerprints are unchanged, the snapshot/run was cleaned, and shortfall performs no DNS/network**
- [ ] **Step 3: With separate network approval, run the probe; verify 30/30 slot terminals, source fingerprints unchanged, no snapshot residue, and one sealed run id**
- [ ] **Step 4: If 10 distinct usable final pages exist, Grok reviews the required ids and uses `install-review`; otherwise retain the manifest-locked automatic `DEFER`**
- [ ] **Step 5: Finalize either PASS or DEFER; if interrupted use only the bound claim recovery path; mirror exit 0/2 from the pending decision**
- [ ] **Step 6: Require `scan-residuals --run-id` to report zero and independently scan the durable report/runtime root for forbidden title/summary/lead/tail/full-body fields or sentinels**

The decision threshold is:

```text
slot_terminal_count == 30
canonical_requested_success_or_partial_count * 10 >= canonical_requested_url_count * 7
reviewed_distinct_canonical_final_urls >= 10
clean_required_review_ids >= 9 of 10
temporary_text_residual_count == 0
```

Failure of any threshold is `DEFER`, not a crawler escalation and not permission to change Coverage `fulltext unknown`.

---

## 6. Plan Self-Review Checklist

- [x] Every R1 roadmap requirement maps to a task and verification.
- [x] No product schema/API/DTO/UI/LLM/source change is included.
- [x] The CRITICAL model impact is avoided rather than ignored.
- [x] Sample ties, null dates, shortfalls, and cross-topic duplicate URLs have deterministic semantics.
- [x] Existing unsafe fetchers and StealthyFetcher are explicitly excluded.
- [x] Tests cannot access external network or `backend/dossier.db`.
- [x] SQLite never opens the source database family; WAL evidence comes from a disposable stable filesystem snapshot.
- [x] Text/database-bearing evidence cannot leave the gitignored runtime root; only text-free bound pending/final-temp metadata may enter the fixed report root.
- [x] DNS, robots, TLS, redirects, and reads share one enforceable deadline with a terminable resolver process.
- [x] Exact URLs with secret-like query keys are rejected; durable URLs are canonicalized and exact values are hash-only.
- [x] Temporary text is capped, ignored, reviewed, and deleted before durable publication.
- [x] Unsealed crash debris and sealed abandonment have separate guarded cleanup commands.
- [x] The usable-rate and Grok thresholds are based on distinct usable URLs, with explicit inclusive boundary tests.
- [x] Real DB/network operation is a separate HOLD and cannot be inferred from implementation success.
- [x] No incomplete placeholder markers remain.
