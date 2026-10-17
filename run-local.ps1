# run-local.ps1
# Starts Doc2Patient locally against a SQLite database.
# Usage:  .\run-local.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $root

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Virtual environment not found at $python. Create it first, then run: pip install -r requirements.txt"
    exit 1
}

# Force a local SQLite database. Environment variables take precedence over .env,
# so this overrides any DATABASE_URL that points at a remote host.
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $root 'app.db')
# Local runs use plain HTTP, so do not mark cookies as HTTPS-only.
$env:SESSION_COOKIE_SECURE = '0'

Write-Host "Database : $env:DATABASE_URL"
Write-Host "URL      : http://127.0.0.1:5000"
Write-Host ""

# Alembic and Flask log informational messages to stderr, which PowerShell would
# otherwise surface as errors, so keep the preference at Continue for these calls.
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

& $python -m flask db upgrade
if ($LASTEXITCODE -ne 0) {
    $ErrorActionPreference = $previousPreference
    Write-Error "Database migration failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

& $python (Join-Path $root 'main.py')
$ErrorActionPreference = $previousPreference
