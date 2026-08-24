"""Pure helpers for deterministic API-key failover ordering."""

from __future__ import annotations

from typing import Tuple


def key_attempt_order(key_count: int, start_index: int) -> Tuple[int, ...]:
    """Return every key index exactly once, starting from ``start_index``."""
    if key_count <= 0:
        return ()
    normalized_start = start_index % key_count
    return tuple((normalized_start + offset) % key_count for offset in range(key_count))

