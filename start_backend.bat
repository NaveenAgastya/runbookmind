@echo off
title RunbookMind Backend API
cd /d "%~dp0"
set PYTHONPATH=%~dp0
"C:\ProgramData\anaconda3\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
