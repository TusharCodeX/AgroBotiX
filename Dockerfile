# AgriPath Multi-Platform Dockerfile (arm64 for Raspberry Pi 4/5, amd64 for testing)
FROM python:3.11-slim

# Install system dependencies for OpenCV and hardware camera interfaces
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and models
COPY backend/ ./backend/
COPY models/ ./models/
COPY config.yaml .
COPY main.py .
COPY run_headless.py .
COPY evaluate.py .

# Expose port for FastAPI backend
EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
