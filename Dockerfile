# =============================================================================
# GigRoute - Production Dockerfile
# Python 3.12 + Gunicorn WSGI Server
# =============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=app:create_app \
    FLASK_ENV=production

# Set working directory
WORKDIR /app

# Install system dependencies (including Cairo for PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r gigroute && useradd -r -g gigroute gigroute

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership to non-root user
RUN chown -R gigroute:gigroute /app

# Switch to non-root user
USER gigroute

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# DB migrations at container start, then Gunicorn
# Strategy: run Alembic migrations (idempotent), seed professions, start server
CMD bash -c "flask db upgrade && \
    (flask seed-professions || true) && \
    gunicorn -c gunicorn.conf.py 'app:create_app()'"
