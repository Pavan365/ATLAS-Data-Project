# syntax=docker/dockerfile:1

# Load the base image.
FROM python:3.12.7-slim

# Set the working directory.
WORKDIR /app

# Install Python dependencies.
COPY ./common/requirements.txt .
RUN pip install -r requirements.txt

# Copy required scripts.
COPY ./common/comms.py .
COPY ./common/config.py .
COPY ./common/infofile.py .

# Copy the main worker script.
COPY ./worker/higgs_worker.py .

CMD ["python", "higgs_worker.py"]