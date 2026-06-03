@echo off
chcp 65001 > nul
title JARVIS MOBILE - Neural Brain WebView
echo ===========================================
echo    JARVIS MOBILE LAUNCHER
echo    Expo + WebView Neural Brain
echo ===========================================
echo.

:: Verificar path
if not exist "mobile\package.json" (
    echo [X] ERROR: Ejecutar desde root del proyecto jarvis/
    echo      Actual: %CD%
    pause
    exit /b 1
)

:: Verificar que backend esta corriendo
echo [*] Verificando backend en localhost:8000...
curl -s http://localhost:8000/api/v1/health > nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Backend NO detectado en puerto 8000.
    echo [*] Levantando backend primero...
    start "JARVIS BACKEND" INICIAR_BACKEND.bat
    echo [*] Esperando 5 segundos para que el backend arranque...
    timeout /t 5 /nobreak > nul
) else (
    echo [OK] Backend detectado en localhost:8000.
)

echo.
echo [*] Iniciando Expo...
echo [*] Escanea el QR con Expo Go (Android/iOS)
echo [*] O presiona 'a' para abrir en emulador Android
echo [*] O presiona 'i' para abrir en simulador iOS
echo.

cd mobile
npx expo start

echo.
echo [*] Expo detenido.
pause
