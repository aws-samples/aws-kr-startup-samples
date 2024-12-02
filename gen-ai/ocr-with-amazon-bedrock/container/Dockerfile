FROM --platform=linux/amd64 python:3.11.10
WORKDIR /opt/app
COPY code/* ./
RUN pip install -r requirements.txt
EXPOSE 8501
CMD streamlit run \
  --server.enableXsrfProtection=false \
  /opt/app/app.py