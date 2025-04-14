FROM ghcr.io/astral-sh/uv:python3.11-alpine

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY mcp-weather-app/ .

RUN uv venv --python 3.11 && \
    uv pip install --system -r pyproject.toml

EXPOSE 8000

CMD ["python", "server.py"]