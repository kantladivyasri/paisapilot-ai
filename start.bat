@echo off
setlocal

echo ========================================================
echo    Starting Nidhi Pilot AI (Backend + Frontend)
echo ========================================================
echo.

:: Start Backend in separate window
echo [1/2] Launching Backend on http://localhost:8000 ...
start "Nidhi Pilot Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Start Frontend in separate window
echo [2/2] Launching Frontend on http://localhost:5173 ...
start "Nidhi Pilot Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================================
echo   Services are starting!
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo ========================================================
echo.
timeout /t 5 >nul
start http://localhost:5173
