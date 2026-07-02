# Academic Filtering Design

## Goal

Make the academic layer easier to read by showing which papers are better first reads for a topic. This is not a formal journal-ranking system. It is a local, explainable "academic signal" layer built from fields the project already has.

The user question this design answers:

- Which papers should I read first?
- Which papers are foundational within this sample?
- Which papers are recent enough to show the current debate?
- Which papers have enough metadata to be worth trusting at a glance?

## Non-Goals

- Do not claim a paper is "authoritative" or "top journal".
- Do not integrate JCR, CAS/中科院分区, ABS, ABDC, or other external ranking tables in V1.
- Do not treat high citation count as truth.
- Do not hide the original OpenAlex result list or citation graph.
- Do not use LLM to judge paper quality.

## Available Signals

The current academic layer already exposes enough for a V1:

- `venue`: whether the source venue is named.
- `year`: recency.
- `cited_by_count`: broad impact signal.
- sample-internal citation indegree: already used for foundational papers.
- `concepts`: topical grouping and rough relevance.
- `foundational_papers`: local sample foundations.
- `schools`: concept-based schools / topic groups.

## V1 Reading Signals

Use neutral labels. These are reading signals, not truth labels.

- `高引用`: citation count is high relative to the current sample.
- `新近`: publication year is recent relative to the current year or sample range.
- `样本内奠基`: the paper appears in current foundational papers, based on sample-internal citations and citation count.
- `venue明确`: venue is present and not an empty/unknown placeholder.
- `低信息`: missing venue and abstract, or very sparse metadata.

Do not call any item `权威`, `顶刊`, or `中上等刊物` in V1.

## UI Sketch

Add a compact "优先阅读信号" area near the top of the Academic tab:

- high-impact count
- recent count
- sample-foundational count
- low-information count

In the paper list, show small badges next to each paper:

- `高引用`
- `新近`
- `样本内奠基`
- `venue明确`
- `低信息`

Default display order for the paper list should become "recommended reading order" in a later implementation:

1. sample-foundational papers
2. high-citation papers
3. recent papers
4. papers with explicit venue
5. remaining papers
6. low-information papers last

Keep the original evidence reachable:

- paper title link remains visible
- venue/year/citation count remain visible
- citation graph section remains visible
- academic schools remain visible

## Implementation Boundary

First implementation should be frontend-derived:

- compute labels from existing `AcademicPaper[]` and `AcademicFoundationalPaper[]`
- do not change backend payloads
- do not add dependencies
- do not persist derived labels

If the same logic becomes needed by cross-synthesis, exports, or tests beyond the UI, move it later into the backend as an optional derived field such as `academic_quality`.

## Acceptance For Implementation Round

An implementation round is done only when:

- Academic tab shows the "优先阅读信号" summary when papers exist.
- Paper cards show the neutral labels above.
- Low-information papers are still visible.
- Original links and citation graph remain available.
- Frontend build passes.
- Academic-panel test coverage proves labels appear from mocked paper data.

If backend is changed in that implementation, add focused tests in `backend/tests/test_academic_layer.py` for the derived label logic.
