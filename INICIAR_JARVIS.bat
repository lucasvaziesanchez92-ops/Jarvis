@echo off
cd /d "%~dp0"
title JARVIS Launcher v3.0
cls

echo.
echo  ========================================
echo   JARVIS NEURAL INTERFACE v3.0
echo   Clean start: backend + frontend...
echo  ========================================
echo.

REM Kill any existing node/python on these ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " 2^>nul') do taskkill /F /PID %%a > nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " 2^>nul') do taskkill /F /PID %%a > nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1234 " 2^>nul') do taskkill /F /PID %%a > nul 2>&1

timeout /t 2 > nul

REM Clean Next.js cache to ensure fresh build
echo [*] Cleaning Next.js cache...
cd web-next
if exist .next rmdir /s /q .next 2>nul
cd ..

REM Activate venv
if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat

REM Start backend in new window
echo [1/3] Starting backend on port 8000...
start "JARVIS Backend" cmd /k "cd /d %~dp0&python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 5 > nul

REM Start frontend in new window
echo [2/3] Starting frontend (clean build) on port 3000...
start "JARVIS Frontend" cmd /k "cd /d %~dp0web-next&npm run dev"

timeout /t 10 > nul

echo [3/3] Opening browser...
start http://localhost:3000

echo.
echo  ========================================
echo   READY:
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:3000
echo   - API Docs: http://localhost:8000/api/v1/docs
echo  ========================================
echo.
pause