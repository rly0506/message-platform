# Event Tree / Literature Graph Design

## Purpose

This design captures the next design-first direction for the workbench: helping the user read complex topics as structures, not as long lists.

The feature has two related but separate reading tasks:

- **Event tree**: explain how a topic branches from root issue to triggers, sub-branches, consequences, and unresolved questions.
- **Academic literature graph**: explain how academic papers relate as foundational works, reviews, recent work, cited hubs, schools, and open debates.

V1 should be text-first. Do not start with a visual canvas. A clear nested structure is more valuable than a decorative graph that the user cannot act on.

## Product Goal

Help the user answer:

- What is the root issue behind this event?
- Which branches are media developments, policy reactions, market consequences, academic explanations, or public sentiment signals?
- Which branch should I read next if I want to broaden cognition rather than skim more headlines?
- In the academic layer, which papers are useful as starting points, which are recent updates, and which represent different schools or concepts?

## Non-Goals

- Do not claim the system has proven causal root causes.
- Do not label any branch as the true cause without evidence.
- Do not build a graph canvas, force-directed layout, or heavy visualization in V1.
- Do not add a vector database, queue system, or new frontend library.
- Do not require LLM access for the core structure. LLM may later improve labels, but local data must remain usable.
- Do not merge this with the cognition map. Cognition marks are about the user's knowledge boundary; event/literature structures are about the topic.

## Event Tree V1

### Shape

Represent the event as a text-first tree:

```text
Root issue
  Trigger events
    Representative reports
  Branches
    Policy / diplomacy
    Market / economic impact
    Security / conflict
    Technology / infrastructure
    Public sentiment signals
  Consequences
  Unresolved questions
```

Each node should show:

- label
- short explanation
- evidence count
- source count
- representative titles or sources
- caveat when the node is inferred from weak evidence

### Existing Data Sources

Use existing payloads first:

- `local events`: date, title, summary, category, stance, score, evidence
- `source_matrix`: sources, tiers, first/latest published time, representative titles
- `narrative_signals`: topic-local repeated claims and representative titles
- `entities` / `entity_groups`: people, organizations, places, concepts
- `stance_evolution`: time periods and dominant stances
- `articles`: titles, snippets, categories, substance/emotion badges

### First Implementation Candidate

Frontend-derived V1 in the Media tab:

- Add a collapsed panel named `事件结构树`.
- Render 4-6 top-level groups using existing categories and stances.
- Use nested lists or compact tree rows, not an interactive graph.
- Keep every node linked back to representative reports or sources.
- Default collapsed to avoid increasing reading burden.

No backend changes unless the frontend derivation proves too brittle.

## Academic Literature Graph V1

### Shape

Represent the academic layer as a reading structure:

```text
Academic reading map
  Foundational papers
  Review / overview papers
  Recent papers
  Highly cited hubs
  Schools / concepts
  Thin evidence / low-information items
```

Each group should show:

- paper count
- representative papers
- venue/year/citation badges already available in the academic panel
- why this group is useful for reading
- original paper links preserved

### Existing Data Sources

Use existing OpenAlex-derived fields:

- `papers`
- `venue`
- `year`
- `cited_by_count`
- `concepts`
- internal citation graph
- `foundational_papers`
- `schools`
- current priority-reading labels from `spec/academic-filtering-design.md`

### First Implementation Candidate

Frontend-derived V1 in the Academic tab:

- Add a collapsed panel named `阅读关系`.
- Group papers by existing signals: foundational, recent, high citation, school/concept.
- Keep the original paper list visible and unchanged.
- Do not replace the current priority-reading summary; this is a second reading aid.

No LLM required.

## Relationship To Cognition Map

These features should not become the cognition map.

- Event tree: structure of the topic.
- Literature graph: structure of academic evidence.
- Cognition map: structure of the user's knowledge boundary, based on the user's marks over time.

The cognition map may later consume event-tree or literature-graph interactions as signals, but V1 should not mix the concepts.

## UX Principles

- Default collapsed: structure helps when requested, but should not dominate the first screen.
- Evidence-linked: every node must point back to reports, sources, or papers.
- Neutral language: use `结构`, `分支`, `信号`, `阅读入口`; avoid `真因`, `权威结论`, `操控`.
- Progressive disclosure: show the tree first, evidence second, original list still available.
- Small scope: prefer text rows and native disclosure controls over a custom graph canvas.

## Risks

- **False causality**: tree language can imply causation. Mitigation: label weak branches as inferred structure and keep evidence visible.
- **Visual overbuild**: a graph can look impressive but reduce readability. Mitigation: text-first V1.
- **Duplicate panels**: media and academic tabs already have many panels. Mitigation: default collapsed and only show when enough data exists.
- **LLM temptation**: root-cause labels are tempting to generate. Mitigation: local categories and evidence first; optional LLM labels later only as explanations.

## Acceptance For Design-First Stage

- This document exists and is linked from `spec/README.md`.
- `spec/roadmap.md` names event tree / literature graph as design-first, not current implementation.
- No frontend or backend code is changed by this design stage.
- Future implementation plan must choose either event tree V1 or academic reading map V1, not both at once.
