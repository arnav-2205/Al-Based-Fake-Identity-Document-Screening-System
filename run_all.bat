@echo off
title SIH26188 Full Stack Launcher
echo ===================================================
echo   Starting SIH26188 Multi-Modal Document Screening
echo ===================================================

echo [1/4] Checking Docker Infrastructure (Optional)...
docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Docker detected. Starting Postgres, Redis, and MinIO...
    docker compose up -d postgres redis minio
) else (
    echo Docker is not running. Spring Boot will use embedded H2 database and local storage.
)

echo [2/4] Starting AI Service (Port 8000)...
start "SIH26188 - AI Service (Port 8000)" powershell -NoExit -Command "cd ai-service; $env:PYTHONPATH='..'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [3/4] Starting Spring Boot Backend (Port 8080)...
start "SIH26188 - Backend (Port 8080)" powershell -NoExit -Command "cd backend; if (Test-Path 'D:\SIHHH\jdk21_temp\jdk-21.0.6+7') { $env:JAVA_HOME='D:\SIHHH\jdk21_temp\jdk-21.0.6+7' }; .\mvnw.cmd spring-boot:run"

echo [4/4] Starting React Frontend (Port 5173)...
start "SIH26188 - Frontend (Port 5173)" powershell -NoExit -Command "cd frontend; npm run dev"

echo.
echo ===================================================
echo   All 3 services are launching in separate windows!
echo   Frontend:    http://localhost:5173
echo   Backend API: http://localhost:8080
echo   AI Service:  http://127.0.0.1:8000
echo ===================================================
pause
