"""
LiveCoachHub Backend — Session Manager

Menyimpan state per replay session secara in-memory.
Setiap session menyimpan rolling window data, processed count,
dan spam tracking. Session dihapus saat reset.

Untuk MVP preliminary, in-memory dict cukup — tidak perlu database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import Future
from threading import RLock


@dataclass
class SessionState:
    """State satu replay session."""
    session_id: str
    product_id: str
    processed_count: int = 0

    # Rolling window: timestamp, comment, user, semantic signal, confidence, text, slots.
    window_entries: List[Tuple[int, str, str, str, float, str, Dict[str, Any]]] = field(default_factory=list)

    # Spam tracking: {user_id: [(timestamp_ms, text_hash), ...]}
    spam_history: Dict[str, List[Tuple[int, int]]] = field(default_factory=dict)

    # Priority events buffer
    priority_events: list = field(default_factory=list)

    # Track high readiness comments
    high_readiness_count: int = 0

    # Track priority comments
    priority_count: int = 0

    # Current stable main action/signal for hysteresis.
    last_action: Optional[str] = None
    last_signal: Optional[str] = None
    last_action_time: Optional[int] = None

    # --- Async LLM state ---
    # Background thread yang sedang menjalankan LLM generate + validate
    pending_llm_future: Optional[Future] = field(default=None, repr=False)
    # Context dari action yang trigger LLM (untuk logging/debug)
    pending_llm_action: Optional[str] = None
    # Fingerprint dan event time dari context yang sedang di-generate.
    pending_generation_fingerprint: Optional[str] = None
    pending_generation_event_ms: Optional[int] = None
    # Coach card yang sudah selesai di-generate, siap dikirim ke frontend
    ready_coach_card: Optional[Any] = field(default=None, repr=False)
    # Kartu terakhir yang aktif di sesi (tidak di-reset saat ready_coach_card diambil)
    latest_coach_card: Optional[Any] = field(default=None, repr=False)
    # Status yang melekat pada latest_coach_card; FALLBACK harus tetap persisten
    # pada polling berikutnya dan tidak boleh berubah menjadi CARD_READY.
    latest_pipeline_status: Optional[str] = None
    # Context kartu terakhir, untuk mencegah generation identik berulang.
    latest_generation_fingerprint: Optional[str] = None
    latest_generation_event_ms: Optional[int] = None
    # Pipeline status untuk ready_coach_card ("CARD_READY" atau "FALLBACK")
    ready_pipeline_status: Optional[str] = None
    # Latency dari LLM generation
    ready_gen_latency: Optional[float] = None

    # Idempotency cache: retry comment_id yang sama tidak memutasi agregasi dua kali.
    processed_results: Dict[str, Any] = field(default_factory=dict, repr=False)

    # Endpoint analyze dan card polling dapat berjalan di thread berbeda.
    lock: Any = field(default_factory=RLock, repr=False)


class SessionManager:
    """Manages replay sessions in-memory."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def create(self, product_id: str) -> SessionState:
        """Buat session baru. Return SessionState."""
        session_id = f"LIVE-{uuid.uuid4().hex[:8].upper()}"
        state = SessionState(session_id=session_id, product_id=product_id)
        self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> Optional[SessionState]:
        """Ambil session. Return None jika tidak ditemukan."""
        return self._sessions.get(session_id)

    def reset(self, session_id: str) -> Optional[SessionState]:
        """Reset session — hapus semua state, buat ulang."""
        old = self._sessions.pop(session_id, None)
        if old is None:
            return None
        with old.lock:
            if old.pending_llm_future is not None:
                old.pending_llm_future.cancel()
        state = SessionState(session_id=session_id, product_id=old.product_id)
        self._sessions[session_id] = state
        return state

    def increment_count(self, session_id: str) -> int:
        """Tambah processed_count dan return nilai baru."""
        session = self._sessions.get(session_id)
        if session:
            session.processed_count += 1
            return session.processed_count
        return 0


# Singleton instance
session_manager = SessionManager()
