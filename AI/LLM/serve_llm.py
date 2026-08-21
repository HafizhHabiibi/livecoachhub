"""
LiveCoachHub — LLM QLoRA Inference Service

FastAPI service yang menjalankan Qwen2.5-1.5B + QLoRA adapter
untuk menghasilkan seller script yang grounded.

Endpoint:
    GET  /health    → Status service dan model
    POST /generate  → Generate seller script dari action + facts

Dipanggil oleh backend/llm_client.py via HTTP.

Cara jalankan:
    cd AI/LLM
    python serve_llm.py --port 8020

Kebutuhan:
    - GPU NVIDIA (RTX 3050 4GB cukup)
    - Dependencies: pip install -r grounded_llm/LLM\ dengan\ QLoRA/requirements_qlora.txt
    - Adapter: livecoach-qlora-adapter/adapter_model.safetensors
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = str(ROOT / "livecoach-qlora-adapter")

# Import system prompt — HARUS identik dengan yang dipakai saat training
sys.path.insert(0, str(ROOT / "grounded_llm" / "LLM dengan QLoRA"))
from system_prompt import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("llm-service")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LiveCoach LLM Service",
    version="1.0.0",
    description="QLoRA Grounded LLM — generate seller script dari action + product facts",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------

_model = None
_tokenizer = None
_device = None
_load_time = None


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    """Request body dari backend/llm_client.py"""
    input: dict                          # {selected_action, audience_state, evidence_comments, product_facts, tone, max_words}
    correction_note: Optional[str] = None  # Catatan koreksi dari Validator (untuk retry)


class GenerateResponse(BaseModel):
    """Response body — backend membaca field 'output'"""
    output: str        # Raw JSON string dari LLM
    latency_ms: float  # Waktu generate (ms)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _load_model():
    """Load base model Qwen2.5 (4-bit) + tempel adapter QLoRA.

    Proses:
    1. Download/load Qwen2.5-1.5B-Instruct dari HuggingFace (auto-cache)
    2. Quantize ke 4-bit NF4 (hemat VRAM, ~1 GB)
    3. Tempelkan adapter LoRA dari livecoach-qlora-adapter/ (~8.7 MB)
    4. Set ke eval mode
    """
    global _model, _tokenizer, _device, _load_time

    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    logger.info("Loading base model: %s", BASE_MODEL)
    logger.info("Adapter path: %s", ADAPTER_DIR)

    # Cek adapter ada
    adapter_file = Path(ADAPTER_DIR) / "adapter_model.safetensors"
    if not adapter_file.exists():
        raise FileNotFoundError(
            f"Adapter tidak ditemukan: {adapter_file}\n"
            f"Jalankan training dulu: cd AI/LLM && python train_llm.py\n"
            f"Atau download: python scripts/download_models.py --llm"
        )

    t0 = time.time()

    # 4-bit quantization config — hemat VRAM
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )

    # Load tokenizer
    _tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    # Load base model (auto-download dari HuggingFace, ~3 GB, cached)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
    )

    # Tempelkan adapter QLoRA
    _model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    _model.eval()

    _device = next(_model.parameters()).device
    _load_time = round(time.time() - t0, 1)

    logger.info("Model loaded in %.1fs on %s", _load_time, _device)


def _ensure_model():
    """Lazy-load model saat pertama kali dipanggil."""
    if _model is None:
        _load_model()


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _generate_response(input_payload: dict, correction_note: str = None) -> str:
    """Generate seller script menggunakan QLoRA model.

    Alur:
    1. Susun chat messages: system prompt + user payload (JSON)
    2. Apply chat template Qwen2.5
    3. Tokenize dan kirim ke GPU
    4. Generate dengan sampling (temperature=0.7)
    5. Decode output, ambil hanya bagian assistant response
    6. Return raw text (diharapkan JSON valid)

    Args:
        input_payload: Dict berisi selected_action, audience_state, dll
        correction_note: Catatan koreksi jika ini retry dari Validator

    Returns:
        Raw string output dari LLM (diharapkan JSON)
    """
    _ensure_model()

    # Susun user message
    user_content = json.dumps(input_payload, ensure_ascii=False)

    # Jika ada correction_note (retry dari Validator), tambahkan
    if correction_note:
        user_content += f"\n\n[KOREKSI]: {correction_note}"

    # Bangun chat messages — format HARUS sama dengan saat training
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # Apply chat template Qwen2.5
    prompt = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    # Tokenize
    inputs = _tokenizer(prompt, return_tensors="pt").to(_device)
    input_length = inputs["input_ids"].shape[1]

    # Generate
    with torch.no_grad():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True,
            pad_token_id=_tokenizer.eos_token_id,
        )

    # Decode hanya bagian output (setelah prompt)
    response_text = _tokenizer.decode(
        output_ids[0][input_length:], skip_special_tokens=True
    ).strip()

    return response_text


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Health check — dipanggil oleh backend/llm_client.py"""
    _ensure_model()
    return {
        "status": "ok",
        "model": BASE_MODEL,
        "adapter": ADAPTER_DIR,
        "device": str(_device),
        "load_time_s": _load_time,
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    """Generate seller script.

    Dipanggil oleh backend/llm_client.py:
        POST /generate
        Body: {"input": {...}, "correction_note": "..."}

    Backend membaca response.output sebagai raw JSON string.
    """
    _ensure_model()

    t0 = time.time()

    try:
        raw_output = _generate_response(req.input, req.correction_note)
        latency = round((time.time() - t0) * 1000, 1)

        logger.info(
            "Generated response for action=%s (%.0fms): %s",
            req.input.get("selected_action", "?"),
            latency,
            raw_output[:100],
        )

        return {"output": raw_output, "latency_ms": latency}

    except Exception as e:
        logger.exception("Generation error: %s", e)
        latency = round((time.time() - t0) * 1000, 1)
        # Return fallback JSON agar backend tidak crash
        fallback = json.dumps({
            "response_text": "Mohon maaf, silakan cek detail produk di halaman toko ya kak.",
            "used_fact_ids": [],
            "claims": [],
            "needs_fallback": True,
        }, ensure_ascii=False)
        return {"output": fallback, "latency_ms": latency}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="LiveCoach LLM QLoRA Service")
    ap.add_argument("--port", type=int, default=8020, help="Port (default: 8020)")
    ap.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    args = ap.parse_args()

    # Pre-load model agar health check langsung ready
    logger.info("Pre-loading model...")
    _load_model()
    logger.info("Model ready! Starting server on %s:%d", args.host, args.port)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
