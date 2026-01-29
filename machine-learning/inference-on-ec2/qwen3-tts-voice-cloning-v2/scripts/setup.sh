#!/bin/bash
set -e

LOG_FILE="/var/log/model-setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "=== Qwen3-TTS Voice Cloning Setup Start ==="
echo "=========================================="
echo "Timestamp: $(date)"

echo ""
echo "=== Phase 0: Wait for apt/dpkg locks ==="
# Deep Learning AMI가 부팅 시 자동으로 apt-get을 실행하므로 모든 lock 해제를 대기
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \
      fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || \
      fuser /var/cache/apt/archives/lock >/dev/null 2>&1; do
    echo "Waiting for apt/dpkg locks to be released..."
    sleep 5
done
echo "All apt/dpkg locks released, proceeding..."

echo ""
echo "=== Phase 1: System packages ==="
apt-get update
apt-get install -y python3-venv libsndfile1 ffmpeg sox

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

models = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
]

for model_name in models:
    print(f"Downloading {model_name}...")
    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    print(f"{model_name} loaded successfully!")
    del model
    torch.cuda.empty_cache()

print("All models downloaded!")
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

print("Loading Qwen3-TTS models...")

# Load all three models
print("Loading Base model (Voice Cloning)...")
model_base = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

print("Loading CustomVoice model (Preset Voices)...")
model_custom = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

print("Loading VoiceDesign model (Voice Design)...")
model_design = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

print("All models loaded successfully!")

# Available speakers for CustomVoice
SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]
LANGUAGES = ["English", "Chinese", "Japanese", "Korean", "German", "French", "Russian", "Portuguese", "Spanish", "Italian"]

def voice_clone(text, language, ref_audio, ref_text):
    """Voice cloning with Base model"""
    try:
        if ref_audio is None:
            return None, "Please upload a reference audio file."
        if not ref_text.strip():
            return None, "Please provide the reference text."
        if not text.strip():
            return None, "Please provide the text to synthesize."

        print(f"[Voice Clone] Generating...")
        wavs, sr = model_base.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )

        output_path = tempfile.mktemp(suffix=".wav")
        sf.write(output_path, wavs[0], sr)
        return output_path, "Success!"

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, f"Error: {str(e)}"

def custom_voice(text, language, speaker, instruct):
    """TTS with preset voices using CustomVoice model"""
    try:
        if not text.strip():
            return None, "Please provide the text to synthesize."

        print(f"[Custom Voice] Speaker: {speaker}, Language: {language}")
        wavs, sr = model_custom.generate_custom_voice(
            text=text,
            language=language,
            speaker=speaker,
            instruct=instruct if instruct.strip() else "",
        )

        output_path = tempfile.mktemp(suffix=".wav")
        sf.write(output_path, wavs[0], sr)
        return output_path, "Success!"

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, f"Error: {str(e)}"

def voice_design(text, language, instruct):
    """TTS with voice description using VoiceDesign model"""
    try:
        if not text.strip():
            return None, "Please provide the text to synthesize."
        if not instruct.strip():
            return None, "Please provide a voice description."

        print(f"[Voice Design] Language: {language}")
        wavs, sr = model_design.generate_voice_design(
            text=text,
            language=language,
            instruct=instruct,
        )

        output_path = tempfile.mktemp(suffix=".wav")
        sf.write(output_path, wavs[0], sr)
        return output_path, "Success!"

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, f"Error: {str(e)}"

# Build Gradio UI with Tabs
with gr.Blocks(title="Qwen3-TTS Demo") as demo:
    gr.Markdown("# Qwen3-TTS Demo")
    gr.Markdown("Three TTS models in one interface: Voice Cloning, Custom Voice, and Voice Design")

    with gr.Tabs():
        # Tab 1: Voice Cloning (Base)
        with gr.TabItem("Voice Cloning"):
            gr.Markdown("### Clone any voice from a reference audio")
            with gr.Row():
                with gr.Column():
                    vc_ref_audio = gr.Audio(label="Reference Audio (3+ sec)", type="filepath")
                    vc_ref_text = gr.Textbox(label="Reference Text", placeholder="Transcript of reference audio...", lines=2)
                    vc_text = gr.Textbox(label="Text to Synthesize", placeholder="Text to generate with cloned voice...", lines=3)
                    vc_lang = gr.Dropdown(choices=LANGUAGES[:4], value="Korean", label="Language")
                    vc_btn = gr.Button("Generate", variant="primary")
                with gr.Column():
                    vc_output = gr.Audio(label="Generated Audio")
                    vc_status = gr.Textbox(label="Status")
            vc_btn.click(voice_clone, inputs=[vc_text, vc_lang, vc_ref_audio, vc_ref_text], outputs=[vc_output, vc_status])

        # Tab 2: Custom Voice (Preset Speakers)
        with gr.TabItem("Custom Voice"):
            gr.Markdown("### Use preset premium voices")
            with gr.Row():
                with gr.Column():
                    cv_text = gr.Textbox(label="Text to Synthesize", placeholder="Enter text...", lines=3)
                    cv_speaker = gr.Dropdown(choices=SPEAKERS, value="Vivian", label="Speaker")
                    cv_lang = gr.Dropdown(choices=LANGUAGES, value="English", label="Language")
                    cv_instruct = gr.Textbox(label="Style Instruction (optional)", placeholder="e.g., Speak with excitement", lines=2)
                    cv_btn = gr.Button("Generate", variant="primary")
                with gr.Column():
                    cv_output = gr.Audio(label="Generated Audio")
                    cv_status = gr.Textbox(label="Status")
            cv_btn.click(custom_voice, inputs=[cv_text, cv_lang, cv_speaker, cv_instruct], outputs=[cv_output, cv_status])

        # Tab 3: Voice Design
        with gr.TabItem("Voice Design"):
            gr.Markdown("### Design a voice with natural language description")
            with gr.Row():
                with gr.Column():
                    vd_text = gr.Textbox(label="Text to Synthesize", placeholder="Enter text...", lines=3)
                    vd_instruct = gr.Textbox(
                        label="Voice Description",
                        placeholder="Describe the voice characteristics...\ne.g., A warm, gentle female voice with a slight smile, speaking slowly and softly",
                        lines=4,
                    )
                    vd_lang = gr.Dropdown(choices=LANGUAGES, value="Korean", label="Language")
                    vd_btn = gr.Button("Generate", variant="primary")
                with gr.Column():
                    vd_output = gr.Audio(label="Generated Audio")
                    vd_status = gr.Textbox(label="Status")
            vd_btn.click(voice_design, inputs=[vd_text, vd_lang, vd_instruct], outputs=[vd_output, vd_status])

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
