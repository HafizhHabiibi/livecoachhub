"""
LiveCoachHub Backend — Validator Bridge

Wrapper yang menghubungkan backend dengan Validator
di ai/grounded_llm/Validator/validator.py.

Sesuai PROJECT.MD Bagian 5 Tahap 9:
"Output dicek. PASS diteruskan; FAIL dapat retry sekali;
kegagalan berikutnya menghasilkan safe fallback."
"""

from __future__ import annotations

import importlib.util
import sys
from typing import Callable, List, Optional

from config import VALIDATOR_DIR, KNOWLEDGE_BASE_DIR

# ---------------------------------------------------------------------------
# Import Validator via importlib
# Validator secara internal membutuhkan akses ke Knowledge Base facts,
# jadi kita perlu memastikan path KB juga ada di sys.path
# (validator.py menggunakan relative path FACTS_PATH)
# ---------------------------------------------------------------------------

# Validator menggunakan relative path ke Knowledge Base,
# jadi kita perlu menambah parent dir ke sys.path agar dia bisa resolve
_grounded_llm_dir = str(VALIDATOR_DIR.parent)
if _grounded_llm_dir not in sys.path:
    sys.path.insert(0, _grounded_llm_dir)

_val_file = VALIDATOR_DIR / "validator.py"
_spec = importlib.util.spec_from_file_location("_ai_validator", str(_val_file))
_val_mod = importlib.util.module_from_spec(_spec)
sys.modules["_ai_validator"] = _val_mod
_spec.loader.exec_module(_val_mod)

_validate = _val_mod.validate
_run_with_validation = _val_mod.run_with_validation
ValidationResult = _val_mod.ValidationResult
_ACTION_FALLBACK_TEMPLATES = _val_mod.ACTION_FALLBACK_TEMPLATES


def validate_output(
    raw_json: str,
    product_facts: List[dict],
    max_words: int,
    selected_action: Optional[str] = None,
    slots: Optional[dict] = None,
) -> ValidationResult:
    """Validasi output LLM terhadap policy.

    Args:
        raw_json: Raw JSON string output dari LLM.
        product_facts: Fakta produk yang diberikan sebagai input.
        max_words: Batas kata yang ditetapkan.

    Returns:
        ValidationResult dengan validation_status "PASSED" atau "FALLBACK".
    """
    return _validate(raw_json, product_facts, max_words, selected_action, slots)


def run_with_retry(
    generate_fn: Callable,
    input_payload: dict,
    selected_action: str,
) -> ValidationResult:
    """Jalankan LLM → validate → retry 1x → fallback.

    Args:
        generate_fn: Fungsi generate(input_payload, correction_note) → raw JSON.
        input_payload: Input untuk LLM.
        selected_action: Action terpilih (untuk fallback template).

    Returns:
        ValidationResult — selalu punya response yang aman.
    """
    return _run_with_validation(generate_fn, input_payload, selected_action)


def get_fallback_template(selected_action: str) -> str:
    """Ambil safe fallback template untuk action tertentu."""
    return _ACTION_FALLBACK_TEMPLATES.get(
        selected_action,
        _ACTION_FALLBACK_TEMPLATES.get("NO_ACTION", "Terima kasih sudah nonton!"),
    )
