@echo off
REM DistriCache - Test Runner Script for Windows
REM Runs all unit tests and integration tests

setlocal enabledelayedexpansion

echo ========================================
echo DistriCache - Test Suite
echo ========================================
echo.

REM Set PYTHONPATH to include current directory
set PYTHONPATH=%CD%

REM Check if pytest is installed
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo Installing pytest...
    pip install pytest pytest-asyncio
)

echo Running Unit Tests...
echo.

echo Test Suite 1: LRU Cache
python -m pytest backend\tests\test_lru_cache.py -v
if errorlevel 1 goto error

echo.
echo Test Suite 2: Consistent Hash Ring
python -m pytest backend\tests\test_consistent_hash.py -v
if errorlevel 1 goto error

echo.
echo Test Suite 3: Database Manager
python -m pytest backend\tests\test_database.py -v
if errorlevel 1 goto error

echo.
echo Test Suite 4: Cache Node Server
python -m pytest backend\tests\test_cache_node_server.py -v
if errorlevel 1 goto error

echo.
echo =====================================
echo All Tests Completed!
echo =====================================
exit /b 0

:error
echo.
echo =====================================
echo Test Failed!
echo =====================================
exit /b 1
