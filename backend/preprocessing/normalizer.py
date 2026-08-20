"""
LiveCoachHub Backend — Preprocessing / Normalizer

Normalisasi teks komentar sebelum dikirim ke NLP model.
Prinsip: bersihkan noise TANPA menghilangkan singkatan/slang
yang penting untuk intent classification (bb, tb, kak, dll).
"""

from __future__ import annotations

import re
import unicodedata


# Pattern untuk mendeteksi emoji berlebihan (>3 emoji berturut-turut)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # misc symbols
    "\U0001F680-\U0001F6FF"  # transport
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)

# Pattern untuk whitespace berlebihan
_MULTI_SPACE = re.compile(r"\s+")

# Pattern untuk karakter non-printable
_NON_PRINTABLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def normalize(text: str) -> str:
    """Normalisasi teks komentar.

    Langkah:
    1. Strip whitespace luar
    2. Lowercase
    3. Hapus karakter non-printable
    4. Normalisasi Unicode (NFC)
    5. Kurangi emoji berlebihan (max 2 emoji cluster berturut-turut)
    6. Normalisasi spasi ganda → single space
    7. Strip ulang

    TIDAK dilakukan:
    - Hapus singkatan (bb, tb, kak, dll) — penting untuk NLP
    - Hapus angka — penting untuk size/harga
    - Stemming/lemmatization — model IndoBERT menangani sendiri
    """
    if not text:
        return ""

    # 1-2. Strip + lowercase
    result = text.strip().lower()

    # 3. Hapus non-printable
    result = _NON_PRINTABLE.sub("", result)

    # 4. Normalisasi Unicode
    result = unicodedata.normalize("NFC", result)

    # 5. Kurangi emoji berlebihan — ganti cluster >2 jadi max 2
    emoji_clusters = _EMOJI_PATTERN.findall(result)
    if len(emoji_clusters) > 2:
        # Hapus semua emoji, simpan max 2 di akhir
        result = _EMOJI_PATTERN.sub("", result).strip()

    # 6. Normalisasi spasi
    result = _MULTI_SPACE.sub(" ", result)

    # 7. Strip ulang
    return result.strip()
