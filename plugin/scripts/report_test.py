#!/usr/bin/env python3
"""Stdlib-only unit tests for report.py — run with python3.

    python3 scripts/report_test.py        # or: cd scripts && python3 report_test.py

Two complementary feature areas are covered:

* RUS-40 Slice 4 (plan §4.24/§4.26): the version-level `test_score`-drop guard
  added to `build_ledger_entry`. We assert over synthetic version sequences that:
    (a) a `> 0.05` test_score drop from the prior version surfaces an alert in BOTH
        the in-memory report (`report["alerts"]["version_score_regression"]`) AND the
        durable `ledger.json` entry (`entry["version_score_regression"]`);
    (b) a `<= 0.05` change produces no such alert in either place.
  This complements (does not replace) the existing per-case 0.2 guard in
  `detect_regressions` (AC4, ref Q15).

* RUS-41 Slice 1: the version enumerator (`load_version_results`) excludes the
  `results/all/` subtree so it cannot be mis-read as a version corrupting the ledger,
  while a normal `results/v1/` is still counted.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import report


# --- helpers ---------------------------------------------------------------

def _write_version(results_dir, name, test_score, train_score=None, gap=0.0):
    """Create <results_dir>/<name>/grades.json with the given scores."""
    if train_score is None:
        train_score = test_score
    vdir = os.path.join(results_dir, name)
    os.makedirs(vdir, exist_ok=True)
    grades = {
        "timestamp": "2026-01-01T00:00:00Z",
        "train_score": train_score,
        "test_score": test_score,
        "train_test_gap": gap,
        "cases": [],
    }
    with open(os.path.join(vdir, "grades.json"), "w") as f:
        json.dump(grades, f)


def _write_grades(version_dir: Path) -> None:
    """Create a minimal valid grades.json inside version_dir."""
    version_dir.mkdir(parents=True, exist_ok=True)
    with open(version_dir / "grades.json", "w") as f:
        json.dump(
            {
                "timestamp": "2026-06-11T00:00:00Z",
                "train_score": 1.0,
                "test_score": 1.0,
                "train_test_gap": 0.0,
                "cases": [],
            },
            f,
        )


# --- pure build_ledger_entry tests ----------------------------------------

class BuildLedgerEntryGuardTest(unittest.TestCase):
    """The version-level guard is computed inside build_ledger_entry itself."""

    def _version(self, name, test_score):
        return {"version": name, "grades": {"test_score": test_score}}

    def test_drop_over_threshold_flags_regression(self):
        prev = {"test_score": 0.90}
        entry = report.build_ledger_entry(
            self._version("v2", 0.80), "v1", [], previous_grades=prev
        )
        # 0.90 - 0.80 = 0.10 > 0.05
        self.assertTrue(entry["version_score_regression"])
        self.assertAlmostEqual(entry["version_score_drop"], 0.10, places=4)

    def test_drop_at_or_below_threshold_does_not_flag(self):
        prev = {"test_score": 0.90}
        entry = report.build_ledger_entry(
            self._version("v2", 0.86), "v1", [], previous_grades=prev
        )
        # 0.90 - 0.86 = 0.04 <= 0.05
        self.assertFalse(entry["version_score_regression"])
        self.assertAlmostEqual(entry["version_score_drop"], 0.04, places=4)

    def test_exactly_threshold_does_not_flag(self):
        prev = {"test_score": 0.90}
        entry = report.build_ledger_entry(
            self._version("v2", 0.85), "v1", [], previous_grades=prev
        )
        # 0.90 - 0.85 = 0.05; guard is strict ">" so 0.05 does NOT alert
        self.assertFalse(entry["version_score_regression"])

    def test_improvement_does_not_flag(self):
        prev = {"test_score": 0.70}
        entry = report.build_ledger_entry(
            self._version("v2", 0.90), "v1", [], previous_grades=prev
        )
        self.assertFalse(entry["version_score_regression"])
        self.assertLess(entry["version_score_drop"], 0)

    def test_baseline_without_previous_does_not_flag(self):
        entry = report.build_ledger_entry(
            self._version("v1", 0.90), None, [], previous_grades=None
        )
        self.assertFalse(entry["version_score_regression"])
        self.assertEqual(entry["version_score_drop"], 0)


# --- end-to-end report + ledger.json tests ---------------------------------

class ReportAndLedgerAlertTest(unittest.TestCase):
    """The flag is surfaced in both report["alerts"] and the durable ledger.json."""

    def test_over_threshold_drop_alerts_in_report_and_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            _write_version(d, "v1", 0.90)
            _write_version(d, "v2", 0.80)  # drop 0.10 > 0.05
            out = os.path.join(d, "report.json")

            rep = report.generate_report(d, out)
            self.assertTrue(rep["alerts"]["version_score_regression"])

            report.update_ledger(d)
            with open(os.path.join(d, "ledger.json")) as f:
                ledger = json.load(f)
            self.assertTrue(ledger[-1]["version_score_regression"])
            self.assertAlmostEqual(ledger[-1]["version_score_drop"], 0.10, places=4)

    def test_within_threshold_change_does_not_alert(self):
        with tempfile.TemporaryDirectory() as d:
            _write_version(d, "v1", 0.90)
            _write_version(d, "v2", 0.87)  # drop 0.03 <= 0.05
            out = os.path.join(d, "report.json")

            rep = report.generate_report(d, out)
            self.assertFalse(rep["alerts"]["version_score_regression"])

            report.update_ledger(d)
            with open(os.path.join(d, "ledger.json")) as f:
                ledger = json.load(f)
            self.assertFalse(ledger[-1]["version_score_regression"])


# --- version enumerator (results/all/ exclusion) tests ---------------------

class LoadVersionResultsTest(unittest.TestCase):
    def test_all_subdir_excluded_v1_still_enumerated(self):
        """results/all/ is skipped; a normal results/v1/ is still a version."""
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp)
            _write_grades(results / "v1")
            _write_grades(results / "all")

            versions = report.load_version_results(str(results))
            names = {v["version"] for v in versions}

            self.assertIn("v1", names, "results/v1/ must still be enumerated")
            self.assertNotIn(
                "all", names, "results/all/ must NOT be enumerated as a version"
            )

    def test_only_all_yields_no_versions(self):
        """A results/ tree whose only graded subdir is all/ yields nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp)
            _write_grades(results / "all")

            versions = report.load_version_results(str(results))

            self.assertEqual(
                versions, [], "results/all/ alone must produce no versions"
            )

    def test_multiple_versions_still_enumerated(self):
        """Normal version dirs are unaffected by the all/ exclusion."""
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp)
            _write_grades(results / "v1")
            _write_grades(results / "v2")
            _write_grades(results / "all")

            versions = report.load_version_results(str(results))
            names = {v["version"] for v in versions}

            self.assertEqual({"v1", "v2"}, names)


if __name__ == "__main__":
    unittest.main()
