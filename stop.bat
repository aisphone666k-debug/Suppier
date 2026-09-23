@echo off
chcp 65001 >nul
title Suppier - Stop Services

echo ===================================================
echo           STOPPING SUPPIER SERVICES
echo ===================================================
echo.

echo กำลังปิด Process ที่รันอยู่บน Port 5000 (Backend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo กำลังปิด Process ที่รันอยู่บน Port 4200 (Frontend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4200 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ปิดเซอร์วิสทั้งหมดเรียบร้อยแล้ว!
timeout /t 3 >nul
