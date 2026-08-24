"""
LiveCoachHub Backend — Pipeline Orchestrator

Menyambung semua modul pipeline menjadi satu alur:
  Comment → Preprocess → Spam Filter → NLP → Taxonomy Adapt
  → Rolling Window → Priority Detect → Action Engine → Fact Retrieval
  → LLM Generate (ASYNC) → Validate → PipelineResult

ARSITEKTUR ASYNC LLM:
  - Fase Cepat (setiap komentar, ~100ms): NLP → Window → Action Engine
  - Fase LLM (background thread): Fact Retrieval → LLM → Validate
  - Coach Card dikirim pada response komentar berikutnya setelah LLM selesai.

Sesuai PROJECT.MD Bagian 5 dan Definition of Done Bagian 10:
"Seluruh pipeline berjalan tanpa hand-off manual antaranggota."

Orchestrator dipanggil oleh endpoint POST /api/v1/comments/analyze
untuk setiap komentar yang masuk.
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Optional

from config import (
    CONFIDENCE_THRESHOLD,
    MAX_WORDS,
    DEFAULT_TONE,
    NLP_MODEL_VERSION,
    WINDOW_SECONDS,
)
from models import (
    PipelineResult,
    NlpPrediction,
    IntentScore,
    AudienceSnapshotOut,
    ActionDecisionOut,
    PriorityEventOut,
    CoachCard,
    LatencyMs,
)
from session import SessionState, session_manager

# Pipeline modules
from preprocessing.normalizer import normalize
from spam_filter.filter import should_count_in_window
from taxonomy_adapter.adapter import adapt, to_frontend_intent, is_actionable
from slot_extractor import extract_slots
import nlp_client
from rolling_window.window import add_signal, get_window_signals
from priority_detector.detector import check_priority
from action_engine.bridge import evaluate as action_evaluate
from knowledge.retrieval import get_facts_for_query
import llm_client
from generation_provenance import resolve_generation_outcome
from generation_dedup import build_generation_fingerprint, should_reuse_generation
from validator.bridge import validate_output, run_with_retry, get_fallback_template

logger = logging.getLogger(__name__)

# Thread pool untuk async LLM — 1 worker cukup karena LLM service singlethreaded
_llm_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-async")
FALLBACK_RETRY_COOLDOWN_MS = 30_000


# ---------------------------------------------------------------------------
# Situation text templates — bahasa manusia untuk audience state
# ---------------------------------------------------------------------------

_SITUATION_TEMPLATES = {
    "SIZE_INFORMATION_GAP": "{count} komentar menanyakan pilihan ukuran dalam {window} detik terakhir",
    "SIZE_FRICTION": "{count} komentar menanyakan ukuran dalam {window} detik terakhir",
    "COLOR_INFORMATION_GAP": "{count} komentar menanyakan pilihan warna dalam {window} detik terakhir",
    "STOCK_FRICTION": "{count} komentar menanyakan stok varian dalam {window} detik terakhir",
    "PRODUCT_INFO_GAP": "{count} komentar menanyakan detail produk dalam {window} detik terakhir",
    "PRICE_FRICTION": "{count} komentar menanyakan harga/promo dalam {window} detik terakhir",
    "NO_CLEAR_SIGNAL": "Belum ada pola dominan dari audiens",
}


def _build_situation(audience_state: str, support_count: int) -> str:
    """Buat deskripsi situasi dalam bahasa manusia."""
    template = _SITUATION_TEMPLATES.get(
        audience_state,
        "{count} komentar terkait dalam {window} detik terakhir",
    )
    return template.format(count=support_count, window=WINDOW_SECONDS)


def _determine_readiness(canonical_signal: str, confidence: float) -> str:
    """Tentukan readiness level berdasarkan sinyal dan confidence."""
    if canonical_signal == "PURCHASE_INTENT" and confidence >= 0.85:
        return "HIGH"
    if canonical_signal == "PURCHASE_INTENT" or confidence >= 0.80:
        return "MEDIUM"
    return "LOW"


def _determine_urgency(canonical_signal: str, confidence: float) -> str:
    """Tentukan urgency level."""
    if canonical_signal == "PURCHASE_INTENT" and confidence >= 0.90:
        return "CRITICAL"
    if canonical_signal == "PURCHASE_INTENT" and confidence >= 0.85:
        return "PRIORITY"
    return "NORMAL"


# ---------------------------------------------------------------------------
# Async LLM — background generation
# ---------------------------------------------------------------------------

def _run_llm_background(
    selected_action: str,
    selected_signal: str,
    audience_state: str,
    slots: dict,
    required_fact_query: dict,
    evidence_texts: List[str],
    product_facts: List[dict],
    urgency: str,
    situation: str,
    support_count: int,
    state_confidence: float,
    evidence_comment_ids: List[str],
    session_id: str,
) -> dict:
    """Jalankan LLM generate + validate di background thread.

    Return dict berisi coach_card data, pipeline_status, dan gen_latency.
    Fungsi ini dipanggil oleh ThreadPoolExecutor.
    """
    t_gen_start = time.time()

    llm_input = llm_client.build_llm_input(
        selected_action=selected_action,
        selected_signal=selected_signal,
        audience_state=audience_state,
        evidence_comments=evidence_texts,
        slots=slots,
        required_fact_query=required_fact_query,
        product_facts=product_facts,
        tone=DEFAULT_TONE,
        max_words=MAX_WORDS,
    )

    # Provider generation dicatat terpisah dari status validasi. Template
    # fallback bisa aman/valid, tetapi tidak boleh dilabel sebagai Gemini.
    generation_providers: List[str] = []

    def generate_tracked(payload: dict, correction_note: Optional[str] = None) -> str:
        generated = llm_client.generate_with_metadata(payload, correction_note)
        generation_providers.append(generated.provider)
        return generated.raw_output

    validation_result = run_with_retry(
        generate_fn=generate_tracked,
        input_payload=llm_input,
        selected_action=selected_action,
    )

    t_gen_end = time.time()
    gen_latency = round((t_gen_end - t_gen_start) * 1000, 1)

    response_data = validation_result.response or {}
    is_passed = validation_result.validation_status == "PASSED"
    outcome = resolve_generation_outcome(
        validation_result.validation_status,
        generation_providers,
    )
    fe_validation_status = "PASSED" if is_passed else "FAILED"

    coach_card = CoachCard(
        priority=urgency,
        situation=situation,
        selected_action=selected_action,
        reason=f"{support_count} pertanyaan terkait / {WINDOW_SECONDS} detik",
        evidence_comment_ids=evidence_comment_ids[:3],
        suggested_response=response_data.get("response_text", get_fallback_template(selected_action)),
        confidence=state_confidence,
        validation_status=fe_validation_status,
        generation_provider=outcome.provider,
        fallback_used=outcome.fallback_used,
        used_fact_ids=response_data.get("used_fact_ids", []),
    )

    logger.info(
        "LLM async selesai untuk session=%s action=%s status=%s (%.0fms)",
        session_id, selected_action, outcome.pipeline_status, gen_latency,
    )

    return {
        "coach_card": coach_card,
        "pipeline_status": outcome.pipeline_status,
        "gen_latency": gen_latency,
    }


def _check_and_collect_llm_result(session: SessionState) -> None:
    """Cek apakah background LLM sudah selesai, simpan hasilnya ke session."""
    if session.pending_llm_future is None:
        return

    future = session.pending_llm_future
    if not future.done():
        return  # Masih jalan, skip

    # LLM selesai — ambil hasilnya
    try:
        result = future.result(timeout=0)
        session.ready_coach_card = result["coach_card"]
        session.latest_coach_card = result["coach_card"]
        session.ready_pipeline_status = result["pipeline_status"]
        session.latest_pipeline_status = result["pipeline_status"]
        session.latest_generation_fingerprint = session.pending_generation_fingerprint
        session.latest_generation_event_ms = session.pending_generation_event_ms
        session.ready_gen_latency = result["gen_latency"]
        logger.info(
            "Coach card ready untuk session=%s action=%s",
            session.session_id, session.pending_llm_action,
        )
    except Exception as e:
        logger.exception("LLM background error: %s", e)
        # Fallback jika LLM error
        session.ready_coach_card = None
        session.ready_pipeline_status = None
        session.ready_gen_latency = None

    # Clear pending state
    session.pending_llm_future = None
    session.pending_llm_action = None
    session.pending_generation_fingerprint = None
    session.pending_generation_event_ms = None


def _cancel_pending_llm(session: SessionState) -> None:
    """Cancel pending LLM jika ada (action baru lebih relevan)."""
    if session.pending_llm_future is not None:
        session.pending_llm_future.cancel()
        logger.info(
            "Cancelled pending LLM untuk session=%s action=%s",
            session.session_id, session.pending_llm_action,
        )
        session.pending_llm_future = None
        session.pending_llm_action = None
        session.pending_generation_fingerprint = None
        session.pending_generation_event_ms = None


def get_session_card(session_id: str) -> dict:
    """Ambil status dan Coach Card dari session (untuk polling/check async)."""
    session = session_manager.get(session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")

    # Check dan kumpulkan hasil jika background task sudah selesai
    _check_and_collect_llm_result(session)

    is_generating = (
        session.pending_llm_future is not None
        and not session.pending_llm_future.done()
    )

    card = session.ready_coach_card or session.latest_coach_card
    status = (
        session.ready_pipeline_status
        or session.latest_pipeline_status
        or ("CARD_READY" if card is not None else "WAITING_SIGNAL")
    )
    latency = session.ready_gen_latency

    # Clear ready flag setelah diambil
    session.ready_coach_card = None
    session.ready_pipeline_status = None
    session.ready_gen_latency = None

    return {
        "session_id": session_id,
        "is_generating": is_generating,
        "pending_action": session.pending_llm_action if is_generating else None,
        "coach_card": card,
        "pipeline_status": status,
        "gen_latency": latency,
    }


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    session_id: str,
    comment_id: str,
    user_id: str,
    timestamp_ms: int,
    text: str,
) -> PipelineResult:
    """Jalankan seluruh pipeline untuk satu komentar.

    ARSITEKTUR ASYNC:
    - Fase Cepat (sinkron): NLP → Window → Action Engine (~100ms)
    - Fase LLM (async): Generate di background thread
    - Coach Card dikirim saat LLM selesai (pada response komentar berikutnya)

    Args:
        session_id: ID session aktif.
        comment_id: ID unik komentar.
        timestamp_ms: Virtual/event time (ms).
        text: Teks komentar mentah.

    Returns:
        PipelineResult sesuai kontrak frontend (Zod PipelineResultSchema).
    """
    t_start = time.time()

    # 0. Ambil session
    session = session_manager.get(session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")

    # Retry idempotent: comment_id yang sama tidak memutasi state dua kali.
    cached_result = session.processed_results.get(comment_id)
    if cached_result is not None:
        return cached_result.model_copy(deep=True)

    # Increment processed count
    processed_count = session_manager.increment_count(session_id)

    # --- Cek apakah LLM background sudah selesai ---
    _check_and_collect_llm_result(session)

    # ===== TAHAP 1: PREPROCESSING =====
    cleaned_text = normalize(text)

    # ===== TAHAP 2: SPAM/DUPLICATE FILTER =====
    count_in_window = should_count_in_window(session, user_id, cleaned_text, timestamp_ms)

    # ===== TAHAP 3: NLP INTENT CLASSIFICATION =====
    t_nlp_start = time.time()
    nlp_intent, nlp_confidence = nlp_client.classify(cleaned_text)
    t_nlp_end = time.time()
    nlp_latency = round((t_nlp_end - t_nlp_start) * 1000, 1)

    # ===== TAHAP 4: TAXONOMY ADAPT =====
    canonical_signal = adapt(nlp_intent)
    frontend_intent = to_frontend_intent(canonical_signal)
    actionable = is_actionable(canonical_signal)
    slots = extract_slots(cleaned_text)

    # Determine readiness & urgency
    readiness = _determine_readiness(canonical_signal, nlp_confidence)
    urgency = _determine_urgency(canonical_signal, nlp_confidence)
    usable = nlp_confidence >= CONFIDENCE_THRESHOLD

    # Build NlpPrediction
    nlp_prediction = NlpPrediction(
        model_version=NLP_MODEL_VERSION,
        comment_id=comment_id,
        raw_intent=nlp_intent if nlp_intent in {
            "product_inquiry", "size_inquiry", "size_recommendation",
            "color_inquiry", "price_inquiry", "stock_availability",
            "purchase_intent", "not_relevant", "other",
        } else "other",
        normalized_signal=frontend_intent,
        slots=slots,
        intents=[IntentScore(intent=frontend_intent, score=round(nlp_confidence, 4))],
        readiness=readiness,
        urgency=urgency,
        overall_confidence=round(nlp_confidence, 4),
        usable_for_decision=usable,
    )

    # ===== TAHAP 5: ROLLING WINDOW (jika layak) =====
    if count_in_window and actionable and usable:
        add_signal(
            session,
            timestamp_ms,
            comment_id,
            user_id,
            canonical_signal,
            nlp_confidence,
            cleaned_text,
            slots,
        )

    # Track readiness
    if readiness == "HIGH":
        session.high_readiness_count += 1

    # ===== TAHAP 6: PRIORITY DETECTOR =====
    check_priority(
        session, comment_id, user_id, canonical_signal, nlp_confidence, text, slots,
    )
    latest_priority = session.priority_events[-1] if session.priority_events else None
    priority_event_out = PriorityEventOut(
        comment_id=latest_priority.comment_id,
        user_id=latest_priority.user_id,
        confidence=latest_priority.confidence,
        priority_level=latest_priority.priority_level,
        text=latest_priority.text,
        slots=latest_priority.slots,
    ) if latest_priority is not None else None

    # ===== TAHAP 7: GET WINDOW SIGNALS (Trend Lane) =====
    window_signals = get_window_signals(session, timestamp_ms)

    # ===== TAHAP 8: ACTION ENGINE =====
    snapshot_out, decision_out = action_evaluate(
        session_id,
        window_signals,
        product_id=session.product_id,
        current_signal=session.last_signal,
    )

    if decision_out.selected_action != "NO_ACTION":
        session.last_action = decision_out.selected_action
        session.last_signal = decision_out.selected_signal
        session.last_action_time = timestamp_ms

    # Update counts dari session
    snapshot_out.high_readiness_count = session.high_readiness_count
    snapshot_out.priority_count = session.priority_count

    # ===== TAHAP 9: CEK READY COACH CARD (dari LLM sebelumnya) =====
    # Jika ada coach card yang sudah selesai di-generate, sertakan di response ini
    if session.ready_coach_card is not None:
        coach_card = session.ready_coach_card
        pipeline_status = session.ready_pipeline_status or "CARD_READY"
        gen_latency = session.ready_gen_latency

        # Clear — sudah dikirim
        session.ready_coach_card = None
        session.ready_pipeline_status = None
        session.ready_gen_latency = None

        total_latency = round((time.time() - t_start) * 1000, 1)
        result = PipelineResult(
            session_id=session_id,
            pipeline_status=pipeline_status,
            processed_count=processed_count,
            nlp_prediction=nlp_prediction,
            audience_snapshot=snapshot_out,
            action_decision=decision_out,
            priority_event=priority_event_out,
            coach_card=coach_card,
            latency_ms=LatencyMs(nlp=nlp_latency, generation=gen_latency, total=total_latency),
        )
        session.processed_results[comment_id] = result.model_copy(deep=True)
        return result

    # ===== TAHAP 10: JIKA ADA ACTION → KICK OFF ASYNC LLM =====
    if decision_out.selected_action != "NO_ACTION":
        generation_fingerprint = build_generation_fingerprint(
            decision_out.selected_action,
            snapshot_out.audience_state,
            snapshot_out.evidence_comment_ids,
            decision_out.required_fact_types,
            decision_out.required_fact_query,
        )

        # Jika LLM sedang jalan untuk action yang SAMA, biarkan selesai (jangan cancel & jangan restart)
        is_same_running = (
            session.pending_llm_future is not None
            and not session.pending_llm_future.done()
            and session.pending_llm_action == decision_out.selected_action
        )

        reuse_latest = should_reuse_generation(
            current_action=decision_out.selected_action,
            latest_action=(
                session.latest_coach_card.selected_action
                if session.latest_coach_card is not None
                else None
            ),
            current_fingerprint=generation_fingerprint,
            latest_fingerprint=session.latest_generation_fingerprint,
            latest_pipeline_status=session.latest_pipeline_status,
            current_event_ms=timestamp_ms,
            latest_event_ms=session.latest_generation_event_ms,
            fallback_retry_cooldown_ms=FALLBACK_RETRY_COOLDOWN_MS,
        )

        if is_same_running:
            logger.info(
                "LLM async untuk session=%s action=%s sedang berjalan, melanjutkan task yang ada",
                session_id, decision_out.selected_action,
            )
        elif reuse_latest:
            logger.info(
                "Reuse Coach Card untuk session=%s action=%s fingerprint=%s",
                session_id, decision_out.selected_action, generation_fingerprint[:12],
            )
        else:
            # Cancel LLM sebelumnya jika aksi berubah
            _cancel_pending_llm(session)

            # Siapkan context untuk LLM
            product_facts = get_facts_for_query(decision_out.required_fact_query)
            evidence_texts = _get_evidence_texts(session, snapshot_out.evidence_comment_ids)
            situation = _build_situation(snapshot_out.audience_state, snapshot_out.support_count)

            # Kick off LLM di background thread
            future = _llm_executor.submit(
                _run_llm_background,
                selected_action=decision_out.selected_action,
                selected_signal=decision_out.selected_signal,
                audience_state=snapshot_out.audience_state,
                slots=decision_out.required_fact_query.get("filters", {}),
                required_fact_query=decision_out.required_fact_query,
                evidence_texts=evidence_texts,
                product_facts=product_facts,
                urgency=urgency,
                situation=situation,
                support_count=snapshot_out.support_count,
                state_confidence=snapshot_out.state_confidence,
                evidence_comment_ids=snapshot_out.evidence_comment_ids,
                session_id=session_id,
            )
            session.pending_llm_future = future
            session.pending_llm_action = decision_out.selected_action
            session.pending_generation_fingerprint = generation_fingerprint
            session.pending_generation_event_ms = timestamp_ms

            logger.info(
                "LLM async dimulai untuk session=%s action=%s",
                session_id, decision_out.selected_action,
            )

    # ===== RETURN FAST RESPONSE (tanpa menunggu LLM) =====
    total_latency = round((time.time() - t_start) * 1000, 1)

    result = PipelineResult(
        session_id=session_id,
        pipeline_status="WAITING_SIGNAL",
        processed_count=processed_count,
        nlp_prediction=nlp_prediction,
        audience_snapshot=snapshot_out,
        action_decision=decision_out,
        priority_event=priority_event_out,
        coach_card=None,
        latency_ms=LatencyMs(nlp=nlp_latency, total=total_latency),
    )
    session.processed_results[comment_id] = result.model_copy(deep=True)
    return result


def _get_evidence_texts(session: SessionState, evidence_ids: List[str]) -> List[str]:
    """Ambil teks asli dari evidence comment IDs.

    Teks disimpan bersama rolling-window entry agar prompt menerima evidence
    aktual, bukan sekadar comment ID.
    """
    evidence_set = set(evidence_ids)
    text_by_id = {
        comment_id: text
        for _, comment_id, _, _, _, text, _ in session.window_entries
        if comment_id in evidence_set
    }
    return [text_by_id[cid] for cid in evidence_ids if cid in text_by_id]
