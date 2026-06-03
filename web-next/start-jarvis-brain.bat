@echo off
title JARVIS Brain Interface

echo.
echo  ██████╗ ██╗   ██╗███████╗███████╗███████╗
echo  ██╔══██╗██║   ██║╚════██║╚════██║██╔════╝
echo  ██║  ██║██║   ██║    ██╔╝    ██╔╝███████╗
echo  ██║  ██║██║   ██║   ██╔╝     ██╔╝ ╚════██║
echo  ██████╔╝╚██████╔╝   ██║      ██║  ███████║
echo  ╚═════╝  ╚═════╝    ╚═╝      ╚═╝  ╚══════╝
echo.

echo Cleaning up existing processes...
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 >nul

cd /d "%~dp0"

echo Building production version...
call npm run build
if errorlevel 1 (
    echo BUILD FAILED - Press any key to exit
    pause >nul
    exit /b 1
)

echo.
echo Starting server...
start http://localhost:3000/brain
call npm run start

pause