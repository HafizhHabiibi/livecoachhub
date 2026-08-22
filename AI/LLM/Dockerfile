# ============================================================
# LiveCoachHub — LLM Dockerfile (Qwen2.5 + QLoRA Adapter)
# Inference service untuk generating grounded seller scripts
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git && \
    rm -rf /var/lib/apt/lists/*

# Inference requirements (dari grounded_llm/LLM dengan QLoRA/)
# JSON array form wajib untuk path dengan spasi (agar kompatibel Windows + BuildKit)
COPY ["grounded_llm/LLM dengan QLoRA/requirements_qlora.txt", "requirements.txt"]
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua source (serve_llm.py, inference.py, adapter, system_prompt, dll)
COPY . .

EXPOSE 8020

# Healthcheck — interval lebih lama karena model loading bisa 30-60s
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

# Host 0.0.0.0 — konsisten dengan fix C-04
CMD ["python", "serve_llm.py", "--host", "0.0.0.0", "--port", "8020"]
