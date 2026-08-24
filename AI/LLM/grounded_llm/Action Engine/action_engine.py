"""
Action Engine - LiveCoach AI (M3/SCR-3: LLM, Knowledge, Policy)

Tanggung jawab modul ini HANYA satu hal: mengubah agregat sinyal 60 detik
(hasil rolling window dari M2/SCR-2) menjadi SATU audience_snapshot dan
SATU action_decision, mengikuti aturan deterministik di action_rules.json.

Modul ini TIDAK memanggil LLM dan TIDAK menyusun kalimat apa pun -- itu
tanggung jawab Grounded LLM (langkah 3-4). Action Engine hanya memutuskan
"apa yang harus dibicarakan", bukan "bagaimana mengucapkannya".

Kontrak output selaras dengan bagian 10.4 dan 11 dokumen spesifikasi:
- AudienceSnapshot: state, window_seconds, state_confidence, signals, evidence_comment_ids
- ActionDecision: selected_action, selected_signal, action_score,
  required_fact_types, required_fact_query

`source_intents` memakai normalized semantic signal hasil Taxonomy Adapter,
bukan raw label model. Mapping raw intent dan kontrak frontend diuji melalui
regression test di root repository.

RIWAYAT PERBAIKAN (lihat DECISIONS_LOG.md di root folder Lomba untuk detail):
action_rules.json sebelumnya (v1) memakai audience_state/selected_action
custom (mis. STOCK_COLOR_CONCERN, MATERIAL_SAFETY_CONCERN, SHOW_PROMO_INFO)
yang TIDAK cocok dengan enum resmi di Section 4.2 & 11 dokumen spesifikasi.
Per 24 Agustus 2026 rule v3 mempertahankan signal spesifik, menerapkan
dominance-first ranking dan hysteresis, serta menghasilkan structured fact
query. State shipping dan objection tetap ditunda sampai label NLP memadai.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


RULES_PATH = Path(__file__).parent / "action_rules.json"


# ---------------------------------------------------------------------------
# Data contracts (selaras dengan TypeScript contract di dokumen bagian 11)
# ---------------------------------------------------------------------------

@dataclass
class AudienceSnapshot:
    state: str
    window_seconds: int
    state_confidence: float
    signals: Dict[str, Any]
    evidence_comment_ids: List[str]


@dataclass
class ActionDecision:
    selected_action: str
    selected_signal: str
    action_score: float
    required_fact_types: List[str]
    required_fact_query: Dict[str, Any]
    reason: str


@dataclass
class WindowIntentSignal:
    """Satu baris agregat dari rolling window 60 detik milik M2.
    intent -> (jumlah komentar pendukung, confidence rata-rata, contoh comment_id)
    """
    intent: str
    support_count: int
    avg_confidence: float
    unique_user_count: int
    evidence_comment_ids: List[str] = field(default_factory=list)
    evidence_comments: List[str] = field(default_factory=list)
    latest_timestamp_ms: int = 0
    slots_summary: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ActionEngine:
    def __init__(self, rules_path: Path = RULES_PATH):
        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = json.load(f)

        self.threshold = self.rules["threshold_policy"]
        self.tie_break = self.rules["tie_break_policy"]
        self.stability = self.rules.get("stability_policy", {})
        self.states = {s["state"]: s for s in self.rules["audience_states"]}
        self.fallback = self.rules["fallback_state"]

    def _passes_threshold(
        self,
        support_count: int,
        confidence: float,
        unique_user_count: int,
    ) -> bool:
        min_count = self.threshold["min_supporting_comments_60s"]
        min_conf = self.threshold["min_state_confidence"]
        min_unique_users = self.threshold.get("min_unique_users_60s", 1)
        if self.threshold["mode"] == "AND":
            return (
                support_count >= min_count
                and confidence >= min_conf
                and unique_user_count >= min_unique_users
            )
        return (
            support_count >= min_count
            or confidence >= min_conf
        ) and unique_user_count >= min_unique_users

    def evaluate(
        self,
        window_signals: List[WindowIntentSignal],
        window_seconds: int = 60,
        current_signal: Optional[str] = None,
    ) -> tuple[AudienceSnapshot, ActionDecision]:
        """Titik masuk utama. Dipanggil backend setiap kali rolling window
        60 detik diperbarui (bagian 3.2 dokumen: "Backend memperbarui
        rolling window 60 detik... Jika sinyal cukup, Action Engine memilih
        satu action").
        """

        # 1. Map tiap WindowIntentSignal ke audience_state yang relevan,
        #    lalu saring yang lolos threshold.
        candidates = []
        for state_name, rule in self.states.items():
            relevant = [
                sig for sig in window_signals if sig.intent in rule["source_intents"]
            ]
            if not relevant:
                continue

            support_count = sum(s.support_count for s in relevant)
            unique_user_count = sum(s.unique_user_count for s in relevant)
            # confidence gabungan: rata-rata tertimbang jumlah komentar
            total_conf = sum(s.avg_confidence * s.support_count for s in relevant)
            confidence = round(total_conf / support_count, 4) if support_count else 0.0

            if not self._passes_threshold(
                support_count, confidence, unique_user_count
            ):
                continue

            evidence_ids = [cid for s in relevant for cid in s.evidence_comment_ids][:3]
            latest_signal = max(relevant, key=lambda signal: signal.latest_timestamp_ms)

            candidates.append(
                {
                    "state": state_name,
                    "rule": rule,
                    "support_count": support_count,
                    "unique_user_count": unique_user_count,
                    "confidence": confidence,
                    "evidence_comment_ids": evidence_ids,
                    "latest_timestamp_ms": latest_signal.latest_timestamp_ms,
                    "slots_summary": latest_signal.slots_summary,
                }
            )

        # 2. Tidak ada yang lolos threshold -> NO_CLEAR_SIGNAL / NO_ACTION
        if not candidates:
            snapshot = AudienceSnapshot(
                state=self.fallback["state"],
                window_seconds=window_seconds,
                state_confidence=0.0,
                signals={
                    "support_count": 0,
                    "unique_user_count": 0,
                    "latest_timestamp_ms": 0,
                    "slots_summary": {},
                },
                evidence_comment_ids=[],
            )
            decision = ActionDecision(
                selected_action=self.fallback["selected_action"],
                selected_signal="IRRELEVANT",
                action_score=0.0,
                required_fact_types=self.fallback["required_fact_types"],
                required_fact_query=self.fallback.get("required_fact_query", {}),
                reason="Belum ada pola kuat dalam 60 detik terakhir.",
            )
            return snapshot, decision

        # 3. Dominance first; business priority is only the final tie-break.
        candidates.sort(
            key=lambda c: (
                -c["unique_user_count"],
                -c["support_count"],
                -c["confidence"],
                c["rule"]["priority_rank"],
            )
        )
        winner = candidates[0]

        # Hysteresis: keep the current eligible signal unless the challenger
        # has a material unique-user advantage.
        if current_signal and winner["rule"]["source_intents"][0] != current_signal:
            current = next(
                (
                    candidate
                    for candidate in candidates
                    if current_signal in candidate["rule"]["source_intents"]
                ),
                None,
            )
            margin = int(self.stability.get("switch_unique_user_margin", 2))
            if current and winner["unique_user_count"] < current["unique_user_count"] + margin:
                winner = current

        rule = winner["rule"]
        selected_signal = rule["source_intents"][0]

        snapshot = AudienceSnapshot(
            state=winner["state"],
            window_seconds=window_seconds,
            state_confidence=winner["confidence"],
            signals={
                "support_count": winner["support_count"],
                "unique_user_count": winner["unique_user_count"],
                "latest_timestamp_ms": winner["latest_timestamp_ms"],
                "slots_summary": winner["slots_summary"],
            },
            evidence_comment_ids=winner["evidence_comment_ids"],
        )

        # Explainable confidence of the selected signal. Dominance itself is
        # represented by support and unique-user counts, not hidden weights.
        action_score = winner["confidence"]

        fact_query = dict(rule.get("required_fact_query", {}))
        fact_query["filters"] = dict(winner["rule"].get("fact_filters", {}))
        fact_query["filters"].update(
            next(
                (
                    signal.slots_summary
                    for signal in window_signals
                    if signal.intent == selected_signal
                ),
                {},
            )
        )

        decision = ActionDecision(
            selected_action=rule["selected_action"],
            selected_signal=selected_signal,
            action_score=action_score,
            required_fact_types=rule["required_fact_types"],
            required_fact_query=fact_query,
            reason=rule["reason_template"].format(support_count=winner["support_count"]),
        )

        return snapshot, decision


# ---------------------------------------------------------------------------
# Demo / sanity check manual (bukan unit test formal -- lihat catatan di bawah)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = ActionEngine()

    # Simulasi window 60 detik: tren harga lebih dominan daripada size.
    window = [
        WindowIntentSignal(
            intent="SIZE_RECOMMENDATION",
            support_count=4,
            avg_confidence=0.91,
            unique_user_count=4,
            evidence_comment_ids=["CMT-018", "CMT-014"],
        ),
        WindowIntentSignal(
            intent="PRICE_PROMO",
            support_count=6,
            avg_confidence=0.9,
            unique_user_count=5,
            evidence_comment_ids=["CMT-020", "CMT-021"],
        ),
    ]

    snapshot, decision = engine.evaluate(window)
    print("AudienceSnapshot:", snapshot)
    print("ActionDecision:", decision)
