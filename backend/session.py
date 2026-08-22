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


@dataclass
class SessionState:
    """State satu replay session."""
    session_id: str
    product_id: str
    processed_count: int = 0

    # Rolling window: list of (timestamp_ms, comment_id, user_id, canonical_signal, confidence)
    window_entries: List[Tuple[int, str, str, str, float]] = field(default_factory=list)

    # Spam tracking: {user_id: [(timestamp_ms, text_hash), ...]}
    spam_history: Dict[str, List[Tuple[int, int]]] = field(default_factory=dict)

    # Priority events buffer
    priority_events: list = field(default_factory=list)

    # Track high readiness comments
    high_readiness_count: int = 0

    # Track priority comments
    priority_count: int = 0

    # Last action (untuk cooldown di masa depan)
    last_action: Optional[str] = None
    last_action_time: Optional[int] = None

    # --- Async LLM state ---
    # Background thread yang sedang menjalankan LLM generate + validate
    pending_llm_future: Optional[Future] = field(default=None, repr=False)
    # Context dari action yang trigger LLM (untuk logging/debug)
    pending_llm_action: Optional[str] = None
    # Coach card yang sudah selesai di-generate, siap dikirim ke frontend
    ready_coach_card: Optional[Any] = field(default=None, repr=False)
    # Pipeline status untuk ready_coach_card ("CARD_READY" atau "FALLBACK")
    ready_pipeline_status: Optional[str] = None
    # Latency dari LLM generation
    ready_gen_latency: Optional[float] = None


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
