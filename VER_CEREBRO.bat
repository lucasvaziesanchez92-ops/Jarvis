@echo off
chcp 65001 > nul
title JARVIS — Cerebro 3D

cd /d "%~dp0web-next"

echo.
echo ═══════════════════════════════════════════════
echo   JARVIS — Cerebro 3D
echo   Cargando modelo anatomico...
echo ═══════════════════════════════════════════════
echo.

start http://localhost:3000/brain
npm run dev -- -p 3000

pause
