FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN uv venv --python 3.12 && \
    uv sync

EXPOSE 8000

CMD ["uv", "run", "python", "proxy_server.py"]
