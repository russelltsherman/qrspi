#!/usr/bin/env python3
"""Unit tests for run_tests (the aggregating Python test runner).

Stdlib-only, unittest-based (matches the unittest.main subset of the repo's
script tests). Run with:
    python3 scripts/run_tests_test.py
Exits 0 if all pass, non-zero on failure.

Covers discovery (glob + pattern filter), single-file execution (pass/fail/
timeout), suite aggregation, and the main() exit-code contract. Test fixtures
are written to a temp dir so these checks never depend on the real suite's
membership.
"""

import io
import os
import tempfile
import unittest

from run_tests import discover_tests, run_one, run_suite, main

PASS_SCRIPT = "import sys; print('ok'); sys.exit(0)\n"
FAIL_SCRIPT = "import sys; print('boom'); sys.exit(1)\n"
HANG_SCRIPT = "import time; time.sleep(30)\n"


def _write(d, name, body):
    path = os.path.join(d, name)
    with open(path, "w") as fh:
        fh.write(body)
    return path


class DiscoverTests(unittest.TestCase):
    def test_finds_only_test_suffix_sorted(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "b_test.py", PASS_SCRIPT)
            _write(d, "a_test.py", PASS_SCRIPT)
            _write(d, "helper.py", PASS_SCRIPT)        # not a *_test.py
            _write(d, "notes.txt", "x")               # not python
            found = [os.path.basename(p) for p in discover_tests(d)]
            self.assertEqual(found, ["a_test.py", "b_test.py"])

    def test_pattern_filters_by_substring(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "resolve_test.py", PASS_SCRIPT)
            _write(d, "persist_test.py", PASS_SCRIPT)
            found = [os.path.basename(p) for p in discover_tests(d, "resolve")]
            self.assertEqual(found, ["resolve_test.py"])

    def test_pattern_no_match_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "resolve_test.py", PASS_SCRIPT)
            self.assertEqual(discover_tests(d, "nope"), [])


class RunOneTests(unittest.TestCase):
    def test_passing_script(self):
        with tempfile.TemporaryDirectory() as d:
            p = _write(d, "ok_test.py", PASS_SCRIPT)
            ok, duration, output = run_one(p)
            self.assertTrue(ok)
            self.assertGreaterEqual(duration, 0.0)
            self.assertIn("ok", output)

    def test_failing_script(self):
        with tempfile.TemporaryDirectory() as d:
            p = _write(d, "bad_test.py", FAIL_SCRIPT)
            ok, _duration, output = run_one(p)
            self.assertFalse(ok)
            self.assertIn("boom", output)

    def test_timeout_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p = _write(d, "hang_test.py", HANG_SCRIPT)
            ok, _duration, output = run_one(p, timeout=1)
            self.assertFalse(ok)
            self.assertIn("TIMEOUT", output)


class RunSuiteTests(unittest.TestCase):
    def test_counts_and_collects_failures(self):
        with tempfile.TemporaryDirectory() as d:
            ok1 = _write(d, "one_test.py", PASS_SCRIPT)
            bad = _write(d, "two_test.py", FAIL_SCRIPT)
            ok2 = _write(d, "three_test.py", PASS_SCRIPT)
            buf = io.StringIO()
            passed, failures = run_suite([ok1, bad, ok2], out=buf)
            self.assertEqual(passed, 2)
            self.assertEqual([os.path.basename(p) for p, _ in failures], ["two_test.py"])
            # Failing output is surfaced in the report, passing output is not.
            self.assertIn("boom", buf.getvalue())
            self.assertNotIn("ok", buf.getvalue().split("Failing test output:")[-1])


class MainTests(unittest.TestCase):
    def test_list_returns_zero_and_runs_nothing(self):
        # --list against the real scripts dir: must succeed and include this file.
        self.assertEqual(main(["--list"]), 0)

    def test_pattern_with_no_match_returns_one(self):
        self.assertEqual(main(["a_pattern_that_matches_no_test_file_xyz"]), 1)


if __name__ == "__main__":
    unittest.main()
