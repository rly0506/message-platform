# Acceptance Standard

Every completed task must include enough evidence for another agent to reproduce the result.

## Minimum Report Template

```markdown
Changed files:
- path/to/file

Verification:
- `command` -> exit 0, key output
- `command` -> exit 0, key output

GitNexus:
- status: fresh/stale and whether `analyze` was run
- detect-changes: risk level, changed symbols, affected flows

Safety:
- `backend/.env`: not tracked
- `backend/dossier.db`: not tracked and not used by tests

Notes:
- skipped checks and why
- residual risks
```

## Full Verification Gate

Use for cross-layer changes, release-quality checkpoints, refactors, database model changes, and anything that touches job runners or API payloads.

### Backend Tests

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest -q
```

Pass criteria:

- command exits `0`
- report contains `passed`
- no failure, error, or unexpected xfail

### Frontend Build

```powershell
cd frontend
npm run build
```

Pass criteria:

- command exits `0`
- `vue-tsc` completes
- Vite build completes and prints output assets

### Frontend E2E

```powershell
cd frontend
npm run test:e2e
```

Pass criteria:

- command exits `0`
- Playwright reports all tests passed
- if count changes, explain why

### Diff Hygiene

```powershell
git diff --check
git status --short
```

Pass criteria:

- `git diff --check` exits `0`
- `git status --short` contains only intended files

### GitNexus Scope

```powershell
node .gitnexus/run.cjs status
node .gitnexus/run.cjs detect-changes --scope all
```

Pass criteria:

- if status is stale, run `node .gitnexus/run.cjs analyze` and repeat status
- changed symbols match the intended files
- high/critical risk is explained by actual affected flows, not ignored

### Secret And Database Safety

```powershell
git status --short -- backend/.env backend/dossier.db
git check-ignore -v backend/.env backend/dossier.db
```

Pass criteria:

- first command has no output
- second command shows both files ignored by `.gitignore`

## Targeted Verification

Small documentation-only changes may use:

```powershell
git diff --check
git status --short
```

Small backend-only changes may use targeted pytest first, then full pytest if the touched code is shared:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_name.py -q
```

Small frontend-only changes may use:

```powershell
cd frontend
npm run build
```

Add `npm run test:e2e` when rendered behavior, DTOs, routing, panels, or workflows change.

## Quantitative Acceptance Examples

- Backend pass: `140 passed, 3 warnings`.
- Frontend e2e pass: `8 passed`.
- Build pass: Vite prints generated assets and exits `0`.
- GitNexus report: `Changes: N files, M symbols; Risk level: low/medium/high/critical`.

Do not say "should pass". Provide command output from the current workspace.
