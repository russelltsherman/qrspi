#!/usr/bin/env python3
"""Unit tests for diagnose.py — stdlib only, run with python3.

    python3 scripts/diagnose_test.py

Slice 2 scope (plan §2.11, structure §Slice 2 Verification): the shared LLM seam
`meta_agent.complete` is mocked, and we assert:
  (a) a grounded `{category, rationale}` is parsed from the mocked response and the
      downstream-consumed keys (`case_id`, `score`, `categories`, `failed_assertions`)
      are preserved;
  (b) the `ALL_PASSING` / empty-failures path short-circuits WITHOUT calling the seam
      (passing cases make no model invocation);
  (c) `--dry-run` writes nothing beyond the diagnosis file.

The mock boundary is `meta_agent.complete` (per impl-log §Slice 1 notes — callers may
mock `complete` directly). Defensive parsing is also covered: an empty/unparseable
seam return degrades to a no-category result rather than raising.
"""

import json
import os
import tempfile
import unittest

import meta_agent
import diagnose


# --- fixtures --------------------------------------------------------------

def _failing_grades():
    """A grades dict with one failing case (mean_score < 0.9)."""
    return {
        "cases": [
            {
                "case_id": "case-fail-1",
                "mean_score": 0.4,
                "stddev": 0.1,
                "tags": ["t"],
                "difficulty": "easy",
                "trials": [
                    {
                        "assertions": [
                            {
                                "check": "must mention the rollback step",
                                "type": "llm_judge",
                                "passed": False,
                                "evidence": "answer omitted the rollback step",
                                "weight": 1.0,
                            }
                        ]
                    }
                ],
            }
        ]
    }


def _all_passing_grades():
    """A grades dict whose only case passes (mean_score >= 0.9)."""
    return {
        "cases": [
            {
                "case_id": "case-pass-1",
                "mean_score": 0.95,
                "stddev": 0.0,
                "tags": [],
                "difficulty": "easy",
                "trials": [{"assertions": []}],
            }
        ]
    }


class _MockSeam:
    """Context manager that replaces meta_agent.complete with a recording stub."""

    def __init__(self, return_value):
        self.return_value = return_value
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = meta_agent.complete

        def fake(system, user, model=None):
            self.calls.append((system, user, model))
            return self.return_value

        meta_agent.complete = fake
        return self

    def __exit__(self, *exc):
        meta_agent.complete = self._orig
        return False


# --- (a) grounded categorization parsed from mocked seam -------------------

class GroundedCategorizationTest(unittest.TestCase):
    def test_categorize_failure_parses_grounded_category_and_rationale(self):
        failure = diagnose.extract_failures(_failing_grades())[0]
        seam_text = json.dumps(
            {"category": "MISSING_INSTRUCTION", "rationale": "answer omitted the rollback step"}
        )
        with _MockSeam(seam_text) as seam:
            result = diagnose.categorize_failure(failure, "the skill text")

        # Grounded fields.
        self.assertEqual(result["category"], "MISSING_INSTRUCTION")
        self.assertEqual(result["rationale"], "answer omitted the rollback step")
        # Downstream-consumed keys preserved.
        self.assertEqual(result["case_id"], "case-fail-1")
        self.assertEqual(result["score"], 0.4)
        self.assertEqual(result["categories"], ["MISSING_INSTRUCTION"])
        self.assertEqual(len(result["failed_assertions"]), 1)
        # The seam saw the full skill text + the failure evidence.
        self.assertEqual(len(seam.calls), 1)
        _system, user, _model = seam.calls[0]
        self.assertIn("the skill text", user)
        self.assertIn("case-fail-1", user)

    def test_unknown_category_degrades_to_no_category(self):
        failure = diagnose.extract_failures(_failing_grades())[0]
        with _MockSeam(json.dumps({"category": "NOT_A_REAL_CATEGORY", "rationale": "x"})):
            result = diagnose.categorize_failure(failure, "skill")
        self.assertIsNone(result["category"])
        self.assertEqual(result["categories"], [])

    def test_empty_seam_result_degrades_without_raising(self):
        failure = diagnose.extract_failures(_failing_grades())[0]
        with _MockSeam(meta_agent.NO_RESULT):
            result = diagnose.categorize_failure(failure, "skill")
        self.assertIsNone(result["category"])
        self.assertEqual(result["rationale"], "")
        self.assertEqual(result["categories"], [])

    def test_unparseable_seam_result_degrades_without_raising(self):
        failure = diagnose.extract_failures(_failing_grades())[0]
        with _MockSeam("this is not json {{{"):
            result = diagnose.categorize_failure(failure, "skill")
        self.assertIsNone(result["category"])
        self.assertEqual(result["categories"], [])

    def test_grounded_category_flows_into_recommendations(self):
        seam_text = json.dumps(
            {"category": "MISSING_INSTRUCTION", "rationale": "omitted rollback"}
        )
        with tempfile.TemporaryDirectory() as d:
            grades_path = os.path.join(d, "grades.json")
            skill_path = os.path.join(d, "skill.md")
            out_path = os.path.join(d, "diagnosis.json")
            with open(grades_path, "w") as f:
                json.dump(_failing_grades(), f)
            with open(skill_path, "w") as f:
                f.write("the skill text")
            with _MockSeam(seam_text):
                diagnosis = diagnose.produce_diagnosis(grades_path, skill_path, out_path)

        self.assertEqual(diagnosis["status"], "FAILURES_DETECTED")
        cats = [r["category"] for r in diagnosis["recommendations"]]
        self.assertIn("MISSING_INSTRUCTION", cats)


# --- (b) ALL_PASSING short-circuits without a model call -------------------

class ShortCircuitTest(unittest.TestCase):
    def test_all_passing_makes_no_seam_call(self):
        with tempfile.TemporaryDirectory() as d:
            grades_path = os.path.join(d, "grades.json")
            skill_path = os.path.join(d, "skill.md")
            out_path = os.path.join(d, "diagnosis.json")
            with open(grades_path, "w") as f:
                json.dump(_all_passing_grades(), f)
            with open(skill_path, "w") as f:
                f.write("skill")
            with _MockSeam("should not be called") as seam:
                diagnosis = diagnose.produce_diagnosis(grades_path, skill_path, out_path)

        self.assertEqual(diagnosis["status"], "ALL_PASSING")
        self.assertEqual(seam.calls, [])  # no model invocation for passing cases


# --- (c) --dry-run writes nothing beyond the diagnosis file ----------------

class DryRunTest(unittest.TestCase):
    def test_dry_run_writes_only_the_diagnosis_file(self):
        seam_text = json.dumps({"category": "UNDER_SPECIFIED", "rationale": "vague"})
        with tempfile.TemporaryDirectory() as d:
            grades_path = os.path.join(d, "grades.json")
            skill_path = os.path.join(d, "skill.md")
            out_path = os.path.join(d, "diagnosis.json")
            with open(grades_path, "w") as f:
                json.dump(_failing_grades(), f)
            with open(skill_path, "w") as f:
                f.write("skill")

            before = set(os.listdir(d))
            with _MockSeam(seam_text):
                diagnose.produce_diagnosis(grades_path, skill_path, out_path, dry_run=True)
            after = set(os.listdir(d))

            # The only new file is the diagnosis file itself.
            new_files = after - before
            self.assertEqual(new_files, {"diagnosis.json"})
            # And it is real, well-formed diagnosis content.
            with open(out_path) as f:
                written = json.load(f)
            self.assertEqual(written["status"], "FAILURES_DETECTED")


if __name__ == "__main__":
    unittest.main()
