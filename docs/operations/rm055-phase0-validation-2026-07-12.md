# RM-055 Phase 0 Validation - 2026-07-12

## Environment Snapshot

- GNews decoding default: disabled
- Scrapling dependency: unavailable
- Scrapling feature default: disabled
- SearXNG feature default: disabled
- SearXNG local service: unavailable during probe

No API keys, proxy values, service URLs, or database contents were printed. The probes imported collectors directly and did not open `backend/dossier.db`.

## GNews Feed Sample

| Query | Locale | Returned | Feed time |
|---|---:|---:|---:|
| Ukraine peace talks | en-US | 100 | 1.926 s |
| AI regulation China | zh-CN | 64 | 2.651 s |

An attempted non-ASCII stdin query was discarded from the evidence because the PowerShell pipeline changed its characters before Python received it.

## URL Decoding Sample

- Eligible sampled URLs: 10
- Decoded: 10
- Observed success rate: 100%
- Method: `batchexecute` for all 10
- Mean decode latency: 2.271 s per URL
- Observed range: 1.903-2.957 s
- All successful results were usable publisher URLs.

## Failure and Fallback Checks

- A controlled invalid GNews article ID returned `method=failed` after 1.403 s.
- Its resolved URL and original URL both remained the input Google News URL.
- With decoding disabled, the resolver returned `method=disabled` and preserved the original URL.
- Therefore decoding failure does not remove the evidence link or abort collection.

## Optional Full Text and Search

Scrapling is not installed in the current backend environment. `extract_url_scrapling()` returned `ok=false` with `scrapling unavailable`, confirming the intended soft-degrade path. No dependency was installed merely to satisfy this probe.

The configured SearXNG local service was unavailable. The collector raised its typed `SearxngError` after 1.624 s. This is an optional, human-operated service and does not block the coverage API.

## Recommendation

**Hold `GNEWS_DECODE_URLS` disabled by default.** The sampled success rate is encouraging, but the current implementation resolves every feed item sequentially. At the observed 2.271 s mean, the 100-item and 64-item feeds imply minute-scale added latency if decoding is enabled for the full result set.

Before default enablement, bound or parallelize decoding, define a per-collection time budget, and repeat validation with a larger mixed sample including failures. The stable original-URL fallback is sufficient for opt-in experiments now.

Keep Scrapling and SearXNG optional. Scrapling requires a deliberate dependency/access review; SearXNG requires the human-run Docker service. Neither should delay product-visible coverage work.
