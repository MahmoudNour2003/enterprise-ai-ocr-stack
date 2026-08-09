# Enterprise AI OCR & BI Assistant Stack - Complete Non-Docker VM Deployment Guide

This document provides the complete, step-by-step instructions for deploying and running the **Enterprise AI OCR & BI Assistant Stack** on Cloud VMs (such as Lightning.ai Studios / Ubuntu) and connecting it to a **local SQL Server database** on your personal PC.

---

## 🏗️ 4 Microservices Architecture Overview

| Microservice | Port | Tech Stack | Description |
| :--- | :--- | :--- | :--- |
| **1. PaddleOCR GPU Engine** | `8080` | Python 3.10 / FastAPI | High-speed GPU-accelerated Arabic & English invoice text extraction |
| **2. Enterprise AI Proxy** | `8000` | Python / FastAPI | OpenAI-compatible proxy with multi-turn tool loops & RLS context injection |
| **3. SQL MCP Server** | `3001` | Node.js / TypeScript | Model Context Protocol server executing read-only SQL queries with RLS isolation |
| **4. n8n Workflow Engine** | `5678` | Node.js / n8n | Orchestrates OCR invoice processing & conversational AI workflows |

---

## 💻 Step 1: Connect your Local PC Database to Cloud VM (Windows PC)

To allow the Cloud VM to connect to your local PC's SQL Server (`SPIP_DB`), establish a **Reverse SSH Tunnel** from your local PC.

### 1. Enable SSH Access to Lightning.ai Studio (On your Windows PC)
Open **PowerShell (Admin)** on your local PC and run:
```powershell
iwr "https://lightning.ai/setup/ssh-windows?t=02753ac1-e22c-4194-b552-d413ca3c3f1a&s=01kysxnzwagjdf5y3y51w85673" -useb | iex
```

### 2. Allow SQL Server Port 1433 in Windows Firewall (On your Windows PC)
In **PowerShell (Admin)** on your local PC, run:
```powershell
New-NetFirewallRule -DisplayName "SQL Server Port 1433" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow
```

### 3. Open Reverse SSH Tunnel (On your Windows PC)
In **PowerShell** on your local PC, run and keep open:
```powershell
ssh -R 1433:127.0.0.1:1433 01kysxnzwagjdf5y3y51w85673
```
*(This forwards Cloud VM port 1433 directly into your PC's SQL Server!)*

---

## ⚙️ Step 2: Configure Environment Variables on Cloud VM

On your Cloud VM, edit `~/enterprise-ai-ocr-stack/sql-mcp-server/.env`:

```ini
MCP_PORT=3001
DB_HOST=127.0.0.1
DB_PORT=1433
DB_NAME=SPIP_DB
DB_USER=AI_CHAT
DB_PASSWORD=AI@123
DB_ENCRYPT=false
DB_TRUST_SERVER_CERT=true
```

---

## 🔑 Step 3: Grant Executable Permissions on Cloud VM

In your Cloud VM terminal, run:

```bash
cd ~/enterprise-ai-ocr-stack
chmod +x *.sh
```

---

## 🎮 Step 4: Enable NVIDIA GPU Mode for PaddleOCR

On your Cloud VM terminal, run:

```bash
./enable_gpu_ocr.sh
```

*(This automatically uninstalls CPU wheels, installs `paddlepaddle-gpu` with CUDA 11.8, and verifies `gpu:0`).*

---

## 🚀 Step 5: Start & Stop All 4 Stack Services

### To Start All Services:
```bash
./start_all_services.sh
```
*(This automatically cleans up old processes, clears stale n8n configs, and launches all 4 services in the background).*

### To Stop All Services:
```bash
./stop_all_services.sh
```

---

## 🏥 Step 6: Health Verification Commands

Verify all 4 microservices are healthy:

```bash
# 1. Check PaddleOCR GPU Service (Port 8080)
curl http://localhost:8080/health
# Expected: {"status":"healthy","service":"PaddleOCR GPU Service","gpu_enabled":true,"device":"gpu:0"}

# 2. Check SQL MCP Server (Port 3001)
curl http://localhost:3001/health
# Expected: {"status":"healthy","databaseConnected":true}

# 3. Check Enterprise AI Proxy (Port 8000)
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 4. Check n8n Dashboard (Port 5678)
curl http://localhost:5678
```

---

## 🔄 Dual Workflows Setup in n8n

Both workflows inside `./workflow` run simultaneously in the same n8n instance:

- 📄 **OCR Invoice Extraction**: `workflow/ocr_invoice_processing_workflow.json` (`POST /webhook/ocr-extract`)
- 💬 **AI BI Assistant Chat**: `workflow/ai_bi_chat_assistant_workflow.json` (`POST /webhook/ai-chat`)
