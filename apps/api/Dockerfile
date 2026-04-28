FROM python:3.12-slim

WORKDIR /app

# Install system dependencies, libpq often required for Postgres connections
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API source code (assuming context is repo root)
COPY apps/api ./apps/api

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
