@echo off
REM Start a single DistriCache Node
REM Usage: start_node.bat [PORT]
REM Example: start_node.bat 8004

setlocal

if "%1"=="" (
    echo Usage: start_node.bat [PORT]
    echo Example: start_node.bat 8004
    exit /b 1
)

set PORT=%1
set HOST=127.0.0.1
set CAPACITY=100

echo Starting Cache Node on port %PORT%...
cd backend
python -m src.nodes.server --port %PORT% --host %HOST% --capacity %CAPACITY%
