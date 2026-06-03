@echo off
title JARVIS - Mobile App
color 0B

echo.
echo  ============================================
echo   JARVIS - Mobile App (React Native / Expo)
echo  ============================================
echo.

:: Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set MY_IP=%%a
    goto :found
)
:found
set MY_IP=%MY_IP: =%

:: Verificar que el backend este corriendo
echo  [1/2] Verificando Backend...
echo.
curl -s http://%MY_IP%:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] ADVERTENCIA: Backend NO esta corriendo en http://%MY_IP%:8000
    echo  [!] Ejecuta primero: iniciar-todo.bat
    echo.
    echo  [i] Presiona cualquier tecla para continuar de todos modos, o Ctrl+C para cancelar...
    pause >nul
    echo.
) else (
    echo  [OK] Backend esta corriendo en http://%MY_IP%:8000
    echo.
)

echo  [2/2] Iniciando Expo...
echo.
echo  ============================================
echo   Expo Dev Server
echo   IMPORTANTE: Tu telefono debe estar en el MISMO WiFi
echo   PC IP: %MY_IP%
echo  ============================================
echo.
echo  Si no puedes conectar por QR, presiona 't' para tunnel
echo  Presiona Ctrl+C para detener
echo  ============================================
echo.

cd /d "C:\Users\First\Documents\Python Projects\javis0.0\jarvis\mobile"
npx expo start

pause
