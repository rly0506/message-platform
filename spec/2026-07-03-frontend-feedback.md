# Frontend Trial Feedback - 2026-07-03

This note records the user's current product feedback after trying the frontend. It is a requirements capture file, not an implemented design. Future iterations should read this before changing discovery, media analysis, sentiment, academic, or topic-management flows.

## Raw Feedback Summary

1. Existing project/topic management is not acceptable as a simple dropdown. The app needs real CRUD: create, rename/edit, delete, archive, and browse existing projects/topics.
2. Event deep-dive chips currently lose topic context. Example: in the context of "俄乌战争", clicking "前线态势" appears to search only those four characters, which is ambiguous and wrong. Follow-up searches must carry the parent topic/event context.
3. News sources are still too few. The product needs broader and higher-quality reporting sources, including major international newspapers, magazines, exclusive reporting, and deep reporting. Sources may come from third-party tools or custom crawling. Local pre-analysis should initialize as much structure as possible before LLM analysis to reduce LLM burden.
4. Refreshing an individual panel after LLM deep analysis should not invalidate or force rerunning the whole LLM analysis. The product needs reusable analysis artifacts and per-layer refresh behavior.
5. Community/sentiment collection fails even though the user is logged into Chrome:
   - Reddit: `OpenCLI is not available at 'opencli'. Set OPENCLI_COMMAND to the full local path.`
   - Bilibili: same OpenCLI error.
   - Xiaohongshu: same OpenCLI error.
   - Xueqiu: same OpenCLI error.
   Local observation: PowerShell can resolve `opencli` at `D:\npm-global\opencli.cmd`, but backend processes may not inherit that path. A likely fix is explicit `OPENCLI_COMMAND=D:\npm-global\opencli.cmd` handling in the dev launcher or backend config diagnostics.
6. "态度随时间变化" is currently not useful for understanding public opinion change. It should either be redesigned into a real opinion-shift view or removed.
7. The intended "事件结构树" is not a flat reading slice. The user means a historical/developmental network or tree where events interact and evolve over time, for example: "黑色病爆发" -> "天主教权威下降" -> "文艺复兴" -> "宗教改革" -> "理性主义" -> "资产阶级革命".
8. "事件结构树" and "事件发展流程" likely overlap and may be merged into one event-development graph/tree experience.
9. In the event timeline, `Selected Node` should appear directly under the clicked event, not at the bottom of the page. Its purpose is quick access to source articles and country/media comparison for that event. The current G20 comparison idea is blocked by insufficient source coverage for all 20 countries and by weak same-event cross-country matching.
10. Academic view needs stronger citation hygiene: paper source, DOI link when available, authors, venue/journal, and publication context. The user is considering high-quality paper filtering. A frontloaded "学界综述" may be useful, but it must follow academic review norms: citations, paraphrase discipline, source attribution, and clear standards. Similar "review" layers may later be considered for media and community.
11. The current academic citation graph is nearly unreadable. The user prefers a media-like tree/network presentation instead of raw citation-id chips.
12. The current cognition-expansion queue feels uncomfortable and unmotivating. Items have no summaries, do not create desire to click deeper, and appear disconnected from the "认知前沿日报" below.
13. User shared a Bilibili video about information collection methods:
   - URL: `https://www.bilibili.com/video/BV1tL2jBgEwh`
   - Verified with local OpenCLI metadata lookup on 2026-07-03:
     - Title: "为什么你的资讯总是慢半拍？2025年，我是如何用 AI 获取硅谷一手情报的"
     - Author: 神烦老狗
     - Published: 2025-12-05 06:58
     - Duration: 5m46s
     - Observed counts at lookup time: 82,424 views, 10,007 favorites, 5,050 likes.
   - Mentioned "core AI intelligence assistant": Filo Mail.
   - Source layers from the video notes:
     - Industry pulse: TLDR, The Rundown AI, Morning Brew.
     - Deep thinking: Stratechery, Lenny's Newsletter, OpenAI Research.
     - Passive monitoring: Google Alerts, for example `site:reddit.com "ai tool"`.
   OpenCLI could read metadata and description, but this note does not yet include a full transcript review. Treat it as a source-ingestion lead, not final product design.
14. This conversation should be written into the workspace. This file is the first capture of that request.

## Problem Clusters

### A. Topic And Project Management

The current topic selector is too weak for an accumulated intelligence workbench. Users need to manage long-running topics such as "俄乌战争", "低空经济", and "能源转型与关键矿产" as durable projects with metadata, status, and history.

Likely capabilities:

- create topic/project
- rename and edit description/query seed
- archive or delete
- duplicate/fork a topic
- show last collection time, article count, analysis status, and stale indicators
- search/filter existing projects

### B. Context-Preserved Deep Dive

Deep-dive chips must be interpreted as subqueries under the current topic, not standalone query strings.

Example:

- Bad: search `前线态势`
- Better: search `俄乌战争 前线态势`
- Better still: use a structured payload such as `{ parent_topic: "俄乌战争", subtopic: "前线态势", intent: "frontline status", entities, timeframe }`

### C. Source Coverage And Local Pre-Analysis

The product needs a source registry that separates:

- broad RSS/news APIs
- high-quality newspapers and magazines
- deep reporting / longform sources
- official/primary sources
- academic sources
- social/community platforms
- user-added source lists such as newsletters, alerts, and feeds

Local pre-analysis should do more before LLM calls:

- deduplicate and cluster articles
- extract entities, dates, locations, actors, claims, and source metadata
- identify event candidates and evidence links
- detect same-event cross-source groups
- prepare structured context for LLM synthesis rather than asking the LLM to rediscover everything from raw text

### D. Analysis Artifact Reuse

Each layer should know whether it depends on:

- raw collected articles
- local analysis artifacts
- community samples
- academic results
- LLM synthesis artifacts

Refreshing one layer should not erase or require rerunning unrelated completed artifacts. LLM analysis should be stored and reused until its inputs change materially.

### E. Community And Opinion Change

The current community tool integration is blocked by OpenCLI path/runtime configuration. The opinion-change UI also does not yet answer the user's real question: how public opinion changes over time.

Possible replacement for "态度随时间变化":

- timeline of major public-opinion shifts
- source/platform distribution
- representative posts/comments with links
- sentiment labels as weak signals, not facts
- explain what evidence supports each shift

If the data is too weak, remove this section rather than showing unusable cards.

### F. Event Development Network

The desired model is a developmental graph/tree of events over time, not only reading categories. It should support:

- chronological event nodes
- causal or influence hypotheses clearly labeled as hypotheses
- evidence-backed links between nodes
- overlapping branches
- source articles per node
- same-event media comparison
- multi-country comparison when evidence exists

This likely merges the current "事件结构树" and "事件发展流程" into a single event-development view.

### G. Academic Layer

Academic output should shift from raw paper lists and unreadable citation chips toward a readable evidence map:

- academic overview/review with explicit citations
- paper cards with authors, year, venue, DOI/source link
- quality signals such as citation count, venue clarity, recency, paper type, and whether it is actually relevant
- literature tree/network grouped by school, method, chronology, or citation relationship

### H. Cognition Expansion

The current cognition-boundary queue needs to become more inviting and more connected to the daily report:

- every item needs a short summary
- explain why it is relevant now
- connect it to the report seed or source evidence
- make "深入" feel like entering a meaningful analysis path, not clicking a random headline

## Initial Iteration Candidates

Recommended sequencing:

1. Fix context-preserved deep dive and topic/project management basics. This addresses the most obvious workflow breakage.
2. Fix OpenCLI path diagnostics and backend configuration so community collection can actually run.
3. Merge event structure tree and event timeline into a single event-development view with inline selected-node details.
4. Redesign source registry and local pre-analysis so later media/academic/community summaries have better evidence.
5. Redesign academic review and citation/literature-map presentation.
6. Rework cognition-boundary queue after report/source connections are stronger.

## Open Design Questions

1. Should "project" and "topic" be the same object, or should a project contain multiple related topics/searches?
2. Should source expansion start with a curated source registry, user-added feeds, or an automated crawler/importer?
3. Should event-development links be local-only evidence links first, or should LLM-generated causal hypotheses be allowed with strict labels?
4. Should the opinion-change view be paused until community collection is reliable?
