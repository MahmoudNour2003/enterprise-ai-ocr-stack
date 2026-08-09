#!/usr/bin/env bash
# ==============================================================================
# Enterprise AI OCR & BI Stack - Stop All Services Script (Linux VM)
# ==============================================================================

echo "🛑 Stopping all 4 Enterprise Stack services..."

# Cleanly stop processes on ports 8080, 8000, 3001, 5678 (silent fallback)
lsof -ti:8080 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3001 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5678 2>/dev/null | xargs kill -9 2>/dev/null || true

# Process name kill fallbacks
pkill -9 -f uvicorn 2>/dev/null || true
pkill -9 -f "node dist/server.js" 2>/dev/null || true
pkill -9 -f n8n 2>/dev/null || true

echo "✅ All Enterprise Stack services stopped successfully!"
