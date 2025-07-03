FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN uv venv --python 3.12
RUN uv pip install -r requirements.txt

COPY app/ .

EXPOSE 8000

# uv를 사용해서 가상환경에서 uvicorn 실행
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]