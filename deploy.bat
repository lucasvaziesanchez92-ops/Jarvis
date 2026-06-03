@echo off
chcp 65001 > nul
echo ═══════════════════════════════════════════════════════════════
echo   JARVIS — Deploy Script (Windows)
echo ═══════════════════════════════════════════════════════════════
echo.

:: Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo [INFO] Copy .env.production to .env and fill in your values.
    exit /b 1
)

:: Check Docker
where docker > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    exit /b 1
)

where docker-compose > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] docker-compose not found.
    exit /b 1
)

echo [1/4] Pulling latest images...
docker-compose pull

echo.
echo [2/4] Building containers...
docker-compose build --no-cache

echo.
echo [3/4] Starting services...
docker-compose up -d

echo.
echo [4/4] Waiting for backend to be ready...
timeout /t 5 /nobreak > nul

:: Health check
curl -s http://localhost:8000/api/v1/health/live > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend is healthy at http://localhost:8000
) else (
    echo [WARN] Backend not responding yet. It may need a few more seconds.
)

curl -s http://localhost:3000 > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Frontend is up at http://localhost:3000
) else (
    echo [WARN] Frontend not responding yet.
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo   JARVIS is running!
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/api/v1/docs
echo ═══════════════════════════════════════════════════════════════
echo.
echo Commands:
echo   docker-compose logs -f backend   # View backend logs
echo   docker-compose logs -f frontend  # View frontend logs
echo   docker-compose down               # Stop everything
echo.
pause
