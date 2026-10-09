# ========================================================
#    Nidhi Pilot AI - PowerShell Automated Installer
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Nidhi Pilot AI - Automated Installation Script" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python detected: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/"
    Exit 1
}

# 2. Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[OK] Node.js detected: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/"
    Exit 1
}

# 3. Setup Backend Environment
Write-Host ""
Write-Host "[1/4] Setting up Python backend virtual environment..." -ForegroundColor Yellow
$backendDir = Join-Path $PSScriptRoot "backend"
$venvDir = Join-Path $backendDir ".venv"

if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment in backend/.venv..." -ForegroundColor Gray
    python -m venv $venvDir
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"
$reqFile = Join-Path $backendDir "requirements.txt"

Write-Host "[2/4] Installing backend dependencies (FastAPI, LangChain, Groq, SQLAlchemy)..." -ForegroundColor Yellow
& $venvPip install -r $reqFile

$envFile = Join-Path $backendDir ".env"
$envExample = Join-Path $backendDir ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "[INFO] Created backend/.env from template." -ForegroundColor Gray
}

# 4. Setup Frontend Environment
Write-Host ""
Write-Host "[3/4] Installing frontend dependencies (React, Vite, Tailwind CSS)..." -ForegroundColor Yellow
$frontendDir = Join-Path $PSScriptRoot "frontend"
Push-Location $frontendDir
npm install
Pop-Location

Write-Host ""
Write-Host "[4/4] Verifying installation..." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Installation Complete Successfully!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start Nidhi Pilot AI, run:" -ForegroundColor Cyan
Write-Host "  .\start.ps1" -ForegroundColor White
Write-Host "or double-click 'start.bat'" -ForegroundColor White
Write-Host ""
Write-Host "The app will run at:" -ForegroundColor Cyan
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor White
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs : http://localhost:8000/docs" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
