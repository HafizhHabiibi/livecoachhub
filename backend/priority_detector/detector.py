"""
LiveCoachHub Backend — Priority Detector (Priority Lane)

Mendeteksi komentar individual yang bernilai tinggi, terutama
purchase_intent ber-confidence tinggi, agar tidak hilang hanya
karena intent lain lebih dominan di Trend Lane.

Sesuai PROJECT.MD Bagian 5 Tahap 4 (Dual Signal Layer — Priority Lane):
- Purchase intent menjadi Priority Event jika confidence tinggi.
- Priority Event ditampilkan sebagai alert terpisah dari main coaching.
- Satu calon pembeli bernilai tinggi tidak hilang hanya karena
  intent lain lebih dominan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config import PRIORITY_CONFIDENCE_THRESHOLD
from session import SessionState


@dataclass
class PriorityEvent:
    """Komentar high-value yang perlu ditampilkan di UI."""
    comment_id: str
    user_id: str
    intent: str  # canonical signal
    confidence: float
    priority_level: str  # "HIGH" atau "MEDIUM"
    text: str


def check_priority(
    session: SessionState,
    comment_id: str,
    user_id: str,
    canonical_signal: str,
    confidence: float,
    text: str,
) -> Optional[PriorityEvent]:
    """Cek apakah komentar ini termasuk Priority Event.

    Saat ini hanya PURCHASE_INTENT yang bisa menjadi Priority Event,
    sesuai cakupan preliminary (4 use case utama).

    Args:
        session: State session aktif (untuk tracking).
        comment_id: ID unik komentar.
        user_id: ID anonim user.
        canonical_signal: Sinyal canonical (output taxonomy adapter).
        confidence: Confidence NLP (0-1).
        text: Teks komentar asli.

    Returns:
        PriorityEvent jika komentar memenuhi syarat, None jika tidak.
    """
    # Saat ini hanya purchase_intent yang dideteksi sebagai priority
    if canonical_signal != "PURCHASE_INTENT":
        return None

    if confidence < PRIORITY_CONFIDENCE_THRESHOLD:
        return None

    # Tentukan priority level
    if confidence >= 0.90:
        priority_level = "HIGH"
    else:
        priority_level = "MEDIUM"

    event = PriorityEvent(
        comment_id=comment_id,
        user_id=user_id,
        intent=canonical_signal,
        confidence=confidence,
        priority_level=priority_level,
        text=text,
    )

    # Tambah ke session buffer
    session.priority_events.append(event)
    session.priority_count += 1

    return event
