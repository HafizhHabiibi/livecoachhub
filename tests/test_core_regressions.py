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
            intent="SIZE_VARIANT",
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
        window_module.add_signal(session, 1000, "CMT-1", "USR-1", "SIZE_VARIANT", 0.9, "size apa")
        window_module.add_signal(session, 2000, "CMT-2", "USR-1", "SIZE_VARIANT", 0.8, "bb 55")
        window_module.add_signal(session, 3000, "CMT-3", "USR-2", "SIZE_VARIANT", 0.85, "pilih m atau l")

        signals = window_module.get_window_signals(session, 3000)

        self.assertEqual(signals[0].support_count, 3)
        self.assertEqual(signals[0].unique_user_count, 2)
        self.assertEqual(session.window_entries[0][-1], "size apa")


class FrontendContractTests(unittest.TestCase):
    def test_user_id_is_required_and_forwarded(self):
        schema = (ROOT / "frontend" / "src" / "contracts" / "livecoachSchemas.ts").read_text(encoding="utf-8")
        controller = (ROOT / "frontend" / "src" / "features" / "replay" / "useReplayController.ts").read_text(encoding="utf-8")
        self.assertIn("user_id: z.string().min(1", schema)
        self.assertIn("user_id: comment.user_id", controller)

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

    def test_showcase_replay_contract_and_phase_order(self):
        replay_path = ROOT / "data" / "replay" / "comments-demo-showcase.jsonl"
        rows = [json.loads(line) for line in replay_path.read_text(encoding="utf-8").splitlines() if line]
        required = {"comment_id", "user_id", "timestamp_ms", "text"}
        self.assertEqual(len(rows), 30)
        self.assertTrue(all(required <= row.keys() for row in rows))
        self.assertEqual(len({row["comment_id"] for row in rows}), len(rows))
        self.assertEqual([row["timestamp_ms"] for row in rows], sorted(row["timestamp_ms"] for row in rows))

        # Dua user unik per trigger phase, berurutan dari priority rendah ke tinggi.
        trigger_phases = [rows[0:2], rows[4:6], rows[8:10], rows[12:14], rows[16:18]]
        self.assertTrue(all(len({row["user_id"] for row in phase}) == 2 for phase in trigger_phases))
        self.assertEqual([phase[0]["timestamp_ms"] for phase in trigger_phases], [0, 12000, 24000, 36000, 48000])


if __name__ == "__main__":
    unittest.main()
