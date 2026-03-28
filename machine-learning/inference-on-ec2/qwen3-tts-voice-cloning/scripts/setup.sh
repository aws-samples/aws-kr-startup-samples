#!/bin/bash
set -e

LOG_FILE="/var/log/model-setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "=== Qwen3-TTS Voice Cloning Setup Start ==="
echo "=========================================="
echo "Timestamp: $(date)"

echo ""
echo "=== Phase 0: Wait for dpkg lock ==="
# Deep Learning AMI가 부팅 시 자동으로 apt-get을 실행하므로 lock 해제를 대기
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    echo "Waiting for dpkg lock to be released..."
    sleep 5
done
echo "dpkg lock released, proceeding..."

echo ""
echo "=== Phase 1: System packages ==="
apt-get update
apt-get install -y python3-venv libsndfile1 ffmpeg

echo ""
echo "=== Phase 2: Create app directory ==="
mkdir -p /opt/app
export HF_HOME=/opt/huggingface

echo ""
echo "=== Phase 3: Python packages ==="
# DLAMI의 PyTorch 환경 활성화
source /opt/pytorch/bin/activate

pip install --upgrade pip
pip install gradio soundfile

# qwen-tts 설치
pip install qwen-tts

echo ""
echo "=== Phase 4: Model download ==="
python3 << 'PYEOF'
import torch
from qwen_tts import Qwen3TTSModel

print("Downloading Qwen3-TTS-12Hz-1.7B-Base model...")
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)
print("Model loaded successfully!")
PYEOF

echo ""
echo "=== Phase 5: Copy server script ==="
cat > /opt/app/server.py << 'SERVEREOF'
import torch
import gradio as gr
import soundfile as sf
import tempfile
import os
from qwen_tts import Qwen3TTSModel

print("Loading Qwen3-TTS model...")
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)
print("Model loaded successfully!")

def voice_clone(text, language, ref_audio, ref_text):
    """Voice cloning inference function"""
    try:
        if ref_audio is None:
            return None, "Please upload a reference audio file."

        if not ref_text.strip():
            return None, "Please provide the reference text (transcript of the reference audio)."

        if not text.strip():
            return None, "Please provide the text to synthesize."

        print(f"Generating voice clone...")
        print(f"  Text: {text[:50]}...")
        print(f"  Language: {language}")
        print(f"  Ref text: {ref_text[:50]}...")

        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )

        # Save to temp file
        output_path = tempfile.mktemp(suffix=".wav")
        sf.write(output_path, wavs[0], sr)

        print(f"Generated audio saved to: {output_path}")
        return output_path, "Success!"

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, f"Error: {str(e)}"

# Gradio Interface
demo = gr.Interface(
    fn=voice_clone,
    inputs=[
        gr.Textbox(
            label="Text to Synthesize",
            placeholder="Enter the text you want to convert to speech...",
            lines=3,
        ),
        gr.Dropdown(
            choices=["English", "Chinese", "Japanese", "Korean"],
            value="English",
            label="Language",
        ),
        gr.Audio(
            label="Reference Audio (3+ seconds recommended)",
            type="filepath",
        ),
        gr.Textbox(
            label="Reference Text (transcript of reference audio)",
            placeholder="Enter the exact text spoken in the reference audio...",
            lines=2,
        ),
    ],
    outputs=[
        gr.Audio(label="Generated Audio"),
        gr.Textbox(label="Status"),
    ],
    title="Qwen3-TTS Voice Cloning",
    description="Upload a reference audio and its transcript, then enter the text you want to synthesize with the cloned voice.",
    examples=[
        [
            "Hello, how are you today? I hope you're having a wonderful day.",
            "English",
            None,
            "",
        ],
    ],
)

if __name__ == "__main__":
    print("Starting Gradio server on port 7860...")
    demo.launch(server_name="0.0.0.0", server_port=7860)
SERVEREOF

echo ""
echo "=== Phase 6: Start Gradio server ==="
cd /opt/app
source /opt/pytorch/bin/activate
export HF_HOME=/opt/huggingface
nohup python3 /opt/app/server.py > /var/log/gradio-server.log 2>&1 &

echo ""
echo "=========================================="
echo "=== Setup Complete ==="
echo "=========================================="
echo "Gradio server starting on port 7860"
echo "Check /var/log/gradio-server.log for server logs"
