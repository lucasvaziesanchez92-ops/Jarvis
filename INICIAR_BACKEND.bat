@echo off
:: JARVIS Backend Launcher — SIEMPRE usa el venv Python
cd /d "C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next"
color 0A
echo BACKEND INICIANDO...
echo Espera que diga 'Application startup complete'
echo.
.\venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8001 --reload
echo.
echo Backend cerrado. Presiona una tecla...
pause
