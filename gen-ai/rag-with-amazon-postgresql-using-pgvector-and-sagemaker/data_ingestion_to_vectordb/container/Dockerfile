FROM python:3.10.13-slim

# pip leaves the install caches populated which uses a
# significant amount of space. These optimizations save a fair
# amount of space in the image, which reduces start up time.
RUN pip --no-cache-dir install -U pip
RUN pip --no-cache-dir install boto3==1.33.9 \
    langchain==0.2.5 \
    langchain-community==0.2.4 \
    langchain-postgres==0.0.7 \
    SQLAlchemy==2.0.28 \
    psycopg[binary]==3.1.19 \
    pgvector==0.2.5 \
    beautifulsoup4==4.12.3


# Include python script for retrieving credentials
# from AWS SecretsManager and Sagemaker helper classes
ADD credentials.py /code/
ADD sm_helper.py /code/

# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE