# JARVIS v3.0 Server Launcher
# Run: .\launch_servers.ps1

$ErrorActionPreference = "Continue"

Write-Host "Starting JARVIS v3.0 servers..." -ForegroundColor Cyan

# Start backend
Write-Host "[1/2] Starting backend on port 8000..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location "C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next"
    & ".\venv\Scripts\python.exe" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
} -Name "JARVIS-Backend"

# Start frontend
Write-Host "[2/2] Starting frontend on port 3000..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location "C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next\web-next"
    .\node_modules\.bin\next.cmd dev --port 3000
} -Name "JARVIS-Frontend"

Write-Host "Waiting 8 seconds for servers to start..." -ForegroundColor Cyan
Start-Sleep 8

# Check if ports are listening
$backendRunning = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue) -ne $null
$frontendRunning = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue) -ne $null

Write-Host ""
Write-Host "=== Status ===" -ForegroundColor Cyan
Write-Host "Backend (8000): $(if($backendRunning){'[OK]'}else{'[FAIL]'})" -ForegroundColor $(if($backendRunning){'Green'}else{'Red'})
Write-Host "Frontend (3000): $(if($frontendRunning){'[OK]'}else{'[FAIL]'})" -ForegroundColor $(if($frontendRunning){'Green'}else{'Red'})
Write-Host ""

if ($frontendRunning) {
    Write-Host "Opening browser..." -ForegroundColor Cyan
    Start-Process "http://localhost:3000"
} else {
    Write-Host "WARNING: Frontend not ready. Check jobs with:" -ForegroundColor Yellow
    Write-Host "  Get-Job" -ForegroundColor Gray
    Write-Host "  Receive-Job -Name 'JARVIS-Frontend'" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Logs: Receive-Job -Name 'JARVIS-Backend' -Stream Output" -ForegroundColor Gray