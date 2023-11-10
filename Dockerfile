# Use a Python slim image
FROM python:3.10.13-slim

# Install gcc
RUN apt-get update && apt-get install --yes gcc

# Create and set the 'app' working directory
RUN mkdir /app
WORKDIR /app

# Copy repository contents into the working directory
COPY . /app

# Install package
RUN pip install .

# Set entrypoint
ENTRYPOINT ["helm-bot"]
