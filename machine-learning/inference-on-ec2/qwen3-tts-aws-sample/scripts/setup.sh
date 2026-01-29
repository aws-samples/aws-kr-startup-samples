#!/bin/bash
set -e

LOG_FILE="/var/log/model-setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "Qwen3-TTS Setup Script"
echo "Started at: $(date)"
echo "=========================================="

# === PHASE 1: System Check ===
echo ""
echo "=== PHASE 1: System Check ==="

echo "Checking GPU..."
nvidia-smi || { echo "ERROR: nvidia-smi failed"; exit 1; }

echo "Checking CUDA..."
nvcc --version || echo "WARNING: nvcc not in PATH"

echo "Checking disk space..."
df -h /

echo "Checking memory..."
free -h

# === PHASE 2: Environment Setup ===
echo ""
echo "=== PHASE 2: Environment Setup ==="

export HF_HOME=/opt/huggingface
export MODEL_NAME="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
export CUDA_VISIBLE_DEVICES=0

mkdir -p $HF_HOME
mkdir -p /opt/app

echo "HF_HOME=$HF_HOME"
echo "MODEL_NAME=$MODEL_NAME"

# === PHASE 3: System Dependencies ===
echo ""
echo "=== PHASE 3: System Dependencies ==="

apt-get update -qq
apt-get install -y -qq python3-venv python3-pip sox libsox-fmt-all

# === PHASE 4: Python Dependencies ===
echo ""
echo "=== PHASE 4: Python Dependencies ==="

pip install --upgrade pip --no-cache-dir
pip install --no-cache-dir \
    torch \
    qwen-tts \
    soundfile \
    scipy \
    fastapi \
    uvicorn

echo "Installed packages:"
pip list | grep -E "torch|qwen-tts|transformers"

# === PHASE 5: Model Download ===
echo ""
echo "=== PHASE 5: Model Download ==="

python3 << 'EOF'
import os
import torch
from qwen_tts import Qwen3TTSModel

model_name = os.environ.get("MODEL_NAME", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
print(f"Downloading model: {model_name}")

model = Qwen3TTSModel.from_pretrained(
    model_name,
    device_map="cuda:0",
    dtype=torch.float16,
)
print("Model downloaded and loaded successfully!")
print(f"Supported speakers: {model.get_supported_speakers()}")
print(f"Supported languages: {model.get_supported_languages()}")
EOF

# === PHASE 6: Validation ===
echo ""
echo "=== PHASE 6: Validation ==="

python3 << 'EOF'
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
EOF

# === PHASE 7: Systemd Service Setup ===
echo ""
echo "=== PHASE 7: Systemd Service Setup ==="

echo "Installing systemd service..."
cp /opt/app/qwen3-tts.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable qwen3-tts.service
systemctl start qwen3-tts.service

echo "Service status:"
systemctl status qwen3-tts.service --no-pager || true
echo "Access UI at http://<public-ip>:7860"

echo ""
echo "=========================================="
echo "Setup completed at: $(date)"
echo "=========================================="
