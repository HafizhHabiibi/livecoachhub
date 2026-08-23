"""
LiveCoachHub Backend — Konfigurasi Global

Semua konstanta, path, dan threshold pipeline dikumpulkan di sini
agar mudah diubah tanpa menyentuh logika bisnis.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Root project
# Di Docker: config.py ada di /app/config.py, AI di-mount di /app/AI
# Di lokal:  config.py ada di backend/config.py, AI di ../AI
# Gunakan env var PROJECT_ROOT jika ada, fallback ke parent.parent (lokal)
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))
# Load env variables from root .env (override=False agar env var Docker Compose tidak tertimpa)
load_dotenv(PROJECT_ROOT / ".env", override=False)

# AI subproject paths
AI_DIR = PROJECT_ROOT / "AI"
INTENT_CLASSIFIER_DIR = AI_DIR / "NLP"
GROUNDED_LLM_DIR = AI_DIR / "LLM" / "grounded_llm"

# Action Engine
ACTION_ENGINE_DIR = GROUNDED_LLM_DIR / "Action Engine"
ACTION_RULES_PATH = ACTION_ENGINE_DIR / "action_rules.json"

# Knowledge Base
KNOWLEDGE_BASE_DIR = GROUNDED_LLM_DIR / "Knowledge Base"
PRODUCT_FACTS_PATH = KNOWLEDGE_BASE_DIR / "product_facts_v2.json"

# Validator
VALIDATOR_DIR = GROUNDED_LLM_DIR / "Validator"

# QLoRA LLM
QLORA_DIR = GROUNDED_LLM_DIR / "LLM dengan QLoRA"

# Data
DATA_DIR = PROJECT_ROOT / "data"
REPLAY_DIR = DATA_DIR / "replay"

# ---------------------------------------------------------------------------
# Service URLs (dikonfigurasi via environment variable atau default)
# ---------------------------------------------------------------------------

NLP_SERVICE_URL = os.getenv("NLP_SERVICE_URL", "http://localhost:8010")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8020")

# LLM configuration (gemini | qlora)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Support multi-key rotation: GEMINI_API_KEYS (comma-separated) atau GEMINI_API_KEY (single)
_raw_keys = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS: list[str] = [k.strip() for k in _raw_keys.split(",") if k.strip()]
# Backward compatibility
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

# ---------------------------------------------------------------------------
# Pipeline Settings
# ---------------------------------------------------------------------------

# Rolling window duration (detik)
WINDOW_SECONDS = 60

# NLP confidence threshold — di bawah ini intent dianggap unreliable
CONFIDENCE_THRESHOLD = 0.70

# Priority Lane — confidence minimum untuk purchase_intent dianggap high-value
PRIORITY_CONFIDENCE_THRESHOLD = 0.85

# LLM max words untuk seller script
MAX_WORDS = 35

# Default tone untuk LLM
DEFAULT_TONE = "santai"

# Spam filter — panjang minimum teks (karakter) setelah normalisasi
SPAM_MIN_LENGTH = 2

# Spam filter — jarak waktu minimum (ms) untuk deteksi duplikat dari user yang sama
DUPLICATE_WINDOW_MS = 30_000  # 30 detik

# ---------------------------------------------------------------------------
# Model info (ditampilkan di /api/v1/demo-config)
# ---------------------------------------------------------------------------

PRODUCT_ID = "TSHIRT-01"
PRODUCT_DISPLAY_NAME = "Essential Cotton T-Shirt"
NLP_MODEL_VERSION = "indobert-livecoach-v1.0"
LLM_MODEL_VERSION = "livecoach-grounded-v1.0"

# ---------------------------------------------------------------------------
# Schema versions (selaras dengan frontend Zod schemas)
# ---------------------------------------------------------------------------

SCHEMA_HEALTH = "health.v1"
SCHEMA_DEMO_CONFIG = "demo_config.v1"
SCHEMA_SESSION = "session.v1"
SCHEMA_PIPELINE_RESULT = "pipeline_result.v1"
SCHEMA_NLP_PREDICTION = "nlp_prediction.v1"
SCHEMA_AUDIENCE_SNAPSHOT = "audience_snapshot.v1"
SCHEMA_ACTION_DECISION = "action_decision.v1"
SCHEMA_COACH_CARD = "coach_card.v1"
SCHEMA_ERROR = "error.v1"
