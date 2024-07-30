FROM --platform=linux/amd64 python:3.10.13-slim

WORKDIR /app

COPY requirements.txt .
COPY *.py .
COPY images/*.png images/

RUN pip --no-cache-dir install -Uq pip
RUN pip --no-cache-dir install -Uq -r requirements.txt

# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE

EXPOSE 8501
CMD streamlit run app.py --server.address=0.0.0.0
# ENTRYPOINT ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
