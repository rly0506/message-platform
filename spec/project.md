# Project Specification

## One Sentence Goal

Build a personal intelligence workbench that helps the user track events, compare source evidence, notice narrative patterns, and broaden cognition while preserving a no-LLM core path.

## Product Shape

The project is not a general news reader. It is an event intelligence desk:

- collect reports and discussion signals
- deduplicate and classify evidence
- build timelines and source matrices
- compare media, academic, community, and synthesis layers
- expose uncertainty and evidence before conclusions
- make dense information readable through progressive disclosure

## Architecture

Backend:

- FastAPI API in `backend/app/api.py`
- SQLModel models and SQLite storage in `backend/app/db.py`
- collection and analysis orchestration in `backend/app/topic_ops.py`
- background job lifecycle in `backend/app/services/search_service.py`
- collectors in `backend/app/collectors/`
- no-LLM local analysis in `backend/app/pipeline/local_analyze.py` and sibling modules
- optional LLM enrichment/synthesis in `backend/app/pipeline/enrich.py` and `backend/app/pipeline/synthesize.py`

Frontend:

- Vue 3 + TypeScript + Vite app in `frontend/`
- top-level composition in `frontend/src/App.vue`
- panels in `frontend/src/components/`
- state and polling composables in `frontend/src/composables/`
- API DTOs in `frontend/src/types/dossier.ts`
- Playwright coverage in `frontend/tests/e2e/`

## Current Core Workflows

- Search topic -> collect media reports -> store articles -> local event timeline.
- Deep analysis -> optional LLM enrichment -> synthesis -> timeline/framing/analysis markdown.
- Discovery -> frontier seeds -> synthesis -> clickable search bridge.
- Sentiment/community -> Reddit/Hacker News/OpenCLI platform signals, treated as non-factual sentiment samples.
- Academic/cross synthesis -> compare media, academic, community, and LLM views.

## Non-Goals

- Do not become a generic social feed.
- Do not make LLM mandatory.
- Do not treat community sentiment as verified facts.
- Do not add heavy queues, vector databases, or new infrastructure until existing local patterns fail by evidence.
- Do not hide evidence behind unsupported conclusions.
