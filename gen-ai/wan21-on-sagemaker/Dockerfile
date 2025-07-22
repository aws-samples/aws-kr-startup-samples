# Wan2.1 SageMaker BYOC Dockerfile - 14B Model with NVIDIA PyTorch base
FROM nvcr.io/nvidia/pytorch:24.02-py3

# Set environment variables
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    ca-certificates \
    wget \
    curl \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy model files
COPY model/ /opt/ml/model/

# Copy inference code
COPY code/ /opt/program/

# Set working directory
WORKDIR /opt/program

# Make serve script executable
RUN chmod +x /opt/program/serve

# Expose port 8080
EXPOSE 8080
