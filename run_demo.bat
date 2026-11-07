@echo off
title RunbookMind Launcher
cd /d "%~dp0"
set PYTHONPATH=%~dp0

echo ========================================================
echo       Starting RunbookMind: AI Incident Response
echo ========================================================
echo.
echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "RunbookMind Backend" cmd /k ""C:\ProgramData\anaconda3\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

echo [2/2] Waiting for Backend to bind port...
timeout /t 3 /nobreak > nul

echo [3/3] Launching Streamlit UI on http://localhost:8501 ...
start "RunbookMind UI" cmd /k ""C:\ProgramData\anaconda3\python.exe" -m streamlit run frontend\app.py"

echo.
echo ========================================================
echo  All services launched!
echo  Web UI:   http://localhost:8501
echo  API Docs: http://localhost:8000/docs
echo ========================================================
