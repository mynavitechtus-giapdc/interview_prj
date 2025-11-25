FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/vectorstore

# Expose API port
EXPOSE 8000

# Run unified API server (includes webhook endpoints)
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
