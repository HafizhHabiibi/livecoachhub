"""
LiveCoachHub Backend — Knowledge Base / Fact Retrieval

Wrapper yang menghubungkan backend dengan KnowledgeBase
di ai/grounded_llm/Knowledge Base/knowledge_base.py.

Sesuai PROJECT.MD Bagian 5 Tahap 7:
"required_fact_types dari main action digunakan untuk mengambil
hanya fakta produk yang relevan dari Knowledge Base."
"""

from __future__ import annotations

import importlib.util
from typing import Dict, List, Optional

from config import KNOWLEDGE_BASE_DIR, PRODUCT_FACTS_PATH

# ---------------------------------------------------------------------------
# Import KnowledgeBase via importlib (menghindari nama bentrok)
# ---------------------------------------------------------------------------

_kb_file = KNOWLEDGE_BASE_DIR / "knowledge_base.py"
_spec = importlib.util.spec_from_file_location("_ai_knowledge_base", str(_kb_file))
_kb_mod = importlib.util.module_from_spec(_spec)
import sys as _sys
_sys.modules["_ai_knowledge_base"] = _kb_mod
_spec.loader.exec_module(_kb_mod)

_KnowledgeBase = _kb_mod.KnowledgeBase

# Singleton instance — di-load sekali saat startup
_kb = _KnowledgeBase(facts_path=PRODUCT_FACTS_PATH)


def get_facts(required_fact_types: List[str]) -> List[dict]:
    """Ambil fakta produk yang relevan berdasarkan required_fact_types.

    Args:
        required_fact_types: List fact types yang dibutuhkan action,
            contoh: ["SIZE_GUIDE"], ["STOCK", "PRICE_PROMO"].

    Returns:
        List of dict {fact_id, value} — hanya fakta publik.
        Return [] jika fact_types kosong.
    """
    if not required_fact_types:
        return []
    return _kb.get_facts(required_fact_types)


def get_facts_for_query(required_fact_query: dict) -> List[dict]:
    """Retrieve a small grounded context using product, topic, and slots."""
    return _kb.get_facts_by_query(required_fact_query)


def get_fact_by_id(fact_id: str) -> Optional[dict]:
    """Lookup satu fact berdasarkan ID. Dipakai Validator."""
    return _kb.get_by_id(fact_id)


def get_all_public_fact_ids() -> List[str]:
    """Return semua fact_id publik. Untuk diagnostik."""
    return _kb.all_public_fact_ids()


def get_product_info() -> Dict[str, str]:
    """Return info produk dasar. Dipakai /api/v1/demo-config."""
    return {
        "product_id": _kb.product_id,
        "schema_version": _kb.schema_version,
    }
