"""
Validator - LiveCoach AI (M3/SCR-3, step 5)

Tugas: memeriksa output LLM (response_text, used_fact_ids, claims,
needs_fallback) SEBELUM dikirim ke frontend, dan memutuskan
validation_status: "PASSED" atau "FALLBACK".

Kebijakan yang dipakai (hasil keputusan bareng):
1. Kalau gagal validasi -> retry generate 1x dengan prompt koreksi
   (dikasih tau persis check mana yang gagal), baru fallback kalau
   masih gagal juga. Latensi penting di live streaming, jadi tidak
   retry berkali-kali.
2. Cross-check angka: KETAT untuk angka utama (ukuran/lingkar dada/
   panjang/harga/gsm/persentase), LONGGAR untuk angka kecil lain yang
   tidak melekat ke satuan tersebut (misal "2 orang nanya").
3. Toleransi panjang: max_words + 20%. Lewat dari itu baru gagal.

CATATAN PERLU DIKONFIRMASI KE KETUA/M1 (bukan diputuskan sepihak di sini):
Dokumen spesifikasi punya 2 definisi ValidationStatus yang berbeda di 2 bagian:
- Section 7.5 & contoh payload 10.4 -> validation_status: "PASSED" atau "FALLBACK"
- Section 11 (Enum Registry) -> ValidationStatus: PASSED | FAILED | NOT_RUN
Modul ini mengikuti Section 7.5/10.4 (PASSED/FALLBACK) karena itu yang dipakai di
contoh JSON response nyata dan di komponen Coach Card. Perlu diklarifikasi ke
ketua (M1/SCR-1) mana yang jadi acuan final sebelum schema_version dinaikkan
resmi -- lihat DECISIONS_LOG.md di root folder Lomba.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

FACTS_PATH = Path(__file__).parent.parent / "Knowledge Base" / "product_facts_v2.json"

with open(FACTS_PATH, "r", encoding="utf-8") as f:
    _facts_raw = json.load(f)["facts"]
ALL_FACTS = {f["fact_id"]: f["value"] for f in _facts_raw}


# ---------------------------------------------------------------------------
# Fallback templates -- dipakai kalau LLM gagal validasi 2x (generate awal + 1 retry)
# ---------------------------------------------------------------------------

ACTION_FALLBACK_TEMPLATES = {
    # [19 Agt 2026] Key disamakan ke selected_action RESMI (Section 4.2 dokumen) --
    # lihat DECISIONS_LOG.md di root. HANDLE_OBJECTION, EXPLAIN_SHIPPING, GUIDE_CHECKOUT
    # belum ditambahkan di sini karena action_rules.json belum mengaktifkan state-nya.
    "SHOW_SIZE_OPTIONS": "Pilihan ukuran tersedia pada panduan produk. Silakan cocokkan kelompok anak, remaja, atau dewasa sebelum memilih ya kak.",
    "SHOW_SIZE_GUIDE": "Untuk memastikan ukuran yang pas, boleh cek size chart lengkap di halaman produk ya kak, atau tanya admin biar gak salah pilih.",
    "SHOW_COLOR_OPTIONS": "Pilihan warna tersedia pada detail produk. Silakan cek varian yang aktif sebelum checkout ya kak.",
    "CONFIRM_STOCK": "Untuk stok/warna spesifik itu, admin akan konfirmasi ya kak, biar datanya pasti.",
    "EXPLAIN_PRODUCT_DETAIL": "Untuk detail produk lebih spesifik, boleh cek deskripsi produk lengkap atau tanya admin ya kak.",
    "EXPLAIN_PRICE_PROMO": "Untuk info harga/promo paling update, boleh cek langsung di halaman checkout ya kak.",
    "NO_ACTION": "Terima kasih sudah nonton, kalau ada pertanyaan produk boleh tulis di kolom komentar ya!",
}

ACTION_KEYWORDS = {
    "SHOW_SIZE_OPTIONS": ("size", "ukuran"),
    "SHOW_SIZE_GUIDE": ("size", "ukuran", "bb", "tb"),
    "SHOW_COLOR_OPTIONS": ("warna", "hitam", "putih", "navy", "maroon"),
    "CONFIRM_STOCK": ("stok", "ready", "tersedia", "habis"),
    "EXPLAIN_PRICE_PROMO": ("harga", "promo", "diskon", "voucher", "rp"),
    "EXPLAIN_PRODUCT_DETAIL": ("produk", "bahan", "kain", "model", "perawatan", "cutting"),
}

COLOR_TERMS = {"hitam", "putih", "navy", "maroon", "abu misty", "sage", "army", "pink", "cream", "coklat"}
SIZE_TOKEN_PATTERN = re.compile(r"(?<![a-z0-9])(xxxl|xxl|xl|xs|s|m|l)(?![a-z0-9])", re.IGNORECASE)

# Pola angka "utama" yang wajib dicek ketat -- angka+satuan ukuran/berat/harga,
# BUKAN kode ukuran (S/M/L/XL dst) karena itu cuma label yang diulang dari
# pertanyaan penonton, bukan klaim numerik baru yang perlu ditelusuri ke fact.
PRIMARY_NUMBER_PATTERN = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:cm|kg|gsm|%)"   # angka + satuan langsung nempel, misal "108 cm"
    r"|rp\.?\s?\d[\d.,]*",                 # "Rp 159.000" / "Rp159.000"
    re.IGNORECASE,
)

RANGE_PATTERN = re.compile(
    r"(\d+)\s*-\s*(\d+)\s*(cm|kg|gsm|%)", re.IGNORECASE
)


def _clean_number_token(raw: str) -> str:
    """Hilangkan spasi & tanda baca ekor (koma/titik penutup kalimat)."""
    token = raw.lower().replace(" ", "")
    return token.rstrip(".,")


def _number_in_any_range(raw_match: str, fact_text: str) -> bool:
    """Cek apakah angka (misal '55 kg') jatuh di dalam salah satu rentang
    yang disebut fact (misal '50-60 kg'). Perlu ini karena LLM boleh
    menyebut angka spesifik dalam rentang yang valid, bukan cuma
    mengutip rentangnya secara verbatim."""
    m = re.match(r"(\d+)(?:[.,]\d+)?\s*(cm|kg|gsm|%)", raw_match, re.IGNORECASE)
    if not m:
        return False
    value, unit = float(m.group(1)), m.group(2).lower()

    for lo, hi, range_unit in RANGE_PATTERN.findall(fact_text):
        if range_unit.lower() == unit and float(lo) <= value <= float(hi):
            return True
    return False


@dataclass
class ValidationResult:
    validation_status: str  # "PASSED" or "FALLBACK"
    failed_checks: List[str] = field(default_factory=list)
    response: Optional[dict] = None


# ---------------------------------------------------------------------------
# Individual checks -- tiap fungsi return None kalau lolos, atau string alasan gagal
# ---------------------------------------------------------------------------

def check_schema(parsed: dict) -> Optional[str]:
    required = {"response_text", "used_fact_ids", "claims", "needs_fallback"}
    missing = required - set(parsed.keys())
    if missing:
        return f"Field wajib hilang: {missing}"
    if not isinstance(parsed["response_text"], str) or not parsed["response_text"].strip():
        return "response_text kosong/bukan string"
    if not isinstance(parsed["used_fact_ids"], list):
        return "used_fact_ids bukan list"
    if not isinstance(parsed["claims"], list):
        return "claims bukan list"
    if not isinstance(parsed["needs_fallback"], bool):
        return "needs_fallback bukan boolean"
    return None


def check_fact_ids_exist(parsed: dict) -> Optional[str]:
    unknown = [fid for fid in parsed["used_fact_ids"] if fid not in ALL_FACTS]
    if unknown:
        return f"fact_id tidak ada di knowledge base: {unknown}"
    return None


def check_fact_ids_grounded_to_input(parsed: dict, input_product_facts: List[dict]) -> Optional[str]:
    given_ids = {pf["fact_id"] for pf in input_product_facts}
    used = set(parsed["used_fact_ids"])
    extra = used - given_ids
    if extra:
        return f"used_fact_ids memakai fact yang TIDAK diberikan sebagai input (kemungkinan halusinasi): {extra}"
    return None


def check_claims_grounded(parsed: dict) -> Optional[str]:
    used = set(parsed["used_fact_ids"])
    claim_ids = {c.get("fact_id") for c in parsed["claims"]}
    extra = claim_ids - used
    if extra:
        return f"claims menautkan ke fact_id di luar used_fact_ids: {extra}"
    return None


def check_primary_numbers(parsed: dict, input_product_facts: List[dict]) -> Optional[str]:
    """Kebijakan SEDANG: setiap angka utama (ukuran/harga/gsm/%) yang muncul
    di response_text harus ditemukan di salah satu fact yang dipakai --
    baik persis (substring) maupun jatuh di dalam rentang yang disebut fact
    (misal '55 kg' valid kalau fact bilang '50-60 kg'). Angka kecil tanpa
    satuan (misal "2 orang nanya") tidak dicek -- longgar.

    Berlaku sama untuk needs_fallback=true: yang dilarang bukan "menyebut
    angka apa pun", tapi menyebut angka yang TIDAK bisa ditelusuri ke fact
    yang benar-benar dipakai (used_fact_ids)."""

    raw_matches = [m.group(0) for m in PRIMARY_NUMBER_PATTERN.finditer(parsed["response_text"])]
    if not raw_matches:
        return None  # tidak ada angka utama disebut, tidak ada yang perlu dicek

    used_fact_text = " ".join(
        ALL_FACTS.get(fid, "") for fid in parsed["used_fact_ids"]
    ).lower()
    used_fact_text_nospace = used_fact_text.replace(" ", "")

    not_grounded = []
    for raw in raw_matches:
        token = _clean_number_token(raw)
        if token in used_fact_text_nospace:
            continue
        if _number_in_any_range(raw, used_fact_text):
            continue
        not_grounded.append(token)

    if not_grounded:
        return f"Angka utama di response_text tidak ditemukan/tidak masuk rentang fact yang dipakai: {not_grounded}"
    return None


def check_length(parsed: dict, max_words: int) -> Optional[str]:
    word_count = len(parsed["response_text"].split())
    limit = int(max_words * 1.2)  # toleransi +20%
    if word_count > limit:
        return f"response_text {word_count} kata, melebihi toleransi {limit} kata (max_words={max_words} +20%)"
    return None


def check_action_alignment(parsed: dict, selected_action: Optional[str]) -> Optional[str]:
    if not selected_action or selected_action not in ACTION_KEYWORDS:
        return None
    response = parsed["response_text"].lower()
    if not any(keyword in response for keyword in ACTION_KEYWORDS[selected_action]):
        return f"response_text tidak selaras dengan selected_action {selected_action}"
    return None


def check_slot_consistency(
    parsed: dict,
    selected_action: Optional[str],
    slots: Optional[dict],
) -> Optional[str]:
    if not slots:
        return None
    response = parsed["response_text"].lower()
    requested_color = slots.get("requested_color")
    mentioned_colors = {color for color in COLOR_TERMS if color in response}
    if requested_color and mentioned_colors and requested_color not in mentioned_colors:
        return f"warna pada respons tidak konsisten dengan requested_color={requested_color}"

    if selected_action == "CONFIRM_STOCK" and slots.get("requested_size"):
        requested_size = str(slots["requested_size"]).upper()
        mentioned_sizes = {match.group(1).upper() for match in SIZE_TOKEN_PATTERN.finditer(response)}
        if mentioned_sizes and requested_size not in mentioned_sizes:
            return f"size pada respons tidak konsisten dengan requested_size={requested_size}"
    return None


def check_availability_consistency(
    parsed: dict,
    selected_action: Optional[str],
    input_product_facts: List[dict],
    slots: Optional[dict],
) -> Optional[str]:
    if selected_action != "CONFIRM_STOCK":
        return None
    fact_text = " ".join(fact.get("value", "") for fact in input_product_facts).lower()
    response = parsed["response_text"].lower()
    requested_size = str((slots or {}).get("requested_size", "")).lower()
    unavailable_sizes = set()
    for segment in re.split(r"[.;,]|\b(?:sedangkan|tetapi|namun)\b", fact_text):
        if not re.search(r"\b(?:habis|tidak tersedia)\b", segment):
            continue
        # A generic rule such as "kecuali disebutkan habis pada fact warna"
        # is a condition, not evidence that every size in the sentence is out.
        if "disebutkan habis" in segment:
            continue
        unavailable_sizes.update(
            match.group(1).lower() for match in SIZE_TOKEN_PATTERN.finditer(segment)
        )
    has_generic_unavailability = "tidak tersedia" in fact_text and not unavailable_sizes
    says_unavailable = has_generic_unavailability
    if requested_size:
        says_unavailable = has_generic_unavailability or requested_size in unavailable_sizes
    claims_available = any(term in response for term in ("masih ready", "masih tersedia", "stok tersedia"))
    if says_unavailable and claims_available:
        return "respons menyatakan tersedia saat fakta input menyebut stok habis/tidak tersedia"
    return None


# ---------------------------------------------------------------------------
# Validator utama
# ---------------------------------------------------------------------------

def validate(
    raw_output: str,
    input_product_facts: List[dict],
    max_words: int,
    selected_action: Optional[str] = None,
    slots: Optional[dict] = None,
) -> ValidationResult:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return ValidationResult(validation_status="FALLBACK", failed_checks=["Output bukan JSON valid"])

    checks = [
        check_schema(parsed),
    ]
    # Kalau schema saja sudah gagal, checks lain tidak relevan (field mungkin hilang)
    if checks[0] is not None:
        return ValidationResult(validation_status="FALLBACK", failed_checks=[checks[0]])

    checks += [
        check_fact_ids_exist(parsed),
        check_fact_ids_grounded_to_input(parsed, input_product_facts),
        check_claims_grounded(parsed),
        check_primary_numbers(parsed, input_product_facts),
        check_length(parsed, max_words),
        check_action_alignment(parsed, selected_action),
        check_slot_consistency(parsed, selected_action, slots),
        check_availability_consistency(parsed, selected_action, input_product_facts, slots),
    ]
    failed = [c for c in checks if c is not None]

    if failed:
        return ValidationResult(validation_status="FALLBACK", failed_checks=failed, response=parsed)

    return ValidationResult(validation_status="PASSED", failed_checks=[], response=parsed)


# ---------------------------------------------------------------------------
# Orkestrasi: generate -> validate -> retry 1x -> fallback template
# ---------------------------------------------------------------------------

def run_with_validation(
    generate_fn: Callable[[dict, Optional[str]], str],
    input_payload: dict,
    selected_action: str,
) -> ValidationResult:
    """generate_fn(input_payload, correction_note) -> raw JSON string dari LLM.
    correction_note diisi None di percobaan pertama, lalu diisi alasan gagal
    di percobaan retry supaya LLM tau persis apa yang harus diperbaiki."""

    max_words = input_payload["max_words"]
    input_facts = input_payload["product_facts"]

    # Percobaan 1
    raw = generate_fn(input_payload, None)
    slots = input_payload.get("slots", {})
    result = validate(raw, input_facts, max_words, selected_action, slots)
    if result.validation_status == "PASSED":
        return result

    # Percobaan 2 (retry dengan koreksi)
    correction_note = "Perbaiki masalah berikut dari jawaban sebelumnya: " + "; ".join(result.failed_checks)
    raw_retry = generate_fn(input_payload, correction_note)
    result_retry = validate(raw_retry, input_facts, max_words, selected_action, slots)
    if result_retry.validation_status == "PASSED":
        return result_retry

    # Masih gagal -> fallback template (bukan output LLM lagi, demi keamanan)
    fallback_text = ACTION_FALLBACK_TEMPLATES.get(selected_action, ACTION_FALLBACK_TEMPLATES["NO_ACTION"])
    used_fact_ids = []
    claims = []
    if input_facts:
        first_fact = input_facts[0]
        fact_id = first_fact.get("fact_id")
        fact_value = first_fact.get("value", "")
        if fact_id and fact_value:
            grounded_excerpt = " ".join(fact_value.split()[:24])
            fallback_text = f"{grounded_excerpt}. Cek detail lengkap di halaman produk ya kak!"
            used_fact_ids = [fact_id]
            claims = [{"fact_id": fact_id, "claim_text": grounded_excerpt}]
    fallback_response = {
        "response_text": fallback_text,
        "used_fact_ids": used_fact_ids,
        "claims": claims,
        "needs_fallback": True,
    }
    return ValidationResult(
        validation_status="FALLBACK",
        failed_checks=result_retry.failed_checks,
        response=fallback_response,
    )
