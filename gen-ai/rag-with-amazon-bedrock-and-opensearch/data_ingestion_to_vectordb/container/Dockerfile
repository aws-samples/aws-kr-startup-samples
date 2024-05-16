FROM python:3.10.13-slim

# pip leaves the install caches populated which uses a
# significant amount of space. These optimizations save a fair
# amount of space in the image, which reduces start up time.
RUN pip --no-cache-dir install -U pip
RUN pip --no-cache-dir install boto3>=1.26.159 \
    langchain==0.1.16 \
    langchain-aws==0.1.0 \
    langchain-community==0.0.34 \
    SQLAlchemy==2.0.28 \
    opensearch-py==2.2.0 \
    beautifulsoup4==4.12.3

# Include python script for retrieving credentials
# from AWS SecretsManager and Sagemaker helper classes
ADD credentials.py /code/

# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
