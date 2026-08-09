#!/usr/bin/env bash
# ==============================================================================
# Enterprise AI OCR Stack - Enable GPU Acceleration for PaddleOCR
# ==============================================================================

echo "🚀 Installing NVIDIA CUDA GPU package for PaddleOCR..."

# 1. Uninstall any existing CPU wheels
pip uninstall -y paddlepaddle paddlepaddle-gpu || true

# 2. Install CUDA 11.8 / 12.1 GPU wheel for PaddlePaddle
pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# 3. Verify CUDA GPU status
python3 -c "import paddle; print('✅ CUDA GPU Compiled:', paddle.is_compiled_with_cuda(), '| Active Device:', paddle.get_device())"

echo "✅ PaddleOCR GPU setup completed!"
