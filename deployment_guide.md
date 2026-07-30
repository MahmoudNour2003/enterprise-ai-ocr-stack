# Enterprise AI OCR Stack Deployment & GPU Guide

This document provides a complete, step-by-step guide for deploying the **Enterprise AI OCR Stack** on Cloud VMs or GPU Cloud Platforms (such as Lightning.ai Studios), configuring Python 3.10, enabling NVIDIA GPU acceleration, and running all services cleanly.

---

## 🏗️ System Architecture

The stack consists of 3 core microservices:

1. **PaddleOCR GPU Inference Service (`Port 8080`)**: High-speed, GPU-accelerated Arabic & English document text extraction service (FastAPI).
2. **Enterprise AI Proxy (`Port 8000`)**: OpenAI-compatible FastAPI bridge connecting n8n to ITI Enterprise AI Provider (`apiaccess.iti.net.eg`).
3. **n8n Workflow Automation Engine (`Port 5678`)**: Orchestrates document processing, structured JSON extraction, and webhook responses.

---

## 🐍 1. Python Version Management (Python 3.10 Setup)

> **Why Python 3.10?**
> Python 3.12 has C++ ABI symbol mismatches with PaddlePaddle libraries on Linux, causing C++ `AnalysisConfig` segfaults. Python 3.10 provides 100% stable execution.

To downgrade Python in your active Conda environment to Python 3.10, run:

```bash
# Downgrade Python to 3.10 inside active conda environment
conda install -y python=3.10

# Verify Python version
python --version
# Expected Output: Python 3.10.x
```

---

## 🎮 2. Enable NVIDIA GPU Acceleration for PaddleOCR

### Step 2.1: Uninstall CPU Wheel & Install CUDA GPU Wheel

Run the following commands to install the CUDA-enabled PaddlePaddle GPU package:

```bash
# 1. Uninstall any existing CPU wheels
pip uninstall -y paddlepaddle paddlepaddle-gpu

# 2. Install CUDA 11.8 GPU Wheel
pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# (Alternative for CUDA 12.1):
# pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu121/

# 3. Install OCR and Proxy Python Dependencies
pip install -r paddleocr/requirements.txt
pip install -r proxy/requirements.txt
```

### Step 2.2: Verify CUDA GPU Availability

Run this Python check:

```bash
python -c "import paddle; print('CUDA Compiled:', paddle.is_compiled_with_cuda(), '| Device:', paddle.get_device())"
# Expected Output: CUDA Compiled: True | Device: gpu:0
```

---

## ⚙️ 3. Environment Configuration (`.env`)

Create your `.env` configuration file in the project root:

```bash
cp .env.example .env
nano .env
```

Configure your `.env` parameters:

```ini
# ITI Enterprise AI Provider Configuration
ITI_API_KEY=your_actual_iti_api_key_token_here
ITI_BASE_URL=http://apiaccess.iti.net.eg/api/v1
PORT=8000
ALLOWED_MODELS=openai.gpt-oss-120b-1:0,deepseek.v3.2,anthropic.claude-3-haiku-20240307-v1:0
MAX_RETRIES=3

# n8n Configuration
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_SECURE_COOKIE=false
WEBHOOK_URL=https://5678-your-public-url.lightning-studio.ai
N8N_WEBHOOK_URL=https://5678-your-public-url.lightning-studio.ai
N8N_ENCRYPTION_KEY=supersecretn8nkey12345
```

---

## 🚀 4. Starting All 3 Services

### Quick Start Command Block (Copy & Paste)

```bash
# 1. Pull latest code from main branch
git pull origin main

# 2. Kill any old process instances
pkill -9 -f uvicorn
pkill -9 -f n8n

# 3. Start PaddleOCR GPU Service (Port 8080)
python -m uvicorn app:app --app-dir ./paddleocr --host 0.0.0.0 --port 8080 &

# 4. Start Enterprise AI Proxy (Port 8000)
python -m uvicorn proxy.app.main:app --host 0.0.0.0 --port 8000 &

# 5. Start n8n Engine via nohup npx (Port 5678)
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_HOST=0.0.0.0
export N8N_SECURE_COOKIE=false
nohup npx n8n start --port 5678 --host 0.0.0.0 > n8n.log 2>&1 &
```

---

## 🏥 5. Service Health Verification

Check if services are healthy and running on GPU:

```bash
# Verify PaddleOCR Health & GPU Status
curl http://localhost:8080/health
# Expected Output: {"status":"healthy","service":"PaddleOCR GPU Service","gpu_enabled":true,"device":"gpu:0"}

# Verify Proxy Status
curl http://localhost:8000/health
# Expected Output: {"status":"healthy"}
```

---

## 🔗 6. n8n Credentials & Postman Testing

### Step 6.1: n8n OpenAI Credential Setup
1. Open n8n Dashboard in your browser (`https://5678-your-public-url.lightning-studio.ai`).
2. Go to **Credentials** ➔ Edit **OpenAI Account**:
   - **API Key**: `sk-dummy123456789`
   - **Base URL / URL**: `http://localhost:8000/v1`
3. Click **Save**!

### Step 6.2: Postman Request Setup
- **HTTP Method**: `POST`
- **Webhook URL**: `https://5678-your-public-url.lightning-studio.ai/webhook/d11ede0e-9d6f-4b45-8ba7-bd833c8df652`
- **Body**: Select `form-data`
  - **Key**: `file` (Type: `File`)
  - **Value**: Select your scanned invoice PDF/image file.
- Click **Send**!
