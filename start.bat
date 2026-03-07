@echo off
title WoxBot — Starting Services
color 0A
echo ============================================================
echo              WoxBot — Starting All Services
echo ============================================================
echo.

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Python virtual environment not found at venv\
    echo         Run: python -m venv venv
    pause
    exit /b 1
)

:: Check if node_modules exist
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo [1/2] Starting Backend (FastAPI on port 8000)...
start "WoxBot-Backend" cmd /k "title WoxBot Backend [Port 8000] && call venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend (Vite on port 5173)...
start "WoxBot-Frontend" cmd /k "title WoxBot Frontend [Port 5173] && cd frontend && npm run dev"

:: Wait for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo              WoxBot Services Started!
echo ============================================================
echo.
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:5173
echo   API Docs : http://localhost:8000/docs
echo.
echo   Use stop.bat to shut down all services.
echo ============================================================
echo.
pause
