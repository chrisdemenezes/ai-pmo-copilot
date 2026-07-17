@echo off
REM STRATECH V1 RC-1 -- Windows one-time setup: Python venv + backend deps,
REM frontend deps. Mirrors scripts/rc1-local-start.sh's preparation steps
REM exactly -- see docs/product/release-candidate/Local-Installation-Guide.html
REM for the full walkthrough and troubleshooting.
setlocal enabledelayedexpansion

echo == STRATECH V1 RC-1 -- local environment setup (Windows) ==

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: python not found on PATH. Install Python 3.11+ before continuing.
  exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python %PYVER% found.

where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: node not found on PATH. Install Node.js 22+ before continuing.
  exit /b 1
)
for /f "tokens=1" %%v in ('node -v') do set NODEVER=%%v
echo Node.js %NODEVER% found.

if not exist ".venv" (
  echo Creating Python virtual environment at .venv ...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Installing backend dependencies (requirements.txt) ...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if not exist "web\node_modules" (
  echo Installing frontend dependencies (npm install) ...
  pushd web
  call npm install
  popd
) else (
  echo Frontend dependencies already installed (web\node_modules present).
)

echo.
echo == Setup complete. Run start.bat to launch the platform. ==
endlocal
