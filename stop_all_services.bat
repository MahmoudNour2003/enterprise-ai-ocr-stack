@echo off
REM ==============================================================================
REM Enterprise AI OCR & BI Stack - Stop All Services Script (Windows VM)
REM ==============================================================================

echo 🛑 Stopping all 4 Enterprise Stack services on Windows...

REM Kill processes running on ports 8080, 8000, 3001, 5678
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3001"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5678"') do taskkill /f /pid %%a 2>nul

echo ✅ All Enterprise Stack services stopped successfully!
pause
