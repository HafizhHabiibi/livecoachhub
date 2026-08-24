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
