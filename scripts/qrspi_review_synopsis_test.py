#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_review_synopsis.py (RUS-91).
Run: python3 scripts/qrspi_review_synopsis_test.py"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrspi_review_synopsis import (  # noqa: E402
    DECISION_READINESS_LENS,
    ledger_row_fields,
    partition_decision_readiness,
    render_synopsis,
)


def _verdict(lens, passed, findings=None, non_blocking=None):
    v = {"lens": lens, "pass": passed, "findings": findings or []}
    if non_blocking is not None:
        v["nonBlockingNotes"] = non_blocking
    return v


def _dr(blocking=None, answerable=None):
    return {
        "lens": DECISION_READINESS_LENS,
        "blockingDecisions": blocking or [],
        "answerable": answerable or [],
    }


class PartitionDecisionReadinessTests(unittest.TestCase):
    def test_partitions_out_the_decision_readiness_lens(self):
        arr = [
            _verdict("completeness", True),
            _dr(blocking=[{"question": "Q?", "rationale": "human call"}]),
            _verdict("edge-alignment", False, findings=["x"]),
        ]
        panel, dr = partition_decision_readiness(arr)
        self.assertEqual([v["lens"] for v in panel],
                         ["completeness", "edge-alignment"])
        self.assertIsNotNone(dr)
        self.assertEqual(dr["lens"], DECISION_READINESS_LENS)

    def test_absent_lens_returns_none(self):
        arr = [_verdict("completeness", True), _verdict("simplicity", True)]
        panel, dr = partition_decision_readiness(arr)
        self.assertEqual(len(panel), 2)
        self.assertIsNone(dr)

    def test_does_not_mutate_input(self):
        arr = [_verdict("completeness", True), _dr()]
        partition_decision_readiness(arr)
        self.assertEqual(len(arr), 2)

    def test_duplicate_decision_readiness_keeps_first_drops_rest(self):
        dr1 = _dr(blocking=[{"question": "first", "rationale": "r"}])
        dr2 = _dr(blocking=[{"question": "second", "rationale": "r"}])
        panel, dr = partition_decision_readiness([dr1, _verdict("a", True), dr2])
        self.assertEqual([v["lens"] for v in panel], ["a"])
        self.assertEqual(dr["blockingDecisions"][0]["question"], "first")

    def test_non_list_input_is_lenient(self):
        panel, dr = partition_decision_readiness(None)
        self.assertEqual(panel, [])
        self.assertIsNone(dr)


class LedgerRowFieldsTests(unittest.TestCase):
    def test_axes_enumerate_every_lens(self):
        arr = [
            _verdict("completeness", True, findings=[]),
            _verdict("edge-alignment", False, findings=["a", "b"]),
        ]
        fields = ledger_row_fields(arr)
        self.assertEqual(fields["axes"], [
            {"lens": "completeness", "pass": True, "blockingCount": 0},
            {"lens": "edge-alignment", "pass": False, "blockingCount": 2},
        ])

    def test_non_blocking_notes_union(self):
        arr = [
            _verdict("a", True, non_blocking=["note1"]),
            _verdict("b", True, non_blocking=["note2", "note3"]),
            _verdict("c", True),  # no nonBlockingNotes key
        ]
        fields = ledger_row_fields(arr)
        self.assertEqual(fields["nonBlockingNotes"], ["note1", "note2", "note3"])

    def test_blocking_count_uses_findings_not_non_blocking(self):
        arr = [_verdict("a", True, findings=["blocker"], non_blocking=["advisory"])]
        fields = ledger_row_fields(arr)
        self.assertEqual(fields["axes"][0]["blockingCount"], 1)

    def test_empty_array(self):
        self.assertEqual(ledger_row_fields([]), {"axes": [], "nonBlockingNotes": []})


class RenderSynopsisTests(unittest.TestCase):
    def test_axis_enumeration_lists_every_lens_with_pass(self):
        arr = [
            _verdict("completeness", True, findings=[]),
            _verdict("edge-alignment", False, findings=["x", "y"]),
            _verdict("simplicity", True, findings=[]),
        ]
        out = render_synopsis(arr, None, "advance")
        self.assertIn("completeness", out)
        self.assertIn("edge-alignment", out)
        self.assertIn("simplicity", out)
        # per-lens pass labels present
        self.assertIn("PASS", out)
        self.assertIn("FAIL", out)
        # blocking count for edge-alignment is 2
        self.assertIn("| edge-alignment | FAIL | 2 |", out)

    def test_non_blocking_passthrough_in_advisory_section(self):
        arr = [_verdict("a", True, non_blocking=["consider X", "consider Y"])]
        out = render_synopsis(arr, None, "advance")
        self.assertIn("Advisory (non-blocking)", out)
        self.assertIn("consider X", out)
        self.assertIn("consider Y", out)

    def test_no_advisory_section_when_no_notes(self):
        arr = [_verdict("a", True)]
        out = render_synopsis(arr, None, "advance")
        self.assertNotIn("Advisory (non-blocking)", out)

    def test_decision_readiness_blocking_section(self):
        dr = _dr(blocking=[
            {"question": "Which auth model?", "rationale": "policy decision"},
        ])
        out = render_synopsis([_verdict("a", True)], dr, "advance")
        self.assertIn("Decision readiness", out)
        self.assertIn("Which auth model?", out)
        self.assertIn("policy decision", out)

    def test_decision_readiness_omitted_when_none(self):
        out = render_synopsis([_verdict("a", True)], None, "advance")
        self.assertNotIn("Decision readiness", out)

    def test_decision_readiness_omitted_when_no_blocking(self):
        dr = _dr(blocking=[], answerable=[{"question": "easy?"}])
        out = render_synopsis([_verdict("a", True)], dr, "advance")
        self.assertNotIn("Decision readiness", out)

    def test_blocking_finding_strings_surface_verbatim(self):
        arr = [
            _verdict("edge-alignment", False,
                     findings=["edge E2 maps to no node", "node N3 unreachable"]),
        ]
        out = render_synopsis(arr, None, "revise")
        # the literal finding strings appear, not just the count
        self.assertIn("edge E2 maps to no node", out)
        self.assertIn("node N3 unreachable", out)
        self.assertIn("Blocking findings", out)

    def test_blocking_findings_deduped(self):
        arr = [
            _verdict("a", False, findings=["dup finding", "dup finding", "other"]),
        ]
        out = render_synopsis(arr, None, "revise")
        self.assertEqual(out.count("- dup finding"), 1)
        self.assertIn("- other", out)

    def test_no_blocking_findings_section_for_passing_lens(self):
        arr = [_verdict("a", True, findings=[])]
        out = render_synopsis(arr, None, "advance")
        self.assertNotIn("Blocking findings —", out)

    def test_no_blocking_findings_section_when_fail_has_no_findings(self):
        # a FAIL with an empty findings list emits no sub-section
        arr = [_verdict("a", False, findings=[])]
        out = render_synopsis(arr, None, "revise")
        self.assertNotIn("Blocking findings —", out)

    def test_non_blocking_notes_unchanged_alongside_blocking_findings(self):
        arr = [
            _verdict("a", False, findings=["a blocker"], non_blocking=["consider Z"]),
        ]
        out = render_synopsis(arr, None, "revise")
        # blocking finding text surfaces
        self.assertIn("a blocker", out)
        # advisory section still renders the non-blocking note, distinctly
        self.assertIn("Advisory (non-blocking)", out)
        self.assertIn("consider Z", out)

    def test_terminal_action_rendered(self):
        out = render_synopsis([_verdict("a", True)], None, "revise")
        self.assertIn("Terminal action:", out)
        self.assertIn("revise", out)


if __name__ == "__main__":
    unittest.main()
