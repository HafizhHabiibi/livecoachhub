"""
Knowledge Base loader & retrieval helper - LiveCoach AI (M3/SCR-3)

Menjawab gap yang ditemukan saat review: sebelumnya tidak ada kode yang
menjembatani ActionDecision.required_fact_types (output Action Engine, lihat
../Action Engine/action_engine.py) dengan daftar fact aktual yang harus
dikirim ke Grounded LLM. Modul ini menyediakan jembatan itu.

Cara pakai (lihat juga blok __main__ di bawah untuk contoh langsung):

    from knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    facts = kb.get_facts(["SIZE_GUIDE"])          # -> List[dict fact_id + value]
    facts = kb.get_facts(["STOCK", "PRICE_PROMO"]) # boleh multi fact_type sekaligus

Catatan penting:
- Pencocokan required_fact_types dilakukan terhadap field "fact_type" (nilai resmi
  sesuai kontrak dokumen Section 4.2/10.4), BUKAN terhadap field "category" yang
  lebih granular (mis. SIZE_GUIDE_ANAK, SIZE_GUIDE_DEWASA_LOKAL). "category" tetap
  disimpan di data mentah untuk kebutuhan organisasi/QA internal tim, tapi tidak
  dipakai untuk logic pencocokan kontrak.
- Fact dengan internal_only=true (saat ini hanya FACT-TS01-STANDARD-REFERENCE-001)
  TIDAK PERNAH dikembalikan oleh get_facts(), supaya tidak pernah bocor ke prompt
  LLM atau ke penonton. Fact ini murni referensi standar teknis internal tim.
- required_fact_types untuk state SHIPPING_FRICTION / OBJECTION_SPIKE / PURCHASE_MOMENT
  (fact_type SHIPPING / FAQ_PLAYBOOK / CHECKOUT_GUIDE) SUDAH bisa di-query lewat modul
  ini (fact-nya sudah ditag), walau action_rules.json belum mengaktifkan ketiga state
  itu. Lihat README.md di folder ini dan di ../Action Engine/README.md untuk detail
  kenapa ketiga ini sengaja ditunda (bukan kelupaan).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

FACTS_PATH = Path(__file__).parent / "product_facts_v2.json"


class KnowledgeBase:
    def __init__(self, facts_path: Path = FACTS_PATH):
        with open(facts_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.schema_version: str = raw["schema_version"]
        self.product_id: str = raw["product_id"]
        self._facts: List[dict] = raw["facts"]
        self._by_id: Dict[str, dict] = {f["fact_id"]: f for f in self._facts}

    def get_facts(self, fact_types: List[str]) -> List[dict]:
        """Kembalikan semua fact publik (internal_only=false/tidak ada) yang
        fact_type-nya termasuk dalam `fact_types`. Urutan mengikuti urutan asli
        di product_facts_v2.json supaya deterministik antar pemanggilan."""
        wanted = set(fact_types)
        return [
            {"fact_id": f["fact_id"], "value": f["value"]}
            for f in self._facts
            if not f.get("internal_only") and f.get("fact_type") in wanted
        ]

    @staticmethod
    def _range_contains(text: str, label: str, value: int) -> bool:
        pattern = re.compile(rf"{label}\s*(\d+)\s*-\s*(\d+)", re.IGNORECASE)
        return any(int(low) <= value <= int(high) for low, high in pattern.findall(text))

    @staticmethod
    def _size_group(size: str) -> str:
        return "adult" if size.upper() in {"XS", "S", "M", "L", "XL", "XXL", "XXXL"} else ""

    def _serialize(self, fact: dict, topic: str, attributes: Optional[dict] = None) -> dict:
        return {
            "fact_id": fact["fact_id"],
            "value": fact["value"],
            "fact_type": fact.get("fact_type"),
            "topic": fact.get("topic", topic),
            "product_id": fact.get("product_id", self.product_id),
            "attributes": fact.get("attributes", attributes or {}),
        }

    def get_facts_by_query(self, query: dict, limit: int = 5) -> List[dict]:
        """Conservative structured retrieval for the post-NLP pipeline.

        Matching order is exact slots, partial slots, then a small generic
        subset. An empty result explicitly means that no sufficient fact is
        available and generation must use a non-claiming fallback.
        """
        if not query or query.get("product_id", self.product_id) != self.product_id:
            return []

        fact_type = query.get("fact_type")
        topic = query.get("topic", "")
        filters = query.get("filters") or {}
        public = [
            fact for fact in self._facts
            if not fact.get("internal_only") and fact.get("fact_type") == fact_type
        ]

        if topic == "size_options":
            fact = next((f for f in public if f["fact_id"] == "FACT-TS01-SIZE-OPTIONS-001"), None)
            return [self._serialize(fact, topic)] if fact else []

        if topic == "size_recommendation":
            requested_size = str(filters.get("requested_size", "")).upper()
            body_weight = filters.get("body_weight")
            body_height = filters.get("body_height")
            scored = []
            for fact in public:
                if fact.get("category") != "SIZE_GUIDE_DEWASA":
                    continue
                score = 0
                fact_id = fact["fact_id"].upper()
                value = fact["value"]
                if requested_size and fact_id.endswith(f"-SIZE-{requested_size}"):
                    score += 4
                if isinstance(body_weight, int) and self._range_contains(value, "BB", body_weight):
                    score += 3
                if isinstance(body_height, int) and self._range_contains(value, "TB", body_height):
                    score += 3
                if score:
                    scored.append((score, fact))
            scored.sort(key=lambda item: (-item[0], item[1]["fact_id"]))
            return [self._serialize(fact, topic, filters) for _, fact in scored[:limit]]

        if topic == "color_options":
            fact = next((f for f in public if f["fact_id"] == "FACT-TS01-COLOR-001"), None)
            return [self._serialize(fact, topic)] if fact else []

        if topic == "stock_availability":
            color = str(filters.get("requested_color", "")).lower()
            size = str(filters.get("requested_size", "")).upper()
            selected: List[dict] = []
            if color:
                selected.extend(f for f in public if color in f["value"].lower())
                # The product color-options fact is supporting evidence for
                # colors whose stock rule is expressed generically.
                if not selected:
                    color_fact = next(
                        (f for f in self._facts if f["fact_id"] == "FACT-TS01-COLOR-001"),
                        None,
                    )
                    if color_fact and color in color_fact["value"].lower():
                        selected.append(color_fact)
            if size and self._size_group(size) == "adult":
                adult = next((f for f in public if f["fact_id"] == "FACT-TS01-STOCK-ADULT"), None)
                if adult:
                    selected.append(adult)
            if not selected and not filters:
                selected = public[:limit]
            unique = {fact["fact_id"]: fact for fact in selected}
            return [self._serialize(fact, topic, filters) for fact in list(unique.values())[:limit]]

        if topic == "price_promo":
            price_topic = filters.get("price_topic")
            category = "PROMO" if price_topic == "promo" else "PRICE" if price_topic == "price" else None
            selected = [f for f in public if category is None or f.get("category") == category]
            return [self._serialize(fact, topic, filters) for fact in selected[:limit]]

        if topic == "product_detail":
            attribute = filters.get("product_attribute")
            categories = {
                "material": {"MATERIAL", "MATERIAL_SAFETY"},
                "care": {"CARE_INSTRUCTION"},
                "cutting": {"PRODUCT_DESCRIPTION", "MODEL_INFO"},
                "model": {"MODEL_INFO", "PRODUCT_DESCRIPTION"},
                "color": {"COLOR_VARIANT"},
            }.get(attribute)
            selected = [f for f in public if categories is None or f.get("category") in categories]
            return [self._serialize(fact, topic, filters) for fact in selected[:limit]]

        return [self._serialize(fact, topic, filters) for fact in public[:limit]]

    def get_by_id(self, fact_id: str) -> Optional[dict]:
        """Lookup satu fact by ID -- dipakai Validator untuk cek used_fact_ids."""
        f = self._by_id.get(fact_id)
        if f is None or f.get("internal_only"):
            return None
        return {"fact_id": f["fact_id"], "value": f["value"]}

    def all_public_fact_ids(self) -> List[str]:
        return [f["fact_id"] for f in self._facts if not f.get("internal_only")]


if __name__ == "__main__":
    kb = KnowledgeBase()
    print(f"Loaded {len(kb.all_public_fact_ids())} public facts (schema {kb.schema_version}).")

    for ft in ["SIZE_GUIDE", "STOCK", "PRICE_PROMO", "PRODUCT_DETAIL", "SHIPPING", "FAQ_PLAYBOOK", "CHECKOUT_GUIDE"]:
        matches = kb.get_facts([ft])
        print(f"  fact_type={ft:<15} -> {len(matches)} fact")

    print("\nContoh required_fact_types=['SIZE_GUIDE'] (potongan pertama):")
    for f in kb.get_facts(["SIZE_GUIDE"])[:3]:
        print(" -", f["fact_id"], ":", f["value"][:70], "...")
