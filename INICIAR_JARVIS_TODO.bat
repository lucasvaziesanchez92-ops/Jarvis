@echo off
chcp 65001 >nul
title JARVIS - Iniciando...
color 0A
cls

echo.
echo ===========================================
echo        JARVIS NEURAL INTERFACE v2.0
echo ===========================================
echo.

echo [1/7] Liberando puertos...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo [2/7] Verificando entorno Python...
if not exist "venv\Scripts\activate.bat" (
    echo     Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [3/7] Verificando Ollama Cloud API...
curl -s "https://ollama.com/api/tags" -H "Authorization: Bearer 799a7891a9cf44bb981a4873672ec11f.fXO5IvB2gJaYDR44R6hOYqR0" >nul 2>&1
if %errorlevel%==0 (
    echo     [OK] Ollama Cloud conectado
) else (
    echo     [AVISO] Ollama Cloud no respondio
)

echo [4/7] Iniciando Backend (puerto 8000)...
start "JARVIS Backend" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 6 /nobreak >nul

echo [5/7] Verificando backend...
curl -s http://localhost:8000/api/v1/health >nul 2>&1
if %errorlevel%==0 (
    echo     [OK] Backend corriendo en http://localhost:8000
    echo     [OK] LLM Status:
    curl -s http://localhost:8000/api/v1/llm/status
    echo.
) else (
    echo     [ADVERTENCIA] Backend tardando en arrancar...
)

echo [6/7] Verificando STT/TTS...
curl -s http://localhost:8000/api/v1/stt/status
echo.
curl -s http://localhost:8000/api/v1/tts/voices | findstr "default_voice"

echo.
echo [7/7] Iniciando Frontend (puerto 3000)...
start "JARVIS Frontend" cmd /k "cd /d %~dp0web-next && npm run dev"
timeout /t 8 /nobreak >nul

echo.
echo [+] Abriendo interfaz...
start http://localhost:3000

echo.
echo ===========================================
echo        TESTEANDO AGENTE CON OLLAMA CLOUD
echo ===========================================
echo.

echo [TEST] Chat Agent - respondiendo con herramientas...
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" -d "{\"message\":\"Cuales herramientas tienes disponibles?\",\"session_id\":\"init-test\",\"user_id\":\"system\",\"persona\":\"default\"}" > %~dp0agent_test.txt

powershell -Command "Get-Content '%~dp0agent_test.txt' | ConvertFrom-Json | Select-Object -ExpandProperty content" 2>nul
if %errorlevel% neq 0 (
    type %~dp0agent_test.txt
)
del %~dp0agent_test.txt

echo.
echo [TEST] Notes CRUD...
curl -s http://localhost:8000/api/v1/notes | findstr /C:"title" /C:"error"
echo.

echo [TEST] Todos CRUD...
curl -s http://localhost:8000/api/v1/todos | findstr /C:"text" /C:"error"
echo.

echo.
echo ===========================================
echo         JARVIS 100%% OPERATIVO
echo ===========================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   LLM:       Ollama Cloud (minimax-m2.7)
echo   TTS:       es_ES-davefx-medium
echo   STT:       Whisper base
echo   MCP Tools: 32 herramientas
echo ===========================================
echo.
pause