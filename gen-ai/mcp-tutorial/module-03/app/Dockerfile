FROM python:3.11-slim

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the application files
COPY streamlit-app/ .

# Install dependencies
RUN pip install -r requirements.txt

EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "app.py"]