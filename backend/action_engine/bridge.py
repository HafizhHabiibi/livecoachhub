"""
LiveCoachHub Backend — Action Engine Bridge

Wrapper yang menghubungkan backend dengan ActionEngine
di ai/grounded_llm/Action Engine/action_engine.py.

Bridge ini:
1. Load action_engine.py via importlib (menghindari nama bentrok)
2. Instansiasi ActionEngine
3. Menerima WindowIntentSignal dari rolling_window
4. Convert output dataclass → Pydantic model sesuai kontrak frontend
"""

from __future__ import annotations

import importlib.util
import sys
from typing import List, Optional, Tuple

from config import ACTION_ENGINE_DIR, ACTION_RULES_PATH, WINDOW_SECONDS
from models import AudienceSnapshotOut, ActionDecisionOut
from rolling_window.window import WindowIntentSignal

# ---------------------------------------------------------------------------
# Import ActionEngine dari subproyek AI via importlib
# (tidak bisa pakai `from action_engine import ...` karena bentrok
#  dengan nama folder backend/action_engine/)
# ---------------------------------------------------------------------------

_ae_file = ACTION_ENGINE_DIR / "action_engine.py"
_spec = importlib.util.spec_from_file_location("_ai_action_engine", str(_ae_file))
_ae_mod = importlib.util.module_from_spec(_spec)
sys.modules["_ai_action_engine"] = _ae_mod  # Register agar dataclass resolver bekerja
_spec.loader.exec_module(_ae_mod)

_ActionEngine = _ae_mod.ActionEngine
_AEWindowIntentSignal = _ae_mod.WindowIntentSignal

# Singleton instance
_engine = _ActionEngine(rules_path=ACTION_RULES_PATH)


def evaluate(
    session_id: str,
    window_signals: List[WindowIntentSignal],
    product_id: str,
    current_signal: Optional[str] = None,
) -> Tuple[AudienceSnapshotOut, ActionDecisionOut]:
    """Evaluasi window signals dan return audience snapshot + action decision.

    Mengkonversi format WindowIntentSignal dari rolling_window ke format
    yang diharapkan ActionEngine, lalu konversi output kembali ke Pydantic models
    sesuai kontrak frontend.

    Args:
        session_id: ID session aktif (untuk output).
        window_signals: Aggregated signals dari rolling_window.

    Returns:
        Tuple (AudienceSnapshotOut, ActionDecisionOut) sesuai kontrak frontend.
    """
    # Convert ke format ActionEngine
    ae_signals = [
        _AEWindowIntentSignal(
            intent=ws.intent,
            support_count=ws.support_count,
            avg_confidence=ws.avg_confidence,
            unique_user_count=ws.unique_user_count,
            evidence_comment_ids=ws.evidence_comment_ids,
            evidence_comments=ws.evidence_comments,
            latest_timestamp_ms=ws.latest_timestamp_ms,
            slots_summary=ws.slots_summary,
        )
        for ws in window_signals
    ]

    # Jalankan Action Engine
    snapshot, decision = _engine.evaluate(
        ae_signals,
        window_seconds=WINDOW_SECONDS,
        current_signal=current_signal,
    )

    # Convert ke Pydantic models sesuai kontrak frontend
    snapshot_out = AudienceSnapshotOut(
        session_id=session_id,
        audience_state=snapshot.state,
        window_seconds=snapshot.window_seconds,
        support_count=snapshot.signals.get("support_count", 0),
        unique_user_count=snapshot.signals.get("unique_user_count", 0),
        latest_timestamp_ms=snapshot.signals.get("latest_timestamp_ms", 0),
        slots_summary=snapshot.signals.get("slots_summary", {}),
        high_readiness_count=0,  # dihitung di orchestrator
        priority_count=0,        # dihitung di orchestrator
        evidence_comment_ids=snapshot.evidence_comment_ids,
        state_confidence=snapshot.state_confidence,
        dominant_signal=decision.selected_signal,
    )

    decision_out = ActionDecisionOut(
        selected_action=decision.selected_action,
        selected_signal=decision.selected_signal,
        audience_state=snapshot.state,
        action_score=decision.action_score,
        required_fact_types=decision.required_fact_types,
        required_fact_query={
            **decision.required_fact_query,
            "product_id": product_id,
        } if decision.required_fact_query else {},
    )

    return snapshot_out, decision_out
