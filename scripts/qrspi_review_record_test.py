#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_review_record.build_record.
Run: python3 scripts/qrspi_review_record_test.py"""

import unittest

import qrspi_review_agreement
import qrspi_review_record as m


def _agreement():
    return qrspi_review_agreement.compute(True, "APPROVED")


class BuildRecordShapeTest(unittest.TestCase):
    def test_carries_base_phase_rounds_terminal_action(self):
        verdicts = [
            {"lens": "design-review", "pass": False,
             "findings": ["unsound step", "missing path"]},
        ]
        rec = m.build_record(
            phase="design", rounds=verdicts,
            terminal_action="cap_reached", agreement=_agreement())
        self.assertEqual(rec["phase"], "design")
        self.assertEqual(rec["terminalAction"], "cap_reached")
        # The base builder derived the {lens, pass, findingsCount} rounds shape.
        self.assertEqual(rec["rounds"], [
            {"lens": "design-review", "pass": False, "findingsCount": 2},
        ])

    def test_embeds_agreement_block_verbatim(self):
        agreement = _agreement()
        rec = m.build_record(
            phase="design", rounds=[],
            terminal_action="converged", agreement=agreement)
        self.assertEqual(rec["agreement"], agreement)
        self.assertEqual(rec["agreement"]["panelVerdict"], "pass")
        self.assertEqual(rec["agreement"]["humanVerdict"], "approved")
        self.assertEqual(rec["agreement"]["agreement"], "agree")

    def test_mode_discriminator_is_on_demand_review(self):
        rec = m.build_record(
            phase="plan", rounds=[],
            terminal_action="converged", agreement=_agreement())
        self.assertEqual(rec["mode"], "on-demand-review")

    def test_pending_agreement_passes_through(self):
        agreement = qrspi_review_agreement.compute(True, None)
        rec = m.build_record(
            phase="design", rounds=[],
            terminal_action="converged", agreement=agreement)
        self.assertEqual(rec["agreement"]["agreement"], "pending")
        self.assertIsNone(rec["agreement"]["humanVerdict"])

    def test_record_keys_superset_of_base_plus_agreement_and_mode(self):
        rec = m.build_record(
            phase="implementation", rounds=[],
            terminal_action="converged", agreement=_agreement())
        for key in ("phase", "rounds", "terminalAction", "agreement", "mode"):
            self.assertIn(key, rec)


class TerminalActionPropagationTest(unittest.TestCase):
    def test_invalid_terminal_action_raises(self):
        # The base builder is fail-closed; the wrapper propagates the ValueError.
        with self.assertRaises(ValueError):
            m.build_record(
                phase="design", rounds=[],
                terminal_action="revise", agreement=_agreement())


if __name__ == "__main__":
    unittest.main()
