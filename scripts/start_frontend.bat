@echo off
title JARVIS AI Frontend
echo ========================================================
echo         J.A.R.V.I.S. - Starting Frontend Terminal
echo ========================================================
cd /d "%~dp0\..\frontend"

if not exist "node_modules" (
    echo [*] Installing frontend npm packages...
    npm install
)

echo [*] Launching Vite development server on http://localhost:5173 ...
npm run dev
pause
