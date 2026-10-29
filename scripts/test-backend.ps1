$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    & .\.venv\Scripts\python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
} finally { Pop-Location }
