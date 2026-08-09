#!/usr/bin/env bash
# ==============================================================================
# Enterprise AI OCR & BI Stack - Stop All Services Script (Linux VM)
# ==============================================================================

echo "🛑 Stopping all 4 Enterprise Stack services..."

# Kill processes running on ports 8080, 8000, 3001, 5678
fuser -k 8080/tcp || true
fuser -k 8000/tcp || true
fuser -k 3001/tcp || true
fuser -k 5678/tcp || true

# Kill background processes by name
pkill -9 -f uvicorn || true
pkill -9 -f "node dist/server.js" || true
pkill -9 -f n8n || true

echo "✅ All Enterprise Stack services stopped successfully!"
