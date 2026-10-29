@echo off
title Launch JARVIS AI Assistant
echo ========================================================
echo         J.A.R.V.I.S. - Launching Full System
echo ========================================================
cd /d "%~dp0\.."

echo [*] Starting Backend API in background window...
start "JARVIS Backend (Port 8000)" cmd /k "scripts\start_backend.bat"

ping 127.0.0.1 -n 3 >nul

echo [*] Starting Frontend UI in background window...
start "JARVIS Frontend (Port 5173)" cmd /k "scripts\start_frontend.bat"

ping 127.0.0.1 -n 4 >nul

echo [*] Launching browser to http://localhost:5173 ...
start http://localhost:5173

echo ========================================================
echo   J.A.R.V.I.S. is now running!
echo   Frontend: http://localhost:5173
echo   Backend:  http://127.0.0.1:8000
echo ========================================================
