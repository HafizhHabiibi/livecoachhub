"""Pure helpers for resolving generation provenance independently of validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class GenerationOutcome:
    provider: str
    fallback_used: bool
    pipeline_status: str


def resolve_generation_outcome(
    validation_status: str,
    attempted_providers: Sequence[str],
) -> GenerationOutcome:
    """Resolve the actual source of the response returned to the UI.

    A validator fallback is always TEMPLATE. A valid template returned by the
    LLM client is also TEMPLATE even though its validation status is PASSED.
    """
    is_passed = validation_status == "PASSED"
    provider = attempted_providers[-1] if is_passed and attempted_providers else "TEMPLATE"
    if provider not in {"GEMINI", "TEMPLATE"}:
        provider = "TEMPLATE"
    fallback_used = provider == "TEMPLATE"
    pipeline_status = "CARD_READY" if is_passed and not fallback_used else "FALLBACK"
    return GenerationOutcome(
        provider=provider,
        fallback_used=fallback_used,
        pipeline_status=pipeline_status,
    )
