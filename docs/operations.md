# Operations

## Backend

Run from project root:

```powershell
.\run_dev.ps1
```

For phone access on trusted Wi-Fi or Tailscale:

```powershell
.\run_dev.ps1 -Lan
```

LAN mode binds the backend to `0.0.0.0`, starts Vite with `--host 0.0.0.0`, and prints the phone URL. Use it only on trusted networks.

Manual backend start:

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

## Daily Digest Email

Manual preview:

```powershell
cd backend
..\venv\Scripts\python.exe cli.py daily-email --preview
```

Manual Agent Mail send is still a two-step write action:

```powershell
$env:DAILY_DIGEST_TO="your-phone-mail@example.com"
..\venv\Scripts\python.exe cli.py daily-email --send
```

If Agent Mail returns a confirmation token, inspect the summary and rerun with
`--confirmation-token <ctk>`. This path is intentionally not unattended.

### Windows Task Scheduler Email

For automatic daily phone email on the current PC, use SMTP plus Windows Task
Scheduler. The PC must be powered on, online, and able to wake/run at the chosen
time. This does not require opening the backend or frontend browser.

Set environment variables for the Windows user that runs the task:

```powershell
setx DAILY_DIGEST_TO "your-phone-mail@example.com"
setx DAILY_DIGEST_SMTP_HOST "smtp.example.com"
setx DAILY_DIGEST_SMTP_PORT "587"
setx DAILY_DIGEST_SMTP_USER "sender@example.com"
setx DAILY_DIGEST_SMTP_PASSWORD "your-smtp-app-password"
setx DAILY_DIGEST_FROM "Personal Intelligence <sender@example.com>"
setx DAILY_DIGEST_SMTP_TLS "1"
```

Open a new PowerShell window after `setx`, then smoke test:

```powershell
.\scripts\send_daily_digest.ps1
```

Register an 08:30 daily task:

```powershell
$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PWD\scripts\send_daily_digest.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 08:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun
Register-ScheduledTask `
  -TaskName "Personal Intelligence Daily Digest" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Run discovery and email the latest daily digest."
```

Useful maintenance commands:

```powershell
Start-ScheduledTask -TaskName "Personal Intelligence Daily Digest"
Get-ScheduledTaskInfo -TaskName "Personal Intelligence Daily Digest"
Unregister-ScheduledTask -TaskName "Personal Intelligence Daily Digest" -Confirm:$false
```

Logs are written to `backend\logs\daily-digest-*.log`.
