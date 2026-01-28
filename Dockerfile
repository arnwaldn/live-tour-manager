# =============================================================================
# Tour Manager - Production Dockerfile
# Python 3.12 + Gunicorn WSGI Server
# =============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r tourmanager && useradd -r -g tourmanager tourmanager

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership to non-root user
RUN chown -R tourmanager:tourmanager /app

# Switch to non-root user
USER tourmanager

# Expose port (Fly.io uses 8080 by default)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run Gunicorn with dynamic port
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 2 \
    --access-logfile - --error-logfile - \
    "app:create_app()"
