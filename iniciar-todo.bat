@echo off
title JARVIS - Iniciar Todo
color 0A

echo.
echo  ============================================
echo   JARVIS - Agente Personal Autonomo
echo  ============================================
echo.

:: Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set MY_IP=%%a
    goto :found
)
:found
set MY_IP=%MY_IP: =%
echo  Tu IP de red: %MY_IP%
echo  (Tu telefono y PC deben estar en el mismo WiFi)
echo.

echo  [1/3] Verificando LM Studio...
echo.

:: Verificar si LM Studio esta corriendo
curl -s http://127.0.0.1:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] ADVERTENCIA: LM Studio NO esta corriendo en http://127.0.0.1:1234
    echo  [!] Asegurate de:
    echo      1. Abrir LM Studio
    echo      2. Cargar un modelo
    echo      3. Click en "Start Server" (puerto 1234)
    echo.
    echo  [i] Presiona cualquier tecla para continuar de todos modos, o Ctrl+C para cancelar...
    pause >nul
    echo.
) else (
    echo  [OK] LM Studio esta respondiendo en http://127.0.0.1:1234
    echo.
)

echo  [2/3] Configurando entorno...
echo.

:: Actualizar .env con la IP correcta para que el telefono pueda conectar
set ENV_FILE=C:\Users\First\Documents\Python Projects\javis0.0\jarvis\.env

(
echo # JARVIS Environment
echo LLM_PROVIDER=lm_studio
echo LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
echo API_HOST=0.0.0.0
echo API_PORT=8000
echo CORS_ORIGINS=["*"]
echo DATA_DIR=data
echo MAX_CONTEXT_MESSAGES=50
echo ENABLE_LANGSMITH=false
echo TAVILY_API_KEY=
echo GMAIL_CREDENTIALS_FILE=
echo GMAIL_TOKEN_FILE=
echo GCAL_TOKEN_FILE=
) > "%ENV_FILE%"

:: Update mobile .env with PC IP
set MOBILE_ENV=C:\Users\First\Documents\Python Projects\javis0.0\jarvis\mobile\.env
(
echo # JARVIS Mobile - Environment
echo EXPO_PUBLIC_API_URL=http://%MY_IP%:8000
) > "%MOBILE_ENV%"

echo  [OK] Backend configurado: http://0.0.0.0:8000
echo  [OK] Mobile configurado: http://%MY_IP%:8000
echo.

:: Verificar que existe la carpeta data
if not exist "C:\Users\First\Documents\Python Projects\javis0.0\jarvis\data" (
    mkdir "C:\Users\First\Documents\Python Projects\javis0.0\jarvis\data"
)

echo  [3/3] Iniciando Backend...
echo.
echo  ============================================
echo   Backend: http://%MY_IP%:8000
echo   LLM:     http://127.0.0.1:1234 (LM Studio)
echo  ============================================
echo.
echo  Endpoints disponibles:
echo    GET  /health
echo    POST /agent/run        ^<-- Mobile app
echo    POST /chat
echo    WS   /ws/chat
echo    CRUD /notes
echo    CRUD /todos
echo    CRUD /calendar
echo    CRUD /emails
echo.
echo  Presiona Ctrl+C para detener el servidor
echo  ============================================
echo.

cd /d "C:\Users\First\Documents\Python Projects\javis0.0\jarvis"
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

pause
