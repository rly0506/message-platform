# RM-055 Source Expansion Gate - 2026-07-13

## Decision

**HOLD the first source-expansion batch.** No feed is added or enabled in this
iteration. This is an evidence decision, not a cancellation of M3'.

The coverage instrument became product-visible on 2026-07-13. RM-055 requires
two weeks of real gap observations before choosing sources, and there is not yet
a longitudinal series from which to identify a repeated language, country,
source-tier, or collector gap.

## Evidence Available Now

- The curated registry contains 38 entries: 29 enabled and 9 disabled.
- Four entries are explicitly uncollectable because they are `zombie`,
  `proxy_only`, `paywalled`, or `api_license`; these must not be silently enabled.
- Fourteen enabled entries are currently classified `fresh_rss` + `public`.
- Enabled registry entries cover five declared languages and nine declared
  countries, but registry breadth does not prove event-level coverage.
- Phase 0 tested 10 eligible GNews URLs: 10 decoded, with 2.271 seconds mean
  latency per URL. The success sample is encouraging, but sequential full-feed
  decoding would add minute-scale latency, so the feature remains opt-in.
- Scrapling was unavailable and the local SearXNG service was unavailable during
  the Phase 0 probe. Their soft-degrade paths worked, but neither produced real
  coverage evidence.
- `GET /api/topics/{topic_id}/coverage` is a point-in-time, evidence-linked view.
  It does not persist daily snapshots, so one response cannot establish a
  recurring gap.

## Executable Observation Gate

The earliest source-selection review is **2026-07-27**, after a 14-calendar-day
window beginning with the product-visible coverage instrument.

For every active topic used during that window, capture the coverage response
after collection and retain the observation date plus:

- article count and independent source count;
- collector, language, country, and source-name distributions;
- source registry tier/type distributions and unclassified article IDs;
- GNews decode eligible/decoded counts and rate;
- the endpoint's explicit `unknown` values without replacing them with zero.

The review may proceed when all of these are true:

1. At least 10 successful observation days exist inside the 14-day window.
2. At least three actively used topics have three or more observations each.
3. A proposed gap recurs on at least three observation days and is visible in at
   least two topics, or is tied to one repeatedly tracked topic with a named
   stakeholder/language requirement.
4. The gap is not merely missing metadata. `unknown`/`unclassified` records must
   be classified before they are used to justify adding a source.
5. The candidate addresses one named gap; "more sources" is not an acceptance
   reason.

## Candidate Feed Acceptance

Keep the first batch to at most three feeds for one named gap. Every candidate
must pass the following before entering `backend/config/feeds.json`:

- public and lawful access, with no login, paywall bypass, or licensed API
  represented as a public feed;
- three successful probes on separate days, with parseable entries and a newest
  item consistent with the source's stated publishing cadence;
- explicit `coverage`, `access`, `last_tested`, `coverage_reason`, language,
  country, source tier, and state-media status;
- stable article URLs and no material duplicate flood against existing sources;
- a backend registry test and a post-rollout comparison against the same
  coverage dimensions that justified the source.

If a candidate fails, retain it as disabled with the observed limitation. Do not
delete the evidence and do not report "source did not publish" when collection
only failed to retrieve it.

## Next Action Without Human Input

Continue RM-055 M4' while this clock runs. The two-week gate may collect evidence
in parallel; it must not be bypassed merely to mark M3' as visually complete.
