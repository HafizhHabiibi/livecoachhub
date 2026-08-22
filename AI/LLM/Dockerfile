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

# Runtime deps untuk serve_llm.py (tidak ada di requirements_qlora.txt yang hanya berisi training deps)
RUN pip install --no-cache-dir torch fastapi uvicorn pydantic huggingface_hub

# Copy semua source (serve_llm.py, inference.py, system_prompt, dll)
COPY . .

# Download QLoRA adapter dari HuggingFace (model weights bisa tidak lengkap di repo)
RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download( \
    repo_id='HafizhHabiibi/livecoach-qlora-adapter', \
    local_dir='/app/livecoach-qlora-adapter', \
    local_dir_use_symlinks=False \
)"

EXPOSE 8020

# Healthcheck — interval lebih lama karena model loading bisa 30-60s
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

# Host 0.0.0.0 — konsisten dengan fix C-04
CMD ["python", "serve_llm.py", "--host", "0.0.0.0", "--port", "8020"]
