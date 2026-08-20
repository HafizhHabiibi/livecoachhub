"""
LiveCoachHub Backend — NLP Client

HTTP client untuk memanggil IndoBERT NLP service (serve.py).
Jika service tidak tersedia, otomatis fallback ke keyword-based
heuristic agar pipeline tetap bisa demo tanpa GPU.

Service endpoint: POST {NLP_SERVICE_URL}/predict
Input:  {"texts": ["..."], "threshold": 0.7}
Output: {"results": [{"text": "...", "intent": "...", "confidence": 0.94}]}
"""

from __future__ import annotations

import logging
import re
from typing import Tuple

import httpx

from config import NLP_SERVICE_URL, CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword-based fallback heuristic
# ---------------------------------------------------------------------------
# Dipakai HANYA jika IndoBERT service tidak tersedia.
# Akurasi jauh di bawah model fine-tuned — cukup untuk demo pipeline.

_KEYWORD_RULES = [
    # (pattern, intent, base_confidence)
    (re.compile(r"\b(size|ukuran|s|m|l|xl|xxl)\b", re.I), "size_inquiry", 0.75),
    (re.compile(r"\b(bb|tb|berat|tinggi|cocok.*(size|ukuran))\b", re.I), "size_recommendation", 0.78),
    (re.compile(r"\b(harga|price|promo|diskon|murah|mahal|ongkir)\b", re.I), "price_inquiry", 0.76),
    (re.compile(r"\b(stok|stock|ready|available|habis|kosong)\b", re.I), "stock_availability", 0.75),
    (re.compile(r"\b(warna|color|hitam|putih|merah|biru|pink)\b", re.I), "color_inquiry", 0.74),
    (re.compile(r"\b(checkout|co |beli|order|mau ambil|langsung ambil)\b", re.I), "purchase_intent", 0.80),
    (re.compile(r"\b(bahan|material|katun|cotton|adem|panas|nerawang|gsm)\b", re.I), "product_inquiry", 0.76),
]


def _fallback_classify(text: str) -> Tuple[str, float]:
    """Keyword-based heuristic fallback.

    Return (intent, confidence). Jika tidak ada keyword match,
    return ('not_relevant', 0.50).
    """
    text_lower = text.lower()

    best_intent = "not_relevant"
    best_conf = 0.50

    for pattern, intent, conf in _KEYWORD_RULES:
        if pattern.search(text_lower):
            if conf > best_conf:
                best_intent = intent
                best_conf = conf

    return best_intent, best_conf


# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------

# Reusable HTTP client
_client = httpx.Client(timeout=5.0)
_nlp_available: bool | None = None  # None = belum dicek


def _check_nlp_health() -> bool:
    """Cek apakah NLP service online."""
    global _nlp_available
    try:
        resp = _client.get(f"{NLP_SERVICE_URL}/health")
        _nlp_available = resp.status_code == 200
    except Exception:
        _nlp_available = False
    return _nlp_available


def is_nlp_available() -> bool:
    """Return status NLP service. Cache hasil terakhir."""
    if _nlp_available is None:
        return _check_nlp_health()
    return _nlp_available


def classify(text: str) -> Tuple[str, float]:
    """Klasifikasi intent satu komentar.

    Mencoba memanggil IndoBERT service terlebih dahulu.
    Jika gagal, fallback ke keyword heuristic.

    Args:
        text: Teks komentar yang sudah di-normalize.

    Returns:
        Tuple (intent_label, confidence).
        intent_label: string lowercase sesuai output IndoBERT.
        confidence: float 0-1.
    """
    global _nlp_available

    # Coba panggil IndoBERT service
    try:
        resp = _client.post(
            f"{NLP_SERVICE_URL}/predict",
            json={"texts": [text], "threshold": CONFIDENCE_THRESHOLD},
        )
        if resp.status_code == 200:
            _nlp_available = True
            data = resp.json()
            results = data.get("results", [])
            if results:
                r = results[0]
                return r["intent"], r["confidence"]
    except Exception as e:
        logger.warning("NLP service unavailable, using fallback: %s", e)
        _nlp_available = False

    # Fallback
    return _fallback_classify(text)


def reset_health_cache():
    """Reset health cache — berguna untuk retry setelah NLP restart."""
    global _nlp_available
    _nlp_available = None
