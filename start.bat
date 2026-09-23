@echo off
chcp 65001 >nul
title Suppier Launcher

echo ===================================================
echo           SUPPIER SYSTEM LAUNCHER
echo ===================================================
echo.

:: 1. รัน Backend ในหน้าต่างใหม่
echo [1/3] กำลังเริ่ม Backend API (Port 5000)...
start "Suppier - Backend (Port 5000)" /D "%~dp0backend" cmd /k npm start

:: 2. รัน Frontend ในหน้าต่างใหม่
echo [2/3] กำลังเริ่ม Frontend Angular (Port 4200)...
start "Suppier - Frontend (Port 4200)" /D "%~dp0" cmd /k npm start

:: 3. หน่วงเวลาเพื่อรอให้ Angular และ Express เริ่มทำงาน
echo [3/3] กำลังรอระบบเตรียมความพร้อม (ประมาณ 6 วินาที)...
timeout /t 6 /nobreak >nul

:: 4. เปิด Microsoft Edge ไปที่ Frontend
echo กำลังเปิดระบบบน Microsoft Edge (http://localhost:4200)...
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" http://localhost:4200
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" http://localhost:4200
) else (
    start msedge http://localhost:4200
)

echo.
echo ===================================================
echo   ระบบเริ่มทำงานเรียบร้อยแล้ว!
echo   - Backend:  http://localhost:5000
echo   - Frontend: http://localhost:4200
echo ===================================================
timeout /t 3 >nul
