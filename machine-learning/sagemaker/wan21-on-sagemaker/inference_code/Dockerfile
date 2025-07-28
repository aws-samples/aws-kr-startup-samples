ARG TARGETPLATFORM=linux/amd64
FROM --platform=$TARGETPLATFORM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive

# 기본 패키지 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    build-essential \
    ninja-build \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /opt/ml/code

# 필요한 Python 패키지 설치
COPY requirements.txt /opt/ml/code/
RUN pip install --no-cache-dir -r requirements.txt

# 추론 코드 복사
COPY . /opt/ml/code/

# 모델 디렉토리 생성
RUN mkdir -p /opt/ml/model

# 컨테이너 시작 시 실행할 스크립트
ENTRYPOINT ["python", "/opt/ml/code/serve.py"]