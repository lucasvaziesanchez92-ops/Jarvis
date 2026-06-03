@echo off
chcp 65001 >nul
echo ========================================
echo JARVIS Project - Full System Test
echo ========================================
echo.

echo [1/8] Testing Health Endpoints...
curl -s http://localhost:8000/api/v1/health | findstr "status"
echo.

echo [2/8] Testing LLM Status (Ollama Cloud)...
curl -s http://localhost:8000/api/v1/llm/status
echo.
echo.

echo [3/8] Testing LLM Providers...
curl -s http://localhost:8000/api/v1/llm/providers | findstr "is_configured"
echo.

echo [4/8] Testing Notes CRUD...
curl -s http://localhost:8000/api/v1/notes
echo.
echo.

echo [5/8] Testing Todos CRUD...
curl -s http://localhost:8000/api/v1/todos
echo.
echo.

echo [6/8] Testing TTS Voices...
curl -s http://localhost:8000/api/v1/tts/voices | findstr "voices"
echo.

echo [7/8] Testing STT Status...
curl -s http://localhost:8000/api/v1/stt/status
echo.
echo.

echo [8/8] Testing Chat Endpoint (Agent with Ollama Cloud)...
curl -s -X POST http://localhost:8000/api/v1/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Di tu nombre y que herramientas tienes disponibles\",\"session_id\":\"test-batch\",\"user_id\":\"batch\",\"persona\":\"default\"}"
echo.
echo.

echo ========================================
echo Tests Complete
echo ========================================
pause