# ============================================================
# LiveCoachHub — Backend Dockerfile (FastAPI)
# Runtime-only — tidak termasuk training dependencies
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# System deps yang dibutuhkan httpx/uvicorn
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps dulu (cached layer terpisah dari source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh backend source
COPY . .

# Set PROJECT_ROOT agar config.py resolve path AI/ dan data/ dengan benar
# (AI di-mount di /app/AI via docker-compose volume)
ENV PROJECT_ROOT=/app

EXPOSE 8000

# Healthcheck agar Docker Compose tahu service ready
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
