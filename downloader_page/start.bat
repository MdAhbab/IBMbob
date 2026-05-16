@echo off
echo ============================================
echo AI CLI Orchestrator - Downloader Page
echo ============================================
echo.
echo Starting Frontend and Backend...
echo.
echo Frontend will run at: http://localhost:5173
echo Backend will run at: http://localhost:8000
echo.
echo Press Ctrl+C to stop both servers
echo ============================================
echo.

start "Frontend (Vite)" cmd /k "npm run dev"
timeout /t 2 /nobreak >nul
start "Backend (FastAPI)" cmd /k "cd backend && python run.py"

echo.
echo Both servers are starting in separate windows...
echo Close this window or press any key to exit
pause >nul

@REM Made with Bob
