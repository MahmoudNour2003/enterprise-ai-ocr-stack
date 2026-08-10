# ⚡ Enterprise AI OCR & BI Assistant Stack (Complete Deployment Guide)

This repository contains the complete microservice architecture for **Enterprise OCR Invoice Extraction** and **Conversational AI Business Intelligence**, running natively without Docker on Cloud VMs (Lightning.ai / Ubuntu) connected to a local PC SQL Server (`SPIP_DB`).

---

## 🚀 Quick Execution Cheatsheet

### 1. Local PC (Windows PowerShell Admin)
```powershell
# Step A: Setup Lightning SSH Connection
iwr "https://lightning.ai/setup/ssh-windows?t=02753ac1-e22c-4194-b552-d413ca3c3f1a&s=01kysxnzwagjdf5y3y51w85673" -useb | iex

# Step B: Allow SQL Server Port 1433 in Firewall
New-NetFirewallRule -DisplayName "SQL Server Port 1433" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow

# Step C: Open Reverse Tunnel to Cloud VM (Keep Open)
ssh -R 1433:127.0.0.1:1433 01kysxnzwagjdf5y3y51w85673
```

### 2. Cloud VM Terminal
```bash
cd ~/enterprise-ai-ocr-stack
git pull origin main

# Grant Executable Permissions
chmod +x *.sh

# Enable GPU Mode (If GPU attached):
./enable_gpu_ocr.sh

# OR Enable CPU Mode (If no GPU attached):
./enable_cpu_ocr.sh

# Start All Services
./start_all_services.sh

# Stop All Services
./stop_all_services.sh
```

---

## 🏥 Service Health Endpoints

- 📷 **PaddleOCR Service**: `http://localhost:8080/health`
- 🗄️ **SQL MCP Server**: `http://localhost:3001/health` (`"databaseConnected": true`)
- 🤖 **Enterprise AI Proxy**: `http://localhost:8000/health`
- ⚡ **n8n Workflow Dashboard**: `http://localhost:5678`

For the complete detailed architectural documentation, see [`deployment_guide.md`](./deployment_guide.md).
