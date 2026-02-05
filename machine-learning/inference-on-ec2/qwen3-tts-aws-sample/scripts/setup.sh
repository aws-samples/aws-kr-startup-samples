#!/bin/bash
# setup.sh - System packages and model pre-loading
# This script is optional - gradio-server can run without it (models will be downloaded on first run)
# But pre-loading makes the first startup faster

LOG_FILE="/var/log/model-setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# PyTorch 환경의 Python 절대 경로 설정
PYTHON=/opt/pytorch/bin/python
PIP=/opt/pytorch/bin/pip

# apt/dpkg lock 대기 함수
wait_for_apt_lock() {
    local max_wait=300  # 최대 5분 대기
    local waited=0
    while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \
          fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || \
          fuser /var/cache/apt/archives/lock >/dev/null 2>&1 || \
          fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        if [ $waited -ge $max_wait ]; then
            echo "Timeout waiting for apt locks after ${max_wait}s"
            return 1
        fi
        echo "Waiting for apt/dpkg locks... (${waited}s)"
        sleep 10
        waited=$((waited + 10))
    done
    echo "All apt/dpkg locks released"
}

echo "=========================================="
echo "=== Qwen3-TTS Setup Start ==="
echo "=========================================="
echo "Timestamp: $(date)"
echo "Using Python: $PYTHON"

echo ""
echo "=== Phase 1: System packages ==="
# apt lock 대기 후 실행 (실패해도 계속 진행)
wait_for_apt_lock || true
apt-get update || true
wait_for_apt_lock || true
apt-get install -y python3-venv libsndfile1 ffmpeg sox || echo "Warning: Some system packages may not have been installed"

echo ""
echo "=== Phase 2: Create directories ==="
mkdir -p /opt/app
mkdir -p /opt/huggingface
export HF_HOME=/opt/huggingface

echo ""
echo "=== Phase 3: Python packages ==="
# PyTorch 환경에 패키지 설치 (실패해도 계속 진행)
$PIP install --upgrade pip || true
$PIP install gradio soundfile qwen-tts || echo "Warning: Some Python packages may not have been installed"

# 설치 확인
echo "Verifying installation..."
$PYTHON -c "import gradio; import qwen_tts; print('Packages verified!')" || echo "Warning: Package verification failed"

echo ""
echo "=== Phase 4: Model pre-loading (optional) ==="
echo "Pre-loading models to cache for faster startup..."
$PYTHON << 'PYEOF' || echo "Warning: Model pre-loading failed (models will be downloaded on first server start)"
import torch
from qwen_tts import Qwen3TTSModel

models = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
]

for model_name in models:
    print(f"Downloading {model_name}...")
    try:
        model = Qwen3TTSModel.from_pretrained(
            model_name,
            device_map="cuda:0",
            dtype=torch.bfloat16,
        )
        print(f"{model_name} loaded successfully!")
        del model
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"Warning: Failed to pre-load {model_name}: {e}")
        continue

print("Model pre-loading complete!")
PYEOF

echo ""
echo "=========================================="
echo "=== Setup Complete ==="
echo "=========================================="
echo "Timestamp: $(date)"
echo "Note: Even if some steps failed, gradio-server.service will start independently"
echo "      and download any missing models on first run."
