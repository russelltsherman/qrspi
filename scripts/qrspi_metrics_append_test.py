#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_metrics_append.py.
Run: python3 scripts/qrspi_metrics_append_test.py"""

import json
import os
import tempfile
import unittest

import qrspi_metrics_append as a
import qrspi_paths


SAMPLE_RECORD = {
    "phase": "design",
    "rounds": [
        {"lens": "completeness", "pass": False, "findingsCount": 2},
        {"lens": "edge", "pass": True, "findingsCount": 0},
    ],
    "terminalAction": "cap_reached",
}


class LedgerPathTest(unittest.TestCase):
    def test_canonical_worktree_layout(self):
        p = a.ledger_path("/repo", "RUS-77")
        self.assertEqual(
            p, "/repo/.worktrees/RUS-77/.qrspi/RUS-77/critic-metrics.jsonl")

    def test_no_double_nesting_under_host_root(self):
        # Guards finding #2: the path must be rooted ONCE at the host checkout,
        # never .worktrees/<id>/.worktrees/<id>/...
        p = a.ledger_path("/host", "RUS-77")
        self.assertEqual(p.count("/.worktrees/RUS-77/"), 1)


class WrapEnvelopeTest(unittest.TestCase):
    def test_injects_envelope_fields(self):
        line = a.wrap_envelope(
            SAMPLE_RECORD, "RUS-77", "2026-06-15T00:00:00+00:00", "run-A")
        self.assertEqual(line["ticketId"], "RUS-77")
        self.assertEqual(line["timestamp"], "2026-06-15T00:00:00+00:00")
        self.assertEqual(line["runId"], "run-A")
        # every CriticStepMetrics field survives
        self.assertEqual(line["phase"], "design")
        self.assertEqual(line["rounds"], SAMPLE_RECORD["rounds"])
        self.assertEqual(line["terminalAction"], "cap_reached")

    def test_does_not_mutate_input_record(self):
        rec = dict(SAMPLE_RECORD)
        a.wrap_envelope(rec, "RUS-77", "t", "run-A")
        self.assertNotIn("ticketId", rec)
        self.assertNotIn("timestamp", rec)
        self.assertNotIn("runId", rec)

    def test_appender_envelope_values_win(self):
        rec = dict(SAMPLE_RECORD, ticketId="STALE", timestamp="STALE",
                   runId="STALE")
        line = a.wrap_envelope(rec, "RUS-77", "fresh", "run-fresh")
        self.assertEqual(line["ticketId"], "RUS-77")
        self.assertEqual(line["timestamp"], "fresh")
        self.assertEqual(line["runId"], "run-fresh")


class AppendCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        # Pin the resolver to a known root, mirroring how qrspi_persist's tests
        # pin the host root. Restored in tearDown.
        self._orig = qrspi_paths.resolve_repo_root
        qrspi_paths.resolve_repo_root = lambda *args, **kw: self.root

    def tearDown(self):
        qrspi_paths.resolve_repo_root = self._orig
        self.tmp.cleanup()

    def _expected_ledger(self, ticket):
        return a.ledger_path(self.root, ticket)

    def _read_lines(self, ticket):
        with open(self._expected_ledger(ticket)) as fh:
            return [ln for ln in fh.read().splitlines() if ln]

    def test_first_call_creates_single_line_ledger(self):
        rc = a.main(["--ticket", "RUS-77", "--record", json.dumps(SAMPLE_RECORD),
                     "--run-id", "run-A"])
        self.assertEqual(rc, 0)
        lines = self._read_lines("RUS-77")
        self.assertEqual(len(lines), 1)

    def test_second_call_appends_first_line_intact(self):
        a.main(["--ticket", "RUS-77", "--record", json.dumps(SAMPLE_RECORD),
                "--run-id", "run-A"])
        first = self._read_lines("RUS-77")[0]
        second_rec = dict(SAMPLE_RECORD, terminalAction="converged")
        a.main(["--ticket", "RUS-77", "--record", json.dumps(second_rec),
                "--run-id", "run-A"])
        lines = self._read_lines("RUS-77")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], first)  # no overwrite
        self.assertEqual(json.loads(lines[1])["terminalAction"], "converged")

    def test_each_line_is_envelope_wrapped_not_bare_record(self):
        a.main(["--ticket", "RUS-77", "--record", json.dumps(SAMPLE_RECORD),
                "--run-id", "run-A"])
        line = json.loads(self._read_lines("RUS-77")[0])
        # every CriticStepMetrics field present
        self.assertEqual(line["phase"], "design")
        self.assertEqual(line["rounds"], SAMPLE_RECORD["rounds"])
        self.assertEqual(line["terminalAction"], "cap_reached")
        # AND the envelope fields
        self.assertEqual(line["ticketId"], "RUS-77")
        self.assertIn("timestamp", line)
        self.assertTrue(line["timestamp"])  # non-empty ISO-8601 string
        self.assertIsInstance(line["timestamp"], str)
        self.assertEqual(line["runId"], "run-A")

    def test_run_id_present_and_round_trips(self):
        # RUS-78: the appender stamps every line with the passed run_id as the
        # string field "runId"; it round-trips through the written ledger.
        rc = a.main(["--ticket", "RUS-77", "--record", json.dumps(SAMPLE_RECORD),
                     "--run-id", "run-roundtrip-123"])
        self.assertEqual(rc, 0)
        line = json.loads(self._read_lines("RUS-77")[0])
        self.assertIn("runId", line)
        self.assertEqual(line["runId"], "run-roundtrip-123")
        self.assertIsInstance(line["runId"], str)

    def test_invalid_json_record_fails_closed_and_writes_nothing(self):
        rc = a.main(["--ticket", "RUS-77", "--record", "{not valid json",
                     "--run-id", "run-A"])
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self._expected_ledger("RUS-77")))

    def test_non_object_record_fails_closed(self):
        rc = a.main(["--ticket", "RUS-77", "--record", "[1, 2, 3]",
                     "--run-id", "run-A"])
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self._expected_ledger("RUS-77")))

    def test_path_resolution_no_double_nesting(self):
        # Path-resolution regression (finding #2): with the resolver pinned to a
        # known root, the ledger lands at exactly
        # <root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl with NO
        # .worktrees/<id>/.worktrees/<id>/... double-nesting.
        a.main(["--ticket", "RUS-77", "--record", json.dumps(SAMPLE_RECORD),
                "--run-id", "run-A"])
        expected = os.path.join(
            self.root, ".worktrees", "RUS-77", ".qrspi", "RUS-77",
            "critic-metrics.jsonl")
        self.assertTrue(os.path.isfile(expected))
        self.assertEqual(expected.count("/.worktrees/RUS-77/"), 1)
        # no phantom double-nested dir was created
        self.assertFalse(os.path.exists(os.path.join(
            self.root, ".worktrees", "RUS-77", ".worktrees")))


if __name__ == "__main__":
    unittest.main()
