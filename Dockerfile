# Use a Python 3.9 slim image
FROM python:3.10.4-slim

RUN apt-get update && \
    apt-get -y install gcc

# Create and set the 'app' working directory
RUN mkdir /app
WORKDIR /app

# Copy repository contents into the working directory
COPY . /app

# Upgrade pip and install dependencies
RUN python setup.py install

# Set entrypoint
ENTRYPOINT ["helm-bot"]
