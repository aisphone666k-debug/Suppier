@echo off
chcp 65001 >nul
title Suppier - Stop Services

echo ===================================================
echo           STOPPING SUPPIER SERVICES
echo ===================================================
echo.

echo Stopping Port 5000 (Backend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Port 8000 (AI Quotation)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Port 4200 (Frontend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4200 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All services stopped successfully!
ping 127.0.0.1 -n 4 >nul
