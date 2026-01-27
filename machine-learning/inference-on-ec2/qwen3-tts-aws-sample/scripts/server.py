import torch
import gradio as gr
import soundfile as sf
import numpy as np
import tempfile
from qwen_tts import Qwen3TTSModel

print("Loading model...")
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.float16,
)
print("Model loaded!")

SPEAKERS = model.get_supported_speakers()
LANGUAGES = model.get_supported_languages()

def generate_speech(text, speaker, language):
    if not text.strip():
        return None
    try:
        result = model.generate_custom_voice(text=text, speaker=speaker, language=language)
        if isinstance(result, tuple):
            audio = result[0]
        else:
            audio = result
        if hasattr(audio, "numpy"):
            audio = audio.numpy()
        audio = np.array(audio).flatten()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, 24000)
            return f.name
    except Exception as e:
        print(f"Error: {e}")
        return None

demo = gr.Interface(
    fn=generate_speech,
    inputs=[
        gr.Textbox(label="Text", placeholder="Enter text to synthesize...", lines=3),
        gr.Dropdown(choices=SPEAKERS, value=SPEAKERS[0], label="Speaker"),
        gr.Dropdown(choices=LANGUAGES, value="auto", label="Language"),
    ],
    outputs=gr.Audio(label="Generated Speech", type="filepath"),
    title="Qwen3-TTS Demo",
    description="Text-to-Speech using Qwen3-TTS-12Hz-1.7B-CustomVoice",
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
