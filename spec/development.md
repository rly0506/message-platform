# Development Rules

## Safety Rules

- Never commit `backend/.env`.
- Never commit or intentionally mutate `backend/dossier.db` in tests.
- Backend tests must rely on `backend/tests/conftest.py`, which sets `DB_PATH` to a temp SQLite database before importing `app.*`.
- Optional LLM paths must degrade gracefully when keys are absent, APIs fail, JSON parsing fails, or model output is empty.
- Network collectors must isolate platform failure: one failed source should enter diagnostics/errors, not crash the whole job.

## GitNexus Rules

Before editing a function, class, or method:

```powershell
node .gitnexus/run.cjs impact <symbol> -d upstream --include-tests
```

If risk is high or critical, report it before editing and explain why the change is still safe or how scope will be reduced.

Before committing code changes:

```powershell
node .gitnexus/run.cjs status
node .gitnexus/run.cjs detect-changes --scope all
```

If the index is stale:

```powershell
node .gitnexus/run.cjs analyze
```

## Change Style

- Prefer deletion over addition.
- Prefer existing helpers and patterns over new abstractions.
- Prefer Python standard library, browser-native behavior, and already-installed dependencies before adding anything.
- Keep changes local to the workflow being modified.
- Do not refactor unrelated code as part of a feature.
- For non-trivial logic, add the smallest runnable test that would fail if the logic broke.

## Frontend Rules

- Keep information readable: one-glance priority, progressive disclosure, and evidence reachable from judgments.
- Do not add visible explanatory copy that describes how the app works unless the user needs it to make a decision.
- Keep class names and DTO contracts stable unless the change explicitly requires them.
- Run `npm run build` after TypeScript or Vue changes.
- Run `npm run test:e2e` after workflow, panel, layout, or DTO changes that affect rendered behavior.

## Backend Rules

- Run targeted pytest first for the touched module.
- Run full backend pytest before reporting a backend feature as complete.
- API contracts must remain backward-compatible unless the task explicitly asks for a breaking change.
- Database migrations must be idempotent and safe for existing SQLite files.
- New optional fields should have defaults that preserve old rows.

## Review Rules

Review findings must lead with bugs and risks, not summaries. For each finding include:

- file and line
- what breaks or bloats
- why it matters
- the smallest fix

If no issues are found, say so and list residual risk or missing coverage.
