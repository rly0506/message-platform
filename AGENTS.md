<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **message-platform** (3328 symbols, 6309 relationships, 288 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "master"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/message-platform/context` | Codebase overview, check index freshness |
| `gitnexus://repo/message-platform/clusters` | All functional areas |
| `gitnexus://repo/message-platform/processes` | All execution flows |
| `gitnexus://repo/message-platform/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

# Project Map

## One Sentence Goal

Build a personal intelligence workbench that helps the user track international events, compare evidence across sources, and broaden cognition without requiring LLM access for the core path.

## Project Structure

- `backend/`: FastAPI + SQLModel + SQLite backend for collection, persistence, local analysis, LLM enrichment, discovery, sentiment, academic, and cross-synthesis jobs.
- `backend/app/api.py`: HTTP API surface.
- `backend/app/db.py`: database models, SQLite engine, and lightweight migrations.
- `backend/app/topic_ops.py`: topic creation, collection, enrichment, local analysis, and synthesis orchestration.
- `backend/app/collectors/`: RSS/GNews/GDELT/Reddit/Hacker News and related source collectors.
- `backend/app/pipeline/`: no-LLM local analysis, enrichment prompts, synthesis, prefiltering, clustering, scoring, entities, and categorization.
- `backend/app/services/`: job runners, API payload shaping, country comparison, and shared service helpers.
- `backend/tests/`: backend regression tests. Tests must use the isolated temp DB from `backend/tests/conftest.py`, not `backend/dossier.db`.
- `frontend/`: Vue 3 + TypeScript + Vite frontend.
- `frontend/src/App.vue`: top-level workbench composition.
- `frontend/src/components/`: tab/panel rendering components.
- `frontend/src/composables/`: frontend state orchestration and job polling.
- `frontend/src/types/dossier.ts`: frontend DTOs matching API payloads.
- `frontend/tests/e2e/`: Playwright checks for core reading workflows.
- `spec/`: project harness specs, acceptance gates, and reproducible review standards.

## Non-Negotiable Constraints

- Core collection and local analysis must run without an LLM key.
- Any LLM feature must fail soft: record an error or return an empty optional result, never break the core workflow.
- Do not write the real `backend/dossier.db` during tests or reviews.
- Do not commit `backend/.env`, real API keys, real proxy ports, or local database files.
- Treat sentiment/community layers as signals, not facts.
- Prefer small, reversible changes. Do not add speculative abstractions or dependencies.
- Before editing code symbols, run GitNexus impact analysis for the touched symbol and report high/critical risk.
- Before committing code changes, run GitNexus `detect-changes` and confirm the affected scope is expected.

## Verification Commands

Run the smallest command that proves the change. For release-quality or cross-layer changes, use the full gate:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
npm run test:e2e

cd ..
git diff --check
node .gitnexus/run.cjs status
node .gitnexus/run.cjs detect-changes --scope all
```

If `node .gitnexus/run.cjs status` reports a stale index, run:

```powershell
node .gitnexus/run.cjs analyze
```

## Harness Specs

Read these before planning or reviewing non-trivial work:

- `spec/README.md`: how to use the harness.
- `spec/project.md`: product goal, architecture, and current scope.
- `spec/development.md`: development rules and safety constraints.
- `spec/acceptance.md`: reproducible acceptance checklist and report template.
- `spec/CHANGELOG.md`: dated log of spec and harness changes.
