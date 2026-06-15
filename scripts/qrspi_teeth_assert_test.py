#!/usr/bin/env python3
"""Tests for the teeth-eval pure majority/marker decision core (RUS-78, Slice 3).

Covers the deterministic catch rule and the >=2-of-3 majority threshold over
synthetic verdicts — the one CI-testable piece of the teeth eval (the agent
spawning lives in the opt-in Workflow runner, off CI).

Run: python3 scripts/qrspi_teeth_assert_test.py
"""

import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import qrspi_teeth_assert as ta  # noqa: E402

SCRIPT = os.path.join(_HERE, "qrspi_teeth_assert.py")

MARKERS = {
    "completeness": "AC-TEETH-COMPLETENESS",
    "internal-consistency": "TEETH-INCONSISTENCY",
    "edge-alignment": "frobnicate_widget()",
}


def _fail(*finding_strings):
    """A failing lens verdict (pass:false) citing the given findings."""
    return {"pass": False, "findings": list(finding_strings)}


def _pass(*finding_strings):
    """A passing lens verdict (pass:true) citing the given findings."""
    return {"pass": True, "findings": list(finding_strings)}


class TestIsCatch(unittest.TestCase):
    def test_catch_via_fail_with_marker(self):
        v = _fail("design omits AC-TEETH-COMPLETENESS from the ticket")
        self.assertTrue(ta._is_catch(v, "AC-TEETH-COMPLETENESS"))

    def test_no_catch_when_pass_true(self):
        # The lens cited the marker but PASSED the design — not a catch (rubber-stamp).
        v = _pass("noted AC-TEETH-COMPLETENESS but it's fine")
        self.assertFalse(ta._is_catch(v, "AC-TEETH-COMPLETENESS"))

    def test_no_catch_when_marker_absent(self):
        v = _fail("the design has some other unrelated problem")
        self.assertFalse(ta._is_catch(v, "AC-TEETH-COMPLETENESS"))

    def test_marker_as_substring_of_finding(self):
        v = _fail("upstream symbol frobnicate_widget() is contradicted by the design")
        self.assertTrue(ta._is_catch(v, "frobnicate_widget()"))

    def test_malformed_verdict_is_not_catch(self):
        self.assertFalse(ta._is_catch(None, "AC-TEETH-COMPLETENESS"))
        self.assertFalse(ta._is_catch({"findings": ["AC-TEETH-COMPLETENESS"]},
                                      "AC-TEETH-COMPLETENESS"))  # missing pass
        self.assertFalse(ta._is_catch({"pass": False, "findings": "AC-TEETH-COMPLETENESS"},
                                      "AC-TEETH-COMPLETENESS"))  # findings not a list
        self.assertFalse(ta._is_catch({"pass": False, "findings": [123]},
                                      "AC-TEETH-COMPLETENESS"))  # non-string finding

    def test_pass_must_be_exactly_false(self):
        # pass:0 / pass:"false" are NOT a real fail — fail-closed to not-a-catch.
        self.assertFalse(ta._is_catch({"pass": 0, "findings": ["AC-TEETH-COMPLETENESS"]},
                                      "AC-TEETH-COMPLETENESS"))


class TestEvaluateThreshold(unittest.TestCase):
    def test_majority_two_of_three_passes(self):
        trials = {
            "completeness": [
                _fail("AC-TEETH-COMPLETENESS dropped"),
                _fail("missing AC-TEETH-COMPLETENESS"),
                _pass("looks complete"),
            ],
        }
        rep = ta.evaluate(trials, {"completeness": "AC-TEETH-COMPLETENESS"}, threshold=2)
        self.assertEqual(rep["perLens"]["completeness"]["caught"], 2)
        self.assertEqual(rep["perLens"]["completeness"]["total"], 3)
        self.assertTrue(rep["perLens"]["completeness"]["pass"])
        self.assertTrue(rep["overallPass"])

    def test_one_of_three_fails_threshold(self):
        trials = {
            "completeness": [
                _fail("AC-TEETH-COMPLETENESS dropped"),
                _pass("looks complete"),
                _pass("fine"),
            ],
        }
        rep = ta.evaluate(trials, {"completeness": "AC-TEETH-COMPLETENESS"}, threshold=2)
        self.assertEqual(rep["perLens"]["completeness"]["caught"], 1)
        self.assertFalse(rep["perLens"]["completeness"]["pass"])
        self.assertFalse(rep["overallPass"])

    def test_overall_pass_requires_all_lenses(self):
        trials = {
            "completeness": [_fail("AC-TEETH-COMPLETENESS"), _fail("AC-TEETH-COMPLETENESS")],
            "internal-consistency": [_fail("TEETH-INCONSISTENCY"), _fail("TEETH-INCONSISTENCY")],
            "edge-alignment": [_pass("fine"), _pass("fine")],
        }
        rep = ta.evaluate(trials, MARKERS, threshold=2)
        self.assertTrue(rep["perLens"]["completeness"]["pass"])
        self.assertTrue(rep["perLens"]["internal-consistency"]["pass"])
        self.assertFalse(rep["perLens"]["edge-alignment"]["pass"])
        self.assertFalse(rep["overallPass"])

    def test_all_three_lenses_catch(self):
        trials = {
            "completeness": [_fail("AC-TEETH-COMPLETENESS"), _fail("AC-TEETH-COMPLETENESS"), _fail("AC-TEETH-COMPLETENESS")],
            "internal-consistency": [_fail("TEETH-INCONSISTENCY"), _fail("TEETH-INCONSISTENCY"), _pass("ok")],
            "edge-alignment": [_fail("frobnicate_widget()"), _fail("frobnicate_widget()"), _pass("ok")],
        }
        rep = ta.evaluate(trials, MARKERS, threshold=2)
        self.assertTrue(rep["overallPass"])

    def test_lens_with_no_trials_fails(self):
        rep = ta.evaluate({}, {"completeness": "AC-TEETH-COMPLETENESS"}, threshold=2)
        self.assertEqual(rep["perLens"]["completeness"]["caught"], 0)
        self.assertEqual(rep["perLens"]["completeness"]["total"], 0)
        self.assertFalse(rep["perLens"]["completeness"]["pass"])
        self.assertFalse(rep["overallPass"])

    def test_empty_markers_overall_false(self):
        # No lens evaluated ⇒ nothing attested ⇒ fail-closed overallPass.
        rep = ta.evaluate({"completeness": [_fail("x")]}, {}, threshold=2)
        self.assertEqual(rep["perLens"], {})
        self.assertFalse(rep["overallPass"])

    def test_nonpositive_threshold_falls_back_to_two(self):
        # A non-positive threshold would let a lens "pass" with zero catches — guarded.
        trials = {"completeness": [_pass("fine")]}
        rep = ta.evaluate(trials, {"completeness": "AC-TEETH-COMPLETENESS"}, threshold=0)
        self.assertFalse(rep["perLens"]["completeness"]["pass"])

    def test_threshold_one(self):
        trials = {"completeness": [_fail("AC-TEETH-COMPLETENESS"), _pass("fine"), _pass("fine")]}
        rep = ta.evaluate(trials, {"completeness": "AC-TEETH-COMPLETENESS"}, threshold=1)
        self.assertTrue(rep["perLens"]["completeness"]["pass"])


class TestCli(unittest.TestCase):
    def _run(self, trials_obj, markers_obj, threshold):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--markers", json.dumps(markers_obj),
             "--threshold", str(threshold)],
            input=json.dumps(trials_obj), capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_cli_round_trips(self):
        trials = {
            "completeness": [_fail("AC-TEETH-COMPLETENESS"), _fail("AC-TEETH-COMPLETENESS")],
        }
        rep = self._run(trials, {"completeness": "AC-TEETH-COMPLETENESS"}, 2)
        self.assertTrue(rep["perLens"]["completeness"]["pass"])
        self.assertTrue(rep["overallPass"])

    def test_cli_empty_stdin_fails_closed(self):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--markers", json.dumps(MARKERS), "--threshold", "2"],
            input="", capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rep = json.loads(proc.stdout)
        self.assertFalse(rep["overallPass"])


if __name__ == "__main__":
    unittest.main()
