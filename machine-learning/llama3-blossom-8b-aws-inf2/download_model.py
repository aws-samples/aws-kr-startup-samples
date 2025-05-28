from huggingface_hub import snapshot_download
import os

def download_model(model_name, download_folder):
    """
    Hugging Face 모델을 지정된 폴더에 다운로드합니다.
    
    Args:
        model_name (str): 다운로드할 모델의 이름 (예: "gpt2", "facebook/bart-large-cnn")
        download_folder (str): 모델이 저장될 로컬 디렉토리 경로
    """
    # 다운로드 폴더가 존재하지 않으면 생성
    os.makedirs(download_folder, exist_ok=True)
    
    # 모델 다운로드
    snapshot_download(
        repo_id=model_name,
        local_dir=download_folder,
        ignore_patterns=[".cache", ".gitattributes"]
    )
    
    print(f"모델 '{model_name}'이(가) '{download_folder}'에 성공적으로 다운로드되었습니다.")

# 사용 예시
if __name__ == "__main__":
    model_name = "Gonsoo/AWS-HF-optimum-neuron-0-0-28-llama-3-Korean-Bllossom-8B"
    download_folder = "./models/llama3-blossom-8b"
    
    download_model(model_name, download_folder)