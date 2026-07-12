# RM-055 Coverage Snapshot Design

## Goal

Make the evidence boundary visible before expanding collection infrastructure. This backend slice validates existing optional data lines and exposes a no-LLM coverage snapshot for a topic or one of its events.

## Scope

1. Phase 0 records real validation results for GNews URL decoding, optional Scrapling extraction, and optional SearXNG availability.
2. Phase 1 adds `GET /api/topics/{topic_id}/coverage` with an optional `event_id` query parameter.

This slice does not persist article bodies, add collectors, install a queue, introduce a vector database, or implement `dig_later`.

## Evidence Sample

Topic scope uses persisted articles linked through `TopicArticle`. Event scope validates ownership, then intersects `Event.article_ids` with the topic's persisted articles. Missing or mismatched events return HTTP 404.

The response states its basis. An empty sample means no persisted articles were collected for this scope. It never means a source did not publish coverage.

## Response Contract

The response contains `topic_id`, optional `event_id`, and a sample object with `basis`, `article_count`, sorted `article_ids`, and an epistemic note. It also contains:

- `independent_source_count`
- collector, language, and country distributions
- GNews-only URL decoding counts, nullable rate, and evidence IDs
- exact `SourceRegistry` type/tier distributions and unclassified evidence IDs
- full-text status fixed to `unknown` with reason `article_bodies_not_persisted`

Every distribution bucket has `{key, count, article_ids}`. Missing collector, language, and country values use `unknown`. Registry metadata comes only from an exact normalized registry-name match; unmatched articles stay `unclassified` and never receive a heuristic tier.

Independent source count uses normalized non-empty `Article.source` values. Missing source names do not create a synthetic source.

URL decoding rate uses only GNews-collected articles. `url_decoded=true` is success; other eligible articles remain not decoded. With no GNews articles, the rate is `null`, not zero.

## Implementation Shape

Create `backend/app/services/coverage_snapshot.py` as a focused read-only aggregation service. Add a thin route in `backend/app/api.py` that delegates to it and maps missing topic/event ownership to HTTP 404.

Do not change existing evidence helpers because their heuristic source-tier fallback conflicts with this endpoint's explicit `unclassified` rule.

## Phase 0 Acceptance

For GNews, record representative queries, sample size, eligible URL count, decoded count/rate, method distribution, latency, failure categories, and fallback behavior without opening the real database. One successful run does not justify default enablement.

For Scrapling, record dependency availability. If installed, test one public page and one controlled failure. Installation alone is not acceptance, and access/legal boundaries remain explicit.

For SearXNG, probe the configured local service without exposing its URL. If unavailable, record that human-run Docker setup is required; Phase 1 continues.

## Safety and Verification

- Core behavior remains usable without LLM keys or optional services.
- Tests use the isolated temp database from `backend/tests/conftest.py`.
- No real database, `.env`, API key, proxy value, or Claude-owned file enters the diff.
- Tests cover topic/event scope, empty samples, unknown buckets, unclassified registry rows, decoding denominator rules, evidence IDs, and 404 ownership checks.
- Run targeted tests, the full backend suite, `git diff --check`, and GitNexus `detect-changes` before commit review.
