@echo off
chcp 65001 > nul
title JARVIS NEURAL BRAIN - Servidor Vite
echo ===========================================
echo    JARVIS NEURAL BRAIN LAUNCHER
echo    Cerebro 3D interactivo
echo ===========================================
echo.

:: Verificar que estamos en el root del proyecto
if not exist "web\vite.config.ts" (
    echo [X] ERROR: Este batch debe correrse desde:
    echo      C:\Users\First\Documents\Python Projects\javis0.0\jarvis\
    echo      Actual: %CD%
    pause
    exit /b 1
)

cd web

:: Build si no existe
if not exist "dist\brain.html" (
    echo [!] dist/ no encontrado. Compilando...
    call npm run build
    if %errorlevel% neq 0 (
        echo [X] Error de compilacion.
        pause
        exit /b 1
    )
)

echo [OK] Build listo.
echo.
echo ===========================================
echo    URLs
echo ===========================================
echo.
echo    Solo Cerebro:
echo      http://localhost:8765/brain.html
echo.
echo    App completa:
echo      http://localhost:8765/index.html
echo.

:: Abrir navegador
start "" "http://localhost:8765/brain.html"

:: Iniciar Vite preview (servidor profesional para ES modules)
echo [*] Iniciando servidor Vite en puerto 8765...
echo [*] Presiona Ctrl+C para detener.
echo.
npx vite preview --port 8765 --host --base /

echo.
:: Volver al root por si hay comandos posteriores
cd ..
pause
