@echo off
chcp 65001 >nul
title Suppier Launcher

echo ===================================================
echo           SUPPIER SYSTEM LAUNCHER
echo ===================================================
echo.

:: 1. รัน Backend API ในหน้าต่างใหม่
echo [1/4] Starting Backend API (Port 5000)...
start "Suppier - Backend (Port 5000)" /D "%~dp0backend" cmd /k npm start

:: 2. รัน AI Quotation Search Microservice ในหน้าต่างใหม่
echo [2/4] Starting AI Quotation Search Microservice (Port 8000)...
start "Suppier - AI Quotation (Port 8000)" /D "%~dp0ai_quotation" cmd /k .venv\Scripts\python.exe main.py

:: 3. รัน Frontend Angular ในหน้าต่างใหม่
echo [3/4] Starting Frontend Angular (Port 4200)...
start "Suppier - Frontend (Port 4200)" /D "%~dp0" cmd /k npm start

:: 4. หน่วงเวลาเพื่อให้ทุกระบบเริ่มทำงาน (6 วินาที)
echo [4/4] Waiting for services to initialize...
ping 127.0.0.1 -n 7 >nul

:: 5. เปิด Microsoft Edge ไปยังหน้าเว็บ
echo Opening Microsoft Edge (http://localhost:4200)...
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" http://localhost:4200
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" http://localhost:4200
) else (
    start msedge http://localhost:4200
)

echo.
echo ===================================================
echo   System is ready!
echo   - Backend API:       http://localhost:5000
echo   - AI Quotation Search: http://localhost:8000
echo   - Frontend:          http://localhost:4200
echo ===================================================
ping 127.0.0.1 -n 4 >nul
