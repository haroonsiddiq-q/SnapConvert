@echo off
cd /d "%~dp0"

REM Start the FastAPI server in the background
start "SnapConvert Server" /min uv run uvicorn snapconvert.main:app --host 127.0.0.1 --port 8000

REM Give it a couple seconds to boot before opening the browser
timeout /t 3 /nobreak >nul

start http://127.0.0.1:8000
