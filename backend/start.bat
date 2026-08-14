@echo off
setlocal enabledelayedexpansion

cd /d %~dp0

set PORT=8000
set MIGRATE=1
set PORT_SET=0

:loop
if "%~1"=="" goto done
if "%~1"=="--no-migrate" (
    set MIGRATE=0
    shift
    goto loop
)
if "%~1"=="--port" (
    set PORT=%~2
    shift
    shift
    goto loop
)
shift
goto loop
:done

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual env not found. Run: .venv\Scripts\pip install -e .
    pause
    exit /b 1
)

if "%MIGRATE%"=="1" (
    echo [START] Running database migration...
    .venv\Scripts\alembic.exe upgrade head
    if errorlevel 1 (
        echo [ERROR] Migration failed
        pause
        exit /b %errorlevel%
    )
    echo [START] Migration done
)

echo [START] VulnScope API: http://127.0.0.1:%PORT%
echo [START] Swagger docs: http://127.0.0.1:%PORT%/docs
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port %PORT% --reload

pause