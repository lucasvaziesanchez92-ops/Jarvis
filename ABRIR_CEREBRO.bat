@echo off
cd /d "C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next"

echo ==========================================
echo   JARVIS Brain Preview
echo ==========================================
echo.

echo Matando procesos anteriores en puerto 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do taskkill /PID %%a /F > nul 2>&1
timeout /t 1 /nobreak > nul

echo Iniciando servidor Python...
start /B python -m http.server 3000 --directory "web-next\public"

echo Esperando 2 segundos...
timeout /t 2 /nobreak > nul

echo Abriendo Chrome...
start chrome "http://localhost:3000/brain_preview.html"

echo.
echo Cerebro cargando en Chrome...
echo Si no ves nada, recarga con F5.
echo.
echo Presiona cualquier tecla para CERRAR el servidor...
pause > nul

echo Cerrando servidor...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do taskkill /PID %%a /F > nul 2>&1
echo Listo.
