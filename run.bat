@echo off
REM DistriCache System Startup Script
REM =================================

setlocal enabledelayedexpansion

echo ========================================
echo DistriCache - Startup
echo ========================================

REM 1. Find Python
set "TARGET_PYTHON=%~dp0venv\python.exe"

if exist "!TARGET_PYTHON!" (
    echo [INFO] Found Virtual Environment: "!TARGET_PYTHON!"
    set "PYTHON_CMD=!TARGET_PYTHON!"
) else (
    echo [ERROR] Virtual environment not found at: "!TARGET_PYTHON!"
    echo [INFO] Falling back to system 'python'...
    set "PYTHON_CMD=python"
)

REM 2. Verify Python works
"!PYTHON_CMD!" --version >nul 2>&1
if errorlevel 1 (
    echo [FATAL] Python interpreter not working or not found.
    echo Command tried: "!PYTHON_CMD!"
    pause
    exit /b 1
)

echo [INFO] Using Python: "!PYTHON_CMD!"

REM 3. Configuration
set LB_PORT=8000
set LB_HOST=127.0.0.1
set NODE1_PORT=8001
set NODE2_PORT=8002
set NODE3_PORT=8003
set NODE_HOST=127.0.0.1
set CACHE_CAPACITY=100
set DB_PATH=cache_db.sqlite

REM Create logs directory
if not exist "logs" mkdir logs

REM 4. Start Services
echo.
echo [INFO] Starting Load Balancer...
start "DistriCache - Load Balancer" cmd /k "cd backend && "!PYTHON_CMD!" -m src.proxy.lb_api --port %LB_PORT% --host %LB_HOST% --db %DB_PATH%"

echo [INFO] Waiting for LB to initialize...
timeout /t 3 /nobreak >nul

echo.
echo [INFO] Starting Cache Nodes...
for %%P in (%NODE1_PORT% %NODE2_PORT% %NODE3_PORT%) do (
    echo   - Starting Node %%P...
    start "DistriCache - Node %%P" cmd /k "cd backend && "!PYTHON_CMD!" -m src.nodes.server --port %%P --host %NODE_HOST% --capacity %CACHE_CAPACITY%"
    timeout /t 1 /nobreak >nul
)

echo.
echo ========================================
echo System Started Successfully
echo ========================================
echo Load Balancer: http://%LB_HOST%:%LB_PORT%
echo.
pause
