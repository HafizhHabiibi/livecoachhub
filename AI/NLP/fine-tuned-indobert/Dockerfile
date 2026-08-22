# ============================================================
# LiveCoachHub — NLP Dockerfile (IndoBERT Intent Classifier)
# Inference-only — training deps TIDAK termasuk
#
# Build context HARUS = AI/NLP/ (bukan fine-tuned-indobert/)
# agar data/processed/indobert_dataset/ bisa di-copy.
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# System deps untuk torch/transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git && \
    rm -rf /var/lib/apt/lists/*

# Inference-only requirements (C-09: pisah dari training deps)
COPY fine-tuned-indobert/requirements-inference.txt .
RUN pip install --no-cache-dir -r requirements-inference.txt

# Copy NLP source code ke /app/fine-tuned-indobert
COPY fine-tuned-indobert/ ./fine-tuned-indobert/

# Copy data directory (dataset_info.json berisi intent_map)
# serve.py: ROOT.parent / "data" / "processed" / "indobert_dataset" / "dataset_info.json"
# ROOT = /app/fine-tuned-indobert → ROOT.parent = /app
COPY data/ ./data/

WORKDIR /app/fine-tuned-indobert

EXPOSE 8010

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Host 0.0.0.0 — fix C-04 agar container lain bisa akses
CMD ["python", "serve.py", "--host", "0.0.0.0", "--port", "8010"]
