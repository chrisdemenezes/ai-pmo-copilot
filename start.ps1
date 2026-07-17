# STRATECH V1 RC-1 -- PowerShell equivalent of start.bat.
# Run setup.ps1 once before the first use of this script.
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    Write-Error ".venv not found. Run setup.ps1 first."
    exit 1
}
if (-not (Test-Path "web\node_modules")) {
    Write-Error "web\node_modules not found. Run setup.ps1 first."
    exit 1
}

if (-not (Test-Path "demo\.env")) {
    Write-Host "demo\.env not found -- creating one from demo\.env.example with a generated SESSION_SECRET."
    Copy-Item "demo\.env.example" "demo\.env"
    $secret = python -c "import secrets;print(secrets.token_urlsafe(32))"
    (Get-Content "demo\.env") -replace '^SESSION_SECRET=.*', "SESSION_SECRET=$secret" | Set-Content "demo\.env"
    Write-Host "Created demo\.env (Demo Mode: mock provider, no external credential needed)."
}

$envVars = @{}
Get-Content "demo\.env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_.Trim() -eq "") { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) { $envVars[$parts[0].Trim()] = $parts[1].Trim() }
}

$backendPort = if ($envVars["BACKEND_PORT"]) { $envVars["BACKEND_PORT"] } else { "8000" }
$frontendPort = if ($envVars["FRONTEND_PORT"]) { $envVars["FRONTEND_PORT"] } else { "3000" }

Write-Host "Starting backend on :$backendPort (SQLite, no Docker) ..."
Start-Process -WindowStyle Normal powershell -ArgumentList @(
    "-NoExit", "-Command",
    ".\.venv\Scripts\Activate.ps1; " +
    "`$env:API_KEY='$($envVars['API_KEY'])'; `$env:LLM_PROVIDER='$($envVars['LLM_PROVIDER'])'; " +
    "`$env:ANTHROPIC_API_KEY='$($envVars['ANTHROPIC_API_KEY'])'; `$env:MOCK_LLM_RESPONSE_FILE='$($envVars['MOCK_LLM_RESPONSE_FILE'])'; " +
    "uvicorn src.main:app --host 0.0.0.0 --port $backendPort"
)

Write-Host "Starting frontend on :$frontendPort ..."
Start-Process -WindowStyle Normal powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd web; `$env:BACKEND_URL='http://localhost:$backendPort'; `$env:API_KEY='$($envVars['API_KEY'])'; " +
    "`$env:WORKSPACE_PASSWORD='$($envVars['WORKSPACE_PASSWORD'])'; `$env:SESSION_SECRET='$($envVars['SESSION_SECRET'])'; " +
    "npx next dev -p $frontendPort"
)

Write-Host ""
Write-Host "Waiting for backend and frontend to come up (about 15-30s) ..."
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "STRATECH V1 RC-1 should now be running:"
Write-Host "  Login:     http://localhost:$frontendPort/entrar   (password: $($envVars['WORKSPACE_PASSWORD']))"
Write-Host "  Dashboard: http://localhost:$frontendPort/dashboard"
Write-Host "  Backend:   http://localhost:$backendPort/health"
Write-Host ""
Write-Host "Next step (first run only): python demo\seed_demo_data.py"
Write-Host "Stop: run stop.ps1 (or stop.bat), or close the two opened windows."
