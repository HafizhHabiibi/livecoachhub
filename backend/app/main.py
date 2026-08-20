"""
LiveCoachHub Backend — FastAPI Entry Point

5 endpoint sesuai kontrak frontend (livecoachApi.ts):
  GET  /health                    → HealthResponse
  GET  /api/v1/demo-config        → DemoConfig
  POST /api/v1/session/start      → SessionStartResponse
  POST /api/v1/comments/analyze   → PipelineResult
  POST /api/v1/session/reset      → SessionResetResponse

CORS diaktifkan untuk frontend di localhost:5173 (Vite dev server).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import dari backend modules (working directory = backend/)
import sys
from pathlib import Path

# Pastikan backend/ ada di sys.path agar semua modul bisa diimport
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from config import (
    PRODUCT_ID,
    PRODUCT_DISPLAY_NAME,
    NLP_MODEL_VERSION,
    LLM_MODEL_VERSION,
    WINDOW_SECONDS,
    SCHEMA_HEALTH,
    SCHEMA_DEMO_CONFIG,
    SCHEMA_SESSION,
    SCHEMA_ERROR,
)
from models import (
    SessionStartRequest,
    CommentAnalyzeRequest,
    SessionResetRequest,
    HealthResponse,
    DemoConfig,
    SessionStartResponse,
    SessionResetResponse,
    PipelineResult,
)
from session import session_manager
from orchestrator import run_pipeline
import nlp_client
import llm_client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("livecoach")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LiveCoach Hub API",
    version="1.0.0",
    description="AI Copilot untuk Live Commerce — Backend Pipeline",
)

# CORS — izinkan frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # Nginx prod
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Error Handler
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Format error sesuai kontrak ApiErrorResponse frontend."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "schema_version": SCHEMA_ERROR,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc.detail),
                "retryable": exc.status_code >= 500,
                "request_id": str(uuid.uuid4()),
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all untuk error tak terduga."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "schema_version": SCHEMA_ERROR,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Terjadi kesalahan internal.",
                "retryable": True,
                "request_id": str(uuid.uuid4()),
            },
        },
    )


# ---------------------------------------------------------------------------
# Endpoint 1: GET /health — Spesifikasi 10.1
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Cek status backend dan dependensi (NLP, LLM).

    Dipanggil frontend saat halaman /demo dibuka.
    """
    nlp_ready = nlp_client.is_nlp_available()
    llm_ready = llm_client.is_llm_available()

    # Status keseluruhan
    if nlp_ready and llm_ready:
        overall = "READY"
    elif not nlp_ready and not llm_ready:
        # Masih bisa jalan dengan fallback
        overall = "DEGRADED"
    else:
        overall = "DEGRADED"

    return {
        "schema_version": SCHEMA_HEALTH,
        "status": overall,
        "services": {
            "api": "READY",
            "nlp_model": "READY" if nlp_ready else "DEGRADED",
            "llm_model": "READY" if llm_ready else "DEGRADED",
        },
    }


# ---------------------------------------------------------------------------
# Endpoint 2: GET /api/v1/demo-config — Spesifikasi 10.2
# ---------------------------------------------------------------------------

@app.get("/api/v1/demo-config")
def get_demo_config():
    """Return konfigurasi demo: produk, window settings, model versions.

    Dipanggil frontend sekali saat load.
    """
    return {
        "schema_version": SCHEMA_DEMO_CONFIG,
        "product": {
            "product_id": PRODUCT_ID,
            "display_name": PRODUCT_DISPLAY_NAME,
        },
        "replay": {
            "window_seconds": WINDOW_SECONDS,
            "speed": 1,
        },
        "models": {
            "nlp": NLP_MODEL_VERSION,
            "llm": LLM_MODEL_VERSION,
        },
    }


# ---------------------------------------------------------------------------
# Endpoint 3: POST /api/v1/session/start — Spesifikasi 10.3
# ---------------------------------------------------------------------------

@app.post("/api/v1/session/start")
def start_session(req: SessionStartRequest):
    """Buat session baru untuk replay.

    Dipanggil SEKALI saat tombol Start ditekan.
    """
    session = session_manager.create(product_id=req.product_id)
    logger.info("Session started: %s (product: %s)", session.session_id, req.product_id)

    return {
        "schema_version": SCHEMA_SESSION,
        "session_id": session.session_id,
        "status": "STARTED",
    }


# ---------------------------------------------------------------------------
# Endpoint 4: POST /api/v1/comments/analyze — Spesifikasi 10.4
# ---------------------------------------------------------------------------

@app.post("/api/v1/comments/analyze")
def analyze_comment(req: CommentAnalyzeRequest):
    """Jalankan pipeline AI untuk satu komentar.

    ENDPOINT UTAMA — menjalankan seluruh pipeline:
    Comment → NLP → Window → Action → Facts → LLM → Validate

    ATURAN (sesuai livecoachApi.ts):
    - Hanya satu request aktif per sesi
    - Komentar berikutnya baru dikirim SETELAH response diterima
    """
    # Validasi session
    session = session_manager.get(req.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session tidak ditemukan: {req.session_id}",
        )

    try:
        # Jalankan pipeline
        result = run_pipeline(
            session_id=req.session_id,
            comment_id=req.comment_id,
            timestamp_ms=req.timestamp_ms,
            text=req.text,
        )

        logger.info(
            "Analyzed %s: intent=%s, state=%s, action=%s (%.0fms)",
            req.comment_id,
            result.nlp_prediction.intents[0].intent if result.nlp_prediction.intents else "?",
            result.audience_snapshot.audience_state,
            result.action_decision.selected_action,
            result.latency_ms.total if result.latency_ms else 0,
        )

        return result.model_dump()

    except Exception as e:
        logger.exception("Pipeline error for %s: %s", req.comment_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Endpoint 5: POST /api/v1/session/reset — Spesifikasi 10.5
# ---------------------------------------------------------------------------

@app.post("/api/v1/session/reset")
def reset_session(req: SessionResetRequest):
    """Reset session — hapus semua state, siap replay ulang.

    Dipanggil saat tombol Reset ditekan.
    """
    session = session_manager.reset(req.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session tidak ditemukan: {req.session_id}",
        )

    # Reset NLP/LLM health cache agar dicek ulang
    nlp_client.reset_health_cache()
    llm_client.reset_health_cache()

    logger.info("Session reset: %s", req.session_id)

    return {
        "schema_version": SCHEMA_SESSION,
        "session_id": req.session_id,
        "status": "RESET",
    }