"""
LiveCoachHub Backend — Taxonomy Adapter

Menjembatani perbedaan label antara output IndoBERT (fashion intent NLP)
dan vocabulary yang dimengerti Action Engine (sinyal canonical).

Sesuai PROJECT.MD Bagian 5 Tahap 5 dan tabel mapping:
"Label NLP dipetakan ke signal vocabulary yang dimengerti Action Engine."

Mapping ini HARUS di-freeze sebelum submission (P0 di Definition of Done).
"""

from __future__ import annotations

from typing import Optional


# ---------------------------------------------------------------------------
# Mapping Table — PROJECT.MD Section tabel mapping
# ---------------------------------------------------------------------------
# Key   = label output IndoBERT (lowercase, sesuai model fine-tune)
# Value = canonical signal yang dimengerti Action Engine (UPPERCASE, sesuai action_rules.json)

NLP_TO_CANONICAL = {
    # Preserve the distinction already learned by IndoBERT.
    "size_inquiry": "SIZE_AVAILABILITY",
    "size_recommendation": "SIZE_RECOMMENDATION",

    # Color options and stock-by-variant require different actions/facts.
    "color_inquiry": "COLOR_AVAILABILITY",
    "stock_availability": "STOCK_AVAILABILITY",

    # Price/promo → PRICE_PROMO
    "price_inquiry": "PRICE_PROMO",

    # Purchase intent → PURCHASE_INTENT (khusus Priority Lane)
    "purchase_intent": "PURCHASE_INTENT",

    # Product inquiry → PRODUCT_DETAIL (termasuk pertanyaan material)
    "product_inquiry": "PRODUCT_DETAIL",

    # Not relevant → IRRELEVANT
    "not_relevant": "IRRELEVANT",

    # Fallback: jika label 'other' muncul (confidence di bawah threshold)
    "other": "IRRELEVANT",
}

# Signal excluded from Trend Lane. Purchase intent has its own Priority Lane.
NON_ACTIONABLE_SIGNALS = {"IRRELEVANT", "PURCHASE_INTENT"}

# Mapping canonical signal → CommentIntent enum frontend
# Dipakai untuk membangun NlpPrediction.intents yang sesuai kontrak frontend
CANONICAL_TO_FRONTEND_INTENT = {
    "SIZE_AVAILABILITY": "SIZE_AVAILABILITY",
    "SIZE_RECOMMENDATION": "SIZE_RECOMMENDATION",
    "COLOR_AVAILABILITY": "COLOR_AVAILABILITY",
    "STOCK_AVAILABILITY": "STOCK_AVAILABILITY",
    "PRICE_PROMO": "PRICE_PROMO",
    "PURCHASE_INTENT": "PURCHASE_INTENT",
    "PRODUCT_DETAIL": "PRODUCT_DETAIL",
    "IRRELEVANT": "IRRELEVANT",
}


def adapt(nlp_intent: str) -> str:
    """Map label IndoBERT ke canonical signal Action Engine.

    Args:
        nlp_intent: Label output dari IndoBERT (lowercase).

    Returns:
        Canonical signal (UPPERCASE) yang dimengerti Action Engine.
        Jika label tidak dikenali, return 'IRRELEVANT'.
    """
    return NLP_TO_CANONICAL.get(nlp_intent, "IRRELEVANT")


def to_frontend_intent(canonical_signal: str) -> str:
    """Map canonical signal ke CommentIntent enum frontend.

    Args:
        canonical_signal: Signal canonical (UPPERCASE).

    Returns:
        CommentIntent string sesuai Zod schema frontend.
    """
    return CANONICAL_TO_FRONTEND_INTENT.get(canonical_signal, "IRRELEVANT")


def is_actionable(canonical_signal: str) -> bool:
    """Cek apakah sinyal ini layak dihitung di rolling window.

    IRRELEVANT tidak masuk Trend Lane; PURCHASE_INTENT masuk Priority Lane.
    """
    return canonical_signal not in NON_ACTIONABLE_SIGNALS
