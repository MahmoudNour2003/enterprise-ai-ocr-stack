# ⚡ Enterprise AI OCR & BI Assistant Stack (100% Non-Docker Native VM Guide)

This repository contains the complete microservice architecture for **Enterprise OCR Document Processing** and **AI Business Intelligence Assistant**, optimized for running **natively on Virtual Machines (Linux / Windows) WITHOUT DOCKER**.

---

## 🏗️ 4 Microservices Architecture

| Microservice | Port | Tech Stack | Non-Docker Startup Command |
| :--- | :--- | :--- | :--- |
| **1. PaddleOCR Engine** | `8080` | Python 3.10 / FastAPI | `python -m uvicorn app:app --app-dir ./paddleocr --port 8080` |
| **2. Enterprise AI Proxy** | `8000` | Python / FastAPI | `python -m uvicorn app.main:app --app-dir ./proxy --port 8000` |
| **3. SQL MCP Server** | `3001` | Node.js / TypeScript | `cd sql-mcp-server && npm install && npm run build && node dist/server.js` |
| **4. n8n Engine** | `5678` | Node.js / n8n | `npx n8n start --port 5678` |

---

## 🚀 Quick Start (Running Without Docker)

### Option 1: Linux / Ubuntu VM (Single Command)
```bash
# Give execution permissions and run the launcher script
chmod +x start_all_services.sh
./start_all_services.sh
```

### Option 2: Windows VM / Local Machine (Single Click)
Double-click `start_all_services.bat` or run:
```cmd
start_all_services.bat
```

---

## 📋 Manual Step-by-Step Execution (Without Docker)

### 1. SQL MCP Server (Port 3001)
```bash
cd sql-mcp-server
npm install
npm run build
node dist/server.js
```

### 2. Enterprise AI Proxy (Port 8000)
```bash
cd proxy
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. PaddleOCR Service (Port 8080)
```bash
cd paddleocr
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

### 4. n8n Engine (Port 5678)
```bash
npm install -g n8n
export N8N_HOST=0.0.0.0
export N8N_PORT=5678
n8n start
```

---

## 🔄 Dual Workflows Included in `./workflow`

- 📄 `ocr_invoice_processing_workflow.json` (`POST http://<VM_IP>:5678/webhook/ocr-extract`)
- 💬 `ai_bi_chat_assistant_workflow.json` (`POST http://<VM_IP>:5678/webhook/ai-chat`)

For detailed PM2 / Systemd production deployment, check [`deployment_guide.md`](./deployment_guide.md).
