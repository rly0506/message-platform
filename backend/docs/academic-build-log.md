# Academic Layer Build Log

Date: 2026-06-27

## Scope

Implemented and audited the academic layer for ChinaNewsMap:

- OpenAlex paper search with `api_key` query authentication.
- Relevance-first OpenAlex retrieval; no `sort=cited_by_count` is sent.
- Inverted abstract reconstruction.
- Converged top-N citation graph with zero extra paper-expansion API calls.
- Academic schools and foundational-paper ranking.
- LLM academic synthesis with mocked tests.
- Background job and API surface:
  - `POST /api/topics/{topic_id}/academic/jobs`
  - `GET /api/topics/{topic_id}/academic`

Allowed task files touched during the resumed pass:

- `backend/app/pipeline/academic.py`
- `backend/app/api.py`
- `backend/tests/test_academic_layer.py`
- `backend/docs/academic-build-log.md`

## Resumption Note

This log was written after resuming from an interrupted run. Before this resumed pass,
a previous optional real end-to-end attempt had already called `init_db()` against the
real database and created the academic tables.

- Original pre-attempt DB MD5 recorded by the previous run:
  `EC14CA986260B9BC26FDBA96675A832A`
- Current resumed baseline DB MD5:
  `F2769960065FF947A52B9B42E2FA3B88`
- Backup from the optional attempt:
  `backend/dossier.db.bak-academic-20260627-022255`
- Academic rows after the failed optional attempt:
  - `papers 0`
  - `citations 0`
  - `topic10_links 0`
- Failure reason for the optional attempt:
  LLM `ReadTimeout`; no academic rows were inserted.

From this resumed baseline onward, checkpoints 1-7 did not change
`backend/dossier.db`.

## GitNexus Impact Notes

GitNexus index was refreshed with:

```powershell
node .gitnexus/run.cjs analyze
```

Important impact results:

- `run_academic_analysis`: LOW, 0 impacted symbols.
- `synthesize_academic_consensus`: LOW, direct caller `run_academic_analysis`.
- `reconstruct_abstract`: LOW, direct caller `normalize_work`, indirect `search_works`.
- `converged_citation_edges`: LOW, 0 impacted symbols in index.
- `academic_view`: LOW, 0 impacted symbols.
- `search_job_payload`: CRITICAL, so it was intentionally not modified.

New thin wrapper symbols were added after the index refresh:

- `rebuild_abstract`
- `build_citation_graph`
- `synthesize_academic`
- `latest_academic_summary`

They are wrappers or a narrow API helper; final `detect_changes` should be used for
post-edit impact mapping.

## OpenAlex Real Field Probe

Read-only request:

```text
GET https://api.openalex.org/works?search=Iran+nuclear+deal&per-page=2&api_key=<redacted>
User-Agent: DossierBot/0.1
```

Result:

```text
status 200
results 2
```

Sample work 1:

```text
id: https://openalex.org/W2284027937
title: A new dawn? The Iran nuclear deal and the future of the Iranian tourism industry
publication_year: 2016
cited_by_count: 64
referenced_works_len: 16
abstract_present: False
authors_first: Masood Khodadadi
concepts_first3: Tourism, Sanctions, Negotiation
venue: Tourism Management Perspectives
url: https://doi.org/10.1016/j.tmp.2015.12.019
```

Sample work 2:

```text
id: https://openalex.org/W2195681498
title: The Iran Nuclear Deal: A Definitive Guide
publication_year: 2015
cited_by_count: 46
referenced_works_len: 0
abstract_present: False
authors_first: Gary Samore
concepts_first3: Computer science
venue: Digital Access to Scholarship at Harvard (DASH) (Harvard University)
url: http://nrs.harvard.edu/urn-3:HUL.InstRepos:27029094
```

Because those two results had no abstract inverted index, a second read-only probe
confirmed abstract reconstruction:

```text
query: climate change adaptation
status: 200
id: https://openalex.org/W2120012334
title: Managing the Risks of Extreme Events and Disasters to Advance Climate Change Adaptation
reconstructed prefix: This Intergovernmental Panel on Climate Change Special Report (IPCC-SREX) explores the challenge of understanding and managing the risks of climate extremes to advance climate change adaptation. Extreme weather and clima
```

Confirmed fields:

- `id`
- `title`
- `publication_year`
- `cited_by_count`
- `referenced_works`
- `abstract_inverted_index`
- `authorships`
- `concepts`
- `primary_location`

## Checkpoint Gates

Command used at every checkpoint:

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests -q
```

Checkpoint 1 - abstract reconstruction:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`

Checkpoint 2 - SQLModel tables:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`

Checkpoint 3 - converged citation graph:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`

Checkpoint 4 - schools and foundational papers:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`

Checkpoint 5 - OpenAlex collector:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`
- Network is mocked in tests.
- Real field probe was read-only and did not touch the DB.

Checkpoint 6 - LLM synthesis:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`
- `llm.chat` is mocked in tests.

Checkpoint 7 - background job and API:

- Result: `53 passed, 3 warnings`
- DB MD5: `F2769960065FF947A52B9B42E2FA3B88`
- OpenAlex and LLM are mocked in tests.

Checkpoint 8 - optional real end-to-end:

- Not retried in the resumed pass.
- Reason: a previous optional attempt already created the schema and then failed at
  the LLM call with `ReadTimeout`. To avoid additional real DB writes and external
  spend, this resumed pass stopped at the mocked, fully green checkpoint 7.

## Additional Resumed Fixes

Two small audit gaps were closed:

1. Added checkpoint-named wrappers in `academic.py`:
   - `rebuild_abstract`
   - `build_citation_graph`
   - `synthesize_academic`
2. Made `GET /api/topics/{topic_id}/academic` return the latest completed academic
   job `summary_md`, without modifying the high-impact shared `search_job_payload`.

Regression tests were added for both.

Red/green evidence:

- First run of `backend/tests/test_academic_layer.py` failed with:
  - missing `academic.rebuild_abstract`
  - `/academic` returning empty `summary_md`
- After the minimal fix:
  - `backend/tests/test_academic_layer.py`: `6 passed, 3 warnings`
  - Full suite: `53 passed, 3 warnings`

