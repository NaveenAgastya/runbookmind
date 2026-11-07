@echo off
title RunbookMind Streamlit UI
cd /d "%~dp0"
set PYTHONPATH=%~dp0
"C:\ProgramData\anaconda3\python.exe" -m streamlit run frontend\app.py
pause
