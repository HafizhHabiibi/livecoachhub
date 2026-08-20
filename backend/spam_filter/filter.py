"""
LiveCoachHub Backend — Spam & Duplicate Filter

Mencegah komentar spam/duplikat dari satu akun mendominasi
rolling window aggregation. Komentar yang ditandai spam TETAP
diproses NLP (agar CommentStream di frontend lengkap), tapi
TIDAK dihitung dalam Trend Lane.

Sesuai PROJECT.MD Bagian 5 Tahap 2:
- Komentar identik atau hampir identik dari user yang sama
  dalam rentang pendek tidak diberi bobot penuh.
- Untuk agregasi, unique_user_count dipakai bersama support_count
  agar satu akun tidak dapat menciptakan tren palsu.
"""

from __future__ import annotations

import re
from typing import Optional

from session import SessionState
from config import SPAM_MIN_LENGTH, DUPLICATE_WINDOW_MS


# Pattern untuk mendeteksi teks yang pure emoji
_ONLY_EMOJI = re.compile(
    r"^["
    r"\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF"
    r"\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251"
    r"\s"
    r"]+$",
    flags=re.UNICODE,
)

# Pattern untuk mendeteksi teks yang pure angka/simbol
_ONLY_NUMBERS = re.compile(r"^[\d\s\.\,\-\+\=\*\/]+$")


def is_spam(text: str) -> bool:
    """Cek apakah komentar termasuk spam berdasarkan isi.

    Kriteria spam:
    1. Terlalu pendek (< SPAM_MIN_LENGTH karakter)
    2. Hanya emoji
    3. Hanya angka/simbol tanpa kata
    """
    if len(text) < SPAM_MIN_LENGTH:
        return True

    if _ONLY_EMOJI.match(text):
        return True

    if _ONLY_NUMBERS.match(text):
        return True

    return False


def is_duplicate(
    session: SessionState,
    user_id: str,
    text: str,
    timestamp_ms: int,
) -> bool:
    """Cek apakah komentar merupakan duplikat dari user yang sama.

    Duplikat = teks identik (berdasarkan hash) dari user yang sama
    dalam rentang DUPLICATE_WINDOW_MS.
    """
    text_hash = hash(text)

    # Ambil history user ini
    user_history = session.spam_history.get(user_id, [])

    # Cek apakah ada teks identik dalam window waktu
    for prev_ts, prev_hash in user_history:
        if prev_hash == text_hash and (timestamp_ms - prev_ts) < DUPLICATE_WINDOW_MS:
            return True

    # Simpan ke history
    if user_id not in session.spam_history:
        session.spam_history[user_id] = []
    session.spam_history[user_id].append((timestamp_ms, text_hash))

    # Bersihkan history lama (> 2x window) agar tidak membengkak
    cutoff = timestamp_ms - (DUPLICATE_WINDOW_MS * 2)
    session.spam_history[user_id] = [
        (ts, h) for ts, h in session.spam_history[user_id]
        if ts > cutoff
    ]

    return False


def should_count_in_window(
    session: SessionState,
    user_id: str,
    text: str,
    timestamp_ms: int,
) -> bool:
    """Gabungan check: apakah komentar ini layak dihitung di rolling window.

    Return True jika komentar BUKAN spam dan BUKAN duplikat.
    Komentar yang return False tetap diproses NLP, tapi tidak
    ditambahkan ke rolling window aggregation.
    """
    if is_spam(text):
        return False

    if is_duplicate(session, user_id, text, timestamp_ms):
        return False

    return True
