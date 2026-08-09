@echo off
REM ==============================================================================
REM Enterprise AI OCR & BI Stack - 100% Non-Docker Native Launcher (Windows VM)
REM ==============================================================================

echo 🚀 Starting all 4 Enterprise Stack services natively on Windows without Docker...

echo 📦 [1/4] Starting PaddleOCR Service on Port 8080...
start "PaddleOCR Service (8080)" cmd /k "cd paddleocr && pip install -r requirements.txt && python -m uvicorn app:app --host 0.0.0.0 --port 8080"

echo 📦 [2/4] Starting SQL MCP Server on Port 3001...
start "SQL MCP Server (3001)" cmd /k "cd sql-mcp-server && npm install && npm run build && node dist/server.js"

echo 📦 [3/4] Starting Enterprise AI Proxy on Port 8000...
start "Enterprise AI Proxy (8000)" cmd /k "cd proxy && pip install -r requirements.txt && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo 📦 [4/4] Starting n8n Workflow Engine on Port 5678...
start "n8n Workflow Engine (5678)" cmd /k "npx n8n start --port 5678 --host 0.0.0.0"

echo ==============================================================================
echo ✅ All 4 services opened in separate command windows without Docker!
echo   - PaddleOCR Service: http://localhost:8080/health
echo   - SQL MCP Server:    http://localhost:3001/health
echo   - AI Proxy:          http://localhost:8000/health
echo   - n8n Dashboard:     http://localhost:5678
echo ==============================================================================
pause
