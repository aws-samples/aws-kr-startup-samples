ARG TARGETPLATFORM=linux/amd64
FROM --platform=$TARGETPLATFORM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive

# Install basic packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    nginx \
    build-essential \
    ninja-build \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/ml/code

# Install required Python packages
COPY requirements.txt /opt/ml/code/
RUN pip install --no-cache-dir -r requirements.txt

# Copy inference code
COPY . /opt/ml/code/

# Create model directory
RUN mkdir -p /opt/ml/model

# Expose port for execution
EXPOSE 8080

# Enable synchronous execution mode for CUDA debugging
ENV CUDA_LAUNCH_BLOCKING=1
ENV TORCH_USE_CUDA_DSA=1

# GPU memory optimization settings
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV CUDA_MEMORY_FRACTION=0.95


# Script to run when container starts
ENTRYPOINT ["python", "/opt/ml/code/serve.py"]