# Current Message-Source Report — 2026-07-15

Status: **READ-ONLY INVENTORY; NOT A LIVE REACHABILITY SWEEP**

Database inspected read-only: `backend/dossier.db`.

Registry and article evidence last advance through: **2026-07-14**.

This report distinguishes a configured source, a source whose metadata was
tested in early July, and a source that supplied a recent stored article. None
of these alone proves current availability on 2026-07-15.

## Executive Summary

- The curated RSS registry has **38** sources: **29 enabled** and **9 disabled**.
- Of enabled sources, **14** are marked `fresh_rss` + `public` from tests dated
  2026-07-04/05; **15** are enabled but still lack coverage/access metadata.
  That is metadata debt, not evidence that those 15 failed or are unusable.
- The last registry collection occurred around `2026-07-14 04:27`; **28** enabled
  feeds recorded `ok`, and **European Commission Press Corner** recorded one
  TLS error. No new source sweep was performed for this report.
- The article corpus contains **6,702** rows. For 2026-07-07 through the latest
  stored timestamp on 2026-07-14, it contains **129** articles from **42** source
  labels: **92 RSS** articles from 16 labels and **37 GNews** articles from 28
  labels. GNews labels are publishers surfaced by a search feed, not necessarily
  direct registry feeds.
- Daily topic refresh uses GNews plus the enabled curated registry feeds. GDELT
  is off in that path; SearXNG is off unless a local environment flag enables it.
  No personal-site, LinkedIn, blog, podcast, video, or private-source collector
  is in the default path.

## Curated RSS Registry

### Enabled: 29

| Tier | Enabled sources | Notes |
|---|---:|---|
| Mainstream | 13 | General international reporting; includes English, Arabic, Spanish, Portuguese, and Russian entries. |
| Official | 7 | First-party institutional material; White House and U.S. State Department are explicitly flagged as state media. |
| Professional | 5 | The Economist, Foreign Affairs, Foreign Policy, Stratechery, and The Conversation. |
| Newsletter | 2 | TLDR and Lenny's Newsletter. |
| Wire | 1 | Agence France-Presse. |
| Research | 1 | OpenAI Research. |

The enabled source names are:

- Mainstream: Al Jazeera, BBC, CNBC World, DW, Folha Mundo, France 24,
  France 24 Arabic, France 24 Spanish, Meduza, NPR World, The Guardian,
  The New York Times, The Washington Post.
- Official: European Central Bank, European Commission Press Corner, Federal
  Reserve, The White House, U.S. State Department Press Releases, UN News,
  WTO News.
- Professional: Foreign Affairs, Foreign Policy, Stratechery, The Conversation,
  The Economist.
- Newsletter/research/wire: Lenny's Newsletter, TLDR, OpenAI Research, and
  Agence France-Presse.

Language distribution across the complete registry is English 31, Russian 4,
and one each of Arabic, Spanish, and Portuguese. Country metadata is weighted
toward the United States (15 of 38); the next largest groups are International
(6), France/Russia/United Kingdom (4 each), and European Union (2).

### Disabled: 9

| Reason/state | Sources | Interpretation |
|---|---|---|
| Candidate not yet verified | Morning Brew; The Rundown AI | Keep disabled until a currently usable direct feed is confirmed. |
| Uncollectable or unsuitable public RSS | OECD Newsroom RSS (`proxy_only`); IMF News RSS, World Bank News RSS, Reuters Public RSS (`zombie`; Reuters also `api_license`) | Do not silently enable or treat as normal RSS. |
| Deliberately excluded state-media narrative samples | RT Russian, TASS, RIA Novosti | Public and previously fresh, but default-disabled and labelled state media. |

## Current Health And Evidence Quality

The registry's latest fetch status is a historical observation, not a live
probe:

| Status at last registry fetch | Sources | Reported articles |
|---|---:|---:|
| `ok` | 28 | 988 |
| `failed` | 1 | 1 |

The failed source was **European Commission Press Corner**. Its stored error is
an SSL `DECRYPTION_FAILED_OR_BAD_RECORD_MAC` error from 2026-07-14. This points
to an external TLS/transport problem for that feed, but the existing record
cannot attribute it to today's VPN state.

The most important reporting gap is not source count: 15 enabled feeds have no
`coverage` or `access` metadata. They must remain `unknown` in a coverage
decision; they are not evidence of a missing country, language, or viewpoint.

## Actual Collection Paths

### Topic/news collection

`collect_topic()` uses GNews by default. Automatic news refresh additionally
sets `use_curated_feeds=True`, so it uses the 29 enabled RSS registry sources.

- **GNews:** English-US and Simplified-Chinese locales; URL decoding is opt-in
  and currently default-off.
- **Curated RSS:** the enabled registry feeds above.
- **GDELT:** available for historical backfill, but off in automatic refresh.
- **SearXNG:** available only when `USE_SEARXNG` is explicitly enabled; default
  is off.

### Frontier discovery (separate from topic/news collection)

Seven discovery sources are enabled in `backend/config/frontier_sources.json`:

- Hacker News front page (technology);
- arXiv `cs.AI`, `cs.LG`, `cs.CL` (technology);
- arXiv `econ.GN`, `q-fin.GN` (finance);
- MIT Technology Review (technology RSS);
- Federal Reserve (finance RSS);
- Carnegie Endowment and Brookings (geopolitics RSS).

The quantitative-biology arXiv source is configured but disabled. Discovery is
a signal-finding layer, not a general-news coverage guarantee.

### Community signals (not factual news sources)

Hacker News can be collected through a public HTTP API and is intentionally
presented as a technology/startup community signal. Reddit uses its configured
official API when credentials exist; otherwise it depends on local OpenCLI,
Chrome, and a logged-in session. These layers are not evidence sources for a
factual claim and must remain labelled as sentiment/community samples.

## Interpretation And Next Decision

The system already has more named sources than it has current, longitudinal
coverage evidence. The immediate bottleneck is:

1. no successful RM-055 observation day yet;
2. no current 2026-07-15 collection run; and
3. 15 enabled feeds with incomplete coverage metadata.

Therefore no source should be added or enabled from this inventory. Restore a
genuine local backend listener, then allow the authorized daily path to produce
post-commit evidence. Only the existing RM-055 observation gate may use
recurring, cross-topic gaps to justify a source decision.
