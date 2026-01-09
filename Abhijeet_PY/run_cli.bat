@echo off
title GeoHackathon 2025 - Judge CLI
color 0E

cls
echo ========================================================
echo   HIERARCHICAL RAG SYSTEM - JUDGE CLI LAUNCHER
echo ========================================================
echo.
echo [1/2] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

echo.
echo [2/2] Launching CLI...
echo.
echo --------------------------------------------------------
echo  Type your query and press Enter.
echo  Type 'q' to quit.
echo --------------------------------------------------------
echo.

python query_cli.py
pause
