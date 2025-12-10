@echo off
echo ========================================
echo   OLLAMA UI - QUICK START SCRIPT
echo ========================================
echo.

echo Checking if Ollama is running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Ollama is not running!
    echo Please start Ollama first or install it from https://ollama.ai
    echo.
    pause
    exit /b 1
)
echo ✓ Ollama is running
echo.

echo Starting Backend Server...
start "Ollama Backend" cmd /k "python backend.py"
timeout /t 3 /nobreak >nul

echo Starting Streamlit UI...
start "Ollama UI" cmd /k "streamlit run app_unified.py"

echo.
echo ========================================
echo   APPLICATION STARTED!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:8501
echo.
echo Two new windows have opened:
echo 1. Backend Server (FastAPI)
echo 2. Streamlit UI (Frontend)
echo.
echo Your browser should open automatically.
echo Press Ctrl+C in each window to stop.
echo.
pause
