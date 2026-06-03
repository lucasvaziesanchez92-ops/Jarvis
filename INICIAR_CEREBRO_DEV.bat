@echo off
chcp 65001 > nul
title JARVIS NEURAL BRAIN - Solo Cerebro (Dev Mode)

echo ==========================================
echo    JARVIS NEURAL BRAIN - DEV MODE
echo ==========================================
echo.

:: Verificar path correcto
if not exist "web\vite.config.ts" (
    echo [X] ERROR: Ejecutar desde root del proyecto jarvis/
    pause
    exit /b 1
)

cd web

echo [*] Iniciando Vite Dev Server en puerto 3000...
echo [*] URL: http://localhost:3000/brain.html
echo.

:: Abrir Chrome directo al brain
start "" "http://localhost:3000/brain.html"

:: Iniciar dev server
npm run dev

echo.
echo [X] Servidor detenido.
pause
