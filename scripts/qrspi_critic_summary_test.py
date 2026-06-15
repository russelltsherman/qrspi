#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_critic_summary.py.
Run: python3 scripts/qrspi_critic_summary_test.py"""

import json
import os
import tempfile
import unittest

import qrspi_critic_summary as s


# In-memory ledger-line fixtures, mirroring qrspi_metrics_append_test.py:SAMPLE_RECORD
# but now including a runId field (the RUS-78 additive field). Each line is a full
# CriticMetricsLedgerLine envelope.

def _line(run_id="run-A", ticket="RUS-78", timestamp="2026-06-15T00:00:00+00:00",
          rounds=None, terminal_action="cap_reached"):
    return {
        "phase": "design",
        "rounds": rounds if rounds is not None else [],
        "terminalAction": terminal_action,
        "ticketId": ticket,
        "timestamp": timestamp,
        "runId": run_id,
    }


class DissentTest(unittest.TestCase):
    def test_dissent_via_fail(self):
        # A round with pass:false counts as dissent even with zero findings.
        line = _line(rounds=[{"lens": "completeness", "pass": False,
                              "findingsCount": 0}])
        out = s.summarize([line])
        self.assertEqual(out["dissentRate"], 1.0)

    def test_dissent_via_nonempty_findings(self):
        # A round with pass:true but findingsCount > 0 still counts as dissent.
        line = _line(rounds=[{"lens": "completeness", "pass": True,
                              "findingsCount": 3}])
        out = s.summarize([line])
        self.assertEqual(out["dissentRate"], 1.0)

    def test_no_dissent_when_pass_and_no_findings(self):
        line = _line(rounds=[{"lens": "edge", "pass": True, "findingsCount": 0}])
        out = s.summarize([line])
        self.assertEqual(out["dissentRate"], 0.0)

    def test_dissent_rate_is_fraction_of_rounds(self):
        line = _line(rounds=[
            {"lens": "a", "pass": False, "findingsCount": 0},
            {"lens": "b", "pass": True, "findingsCount": 0},
        ])
        out = s.summarize([line])
        self.assertEqual(out["dissentRate"], 0.5)


class DissentRevisedRateTest(unittest.TestCase):
    def test_dissent_revised_rate(self):
        # A pass:false round FOLLOWED by a later round => a revise was attempted
        # (rate 1.0). A trailing pass:false with no following round => 0.0.
        revised = _line(rounds=[
            {"lens": "a", "pass": False, "findingsCount": 1},
            {"lens": "a", "pass": True, "findingsCount": 0},
        ])
        self.assertEqual(s.summarize([revised])["dissentRevisedRate"], 1.0)

        not_revised = _line(rounds=[
            {"lens": "a", "pass": True, "findingsCount": 0},
            {"lens": "a", "pass": False, "findingsCount": 1},
        ])
        self.assertEqual(s.summarize([not_revised])["dissentRevisedRate"], 0.0)

    def test_dissent_revised_rate_zero_when_no_pass_false(self):
        line = _line(rounds=[{"lens": "a", "pass": True, "findingsCount": 0}])
        self.assertEqual(s.summarize([line])["dissentRevisedRate"], 0.0)


class LoaderTest(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        with open(path, "w") as fh:
            fh.write(text)
        self.addCleanup(os.unlink, path)
        return path

    def test_trailing_partial_line(self):
        # A ledger ending in a truncated/invalid JSON line is tolerated; good
        # lines still parse and abortedRecords counts the bad one.
        good = json.dumps(_line(run_id="run-A"))
        path = self._write(good + "\n" + '{"phase": "design", "rounds')  # truncated
        lines, aborted = s._read_lines(path)
        self.assertEqual(len(lines), 1)
        self.assertEqual(aborted, 1)
        out = s.summarize(lines, aborted=aborted)
        self.assertEqual(out["stepCount"], 1)
        self.assertEqual(out["abortedRecords"], 1)

    def test_aborted_record_counting(self):
        # Multiple malformed lines interleaved are skipped and counted.
        a = json.dumps(_line(run_id="run-A"))
        b = json.dumps(_line(run_id="run-B"))
        path = self._write("\n".join([
            a, "{garbage", b, "not json at all", "",
        ]) + "\n")
        lines, aborted = s._read_lines(path)
        self.assertEqual(len(lines), 2)
        self.assertEqual(aborted, 2)

    def test_non_object_line_counts_as_aborted(self):
        path = self._write(json.dumps([1, 2, 3]) + "\n"
                           + json.dumps(_line()) + "\n")
        lines, aborted = s._read_lines(path)
        self.assertEqual(len(lines), 1)
        self.assertEqual(aborted, 1)

    def test_load_ledger_returns_only_good_dicts(self):
        path = self._write(json.dumps(_line()) + "\n{bad\n")
        result = s.load_ledger(path)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)


class ScopingTest(unittest.TestCase):
    def test_run_id_exact_scoping(self):
        lines = [
            _line(run_id="run-A", rounds=[{"lens": "a", "pass": False,
                                           "findingsCount": 1}]),
            _line(run_id="run-B", rounds=[{"lens": "a", "pass": False,
                                           "findingsCount": 1}]),
            _line(run_id="run-A", rounds=[{"lens": "a", "pass": True,
                                           "findingsCount": 0}]),
        ]
        out = s.summarize(lines, run_id="run-A")
        self.assertEqual(out["stepCount"], 2)

    def test_since_and_ticket_scoping(self):
        lines = [
            _line(ticket="RUS-78", timestamp="2026-06-15T00:00:00+00:00"),
            _line(ticket="RUS-78", timestamp="2026-06-16T00:00:00+00:00"),
            _line(ticket="RUS-99", timestamp="2026-06-16T00:00:00+00:00"),
        ]
        # since restricts to the later window
        self.assertEqual(
            s.summarize(lines, since="2026-06-16T00:00:00+00:00")["stepCount"], 2)
        # ticket exact filter
        self.assertEqual(
            s.summarize(lines, ticket="RUS-99")["stepCount"], 1)
        # combined
        self.assertEqual(
            s.summarize(lines, since="2026-06-16T00:00:00+00:00",
                        ticket="RUS-99")["stepCount"], 1)


class ReportShapeTest(unittest.TestCase):
    def test_timestamp_span(self):
        lines = [
            _line(timestamp="2026-06-15T00:00:00+00:00"),
            _line(timestamp="2026-06-17T00:00:00+00:00"),
            _line(timestamp="2026-06-16T00:00:00+00:00"),
        ]
        span = s.summarize(lines)["timestampSpan"]
        self.assertEqual(span["start"], "2026-06-15T00:00:00+00:00")
        self.assertEqual(span["end"], "2026-06-17T00:00:00+00:00")

    def test_timestamp_span_null_when_empty(self):
        span = s.summarize([])["timestampSpan"]
        self.assertIsNone(span["start"])
        self.assertIsNone(span["end"])

    def test_per_lens_edge_rollup(self):
        line = _line(rounds=[
            {"lens": None, "pass": False, "findingsCount": 1},
            {"lens": "completeness", "pass": True, "findingsCount": 0},
        ])
        per_lens = s.summarize([line])["perLens"]
        self.assertIn("edge", per_lens)        # lens:null rolled under "edge"
        self.assertIn("completeness", per_lens)
        self.assertEqual(per_lens["edge"]["steps"], 1)
        self.assertEqual(per_lens["edge"]["dissentRate"], 1.0)
        self.assertEqual(per_lens["completeness"]["dissentRate"], 0.0)

    def test_terminal_action_counts(self):
        lines = [
            _line(terminal_action="converged"),
            _line(terminal_action="converged"),
            _line(terminal_action="cap_reached"),
        ]
        counts = s.summarize(lines)["terminalActionCounts"]
        self.assertEqual(counts["converged"], 2)
        self.assertEqual(counts["cap_reached"], 1)


class CliTest(unittest.TestCase):
    def test_main_prints_json_with_all_keys(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        self.addCleanup(os.unlink, path)
        with open(path, "w") as fh:
            fh.write(json.dumps(_line(run_id="run-A", rounds=[
                {"lens": "a", "pass": False, "findingsCount": 1},
                {"lens": "a", "pass": True, "findingsCount": 0},
            ])) + "\n")
            fh.write(json.dumps(_line(run_id="run-B")) + "\n")

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = s.main(["--run-id", "run-A", path])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        for key in ("stepCount", "timestampSpan", "dissentRate",
                    "dissentRevisedRate", "terminalActionCounts", "perLens",
                    "abortedRecords"):
            self.assertIn(key, out)
        # --run-id scoped to run-A only (1 line)
        self.assertEqual(out["stepCount"], 1)


if __name__ == "__main__":
    unittest.main()
