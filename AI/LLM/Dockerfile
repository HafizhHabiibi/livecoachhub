# ============================================================
# LiveCoachHub — LLM Dockerfile (Qwen2.5 + QLoRA Adapter)
# Inference service untuk generating grounded seller scripts
#
# Menggunakan NVIDIA CUDA base image agar bitsandbytes 4-bit
# quantization bisa jalan di GPU.
# ============================================================

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python 3.11 dan system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    curl git && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --no-cache-dir --upgrade pip

# Inference requirements (dari grounded_llm/LLM dengan QLoRA/)
# JSON array form wajib untuk path dengan spasi (agar kompatibel Windows + BuildKit)
COPY ["grounded_llm/LLM dengan QLoRA/requirements_qlora.txt", "requirements.txt"]
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch dengan CUDA support + runtime deps untuk serve_llm.py
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir fastapi uvicorn pydantic huggingface_hub

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
# start-period lebih lama karena download base model ~3 GB pertama kali
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

# Host 0.0.0.0 — konsisten dengan fix C-04
CMD ["python", "serve_llm.py", "--host", "0.0.0.0", "--port", "8020"]
