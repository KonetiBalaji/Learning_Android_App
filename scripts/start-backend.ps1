param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
    & .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    $serverArgs = @('-m', 'uvicorn', 'study.api:create_app', '--factory', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', $Port)
    if (Test-Path '.env.local') { $serverArgs += @('--env-file', '.env.local') }
    & .\.venv\Scripts\python.exe @serverArgs
} finally { Pop-Location }
