# Base image
ARG ECR_REGISTRY
ARG ECR_REPOSITORY
ARG IMAGE_TAG
FROM ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}

# Install necessary packages
RUN apt-get update && \
    apt-get install -y sudo wget git xz-utils nginx ca-certificates libsm6 libxext6 ffmpeg libfontconfig1 libxrender1 libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

# Create new environment with specific Python version
RUN conda create -n py38 python=3.8.16 pip -y && \
    conda clean -ya

# Set PATH to use Python 3.8 by default
ENV PATH=/opt/conda/envs/py38/bin:$PATH

# Install dependencies using the Python 3.8 environment
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117 && \
    pip install flask gevent gunicorn boto3 && \
    pip install mmcv-full -f https://download.openmmlab.com/mmcv/dist/cu117/torch2.0/index.html && \
    mkdir -p /opt/program/facefusion && \
    git clone https://github.com/raphael-shin/facechain.git /opt/program/facefusion && \
    cd /opt/program/facefusion && \
    pip install -r requirements.txt --no-cache-dir

# Verify Python version
RUN echo "Python version:" && python --version && \
    echo "Python path:" && which python

# Set environment variables
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"
ENV PYTHONPATH="${PYTHONPATH}:/opt/program/facefusion"

COPY src /opt/program
WORKDIR /opt/program

# Grant execution permissions to the script
RUN chmod +x /opt/program/serve

# SageMaker uses this port by default
EXPOSE 8080

# Set the entrypoint to run the serve script
ENTRYPOINT ["python", "/opt/program/serve"]