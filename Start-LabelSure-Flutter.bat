@echo off
setlocal EnableExtensions DisableDelayedExpansion
title LabelSure - Flutter Project Launcher
cd /d "%~dp0"

echo.
echo   =======================================================
echo   LabelSure / Team APEX - Flutter Edition
echo   Legal Metrology Packaged Commodities Compliance AI
echo   =======================================================
echo.

if exist "C:\src\flutter\bin\flutter.bat" set "PATH=C:\src\flutter\bin;%PATH%"

where flutter.bat >nul 2>&1
if errorlevel 1 (
    where flutter >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Flutter SDK was not found on PATH.
        echo Please ensure Flutter is installed and added to your PATH.
        goto :failed
    )
)

if not exist "backend\requirements.txt" (
    echo ERROR: Keep this launcher in the LabelSure root directory.
    goto :failed
)

if not exist "backend\.venv\Scripts\python.exe" (
    if /i "%~1"=="--check" goto :setupneeded
    echo Creating the Python backend environment...
    python -m venv "backend\.venv"
    if errorlevel 1 goto :failed
)

if not exist "backend\.env" (
    if exist "backend\.env.example" copy "backend\.env.example" "backend\.env" >nul
)

"backend\.venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, psycopg, jwt, pwdlib, argon2, alembic" >nul 2>&1
if errorlevel 1 (
    if /i "%~1"=="--check" goto :setupneeded
    echo Installing backend dependencies...
    "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
    if errorlevel 1 goto :failed
)

if not exist "frontend_flutter\pubspec.yaml" (
    echo ERROR: frontend_flutter directory not found.
    goto :failed
)

if /i "%~1"=="--check" (
    echo Local dependencies are ready. No services were started.
    exit /b 0
)

rem Check port 8000 and port 5173
powershell.exe -NoProfile -Command "$busy = @(Get-NetTCPConnection -State Listen -LocalPort 8000,5173 -ErrorAction SilentlyContinue); if ($busy.Count) { Write-Host 'Ports already in use:' ($busy.LocalPort -join ', '); exit 1 }"
if errorlevel 1 (
    echo Close existing backend/frontend windows or free ports 8000 and 5173, then retry.
    goto :failed
)

echo Configuring backend database and applying migrations...
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
".venv\Scripts\python.exe" -m app.scripts.seed_users
popd

echo Starting LabelSure FastAPI backend on http://127.0.0.1:8000...
start "LabelSure - Backend (FastAPI)" /D "%~dp0backend" cmd.exe /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting LabelSure Flutter App on http://localhost:5173...
start "LabelSure - Flutter Web" /D "%~dp0frontend_flutter" cmd.exe /k "flutter run -d chrome --web-port 5173"

echo Waiting for FastAPI backend and Flutter web server...
powershell.exe -NoProfile -Command "$deadline = (Get-Date).AddSeconds(90); do { try { $api = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 2; if ($api.status -eq 'ok') { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo Backend did not become healthy within 90 seconds. Check the backend window.
    goto :failed
)

echo.
echo =======================================================
echo LabelSure Flutter is running!
echo   Frontend App: http://localhost:5173
echo   API Docs:     http://127.0.0.1:8000/docs
echo To stop: press 'q' or Ctrl+C in both command windows.
echo =======================================================
exit /b 0

:setupneeded
echo Local dependencies need setup. Double-click this file without --check.
exit /b 1

:failed
echo.
echo LabelSure Flutter launcher could not complete startup. See messages above.
if /i not "%~1"=="--check" pause
exit /b 1
