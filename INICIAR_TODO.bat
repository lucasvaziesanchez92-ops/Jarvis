@echo off
setlocal enabledelayedexpansion

call :Main
pause
exit /b

:Main
title JARVIS Launcher
color 0E

echo ==========================================
echo    JARVIS NEURAL INTERFACE
echo ==========================================
echo.

echo [1/4] Limpiando procesos viejos...
taskkill /F /FI "WINDOWTITLE eq JARVIS BACKEND" >NUL 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS FRONTEND" >NUL 2>&1
timeout /t 2 /nobreak >NUL
echo      OK

echo.
echo [2/4] Iniciando BACKEND en puerto 8001...
start "JARVIS BACKEND" cmd /c "cd /d C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next && venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8001 --reload"
echo      Esperando que arranque...
timeout /t 20 /nobreak >NUL

echo.
echo [3/4] Iniciando FRONTEND en puerto 3010...
start "JARVIS FRONTEND" cmd /c "cd /d C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next\web-next && set API_URL=http://127.0.0.1:8001 && npm run dev -- --port 3010"
echo      Esperando que arranque...
timeout /t 15 /nobreak >NUL

echo.
echo [4/4] Abriendo navegador...
start "" http://localhost:3010

echo.
echo ==========================================
echo    JARVIS LISTO
echo    Frontend : http://localhost:3010
echo    Backend  : http://localhost:8010
echo ==========================================
exit /b
