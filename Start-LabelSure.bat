@echo off
setlocal EnableExtensions DisableDelayedExpansion
title LabelSure - Project Launcher
cd /d "%~dp0"

echo.
echo   LabelSure / Team APEX
echo   Starting the web application and API
echo.

where node.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is missing. Install Node.js 22.12 or newer first.
    goto :failed
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm.cmd was not found on PATH.
    goto :failed
)
if not exist "backend\requirements.txt" (
    echo ERROR: Keep this launcher in the LabelSure project folder.
    goto :failed
)

if not exist "backend\.venv\Scripts\python.exe" (
    if /i "%~1"=="--check" goto :setupneeded
    echo Creating the Python environment...
    python -m venv "backend\.venv"
    if errorlevel 1 goto :failed
)
"backend\.venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, psycopg, jwt, pwdlib, argon2, alembic" >nul 2>&1
if errorlevel 1 (
    if /i "%~1"=="--check" goto :setupneeded
    echo Installing backend dependencies...
    "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
    if errorlevel 1 goto :failed
)
if not exist "frontend\node_modules\vite\bin\vite.js" (
    if /i "%~1"=="--check" goto :setupneeded
    echo Installing frontend dependencies...
    pushd "frontend"
    call npm.cmd ci
    if errorlevel 1 (
        popd
        goto :failed
    )
    popd
)

if /i "%~1"=="--check" (
    echo Local dependencies are ready. No services were started.
    exit /b 0
)

rem Check both ports before starting either service. Never stop unrelated processes.
powershell.exe -NoProfile -Command "$busy = @(Get-NetTCPConnection -State Listen -LocalPort 8000,5173 -ErrorAction SilentlyContinue); if ($busy.Count) { Write-Host 'Ports already in use:' ($busy.LocalPort -join ', '); exit 1 }"
if errorlevel 1 (
    echo Close existing backend/frontend windows or free ports 8000 and 5173, then retry.
    goto :failed
)

echo Opening backend and frontend log windows...
pushd "backend"
".venv\Scripts\python.exe" -m app.scripts.configure_local
if errorlevel 1 (
    popd
    goto :failed
)
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    popd
    goto :failed
)
popd
start "LabelSure - Backend" /D "%~dp0backend" cmd.exe /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "LabelSure - Frontend" /D "%~dp0frontend" cmd.exe /k "npm.cmd run dev -- --port 5173 --strictPort"

echo Waiting for the API database check and web server...
powershell.exe -NoProfile -Command "$deadline = (Get-Date).AddSeconds(60); do { try { $api = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 2; $web = Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2; if ($api.status -eq 'ok' -and $web.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo.
    echo Startup did not become healthy within 60 seconds.
    echo Check the backend and frontend windows for errors.
    echo If you configured PostgreSQL, make sure that database is running.
    goto :failed
)

echo.
echo LabelSure is ready: http://localhost:5173
echo API documentation: http://127.0.0.1:8000/docs
echo To stop: press Ctrl+C in BOTH service windows, then close them.
start "" "http://localhost:5173"
exit /b 0

:setupneeded
echo Local dependencies need setup. Double-click this file without --check.
exit /b 1

:failed
echo.
echo LabelSure could not complete startup. See the message above.
if /i not "%~1"=="--check" pause
exit /b 1
