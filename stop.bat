@echo off
REM STRATECH V1 RC-1 -- Windows stop: closes the backend/frontend windows
REM opened by start.bat, falling back to killing whatever is listening on
REM the configured ports (mirrors demo/stop-demo.sh's port-based fallback).
setlocal enabledelayedexpansion

if not defined BACKEND_PORT set BACKEND_PORT=8000
if not defined FRONTEND_PORT set FRONTEND_PORT=3000

echo Closing STRATECH RC-1 windows (if open) ...
taskkill /FI "WINDOWTITLE eq STRATECH RC-1 - Backend*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq STRATECH RC-1 - Frontend*" /T /F >nul 2>nul

echo Stopping any remaining process on port %BACKEND_PORT% ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>nul
)

echo Stopping any remaining process on port %FRONTEND_PORT% ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>nul
)

echo STRATECH V1 RC-1 stopped.
endlocal
