@echo off
title JARVIS AI Backend Server
echo ========================================================
echo         J.A.R.V.I.S. - Starting Backend Server
echo ========================================================
cd /d "%~dp0\.."

set PYTHONUTF8=1
set PYTHONPATH=.

if not exist "backend\venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Creating backend\venv...
    python -m venv backend\venv
    echo [*] Installing requirements...
    backend\venv\Scripts\pip install -r backend\requirements.txt
)

echo [*] Launching FastAPI backend on http://127.0.0.1:8000 ...
backend\venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
