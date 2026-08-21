"""
LiveCoachHub Backend — Pydantic Data Contracts

Setiap model di sini HARUS 1:1 match dengan Zod schema di frontend
(frontend/src/contracts/livecoachSchemas.ts). Jika frontend mengubah
schema, file ini juga harus diupdate.

Referensi: Spesifikasi Bagian 10 (API Payloads) dan Bagian 11 (Core Contract).
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# ENUM-LIKE LITERALS — Spesifikasi Bagian 11
# ============================================================

PipelineStatus = Literal["WAITING_SIGNAL", "CARD_READY", "FALLBACK", "ERROR"]
Readiness = Literal["LOW", "MEDIUM", "HIGH"]
Urgency = Literal["NORMAL", "PRIORITY", "CRITICAL"]
ValidationStatus = Literal["PASSED", "FAILED", "NOT_RUN"]

AudienceState = Literal[
    "PRICE_FRICTION", "SIZE_FRICTION", "STOCK_FRICTION",
    "PRODUCT_INFO_GAP", "SHIPPING_FRICTION", "OBJECTION_SPIKE",
    "PURCHASE_MOMENT", "NO_CLEAR_SIGNAL",
]

SelectedAction = Literal[
    "EXPLAIN_PRICE_PROMO", "SHOW_SIZE_GUIDE", "CONFIRM_STOCK",
    "EXPLAIN_PRODUCT_DETAIL", "EXPLAIN_SHIPPING", "HANDLE_OBJECTION",
    "GUIDE_CHECKOUT", "NO_ACTION",
]

CommentIntent = Literal[
    "PRICE_PROMO", "SIZE_VARIANT", "STOCK_AVAILABILITY",
    "PRODUCT_DETAIL", "SHIPPING", "PURCHASE_INTENT",
    "OBJECTION_COMPLAINT", "IRRELEVANT_SPAM",
]

ApiErrorCode = Literal[
    "MODEL_UNAVAILABLE", "SESSION_NOT_FOUND", "INVALID_REQUEST",
    "RATE_LIMITED", "INTERNAL_ERROR",
]


# ============================================================
# REQUEST MODELS — Spesifikasi Bagian 10
# ============================================================

class SessionStartRequest(BaseModel):
    product_id: str


class CommentAnalyzeRequest(BaseModel):
    session_id: str
    comment_id: str
    timestamp_ms: int
    text: str


class SessionResetRequest(BaseModel):
    session_id: str


# ============================================================
# RESPONSE MODELS — Spesifikasi Bagian 10 + 11
# ============================================================

class HealthResponse(BaseModel):
    schema_version: str = "health.v1"
    status: Literal["READY", "DEGRADED", "OFFLINE"]
    services: dict  # {api, nlp_model, llm_model}


class DemoConfig(BaseModel):
    schema_version: str = "demo_config.v1"
    product: dict  # {product_id, display_name}
    replay: dict   # {window_seconds, speed}
    models: dict   # {nlp, llm}


class SessionStartResponse(BaseModel):
    schema_version: str = "session.v1"
    session_id: str
    status: Literal["STARTED"] = "STARTED"


class SessionResetResponse(BaseModel):
    schema_version: str = "session.v1"
    session_id: str
    status: Literal["RESET"] = "RESET"


class ApiErrorResponse(BaseModel):
    schema_version: str = "error.v1"
    error: dict  # {code, message, retryable, request_id}


# ============================================================
# PIPELINE RESULT — Spesifikasi Bagian 11
# ============================================================

class IntentScore(BaseModel):
    intent: CommentIntent
    score: float = Field(ge=0, le=1)


class NlpPrediction(BaseModel):
    schema_version: str = "nlp_prediction.v1"
    model_version: str
    comment_id: str
    intents: List[IntentScore]
    readiness: Readiness
    urgency: Urgency
    overall_confidence: float = Field(ge=0, le=1)
    usable_for_decision: bool


class AudienceSnapshotOut(BaseModel):
    """Output audience snapshot — 'Out' suffix agar tidak clash dengan
    dataclass AudienceSnapshot di action_engine.py."""
    schema_version: str = "audience_snapshot.v1"
    session_id: str
    audience_state: AudienceState
    window_seconds: int
    support_count: int = Field(ge=0)
    high_readiness_count: int = Field(ge=0)
    priority_count: int = Field(ge=0)
    evidence_comment_ids: List[str]
    state_confidence: float = Field(ge=0, le=1)


class ActionDecisionOut(BaseModel):
    schema_version: str = "action_decision.v1"
    selected_action: SelectedAction
    audience_state: AudienceState
    action_score: float = Field(ge=0, le=1)
    required_fact_types: List[str]


class CoachCard(BaseModel):
    schema_version: str = "coach_card.v1"
    priority: Urgency
    situation: str
    selected_action: SelectedAction
    reason: str
    evidence_comment_ids: List[str] = Field(max_length=3)
    suggested_response: str
    confidence: float = Field(ge=0, le=1)
    validation_status: ValidationStatus
    fallback_used: bool
    used_fact_ids: List[str]


class LatencyMs(BaseModel):
    model_config = {"exclude_none": True}  # Jangan kirim field null ke frontend
    nlp: Optional[float] = None
    generation: Optional[float] = None
    total: float


class PipelineResult(BaseModel):
    schema_version: str = "pipeline_result.v1"
    session_id: str
    pipeline_status: PipelineStatus
    processed_count: int = Field(ge=0)
    nlp_prediction: NlpPrediction
    audience_snapshot: AudienceSnapshotOut
    action_decision: ActionDecisionOut
    coach_card: Optional[CoachCard] = None
    latency_ms: Optional[LatencyMs] = None
