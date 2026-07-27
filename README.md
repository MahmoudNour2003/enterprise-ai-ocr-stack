# Multi-Format Invoice Extraction Stack (PaddleOCR-VL + Enterprise Proxy + n8n)

A production-ready Dockerized architecture deployed on Azure VM (CPU Optimized) that processes **Digital PDFs**, **Scanned PDFs**, and **Scanned Images (PNG/JPG)** using **PaddleOCR-VL-0.9B** and **ITI Enterprise AI Provider**.

---

## 🏗️ End-to-End Architecture Overview

```
Client (Postman / HTTP POST to Azure VM Port 80)
            │
            ▼
n8n Container (Port 80)
  └── Webhook Endpoint (/webhook/d11ede0e-9d6f-4b45-8ba7-bd833c8df652)
        │
        ├── 1. Switch Node: Check MIME Type
        │     ├── Image (PNG/JPG) ──────────────────────────┐
        │     └── PDF (application/pdf) ─► Extract PDF Text │
        │                                       │           │
        │                                 Text > 100?       │
        │                                ├── Yes (Digital) ─┼──► AI Agent (LLM)
        │                                └── No (Scanned) ──┤
        │                                                   │
        ▼                                                   │
PaddleOCR-VL-0.9B Container (CPU Port 8080) ────────────────┘
  └── Runs high-precision OCR on scanned PDFs & Images
        │
        ▼ (Extracted Text)
AI Agent Node
  └── Calls OpenAI Chat Model at http://enterprise-proxy:8000/v1
        │
        ▼
Enterprise Proxy Container (Port 8000)
  └── Bridges request to ITI Enterprise AI Provider
        │
        ▼
Return Standard Invoice JSON Object
```

---

## 📋 Azure VM Setup & Deployment (A to Z Guide)

### Step 1: Azure VM Provisioning
When creating your VM in Azure Portal:
- **OS**: Ubuntu 22.04 LTS
- **VM Size**: **`Standard_D4s_v4`** or **`Standard_D4s_v5`** (4 vCPUs, 16GB RAM)
- **Region**: `East US` (or `North Europe` / `West Europe`)
- **Availability Options**: `No infrastructure redundancy required`
- **Networking**: Inbound Security Group Rule -> Allow Port `80` (HTTP) & Port `22` (SSH)

---

### Step 2: Install Docker on Azure VM

SSH into your Azure VM:
```bash
ssh azureuser@<YOUR_AZURE_VM_PUBLIC_IP>
```

Install Docker & Docker Compose:
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
newgrp docker
```

---

### Step 3: Clone Repository & Configure Environment

```bash
git clone https://github.com/your-username/enterprise-ai-ocr-stack.git
cd enterprise-ai-ocr-stack

# Copy environment template
cp .env.example .env
```

Edit `.env` and add your Azure Public IP and ITI API Key:
```env
AZURE_VM_PUBLIC_IP=your_azure_vm_public_ip
ITI_API_KEY=your_actual_iti_api_key
```

---

### Step 4: Launch the Stack

Run a single command:
```bash
docker compose up -d
```

---

## 📡 Single Unified Public Webhook Endpoint

Clients hit **ONE single URL** on Port 80:

```text
POST http://<AZURE_VM_PUBLIC_IP>/webhook/d11ede0e-9d6f-4b45-8ba7-bd833c8df652
```

### Postman Test Setup:
- **Method**: `POST`
- **URL**: `http://<AZURE_VM_PUBLIC_IP>/webhook/d11ede0e-9d6f-4b45-8ba7-bd833c8df652`
- **Body**: `form-data` -> Key: `file` (File type) -> Select any PDF or Image invoice.
