FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Set working directory
WORKDIR /app

# Copy the application files
COPY . .

# Install dependencies
RUN uv venv --python 3.12 && \
    uv sync

EXPOSE 8000

# Run the application
CMD ["uv", "run", "main.py"] 