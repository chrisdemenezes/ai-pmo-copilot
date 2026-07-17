# STRATECH V1 RC-1 -- PowerShell equivalent of setup.bat.
# See docs/product/release-candidate/Local-Installation-Guide.html for the full walkthrough.
$ErrorActionPreference = "Stop"

Write-Host "== STRATECH V1 RC-1 -- local environment setup (PowerShell) =="

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "python not found on PATH. Install Python 3.11+ before continuing."
    exit 1
}
Write-Host "Python $(python --version 2>&1) found."

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "node not found on PATH. Install Node.js 22+ before continuing."
    exit 1
}
Write-Host "Node.js $(node -v) found."

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment at .venv ..."
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
Write-Host "Installing backend dependencies (requirements.txt) ..."
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if (-not (Test-Path "web\node_modules")) {
    Write-Host "Installing frontend dependencies (npm install) ..."
    Push-Location web
    npm install
    Pop-Location
} else {
    Write-Host "Frontend dependencies already installed (web\node_modules present)."
}

Write-Host ""
Write-Host "== Setup complete. Run start.ps1 to launch the platform. =="
