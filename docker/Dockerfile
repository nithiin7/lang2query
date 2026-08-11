# Lang2Query Backend Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /srv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata first for better caching
COPY backend/pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy source code
COPY backend/app/ ./app/
COPY Makefile ./

# Create necessary directories
RUN mkdir -p app/ai/kb app/ai/output app/ai/input

# Download models (optional - can be done at runtime)
# RUN python download.py

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /srv
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# `main.py`'s package-relative imports (e.g. `from core.config import ...`)
# assume backend/app/ is the import root, so run from inside app/ rather
# than adding it to PYTHONPATH from a different working directory.
WORKDIR /srv/app

# Default command
CMD ["python", "-m", "main"]
