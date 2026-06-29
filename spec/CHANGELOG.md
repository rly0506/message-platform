# Spec Changelog

## 2026-06-29

### Added

- Implemented the readable-cognition roadmap in five small commits:
  - surfaced article substance-score coverage in the media feed;
  - rendered community sentiment as compact readable sample cards;
  - added on-demand article perspective for summary/fulltext sentence inspection;
  - added topic-local narrative convergence signals;
  - added one-click cognition marks and a lightweight cognition accumulation panel.

### Reason

Prioritize reading experience before larger cognition-map work: make substance, signals, and personal judgement markers visible without making LLM or heavy infrastructure part of the core path.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_cognition_marks.py -q` -> `2 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `150 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- tests/e2e/source-matrix.spec.ts -g "groups original articles"` -> `2 passed`
- `cd frontend && npm run test:e2e` -> `10 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk medium, affected processes 5

### Added

- Created the spec harness:
  - `spec/README.md`
  - `spec/project.md`
  - `spec/development.md`
  - `spec/acceptance.md`
- Extended `AGENTS.md` with project map, one-sentence goal, project structure, non-negotiable constraints, verification commands, and spec links.
- Added this changelog and linked it from `AGENTS.md` and `spec/README.md`.

### Reason

Give future agents a stable project map and reproducible acceptance standard before they edit code or claim work is complete.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `140 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `8 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk low, affected processes 0
