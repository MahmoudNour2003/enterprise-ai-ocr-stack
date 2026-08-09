# Enterprise AI OCR & BI Assistant Stack - Deployment & GPU Guide

This document provides a complete, step-by-step guide for deploying the **Enterprise AI OCR & BI Assistant Stack** on Cloud Virtual Machines (Linux Ubuntu 22.04 LTS / GPU Platforms) or local servers, running all services with or without Docker.

---

## 🏗️ System Architecture & Services Overview

The stack consists of **4 microservices**:

1. **PaddleOCR GPU/CPU Service (`Port 8080`)**: High-speed document text extraction service (FastAPI).
2. **Enterprise AI Proxy (`Port 8000`)**: OpenAI-compatible FastAPI bridge connecting n8n to ITI Enterprise AI with multi-turn tool execution & RLS context injection.
3. **SQL MCP Server (`Port 3001`)**: Node.js / TypeScript Model Context Protocol server executing read-only SQL queries against SQL Server (`SPIP_DB`).
4. **n8n Workflow Automation Engine (`Port 5678`)**: Orchestrates both OCR invoice extraction & conversational AI BI workflows.

---

## ⚡ Standalone VM Execution Guide (WITHOUT Docker)

Use this method to run services directly on your Virtual Machine host OS.

### Prerequisites:
- **Node.js**: `v20.x` or `v22.x`
- **Python**: `3.10`
- **SQL Server**: Access to `SPIP_DB` (MS SQL Server 2019/2022)

---

### 1️⃣ Run SQL MCP Server (Port 3001 - Standalone Node.js)

```bash
# 1. Navigate to sql-mcp-server directory
cd sql-mcp-server

# 2. Install dependencies
npm install

# 3. Configure environment variables (.env file)
cat << 'EOF' > .env
MCP_PORT=3001
DB_HOST=127.0.0.1
DB_PORT=1433
DB_NAME=SPIP_DB
DB_USER=AI_CHAT
DB_PASSWORD=AI@123
DB_ENCRYPT=false
DB_TRUST_SERVER_CERT=true
EOF

# 4. Build TypeScript to JavaScript
npm run build

# 5. Launch the MCP Server directly via Node.js
node dist/server.js
```
*(Verify health at `http://localhost:3001/health`)*

---

### 2️⃣ Run Enterprise AI Proxy (Port 8000 - Python FastAPI)

```bash
# 1. Navigate to proxy directory
cd proxy

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables (.env)
cat << 'EOF' > .env
ITI_API_KEY=your_actual_iti_api_key_token_here
ITI_BASE_URL=http://apiaccess.iti.net.eg/api/v1
PORT=8000
ALLOWED_MODELS=openai.gpt-oss-120b-1:0,deepseek.v3.2
EOF

# 4. Launch FastAPI Proxy
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*(Verify model list at `http://localhost:8000/v1/models`)*

---

### 3️⃣ Run PaddleOCR Service (Port 8080 - Python FastAPI)

```bash
# 1. Navigate to paddleocr directory
cd paddleocr

# 2. Install PaddleOCR dependencies
pip install -r requirements.txt

# 3. Launch PaddleOCR Service
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```
*(Verify health at `http://localhost:8080/health`)*

---

### 4️⃣ Run n8n Automation Engine (Port 5678)

```bash
# Install and start n8n
npm install -g n8n
export N8N_HOST=0.0.0.0
export N8N_PORT=5678
n8n start
```
*(Access n8n dashboard at `http://<VM_IP>:5678`)*

---

## 🐳 Full Docker Compose VM Deployment

To run all 4 microservices automatically with healthchecks via Docker:

```bash
# 1. Clone repository
git clone https://github.com/MahmoudNour2003/enterprise-ai-ocr-stack.git
cd enterprise-ai-ocr-stack

# 2. Configure .env
cp .env.example .env

# 3. Build and launch all containers
docker-compose up -d --build
```

---

## 🔄 Dual Workflows Setup in n8n

Both workflows run simultaneously inside the same n8n instance on the VM:

1. **OCR Invoice Extraction Workflow**:
   - File: `workflow/ocr_invoice_processing_workflow.json`
   - Webhook Endpoint: `POST http://<VM_IP>:5678/webhook/ocr-extract`
2. **AI Business Intelligence Assistant Workflow**:
   - File: `workflow/ai_bi_chat_assistant_workflow.json`
   - Webhook Endpoint: `POST http://<VM_IP>:5678/webhook/ai-chat`

---

## 🔒 SQL Server Row-Level Security (RLS) Architecture

When a request reaches n8n:
1. `.NET API` passes `userId` in the HTTP JSON payload to n8n.
2. n8n forwards the message to the **FastAPI Proxy (`:8000`)**.
3. The Proxy extracts `userId` and passes it to the **SQL MCP Server (`:3001`)**.
4. The MCP Server executes an atomic batch query:
   ```sql
   EXEC sp_set_session_context @key = N'UserId', @value = 5;
   SELECT TOP 1000 InvoiceNumber, TotalAmount, Status FROM Invoices;
   ```
5. **SQL Server RLS** hard-filters `UploadedByUserId = 5` at the database kernel level, guaranteeing **100% data isolation** across users!
