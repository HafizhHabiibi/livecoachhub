"""
LiveCoachHub Backend — Rolling Window (Trend Lane)

Mengagregasi sinyal intent dalam rolling window 60 detik.
Setiap kali komentar baru masuk, window dihitung ulang untuk
menghasilkan List[WindowIntentSignal] yang dikirim ke Action Engine.

Sesuai PROJECT.MD Bagian 5 Tahap 4 (Dual Signal Layer — Trend Lane):
- Rolling window 60 detik
- Menghitung support_count, unique_user_count, avg_confidence,
  serta evidence_comment_ids per sinyal canonical.

Mekanisme waktu mengikuti virtual/event time dari replay, BUKAN wall clock.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from config import WINDOW_SECONDS
from session import SessionState


@dataclass
class WindowIntentSignal:
    """Satu baris agregat dari rolling window.
    Format ini selaras dengan WindowIntentSignal di action_engine.py."""
    intent: str
    support_count: int
    avg_confidence: float
    unique_user_count: int = 0
    evidence_comment_ids: List[str] = field(default_factory=list)


def add_signal(
    session: SessionState,
    timestamp_ms: int,
    comment_id: str,
    user_id: str,
    canonical_signal: str,
    confidence: float,
) -> None:
    """Tambahkan sinyal baru ke rolling window session.

    Args:
        session: State session aktif.
        timestamp_ms: Virtual/event time dari komentar (ms).
        comment_id: ID unik komentar.
        user_id: ID anonim user.
        canonical_signal: Sinyal canonical (output taxonomy adapter).
        confidence: Confidence NLP (0-1).
    """
    session.window_entries.append(
        (timestamp_ms, comment_id, user_id, canonical_signal, confidence)
    )


def get_window_signals(
    session: SessionState,
    current_time_ms: int,
) -> List[WindowIntentSignal]:
    """Hitung agregasi sinyal dalam rolling window 60 detik.

    Hanya entry dengan timestamp_ms dalam rentang
    [current_time_ms - window_ms, current_time_ms] yang dihitung.

    Args:
        session: State session aktif.
        current_time_ms: Virtual time saat ini (ms).

    Returns:
        List of WindowIntentSignal, satu per sinyal canonical yang
        muncul dalam window. Diurutkan berdasarkan support_count DESC.
    """
    window_ms = WINDOW_SECONDS * 1000
    cutoff = current_time_ms - window_ms

    # Filter entries yang masuk window
    active_entries = [
        (ts, cid, uid, signal, conf)
        for ts, cid, uid, signal, conf in session.window_entries
        if ts >= cutoff
    ]

    # Bersihkan entries lama dari session (opsional, hemat memori)
    session.window_entries = [
        e for e in session.window_entries if e[0] >= cutoff
    ]

    # Agregasi per sinyal
    aggregation: Dict[str, dict] = defaultdict(lambda: {
        "support_count": 0,
        "unique_users": set(),
        "confidences": [],
        "evidence_comment_ids": [],
    })

    for ts, cid, uid, signal, conf in active_entries:
        agg = aggregation[signal]
        agg["support_count"] += 1
        agg["unique_users"].add(uid)
        agg["confidences"].append(conf)
        # Simpan max 3 evidence terbaru
        if len(agg["evidence_comment_ids"]) < 3:
            agg["evidence_comment_ids"].append(cid)

    # Build output
    results = []
    for signal, agg in aggregation.items():
        avg_conf = (
            sum(agg["confidences"]) / len(agg["confidences"])
            if agg["confidences"]
            else 0.0
        )
        results.append(WindowIntentSignal(
            intent=signal,
            support_count=agg["support_count"],
            avg_confidence=round(avg_conf, 4),
            unique_user_count=len(agg["unique_users"]),
            evidence_comment_ids=agg["evidence_comment_ids"],
        ))

    # Urutkan berdasarkan support_count terbanyak
    results.sort(key=lambda s: s.support_count, reverse=True)
    return results
