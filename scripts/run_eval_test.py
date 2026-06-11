#!/usr/bin/env python3
"""Offline unit tests for the run_eval execution runtime.

Stdlib-only. These tests stub the ``call_model`` seam by replacing the module
attribute, so they never import ``anthropic``, hit the network, or read an API
key. Run with::

    python3 scripts/run_eval_test.py
"""

import importlib
import sys
import unittest
from pathlib import Path

# Make `run_eval` importable as a top-level module regardless of cwd.
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

run_eval = importlib.import_module("run_eval")


def _case(case_id="c1", prompt="hello"):
    return {"id": case_id, "prompt": prompt, "assertions": []}


class ExecuteSingleTest(unittest.TestCase):
    def setUp(self):
        # Preserve and restore the real seam around each test.
        self._orig_call_model = run_eval.call_model
        self.addCleanup(setattr, run_eval, "call_model", self._orig_call_model)

    def test_success_populates_fields_and_executed_true(self):
        def fake_call_model(system, messages, model, max_tokens, timeout_s):
            return {
                "output": "the answer",
                "tokens": {"input": 11, "output": 7},
                "raw_transcript_turn": {"role": "assistant", "content": "the answer"},
            }

        run_eval.call_model = fake_call_model

        result = run_eval.execute_single(
            skill_text="SYSTEM",
            case=_case(),
            trial_id=0,
            timeout_ms=120000,
            model="some-model",
            max_tokens=128000,
        )

        self.assertTrue(result.executed)
        self.assertIsNone(result.error)
        self.assertEqual(result.output, "the answer")
        self.assertEqual(result.tokens, {"input": 11, "output": 7})
        # Transcript = input messages (the user turn) + the assistant turn.
        self.assertEqual(result.transcript[0]["role"], "user")
        self.assertEqual(
            result.transcript[-1],
            {"role": "assistant", "content": "the answer"},
        )

    def test_seam_raises_populates_error_and_executed_false(self):
        def fake_call_model(system, messages, model, max_tokens, timeout_s):
            raise RuntimeError("boom")

        run_eval.call_model = fake_call_model

        result = run_eval.execute_single(
            skill_text="SYSTEM",
            case=_case(),
            trial_id=0,
            timeout_ms=120000,
            model="some-model",
            max_tokens=128000,
        )

        self.assertFalse(result.executed)
        self.assertIsNotNone(result.error)
        self.assertIn("boom", result.error)

    def test_timeout_maps_to_error_and_executed_false(self):
        class _Timeout(Exception):
            pass

        def fake_call_model(system, messages, model, max_tokens, timeout_s):
            raise _Timeout("deadline exceeded")

        run_eval.call_model = fake_call_model

        result = run_eval.execute_single(
            skill_text="SYSTEM",
            case=_case(),
            trial_id=0,
            timeout_ms=50,
            model="some-model",
            max_tokens=128000,
        )

        self.assertFalse(result.executed)
        self.assertIsNotNone(result.error)
        self.assertIn("deadline exceeded", result.error)

    def test_tokens_normalized_to_input_output_keys(self):
        def fake_call_model(system, messages, model, max_tokens, timeout_s):
            return {
                "output": "x",
                "tokens": {"input": 3, "output": 4},
                "raw_transcript_turn": {"role": "assistant", "content": "x"},
            }

        run_eval.call_model = fake_call_model

        result = run_eval.execute_single(
            skill_text="SYSTEM",
            case=_case(),
            trial_id=0,
            timeout_ms=120000,
            model="some-model",
            max_tokens=128000,
        )

        self.assertEqual(set(result.tokens.keys()), {"input", "output"})


class ModuleContractTest(unittest.TestCase):
    def test_anthropic_not_imported_at_collection(self):
        # The SDK import is local to call_model, so importing run_eval must not
        # pull anthropic into sys.modules.
        self.assertNotIn("anthropic", sys.modules)

    def test_executed_field_present(self):
        import dataclasses

        fields = {f.name for f in dataclasses.fields(run_eval.ExecutionResult)}
        self.assertIn("executed", fields)


if __name__ == "__main__":
    unittest.main()
