# ========================================================
#    Nidhi Pilot AI - PowerShell Runner
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Starting Nidhi Pilot AI (Backend + Frontend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "[1/2] Launching Backend on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backendDir'; .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "[2/2] Launching Frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontendDir'; npm run dev"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Both services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "   Frontend : http://localhost:5173" -ForegroundColor White
Write-Host "   Backend  : http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs : http://localhost:8000/docs" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Green

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
