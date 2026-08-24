"""Rule-based entity extraction for the single-product fashion MVP.

The intent classifier answers *what* a comment is about. This module keeps
small, explicit entities needed by deterministic retrieval without adding a
second probabilistic model.
"""

from __future__ import annotations

import re
from typing import Any, Dict


_SIZE_PATTERN = re.compile(r"(?<![a-z0-9])(xxxl|xxl|xl|xs|s|m|l)(?![a-z0-9])", re.IGNORECASE)
_WEIGHT_PATTERN = re.compile(r"(?:\bbb\b|berat(?:\s+badan)?)\s*[:=]?\s*(\d{2,3})(?:[.,]\d+)?\s*(?:kg)?\b", re.IGNORECASE)
_HEIGHT_PATTERN = re.compile(r"(?:\btb\b|tinggi(?:\s+badan)?)\s*[:=]?\s*(\d{2,3})(?:[.,]\d+)?\s*(?:cm)?\b", re.IGNORECASE)

_COLOR_ALIASES = {
    "hitam": "hitam",
    "item": "hitam",
    "black": "hitam",
    "putih": "putih",
    "white": "putih",
    "navy": "navy",
    "biru dongker": "navy",
    "abu misty": "abu misty",
    "abu-abu": "abu misty",
    "abu": "abu misty",
    "grey": "abu misty",
    "gray": "abu misty",
    "maroon": "maroon",
    "merah marun": "maroon",
    "sage": "sage",
    "army": "army",
    "pink": "pink",
    "cream": "cream",
    "krem": "cream",
    "coklat": "coklat",
    "putih tulang": "putih tulang",
}

_PRODUCT_ATTRIBUTE_KEYWORDS = {
    "material": ("bahan", "kain", "cotton", "katun", "gsm", "tebal", "nerawang"),
    "care": ("cuci", "dicuci", "setrika", "perawatan", "melar", "luntur"),
    "cutting": ("cutting", "potongan", "fit", "oversize", "regular"),
    "model": ("model", "lengan", "unisex"),
    "color": ("warna", "color"),
}


def _first_color(text: str) -> str | None:
    # Longest aliases first so "abu misty" wins over "abu".
    for alias in sorted(_COLOR_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE):
            return _COLOR_ALIASES[alias]
    return None


def _product_attribute(text: str) -> str | None:
    lowered = text.lower()
    for attribute, keywords in _PRODUCT_ATTRIBUTE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return attribute
    return None


def extract_slots(text: str) -> Dict[str, Any]:
    """Extract only high-confidence slots explicitly present in ``text``."""
    slots: Dict[str, Any] = {}

    size_match = _SIZE_PATTERN.search(text)
    if size_match:
        slots["requested_size"] = size_match.group(1).upper()

    color = _first_color(text)
    if color:
        slots["requested_color"] = color

    weight_match = _WEIGHT_PATTERN.search(text)
    if weight_match:
        weight = int(weight_match.group(1))
        if 20 <= weight <= 300:
            slots["body_weight"] = weight

    height_match = _HEIGHT_PATTERN.search(text)
    if height_match:
        height = int(height_match.group(1))
        if 70 <= height <= 250:
            slots["body_height"] = height

    attribute = _product_attribute(text)
    if attribute:
        slots["product_attribute"] = attribute

    lowered = text.lower()
    if any(keyword in lowered for keyword in ("promo", "diskon", "voucher", "potongan")):
        slots["price_topic"] = "promo"
    elif any(keyword in lowered for keyword in ("harga", "berapa", "brp", "rp")):
        slots["price_topic"] = "price"

    return slots
