#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_review_agreement.compute.
Run: python3 scripts/qrspi_review_agreement_test.py"""

import unittest

import qrspi_review_agreement as m


def check(label, got, want):
    """Assert helper kept readable: compare the computed agreement to the
    expected category, surfacing the case label on failure."""
    assert got == want, "%s: expected agreement %r, got %r" % (label, want, got)


class AgreementCategoryTest(unittest.TestCase):
    def test_pass_approved_agrees(self):
        check("pass+approved", m.compute(True, "APPROVED")["agreement"], "agree")

    def test_fail_changes_requested_agrees(self):
        check("fail+changes_requested",
              m.compute(False, "CHANGES_REQUESTED")["agreement"], "agree")

    def test_pass_changes_requested_disagrees(self):
        check("pass+changes_requested",
              m.compute(True, "CHANGES_REQUESTED")["agreement"], "disagree")

    def test_fail_approved_disagrees(self):
        check("fail+approved",
              m.compute(False, "APPROVED")["agreement"], "disagree")

    def test_pass_none_is_pending(self):
        check("pass+None", m.compute(True, None)["agreement"], "pending")

    def test_fail_none_is_pending(self):
        check("fail+None", m.compute(False, None)["agreement"], "pending")

    def test_commented_is_pending_for_pass(self):
        check("pass+commented",
              m.compute(True, "COMMENTED")["agreement"], "pending")

    def test_commented_is_pending_for_fail(self):
        check("fail+commented",
              m.compute(False, "COMMENTED")["agreement"], "pending")


class VerdictNormalizationTest(unittest.TestCase):
    def test_panel_pass_maps_to_pass(self):
        self.assertEqual(m.compute(True, None)["panelVerdict"], "pass")

    def test_panel_fail_maps_to_fail(self):
        self.assertEqual(m.compute(False, None)["panelVerdict"], "fail")

    def test_human_decision_is_case_insensitive(self):
        self.assertEqual(m.compute(True, "approved")["humanVerdict"], "approved")
        self.assertEqual(m.compute(True, "Approved")["humanVerdict"], "approved")
        self.assertEqual(
            m.compute(False, "changes_requested")["humanVerdict"],
            "changes_requested")

    def test_human_decision_whitespace_tolerated(self):
        self.assertEqual(m.compute(True, "  APPROVED  ")["humanVerdict"], "approved")

    def test_none_human_decision_normalizes_to_null(self):
        self.assertIsNone(m.compute(True, None)["humanVerdict"])

    def test_unknown_human_decision_normalizes_to_null_and_pending(self):
        # Never raises; an unrecognized decision is no decisive verdict.
        rec = m.compute(True, "DISMISSED")
        self.assertIsNone(rec["humanVerdict"])
        self.assertEqual(rec["agreement"], "pending")

    def test_non_string_human_decision_tolerated(self):
        rec = m.compute(True, 123)
        self.assertIsNone(rec["humanVerdict"])
        self.assertEqual(rec["agreement"], "pending")


class ResultKeyContractTest(unittest.TestCase):
    def test_keys_are_exactly_the_agreement_result_contract(self):
        rec = m.compute(True, "APPROVED")
        self.assertEqual(
            set(rec.keys()), {"panelVerdict", "humanVerdict", "agreement"})


if __name__ == "__main__":
    unittest.main()
