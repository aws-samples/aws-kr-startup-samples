FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]