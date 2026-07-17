@echo off
REM STRATECH V1 RC-1 -- Windows startup: creates demo\.env if missing (same
REM Demo Mode as demo/start-demo.sh, generated SESSION_SECRET, no external
REM credential needed), then starts backend and frontend each in their own
REM window. Run setup.bat once before the first use of this script.
setlocal enabledelayedexpansion

if not exist ".venv" (
  echo ERROR: .venv not found. Run setup.bat first.
  exit /b 1
)
if not exist "web\node_modules" (
  echo ERROR: web\node_modules not found. Run setup.bat first.
  exit /b 1
)

if not exist "demo\.env" (
  echo demo\.env not found -- creating one from demo\.env.example with a generated SESSION_SECRET.
  copy demo\.env.example demo\.env >nul
  for /f "delims=" %%s in ('python -c "import secrets;print(secrets.token_urlsafe(32))"') do set GENSECRET=%%s
  powershell -NoProfile -Command "(Get-Content 'demo\.env') -replace '^SESSION_SECRET=.*', 'SESSION_SECRET=!GENSECRET!' | Set-Content 'demo\.env'"
  echo Created demo\.env (Demo Mode: mock provider, no external credential needed).
)

REM Load demo\.env into this process's environment (KEY=VALUE lines only).
for /f "usebackq tokens=1,* delims==" %%a in ("demo\.env") do (
  set line=%%a
  if not "!line:~0,1!"=="#" if not "!line!"=="" set %%a=%%b
)

if not defined BACKEND_PORT set BACKEND_PORT=8000
if not defined FRONTEND_PORT set FRONTEND_PORT=3000

echo Starting backend on :%BACKEND_PORT% (SQLite, no Docker) ...
start "STRATECH RC-1 - Backend" cmd /k ".venv\Scripts\activate.bat && set API_KEY=%API_KEY% && set LLM_PROVIDER=%LLM_PROVIDER% && set ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY% && set MOCK_LLM_RESPONSE_FILE=%MOCK_LLM_RESPONSE_FILE% && uvicorn src.main:app --host 0.0.0.0 --port %BACKEND_PORT%"

echo Starting frontend on :%FRONTEND_PORT% ...
start "STRATECH RC-1 - Frontend" cmd /k "cd web && set BACKEND_URL=http://localhost:%BACKEND_PORT% && set API_KEY=%API_KEY% && set WORKSPACE_PASSWORD=%WORKSPACE_PASSWORD% && set SESSION_SECRET=%SESSION_SECRET% && npx next dev -p %FRONTEND_PORT%"

echo.
echo Waiting for backend and frontend to come up (about 15-30s) ...
timeout /t 15 /nobreak >nul

echo.
echo STRATECH V1 RC-1 should now be running:
echo   Login:     http://localhost:%FRONTEND_PORT%/entrar   (password: %WORKSPACE_PASSWORD%)
echo   Dashboard: http://localhost:%FRONTEND_PORT%/dashboard
echo   Backend:   http://localhost:%BACKEND_PORT%/health
echo.
echo Next step (first run only): python demo\seed_demo_data.py
echo Stop: run stop.bat, or close the two opened windows.
endlocal
