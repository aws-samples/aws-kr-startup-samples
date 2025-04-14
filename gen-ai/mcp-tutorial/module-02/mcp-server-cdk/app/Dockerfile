FROM ghcr.io/astral-sh/uv:python3.11-alpine

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy the rest of the application
COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]