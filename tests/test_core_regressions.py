"""Dependency-light regression tests for critical competition invariants."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


provenance = load_module(
    "generation_provenance_test",
    ROOT / "backend" / "generation_provenance.py",
)
key_rotation = load_module(
    "key_rotation_test",
    ROOT / "backend" / "key_rotation.py",
)
generation_dedup = load_module(
    "generation_dedup_test",
    ROOT / "backend" / "generation_dedup.py",
)
action_engine = load_module(
    "action_engine_test",
    ROOT / "AI" / "LLM" / "grounded_llm" / "Action Engine" / "action_engine.py",
)
taxonomy_adapter = load_module(
    "taxonomy_adapter_test",
    ROOT / "backend" / "taxonomy_adapter" / "adapter.py",
)
slot_extractor = load_module(
    "slot_extractor_test",
    ROOT / "backend" / "slot_extractor" / "extractor.py",
)
knowledge_base = load_module(
    "knowledge_base_test",
    ROOT / "AI" / "LLM" / "grounded_llm" / "Knowledge Base" / "knowledge_base.py",
)
validator = load_module(
    "validator_test",
    ROOT / "AI" / "LLM" / "grounded_llm" / "Validator" / "validator.py",
)

config_stub = types.ModuleType("config")
config_stub.WINDOW_SECONDS = 60
sys.modules["config"] = config_stub
session_module = load_module("session", ROOT / "backend" / "session.py")
window_module = load_module(
    "rolling_window_test",
    ROOT / "backend" / "rolling_window" / "window.py",
)


class GenerationProvenanceTests(unittest.TestCase):
    def test_gemini_pass_is_card_ready(self):
        outcome = provenance.resolve_generation_outcome("PASSED", ["GEMINI"])
        self.assertEqual(outcome.provider, "GEMINI")
        self.assertFalse(outcome.fallback_used)
        self.assertEqual(outcome.pipeline_status, "CARD_READY")

    def test_valid_template_is_still_fallback(self):
        outcome = provenance.resolve_generation_outcome("PASSED", ["TEMPLATE"])
        self.assertEqual(outcome.provider, "TEMPLATE")
        self.assertTrue(outcome.fallback_used)
        self.assertEqual(outcome.pipeline_status, "FALLBACK")

    def test_validator_fallback_overrides_gemini_attempt(self):
        outcome = provenance.resolve_generation_outcome("FALLBACK", ["GEMINI", "GEMINI"])
        self.assertEqual(outcome.provider, "TEMPLATE")
        self.assertTrue(outcome.fallback_used)
        self.assertEqual(outcome.pipeline_status, "FALLBACK")


class KeyRotationTests(unittest.TestCase):
    def test_three_keys_are_attempted_once_from_every_start(self):
        expected = {
            0: (0, 1, 2),
            1: (1, 2, 0),
            2: (2, 0, 1),
        }
        for start, order in expected.items():
            with self.subTest(start=start):
                self.assertEqual(key_rotation.key_attempt_order(3, start), order)

    def test_dynamic_key_counts_never_skip_or_repeat(self):
        for key_count in (1, 2, 5, 6):
            for start in range(key_count):
                with self.subTest(key_count=key_count, start=start):
                    order = key_rotation.key_attempt_order(key_count, start)
                    self.assertEqual(len(order), key_count)
                    self.assertEqual(set(order), set(range(key_count)))

    def test_empty_key_list_has_no_attempts(self):
        self.assertEqual(key_rotation.key_attempt_order(0, 0), ())

    def test_llm_client_uses_snapshot_attempt_order(self):
        source = (ROOT / "backend" / "llm_client.py").read_text(encoding="utf-8")
        self.assertIn("key_attempt_order(len(keys), _gemini_key_index)", source)
        self.assertNotIn("(_gemini_key_index + attempt) % len(keys)", source)


class GenerationDedupTests(unittest.TestCase):
    def make_fingerprint(self, evidence=("CMT-1", "CMT-2")):
        return generation_dedup.build_generation_fingerprint(
            "SHOW_SIZE_GUIDE",
            "SIZE_FRICTION",
            evidence,
            ("SIZE_GUIDE",),
        )

    def test_same_valid_context_is_reused(self):
        fingerprint = self.make_fingerprint()
        self.assertTrue(generation_dedup.should_reuse_generation(
            "SHOW_SIZE_GUIDE", "SHOW_SIZE_GUIDE",
            fingerprint, fingerprint, "CARD_READY", 60_000, 1_000, 30_000,
        ))

    def test_material_evidence_change_requires_generation(self):
        self.assertFalse(generation_dedup.should_reuse_generation(
            "SHOW_SIZE_GUIDE", "SHOW_SIZE_GUIDE",
            self.make_fingerprint(("CMT-2", "CMT-3")),
            self.make_fingerprint(),
            "CARD_READY",
            5_000,
            1_000,
            30_000,
        ))

    def test_fallback_is_reused_only_during_cooldown(self):
        fingerprint = self.make_fingerprint()
        self.assertTrue(generation_dedup.should_reuse_generation(
            "SHOW_SIZE_GUIDE", "SHOW_SIZE_GUIDE",
            fingerprint, fingerprint, "FALLBACK", 29_999, 0, 30_000,
        ))
        self.assertFalse(generation_dedup.should_reuse_generation(
            "SHOW_SIZE_GUIDE", "SHOW_SIZE_GUIDE",
            fingerprint, fingerprint, "FALLBACK", 30_000, 0, 30_000,
        ))

    def test_fallback_cooldown_ignores_minor_evidence_change(self):
        self.assertTrue(generation_dedup.should_reuse_generation(
            "SHOW_SIZE_GUIDE", "SHOW_SIZE_GUIDE",
            self.make_fingerprint(("CMT-2", "CMT-3")),
            self.make_fingerprint(),
            "FALLBACK",
            10_000,
            0,
            30_000,
        ))


class UniqueUserThresholdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rules = ROOT / "AI" / "LLM" / "grounded_llm" / "Action Engine" / "action_rules.json"
        cls.engine = action_engine.ActionEngine(rules_path=rules)

    def make_signal(self, support: int, unique_users: int):
        return action_engine.WindowIntentSignal(
            intent="SIZE_RECOMMENDATION",
            support_count=support,
            avg_confidence=0.9,
            unique_user_count=unique_users,
            evidence_comment_ids=["CMT-1", "CMT-2"],
        )

    def test_one_user_cannot_create_trend(self):
        snapshot, decision = self.engine.evaluate([self.make_signal(4, 1)])
        self.assertEqual(snapshot.state, "NO_CLEAR_SIGNAL")
        self.assertEqual(decision.selected_action, "NO_ACTION")

    def test_two_users_can_create_trend(self):
        snapshot, decision = self.engine.evaluate([self.make_signal(2, 2)])
        self.assertEqual(snapshot.state, "SIZE_FRICTION")
        self.assertEqual(decision.selected_action, "SHOW_SIZE_GUIDE")


class RollingWindowIdentityTests(unittest.TestCase):
    def test_unique_users_and_evidence_text_are_preserved(self):
        session = session_module.SessionState(session_id="TEST", product_id="TSHIRT-01")
        window_module.add_signal(session, 1000, "CMT-1", "USR-1", "SIZE_RECOMMENDATION", 0.9, "size apa")
        window_module.add_signal(session, 2000, "CMT-2", "USR-1", "SIZE_RECOMMENDATION", 0.8, "bb 55", {"body_weight": 55})
        window_module.add_signal(session, 3000, "CMT-3", "USR-2", "SIZE_RECOMMENDATION", 0.85, "pilih m atau l", {"requested_size": "M"})

        signals = window_module.get_window_signals(session, 3000)

        self.assertEqual(signals[0].support_count, 3)
        self.assertEqual(signals[0].unique_user_count, 2)
        self.assertEqual(session.window_entries[0][-2], "size apa")
        self.assertEqual(signals[0].evidence_comments, ["size apa", "bb 55", "pilih m atau l"])
        self.assertEqual(signals[0].slots_summary["requested_size"], "M")
        self.assertNotIn("body_weight", signals[0].slots_summary)

    def test_slots_from_different_users_are_not_combined(self):
        session = session_module.SessionState(session_id="TEST", product_id="TSHIRT-01")
        window_module.add_signal(
            session, 1000, "CMT-1", "USR-1", "SIZE_RECOMMENDATION", 0.9,
            "bb 55", {"body_weight": 55},
        )
        window_module.add_signal(
            session, 2000, "CMT-2", "USR-2", "SIZE_RECOMMENDATION", 0.9,
            "tb 170", {"body_height": 170},
        )

        slots = window_module.get_window_signals(session, 2000)[0].slots_summary
        self.assertEqual(slots, {"body_height": 170})


class PostNlpRedesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rules = ROOT / "AI" / "LLM" / "grounded_llm" / "Action Engine" / "action_rules.json"
        cls.engine = action_engine.ActionEngine(rules_path=rules)
        facts = ROOT / "AI" / "LLM" / "grounded_llm" / "Knowledge Base" / "product_facts_v2.json"
        cls.kb = knowledge_base.KnowledgeBase(facts_path=facts)

    @staticmethod
    def signal(intent, support, users, confidence=0.9, slots=None):
        return action_engine.WindowIntentSignal(
            intent=intent,
            support_count=support,
            avg_confidence=confidence,
            unique_user_count=users,
            evidence_comment_ids=[f"{intent}-1", f"{intent}-2"],
            slots_summary=slots or {},
        )

    def test_specific_intents_are_not_collapsed(self):
        self.assertEqual(taxonomy_adapter.adapt("size_inquiry"), "SIZE_AVAILABILITY")
        self.assertEqual(taxonomy_adapter.adapt("size_recommendation"), "SIZE_RECOMMENDATION")
        self.assertEqual(taxonomy_adapter.adapt("color_inquiry"), "COLOR_AVAILABILITY")
        self.assertEqual(taxonomy_adapter.adapt("stock_availability"), "STOCK_AVAILABILITY")
        self.assertFalse(taxonomy_adapter.is_actionable("PURCHASE_INTENT"))

    def test_slot_extractor_preserves_explicit_entities(self):
        slots = slot_extractor.extract_slots("BB 55 TB 160, hitam size XL masih ready?")
        self.assertEqual(slots["body_weight"], 55)
        self.assertEqual(slots["body_height"], 160)
        self.assertEqual(slots["requested_color"], "hitam")
        self.assertEqual(slots["requested_size"], "XL")

    def test_dominant_signal_beats_fixed_business_rank(self):
        snapshot, decision = self.engine.evaluate([
            self.signal("SIZE_AVAILABILITY", 2, 2, 0.94),
            self.signal("PRICE_PROMO", 8, 6, 0.90),
        ])
        self.assertEqual(snapshot.state, "PRICE_FRICTION")
        self.assertEqual(decision.selected_action, "EXPLAIN_PRICE_PROMO")

    def test_hysteresis_requires_two_more_unique_users(self):
        _, stable = self.engine.evaluate([
            self.signal("SIZE_RECOMMENDATION", 3, 3),
            self.signal("PRICE_PROMO", 6, 4),
        ], current_signal="SIZE_RECOMMENDATION")
        self.assertEqual(stable.selected_signal, "SIZE_RECOMMENDATION")

        _, switched = self.engine.evaluate([
            self.signal("SIZE_RECOMMENDATION", 3, 3),
            self.signal("PRICE_PROMO", 7, 5),
        ], current_signal="SIZE_RECOMMENDATION")
        self.assertEqual(switched.selected_signal, "PRICE_PROMO")

    def test_snapshot_exposes_ranking_and_retrieval_context(self):
        snapshot, _ = self.engine.evaluate([
            self.signal(
                "SIZE_RECOMMENDATION",
                3,
                2,
                slots={"body_weight": 55, "body_height": 160},
            ),
        ])
        self.assertEqual(snapshot.signals["unique_user_count"], 2)
        self.assertEqual(snapshot.signals["slots_summary"]["body_weight"], 55)

    def test_size_retrieval_uses_body_slots(self):
        facts = self.kb.get_facts_by_query({
            "product_id": "TSHIRT-01",
            "fact_type": "SIZE_GUIDE",
            "topic": "size_recommendation",
            "filters": {"body_weight": 55, "body_height": 160},
        })
        self.assertTrue(facts)
        self.assertEqual(facts[0]["fact_id"], "FACT-TS01-SIZE-M")
        self.assertLessEqual(len(facts), 5)

    def test_size_options_retrieval_is_single_purpose(self):
        facts = self.kb.get_facts_by_query({
            "product_id": "TSHIRT-01",
            "fact_type": "SIZE_GUIDE",
            "topic": "size_options",
            "filters": {},
        })
        self.assertEqual([fact["fact_id"] for fact in facts], ["FACT-TS01-SIZE-OPTIONS-001"])

    def test_validator_rejects_action_misalignment(self):
        raw = json.dumps({
            "response_text": "Size M tersedia untuk pilihan ukuran.",
            "used_fact_ids": [],
            "claims": [],
            "needs_fallback": True,
        })
        result = validator.validate(raw, [], 35, "EXPLAIN_PRICE_PROMO", {})
        self.assertEqual(result.validation_status, "FALLBACK")
        self.assertTrue(any("selected_action" in reason for reason in result.failed_checks))

    def test_validator_rejects_conflicting_color_slot(self):
        raw = json.dumps({
            "response_text": "Warna putih masih tersedia ya kak.",
            "used_fact_ids": [],
            "claims": [],
            "needs_fallback": True,
        })
        result = validator.validate(
            raw, [], 35, "SHOW_COLOR_OPTIONS", {"requested_color": "hitam"},
        )
        self.assertEqual(result.validation_status, "FALLBACK")
        self.assertTrue(any("requested_color" in reason for reason in result.failed_checks))

    def test_validator_checks_unavailable_requested_size_only(self):
        stock_fact = {
            "fact_id": "FACT-TS01-STOCK-ADULT",
            "value": "Stok dewasa S sampai XL ready, sedangkan XXL habis.",
        }
        ready_m = json.dumps({
            "response_text": "Stok size M masih ready ya kak.",
            "used_fact_ids": [stock_fact["fact_id"]],
            "claims": [{"fact_id": stock_fact["fact_id"], "claim_text": "M ready"}],
            "needs_fallback": False,
        })
        result_m = validator.validate(
            ready_m, [stock_fact], 35, "CONFIRM_STOCK", {"requested_size": "M"},
        )
        self.assertEqual(result_m.validation_status, "PASSED")

        ready_xxl = ready_m.replace("size M", "size XXL")
        result_xxl = validator.validate(
            ready_xxl, [stock_fact], 35, "CONFIRM_STOCK", {"requested_size": "XXL"},
        )
        self.assertEqual(result_xxl.validation_status, "FALLBACK")

    def test_validator_understands_real_white_xxl_stock_fact(self):
        facts = self.kb.get_facts_by_query({
            "product_id": "TSHIRT-01",
            "fact_type": "STOCK",
            "topic": "stock_availability",
            "filters": {"requested_color": "putih", "requested_size": "XXL"},
        })
        raw = json.dumps({
            "response_text": "Stok putih size XXL masih ready ya kak.",
            "used_fact_ids": [fact["fact_id"] for fact in facts],
            "claims": [
                {"fact_id": facts[0]["fact_id"], "claim_text": "Putih XXL ready"},
            ],
            "needs_fallback": False,
        })
        result = validator.validate(
            raw, facts, 35, "CONFIRM_STOCK",
            {"requested_color": "putih", "requested_size": "XXL"},
        )
        self.assertEqual(result.validation_status, "FALLBACK")
        self.assertTrue(any("habis" in reason for reason in result.failed_checks))


class FrontendContractTests(unittest.TestCase):
    def test_user_id_is_required_and_forwarded(self):
        schema = (ROOT / "frontend" / "src" / "contracts" / "livecoachSchemas.ts").read_text(encoding="utf-8")
        controller = (ROOT / "frontend" / "src" / "features" / "replay" / "useReplayController.ts").read_text(encoding="utf-8")
        backend_models = (ROOT / "backend" / "models.py").read_text(encoding="utf-8")
        self.assertIn("user_id: z.string().min(1", schema)
        self.assertIn("user_id: comment.user_id", controller)
        self.assertIn("user_id: str = Field(min_length=1)", backend_models)

    def test_generation_provider_is_runtime_validated(self):
        schema = (ROOT / "frontend" / "src" / "contracts" / "livecoachSchemas.ts").read_text(encoding="utf-8")
        self.assertIn("generation_provider: GenerationProviderSchema", schema)

    def test_frontend_does_not_promote_previous_fallback_to_card_ready(self):
        controller = (ROOT / "frontend" / "src" / "features" / "replay" / "useReplayController.ts").read_text(encoding="utf-8")
        self.assertIn("prev?.pipeline_status ?? result.pipeline_status", controller)

    def test_session_card_polling_is_runtime_validated_without_any_cast(self):
        schema = (ROOT / "frontend" / "src" / "contracts" / "livecoachSchemas.ts").read_text(encoding="utf-8")
        api = (ROOT / "frontend" / "src" / "services" / "livecoachApi.ts").read_text(encoding="utf-8")
        controller = (ROOT / "frontend" / "src" / "features" / "replay" / "useReplayController.ts").read_text(encoding="utf-8")
        self.assertIn("SessionCardResponseSchema", schema)
        self.assertIn("parseOrThrow(SessionCardResponseSchema", api)
        self.assertNotIn("pipeline_status as any", controller)

    def test_health_uses_clean_operator_facing_labels(self):
        presentation = (ROOT / "frontend" / "src" / "features" / "replay" / "systemHealth.ts").read_text(encoding="utf-8")
        controller = (ROOT / "frontend" / "src" / "features" / "replay" / "useReplayController.ts").read_text(encoding="utf-8")
        self.assertIn("label: 'Sistem siap'", presentation)
        self.assertIn("label: 'Mode aman'", presentation)
        self.assertIn("Gemini akan diverifikasi saat rekomendasi pertama dibuat.", presentation)
        self.assertNotIn("label: 'Mode fallback'", presentation)
        self.assertIn("void refreshHealth()", controller)

    def test_coach_card_distinguishes_gemini_and_template_provenance(self):
        card = (ROOT / "frontend" / "src" / "components" / "CoachCard.tsx").read_text(encoding="utf-8")
        self.assertIn("Gemini · Sesuai Knowledge Base", card)
        self.assertIn("Template · Berbasis Knowledge Base", card)
        self.assertNotIn("fallback-label", card)

    def test_priority_event_is_visible_and_runtime_validated(self):
        schema = (ROOT / "frontend" / "src" / "contracts" / "livecoachSchemas.ts").read_text(encoding="utf-8")
        page = (ROOT / "frontend" / "src" / "pages" / "DemoPage.tsx").read_text(encoding="utf-8")
        alert = (ROOT / "frontend" / "src" / "components" / "PriorityAlert.tsx").read_text(encoding="utf-8")
        self.assertIn("PriorityEventSchema.nullable()", schema)
        self.assertIn("<PriorityAlert event={controller.latestResult?.priority_event", page)
        self.assertIn("event.text", alert)

    def test_typescript_version_is_pinned_for_eslint_compatibility(self):
        package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual("5.5.4", package["devDependencies"]["typescript"])
        self.assertEqual("5.5.4", lock["packages"][""]["devDependencies"]["typescript"])
        self.assertEqual("5.5.4", lock["packages"]["node_modules/typescript"]["version"])

    def test_retry_transition_and_retryable_flag_are_connected(self):
        state = (ROOT / "frontend" / "src" / "features" / "replay" / "replayState.ts").read_text(encoding="utf-8")
        page = (ROOT / "frontend" / "src" / "pages" / "DemoPage.tsx").read_text(encoding="utf-8")
        self.assertIn("ERROR: ['STARTING', 'RUNNING', 'FILE_READY']", state)
        self.assertIn("controller.canRetryError", page)

    def test_finished_poller_stops_and_does_not_use_async_interval(self):
        controller = (ROOT / "frontend" / "src" / "features" / "replay" / "useReplayController.ts").read_text(encoding="utf-8")
        self.assertIn("uiState !== 'FINISHED' || cardData.is_generating", controller)
        poller = controller.split("BACKGROUND CARD POLLER", 1)[1].split("SLEEP dengan support", 1)[0]
        self.assertNotIn("setInterval(async", poller)

    def test_replay_parser_rejects_descending_timestamps(self):
        parser = (ROOT / "frontend" / "src" / "features" / "replay" / "jsonlParser.ts").read_text(encoding="utf-8")
        self.assertIn("timestamp_ms harus berurutan naik", parser)
        self.assertNotIn("comments.sort(", parser)


class OrchestratorRegressionTests(unittest.TestCase):
    def test_comment_id_cache_is_only_checked_in_comment_pipeline(self):
        source = (ROOT / "backend" / "orchestrator.py").read_text(encoding="utf-8")
        polling_source = source.split("def get_session_card", 1)[1].split("def run_pipeline", 1)[0]
        pipeline_source = source.split("def run_pipeline", 1)[1]

        self.assertNotIn("processed_results.get(comment_id)", polling_source)
        self.assertIn("processed_results.get(comment_id)", pipeline_source)


class ReplayContractTests(unittest.TestCase):
    def test_demo_rows_have_user_identity(self):
        replay_path = ROOT / "data" / "replay" / "comments-demo.jsonl"
        rows = [json.loads(line) for line in replay_path.read_text(encoding="utf-8").splitlines() if line]
        self.assertTrue(rows)
        self.assertTrue(all(row.get("user_id") for row in rows))
        self.assertLess(len({row["user_id"] for row in rows}), len(rows))

if __name__ == "__main__":
    unittest.main()
