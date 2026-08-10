#!/usr/bin/env bash
# ==============================================================================
# Enterprise AI OCR Stack - Enable CPU Mode for PaddleOCR
# ==============================================================================

echo "ℹ️ Installing CPU package for PaddleOCR..."

# 1. Uninstall any existing GPU/CPU wheels
pip uninstall -y paddlepaddle paddlepaddle-gpu || true

# 2. Install standard CPU PaddlePaddle package
pip install paddlepaddle

# 3. Verify CPU status
python3 -c "import paddle; print('✅ Paddle Installed | Active Device:', paddle.get_device())"

echo "✅ PaddleOCR CPU setup completed!"
