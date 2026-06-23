# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first
COPY requirements.txt ./backend/requirements.txt
WORKDIR /app/backend
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
WORKDIR /app
COPY . /app/backend
ENV PYTHONPATH=/app

# Create non-root user
RUN chmod +x /app/backend/entrypoint.sh && useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Default envs (override in compose/production)
ENV FLASK_ENV=production \
    PORT=5000 \
    FLASK_APP=backend.app:create_app

# Entrypoint runs wait and then gunicorn (app factory)
WORKDIR /app/backend
ENTRYPOINT ["/bin/sh", "-c", "./entrypoint.sh"]
