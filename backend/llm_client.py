"""
LiveCoachHub Backend — LLM Client

Client dual-mode untuk memanggil Gemini API atau QLoRA LLM service,
dengan template-based fallback jika keduanya tidak tersedia.

Sesuai PROJECT.MD Bagian 5 Tahap 8:
"Action/state, evidence comments, product facts, tone, dan max_words
dikirim ke LLM. Model menghasilkan seller script yang grounded."

Tiga mode operasi:
- Mode 1 (Gemini API): Cloud LLM dengan auto-rotation multi API key
- Mode 2 (QLoRA service): HTTP POST ke local LLM service
- Mode 3 (Template fallback): Gunakan ACTION_FALLBACK_TEMPLATES
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Dict, List, Optional

import httpx
from google import genai
from google.genai import types as genai_types

import config
from config import (
    LLM_SERVICE_URL,
    MAX_WORDS,
    DEFAULT_TONE,
    QLORA_DIR,
)

logger = logging.getLogger(__name__)

# Tambahkan path QLoRA untuk mengimpor system prompt resmi
_qlora_dir_str = str(QLORA_DIR)
if _qlora_dir_str not in sys.path:
    sys.path.insert(0, _qlora_dir_str)
from system_prompt import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Gemini API Key Rotation State
# ---------------------------------------------------------------------------
_gemini_key_index: int = 0          # Index key yang sedang aktif
_gemini_clients: dict = {}          # Cache Client per API key


def _get_gemini_client(api_key: str) -> genai.Client:
    """Get atau create cached Client untuk API key tertentu."""
    if api_key not in _gemini_clients:
        _gemini_clients[api_key] = genai.Client(api_key=api_key)
    return _gemini_clients[api_key]


# Reusable HTTP client
_client = httpx.Client(timeout=30.0)
_llm_available: bool | None = None


# ---------------------------------------------------------------------------
# Fallback templates — diambil dari Validator (ACTION_FALLBACK_TEMPLATES)
# Dipakai ketika QLoRA LLM belum tersedia.
# ---------------------------------------------------------------------------

_FALLBACK_TEMPLATES = {
    "SHOW_SIZE_GUIDE": (
        "Untuk memastikan ukuran yang pas, boleh cek size chart lengkap "
        "di halaman produk ya kak, atau tanya admin biar gak salah pilih."
    ),
    "CONFIRM_STOCK": (
        "Untuk stok/warna spesifik itu, admin akan konfirmasi ya kak, "
        "biar datanya pasti."
    ),
    "EXPLAIN_PRODUCT_DETAIL": (
        "Untuk detail produk lebih spesifik, boleh cek deskripsi produk "
        "lengkap atau tanya admin ya kak."
    ),
    "EXPLAIN_PRICE_PROMO": (
        "Untuk info harga/promo paling update, boleh cek langsung di "
        "halaman checkout ya kak."
    ),
    "NO_ACTION": (
        "Terima kasih sudah nonton, kalau ada pertanyaan produk boleh "
        "tulis di kolom komentar ya!"
    ),
}


def _check_llm_health() -> bool:
    """Cek apakah LLM service online."""
    global _llm_available
    try:
        resp = _client.get(f"{LLM_SERVICE_URL}/health")
        _llm_available = resp.status_code == 200
    except Exception:
        _llm_available = False
    return _llm_available


def is_llm_available() -> bool:
    """Return status LLM service. Re-check jika sebelumnya unavailable."""
    global _llm_available

    if config.LLM_PROVIDER == "gemini":
        # Untuk Gemini API, ketersediaan tergantung pada adanya minimal 1 API Key
        _llm_available = len(config.GEMINI_API_KEYS) > 0
        return _llm_available

    if _llm_available is None or _llm_available is False:
        return _check_llm_health()
    return _llm_available


def build_llm_input(
    selected_action: str,
    audience_state: str,
    evidence_comments: List[str],
    product_facts: List[dict],
    tone: str = DEFAULT_TONE,
    max_words: int = MAX_WORDS,
) -> dict:
    """Susun input payload untuk LLM sesuai format response dataset.

    Format ini harus sama dengan yang dipakai saat training QLoRA
    (lihat system_prompt.py dan response_dataset.jsonl).
    """
    return {
        "selected_action": selected_action,
        "audience_state": audience_state,
        "evidence_comments": evidence_comments,
        "product_facts": product_facts,
        "tone": tone,
        "max_words": max_words,
    }


def generate(input_payload: dict, correction_note: Optional[str] = None) -> str:
    """Generate response dari LLM.

    Mencoba memanggil provider yang aktif (Gemini API atau QLoRA service).
    Jika gagal, return template fallback sebagai valid JSON.

    Args:
        input_payload: Dict sesuai format build_llm_input().
        correction_note: Catatan koreksi dari Validator (untuk retry).

    Returns:
        Raw JSON string — output LLM atau template fallback.
    """
    global _llm_available, _gemini_key_index

    # ---------------------------------------------------------
    # Mode 1: Gemini API (dengan auto-rotation multi key)
    # ---------------------------------------------------------
    if config.LLM_PROVIDER == "gemini":
        if not config.GEMINI_API_KEYS:
            logger.warning("GEMINI_API_KEYS belum disetel di .env, menggunakan template fallback")
            _llm_available = False
            return _generate_template_fallback(input_payload)

        user_content = json.dumps(input_payload, ensure_ascii=False)
        if correction_note:
            user_content += f"\n\n[KOREKSI]: {correction_note}"

        # Coba setiap key mulai dari key yang sedang aktif
        keys = config.GEMINI_API_KEYS
        for attempt in range(len(keys)):
            key_idx = (_gemini_key_index + attempt) % len(keys)
            current_key = keys[key_idx]

            try:
                client = _get_gemini_client(current_key)
                response = client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=user_content,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                raw_output = response.text
                if raw_output:
                    _llm_available = True
                    _gemini_key_index = key_idx  # Ingat key yang berhasil
                    return raw_output
            except Exception as e:
                error_str = str(e).lower()
                # Rotate ke key berikutnya jika rate limit / quota exceeded
                if "429" in error_str or "quota" in error_str or "rate" in error_str:
                    logger.warning(
                        "Gemini key %d/%d rate limited, rotating to next key: %s",
                        key_idx + 1, len(keys), e
                    )
                    _gemini_key_index = (key_idx + 1) % len(keys)
                    continue
                else:
                    logger.warning("Gemini API error (non-rate-limit): %s", e)
                    break  # Error lain, langsung fallback

        # Semua key gagal
        logger.warning("All %d Gemini API keys exhausted, using template fallback", len(keys))
        _llm_available = False
        return _generate_template_fallback(input_payload)

    # ---------------------------------------------------------
    # Mode 2: Local QLoRA Service
    # ---------------------------------------------------------
    try:
        body = {"input": input_payload}
        if correction_note:
            body["correction_note"] = correction_note

        resp = _client.post(
            f"{LLM_SERVICE_URL}/generate",
            json=body,
        )
        if resp.status_code == 200:
            _llm_available = True
            data = resp.json()
            raw_output = data.get("output", data.get("response", ""))
            if raw_output:
                return raw_output
    except Exception as e:
        logger.warning("LLM service unavailable, using template fallback: %s", e)
        _llm_available = False

    # Fallback: gunakan template
    return _generate_template_fallback(input_payload)


def _generate_template_fallback(input_payload: dict) -> str:
    """Generate valid JSON response menggunakan template.

    Template ini pasti lolos Validator karena formatnya benar
    dan tidak mengklaim fakta yang tidak ada.
    """
    selected_action = input_payload.get("selected_action", "NO_ACTION")
    product_facts = input_payload.get("product_facts", [])

    response_text = _FALLBACK_TEMPLATES.get(
        selected_action,
        _FALLBACK_TEMPLATES["NO_ACTION"],
    )

    # Jika ada product_facts, coba buat respons yang lebih informatif
    # dengan menyebut fact_id (agar used_fact_ids terisi)
    used_fact_ids = []
    claims = []

    if product_facts:
        # Ambil fact pertama untuk referensi
        first_fact = product_facts[0]
        fact_id = first_fact.get("fact_id", "")
        fact_value = first_fact.get("value", "")

        if fact_value and fact_id:
            used_fact_ids.append(fact_id)
            # Potong fact value agar muat max_words
            words = fact_value.split()[:20]
            short_value = " ".join(words)
            response_text = f"{short_value}. Cek detail lengkap di halaman produk ya kak!"
            claims.append({
                "fact_id": fact_id,
                "claim_text": short_value,
            })

    result = {
        "response_text": response_text,
        "used_fact_ids": used_fact_ids,
        "claims": claims,
        "needs_fallback": len(used_fact_ids) == 0,
    }

    return json.dumps(result, ensure_ascii=False)


def reset_health_cache():
    """Reset health cache — berguna untuk retry setelah LLM restart."""
    global _llm_available
    _llm_available = None
