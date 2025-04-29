FROM ghcr.io/astral-sh/uv:python3.11-alpine

# Set working directory
WORKDIR /app

# Copy the application files
COPY mcp-weather-app/ .

# Install dependencies
RUN uv venv --python 3.11 && \
    uv pip install --system -r pyproject.toml

EXPOSE 8000

# Run the application
CMD ["uv", "run", "start"] 