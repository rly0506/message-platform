# Dev launcher: starts backend (:8000) and frontend (:5173) in two
# independent, auto-restarting windows. Run once from project root:
#     .\run_dev.ps1
# Stop by closing those two windows. This window can be closed anytime.
#
# Port-conflict policy (NON-destructive):
#   - If a port is held by a STALE dev process of ours (python for backend,
#     node for frontend), we recycle it (kill + reuse the same port).
#   - If it is held by SOMETHING ELSE, we DO NOT kill it. The backend moves to
#     the next free port and the frontend is told the new URL via VITE_API_BASE,
#     so everything still connects and your other program is left untouched.
#
# NOTE: ASCII-only on purpose. Windows PowerShell 5.1 reads .ps1 files as
# system ANSI (GBK on zh-CN) unless they have a BOM, so non-ASCII text here
# would be mangled. Keep this file ASCII.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Get-PortOwner([int]$port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $c) { return $null }
    return Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
}

# Returns a usable port. If $preferred is held by a process whose name matches
# $ourName (a stale dev process), recycle it. Otherwise leave it and scan upward.
function Resolve-Port([int]$preferred, [string]$ourName, [string]$label) {
    $owner = Get-PortOwner $preferred
    if (-not $owner) {
        Write-Host ("[{0}] port {1} free" -f $label, $preferred) -ForegroundColor DarkGray
        return $preferred
    }
    if ($owner.ProcessName -like "*$ourName*") {
        Write-Host ("[{0}] port {1} held by stale {2} PID {3} -- recycling" -f $label, $preferred, $owner.ProcessName, $owner.Id) -ForegroundColor Yellow
        try { Stop-Process -Id $owner.Id -Force -ErrorAction Stop; Start-Sleep -Milliseconds 600 }
        catch { Write-Host ("[{0}] could not kill PID {1}: {2}" -f $label, $owner.Id, $_.Exception.Message) -ForegroundColor Red }
        if (-not (Get-PortOwner $preferred)) { return $preferred }
    }
    else {
        Write-Host ("[{0}] port {1} held by {2} PID {3} (NOT ours) -- leaving it, finding another port" -f $label, $preferred, $owner.ProcessName, $owner.Id) -ForegroundColor Yellow
    }
    for ($p = $preferred + 1; $p -le $preferred + 20; $p++) {
        if (-not (Get-PortOwner $p)) {
            Write-Host ("[{0}] using port {1} instead" -f $label, $p) -ForegroundColor Cyan
            return $p
        }
    }
    throw ("[{0}] no free port in {1}-{2}" -f $label, $preferred, ($preferred + 20))
}

Write-Host "Resolving ports..." -ForegroundColor Cyan
$bport = Resolve-Port 8000 "python" "backend"
$fport = Resolve-Port 5173 "node"   "frontend"
$apiBase = "http://127.0.0.1:$bport"

# ---- backend: uvicorn, auto-restart on crash ----
$backend = @"
`$host.UI.RawUI.WindowTitle = 'BACKEND :$bport  (auto-restart; close window to stop)'
`$env:PYTHONIOENCODING = 'utf-8'
Set-Location '$root'
while (`$true) {
    Write-Host '[backend] starting uvicorn :$bport ...' -ForegroundColor Cyan
    & '$root\venv\Scripts\python.exe' -m uvicorn app.api:app --app-dir backend --host 127.0.0.1 --port $bport --reload
    Write-Host '[backend] exited; restarting in 2s (Ctrl+C to stop this window)...' -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}
"@

# ---- frontend: vite, auto-restart on crash; pinned to chosen backend ----
$frontend = @"
`$host.UI.RawUI.WindowTitle = 'FRONTEND :$fport  (auto-restart; close window to stop)'
`$env:VITE_API_BASE = '$apiBase'
Set-Location '$root\frontend'
while (`$true) {
    Write-Host '[frontend] starting vite :$fport  (API -> $apiBase) ...' -ForegroundColor Cyan
    npm run dev -- --port $fport --strictPort
    Write-Host '[frontend] exited; restarting in 2s (Ctrl+C to stop this window)...' -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontend

Write-Host ""
Write-Host "Launched in two new windows:" -ForegroundColor Green
Write-Host ("  backend   {0}   (health: /api/health)" -f $apiBase)
Write-Host ("  frontend  http://localhost:{0}    <- open this in browser" -f $fport)
Write-Host ""
Write-Host "To stop: close those two windows. This window is safe to close." -ForegroundColor DarkGray
