# Multi-Format Invoice Extraction Stack (PaddleOCR-VL + Enterprise Proxy + n8n)

A production-ready Dockerized architecture deployed on an Azure GPU VM that processes **Digital PDFs**, **Scanned PDFs**, and **Scanned Images (PNG/JPG)** using **PaddleOCR-VL-0.9B (GPU-Accelerated)** and **ITI Enterprise AI Provider**.

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
        │                                 Text > 50?        │
        │                                ├── Yes (Digital) ─┼──► AI Agent (LLM)
        │                                └── No (Scanned) ──┤
        │                                                   │
        ▼                                                   │
PaddleOCR-VL-0.9B Container (vLLM GPU Port 8080) ───────────┘
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
- **Size**: **NVIDIA GPU VM** (e.g., `Standard_NC4as_T4_v3` with 1x NVIDIA T4 GPU)
- **Networking**: Inbound Security Group Rule -> Allow Port `80` (HTTP)

---

### Step 2: Install GPU Drivers & NVIDIA Container Toolkit on Azure VM

SSH into your Azure VM:
```bash
ssh azureuser@<AZURE_VM_PUBLIC_IP>
```

Run the initialization script:
```bash
# 1. Update and install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
newgrp docker

# 2. Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb [^ ]*#& [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg]#' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
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
