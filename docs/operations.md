# Operations

## Backend

Run from project root:

```powershell
uvicorn app.api:app --app-dir backend --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Optional LLM configuration:

```env
ANTHROPIC_API_KEY=your_pixel_api_key
ANTHROPIC_BASE_URL=https://ai-pixel.online
LLM_PROVIDER=openai
HAIKU_MODEL=gpt-5.4-mini
SYNTH_MODEL=gpt-5.4
```

LLM smoke test:

```powershell
venv\Scripts\python.exe backend\cli.py llm-check
```

LLM enrichment and synthesis:

```powershell
venv\Scripts\python.exe backend\cli.py enrich <topic_id>
venv\Scripts\python.exe backend\cli.py build <topic_id>
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

The default Vite port is `5173`. If it is occupied, Vite may use `5174` or another nearby port.

## Tests

Backend:

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
```

Frontend:

```powershell
cd frontend
npm run build
npm run test:e2e
```

## GitNexus

```powershell
gitnexus status
gitnexus analyze
gitnexus doctor
gitnexus check --cycles --json
```

Known limitation: FTS/BM25 search may be unavailable on this Windows environment. Use `gitnexus context <symbol>` and `gitnexus check --cycles --json` when query results are degraded.

Before editing a function, class, or method:

```powershell
gitnexus impact <symbol>
```

After refactor:

```powershell
gitnexus detect-changes
gitnexus analyze
gitnexus check --cycles --json
```

## Installed Agent Tools

- Agent Reach skill: `C:\Users\任锂帅\.agents\skills\agent-reach`
- GitNexus skills: `C:\Users\任锂帅\.agents\skills\gitnexus-*`
- Superpowers plugin: `C:\Users\任锂帅\.codex\plugins\cache\openai-api-curated\superpowers`

## Main API Endpoints

- `POST /api/search/jobs`
- `GET /api/search/jobs/{job_id}`
- `POST /api/search/jobs/{job_id}/rerun`
- `GET /api/topics`
- `GET /api/topics/{topic_id}`
- `GET /api/topics/{topic_id}/articles`
- `GET /api/topics/{topic_id}/local-events`
