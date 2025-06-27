# Base image
ARG ECR_REGISTRY
ARG ECR_REPOSITORY
ARG IMAGE_TAG
FROM ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}

# Install necessary packages
RUN apt-get update && \
    apt-get install -y sudo wget git xz-utils nginx ca-certificates libsm6 libxext6 ffmpeg libfontconfig1 libxrender1 libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
    pip install opencv-python-headless opencv-contrib-python flask gevent gunicorn boto3 && \
    rm -rf /root/.cache

# Clone the GFPGAN repository to the home directory and install requirements
RUN mkdir -p /opt/program/GFPGAN && \
    git clone https://github.com/TencentARC/GFPGAN.git /opt/program/GFPGAN && \
    cd /opt/program/GFPGAN && \
    pip install basicsr && \
    pip install facexlib && \
    pip install realesrgan && \
    pip install -r requirements.txt --no-cache-dir && \
    sed -i 's/from torchvision.transforms.functional_tensor/from torchvision.transforms.functional/g' /opt/conda/lib/python3.11/site-packages/basicsr/data/degradations.py
    
# Set environment variables
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"
ENV PYTHONPATH="${PYTHONPATH}:/opt/program/GFPGAN"

COPY src /opt/program
WORKDIR /opt/program

# 스크립트에 실행 권한 부여
RUN chmod +x /opt/program/serve

# SageMaker는 기본적으로 이 포트를 사용합니다
EXPOSE 8080

# serve 스크립트를 실행하는 엔트리포인트 설정
ENTRYPOINT ["serve"]