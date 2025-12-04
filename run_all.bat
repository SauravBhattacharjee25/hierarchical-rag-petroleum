@echo off
title GeoHackathon 2025 - Team Conquerers Solution
color 0A

echo ========================================================
echo      GeoHackathon 2025 - Team Conquerers Solution
echo ========================================================
echo.
echo [1/3] Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b
)

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some dependencies might have failed to install.
    echo Trying to continue...
)

echo.
echo [3/3] Starting RAG System...
echo.
echo --------------------------------------------------------
echo  OPEN YOUR BROWSER TO: http://localhost:5000
echo --------------------------------------------------------
echo.

python run.py

pause
