#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_critic_metrics.build_record.
Run: python3 scripts/qrspi_critic_metrics_test.py"""

import unittest

import qrspi_critic_metrics as m


class BuildRecordRoundsTest(unittest.TestCase):
    def test_all_pass_verdicts_zero_findings(self):
        verdicts = [
            {"lens": "completeness", "pass": True, "findings": []},
            {"lens": "simplicity", "pass": True, "findings": []},
        ]
        rec = m.build_record(verdicts, "converged", phase="design")
        self.assertEqual(rec["phase"], "design")
        self.assertEqual(rec["terminalAction"], "converged")
        self.assertEqual(rec["rounds"], [
            {"lens": "completeness", "pass": True, "findingsCount": 0},
            {"lens": "simplicity", "pass": True, "findingsCount": 0},
        ])

    def test_mixed_pass_fail_and_findings_counts(self):
        # OQ4: BOTH the pass/fail flag AND the findings count are preserved per
        # round — never collapsed into a single rate.
        verdicts = [
            {"lens": "completeness", "pass": False,
             "findings": ["dropped AC-2", "vague metric"]},
            {"lens": "edge", "pass": True, "findings": []},
            {"lens": "consistency", "pass": False, "findings": ["contradiction"]},
        ]
        rec = m.build_record(verdicts, "cap_reached", phase="design")
        self.assertEqual(rec["rounds"], [
            {"lens": "completeness", "pass": False, "findingsCount": 2},
            {"lens": "edge", "pass": True, "findingsCount": 0},
            {"lens": "consistency", "pass": False, "findingsCount": 1},
        ])

    def test_empty_verdicts_yields_empty_rounds(self):
        rec = m.build_record([], "exhausted", phase="design")
        self.assertEqual(rec["rounds"], [])

    def test_missing_findings_key_counts_zero(self):
        verdicts = [{"lens": "x", "pass": True}]
        rec = m.build_record(verdicts, "converged", phase="design")
        self.assertEqual(rec["rounds"][0]["findingsCount"], 0)


class TokenFieldsTest(unittest.TestCase):
    def test_no_usage_omits_token_fields(self):
        # OQ2: the live path supplies no usage, so tokensIn/tokensOut are absent.
        rec = m.build_record([], "converged", phase="design")
        self.assertNotIn("tokensIn", rec)
        self.assertNotIn("tokensOut", rec)

    def test_usage_none_explicit_omits_token_fields(self):
        rec = m.build_record([], "converged", usage=None, phase="design")
        self.assertNotIn("tokensIn", rec)
        self.assertNotIn("tokensOut", rec)

    def test_usage_provided_includes_token_fields(self):
        rec = m.build_record([], "converged",
                             usage={"tokensIn": 1200, "tokensOut": 340},
                             phase="design")
        self.assertEqual(rec["tokensIn"], 1200)
        self.assertEqual(rec["tokensOut"], 340)

    def test_partial_usage_includes_only_supplied_keys(self):
        rec = m.build_record([], "converged",
                             usage={"tokensIn": 50}, phase="design")
        self.assertEqual(rec["tokensIn"], 50)
        self.assertNotIn("tokensOut", rec)


class TerminalActionTest(unittest.TestCase):
    def test_each_valid_terminal_action_accepted(self):
        for action in ("converged", "cap_reached", "exhausted", "aborted"):
            rec = m.build_record([], action, phase="design")
            self.assertEqual(rec["terminalAction"], action)

    def test_revise_is_rejected_as_non_terminal(self):
        with self.assertRaises(ValueError):
            m.build_record([], "revise", phase="design")

    def test_other_invalid_terminal_action_raises(self):
        for bad in ("done", "", None, "CONVERGED", "pass"):
            with self.assertRaises(ValueError):
                m.build_record([], bad, phase="design")


if __name__ == "__main__":
    unittest.main()
