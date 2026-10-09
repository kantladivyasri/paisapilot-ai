@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo    Nidhi Pilot AI - Automated Installation Script
echo ========================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
echo [OK] Python found.

:: 2. Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in your PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js found.

:: 3. Setup Backend Environment
echo.
echo [1/4] Setting up Python backend virtual environment...
cd backend
if not exist ".venv" (
    echo Creating virtual environment in backend\.venv...
    python -m venv .venv
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

echo [2/4] Installing backend dependencies (FastAPI, LangChain, Groq, SQLAlchemy)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Backend dependency installation failed.
    pause
    exit /b 1
)

:: Copy .env if not exists
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [INFO] Created backend\.env from template.
    )
)
cd ..

:: 4. Setup Frontend Environment
echo.
echo [3/4] Installing frontend dependencies (React, Vite, Tailwind CSS)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend npm install failed.
    pause
    exit /b 1
)
cd ..

echo.
echo [4/4] Verifying installation...
echo ========================================================
echo    Installation Complete!
echo ========================================================
echo.
echo To start Nidhi Pilot AI:
echo   - Double-click 'start.bat'
echo   OR
echo   - Run '.\start.ps1' in PowerShell
echo.
echo The app will be available at:
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo ========================================================
echo.
pause
