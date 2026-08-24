"""Pure helpers for deduplicating equivalent LLM generations."""

from __future__ import annotations

import hashlib
import json
from typing import Sequence


def build_generation_fingerprint(
    selected_action: str,
    audience_state: str,
    evidence_comment_ids: Sequence[str],
    required_fact_types: Sequence[str],
) -> str:
    """Build a stable fingerprint for the material generation context."""
    payload = {
        "selected_action": selected_action,
        "audience_state": audience_state,
        "evidence_comment_ids": list(evidence_comment_ids),
        "required_fact_types": list(required_fact_types),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def should_reuse_generation(
    current_action: str,
    latest_action: str | None,
    current_fingerprint: str,
    latest_fingerprint: str | None,
    latest_pipeline_status: str | None,
    current_event_ms: int,
    latest_event_ms: int | None,
    fallback_retry_cooldown_ms: int,
) -> bool:
    """Reuse equivalent output; allow fallback retry only after its cooldown."""
    if latest_pipeline_status == "FALLBACK":
        if current_action != latest_action:
            return False
        if latest_event_ms is None:
            return True
        elapsed_ms = max(0, current_event_ms - latest_event_ms)
        return elapsed_ms < fallback_retry_cooldown_ms
    return bool(latest_fingerprint and current_fingerprint == latest_fingerprint)
