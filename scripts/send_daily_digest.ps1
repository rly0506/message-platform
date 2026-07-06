param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [switch]$Annotate
)

$ErrorActionPreference = 'Stop'

$python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$backend = Join-Path $ProjectRoot 'backend'
$logDir = Join-Path $backend 'logs'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logPath = Join-Path $logDir "daily-digest-$timestamp.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    $line | Tee-Object -FilePath $logPath -Append
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtualenv not found at $python"
}

if (-not $env:DAILY_DIGEST_TO) {
    throw 'DAILY_DIGEST_TO is required.'
}

if (-not $env:DAILY_DIGEST_SMTP_HOST) {
    throw 'DAILY_DIGEST_SMTP_HOST is required for unattended SMTP sending.'
}

Write-Log "Starting discovery run."
Push-Location $backend
try {
    $discoverArgs = @('cli.py', 'discover', '--no-print')
    if ($Annotate) {
        $discoverArgs += '--annotate'
    }
    & $python @discoverArgs *>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "discover failed with exit code $LASTEXITCODE"
    }

    Write-Log "Sending daily digest via SMTP."
    & $python 'cli.py' 'daily-email' '--send-smtp' *>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "daily-email --send-smtp failed with exit code $LASTEXITCODE"
    }

    Write-Log "Daily digest sent."
}
finally {
    Pop-Location
}
