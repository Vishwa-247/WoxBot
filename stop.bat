@echo off
title WoxBot — Stopping Services
color 0C
echo ============================================================
echo              WoxBot — Stopping All Services
echo ============================================================
echo.

:: Kill backend (port 8000)
echo [1/2] Stopping Backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       Backend stopped.

:: Kill frontend (port 5173)
echo [2/2] Stopping Frontend (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       Frontend stopped.

:: Also kill any stray node/uvicorn processes with WoxBot titles
taskkill /FI "WINDOWTITLE eq WoxBot Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq WoxBot Frontend*" /F >nul 2>&1

echo.
echo ============================================================
echo              All WoxBot Services Stopped
echo ============================================================
echo.
pause
