#!/usr/bin/env bash
# ==============================================================================
# Enterprise AI OCR & BI Stack - 100% Non-Docker Native Launcher (Linux VM)
# ==============================================================================

echo "🚀 Starting all 4 Enterprise Stack services natively without Docker..."

# 1. Stop all existing running service instances cleanly
chmod +x ./stop_all_services.sh 2>/dev/null || true
./stop_all_services.sh 2>/dev/null || true

# Fix n8n encryption key mismatch error if cached config exists
rm -f ~/.n8n/config || true
rm -f /teamspace/studios/this_studio/.n8n/config || true

# 2. Start Service 1: PaddleOCR GPU Service (Port 8080)
echo "📦 [1/4] Starting PaddleOCR GPU Service on Port 8080..."
cd paddleocr
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080 > ../paddleocr.log 2>&1 &
cd ..

# 3. Start Service 2: SQL MCP Server (Port 3001)
echo "📦 [2/4] Starting SQL MCP Server on Port 3001..."
cd sql-mcp-server
npm install > /dev/null 2>&1
npm run build > /dev/null 2>&1
node dist/server.js > ../sql-mcp.log 2>&1 &
cd ..

# 4. Start Service 3: Enterprise AI Proxy (Port 8000)
echo "📦 [3/4] Starting Enterprise AI Proxy on Port 8000..."
cd proxy
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../proxy.log 2>&1 &
cd ..

# 5. Start Service 4: n8n Engine (Port 5678)
echo "📦 [4/4] Starting n8n Workflow Engine on Port 5678..."
export N8N_HOST=0.0.0.0
export N8N_PORT=5678
export N8N_PROTOCOL=http
nohup npx n8n start --port 5678 --host 0.0.0.0 > n8n.log 2>&1 &

echo "=============================================================================="
echo "✅ All 4 services are launched in the background without Docker!"
echo "   - PaddleOCR Service: http://localhost:8080/health"
echo "   - SQL MCP Server:    http://localhost:3001/health"
echo "   - AI Proxy:          http://localhost:8000/health"
echo "   - n8n Dashboard:     http://localhost:5678"
echo "=============================================================================="
