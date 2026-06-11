#!/usr/bin/env python3
"""Stdlib-only unit tests for eval_all.py (the multi-agent eval driver).

Run from the scripts/ directory so the bare-name import resolves:

    cd scripts && python3 eval_all_test.py

Covers: agent discovery/glob, phase->path mapping, suite filtering (preserving
name/cases), aggregation (phase-level vs suite-level distinct fields), the
error-vs-low-score distinction, the --regression-only exit code, and the
integration with Slice 1 (report.py excludes a populated results/all/).
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import eval_all
import report  # Slice 1 guard, reused in the integration test


class DiscoverAgentsTest(unittest.TestCase):
    def test_globs_qrspi_agents_and_strips_prefix(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "qrspi-foo.md").write_text("foo")
            (Path(d) / "qrspi-bar.md").write_text("bar")
            (Path(d) / "README.md").write_text("not an agent")
            (Path(d) / "qrspi-baz.txt").write_text("wrong extension")
            phases = eval_all.discover_agents(d)
        self.assertEqual(phases, ["bar", "foo"])  # sorted, prefix stripped


class PhaseToAgentPathTest(unittest.TestCase):
    def test_maps_phase_to_agent_file(self):
        self.assertEqual(
            eval_all.phase_to_agent_path("design", ".claude/agents"),
            os.path.join(".claude/agents", "qrspi-design.md"),
        )


class FilterSuiteTest(unittest.TestCase):
    def setUp(self):
        self.suite = {
            "name": "qrspi-suite",
            "version": "1",
            "cases": [
                {"id": "c1", "phase": "questions", "prompt": "p", "assertions": []},
                {"id": "c2", "phase": "design", "prompt": "p", "assertions": []},
                {"id": "c3", "phase": "questions", "prompt": "p", "assertions": []},
            ],
        }

    def test_keeps_name_and_only_matching_cases(self):
        sub = eval_all.filter_suite(self.suite, "questions")
        self.assertEqual(sub["name"], "qrspi-suite")
        self.assertIn("cases", sub)
        self.assertEqual([c["id"] for c in sub["cases"]], ["c1", "c3"])

    def test_never_drops_cases_key_even_when_empty(self):
        sub = eval_all.filter_suite(self.suite, "nonexistent")
        self.assertIn("cases", sub)
        self.assertEqual(sub["cases"], [])
        self.assertIn("name", sub)

    def test_preserves_other_top_level_fields(self):
        sub = eval_all.filter_suite(self.suite, "design")
        self.assertEqual(sub["version"], "1")


class ReadPhaseResultTest(unittest.TestCase):
    def _write(self, d, grades=None, results=None, baseline=None):
        if grades is not None:
            (Path(d) / "grades.json").write_text(json.dumps(grades))
        if results is not None:
            (Path(d) / "results.json").write_text(json.dumps(results))
        if baseline is not None:
            (Path(d) / "baseline.json").write_text(json.dumps(baseline))

    def test_ok_status_when_scored_and_no_error(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d,
                        grades={"train_score": 0.9, "test_score": 0.8},
                        results={"results": [{"case_id": "c1", "error": None}]})
            pr = eval_all.read_phase_result("design", d)
        self.assertEqual(pr["status"], "ok")
        self.assertEqual(pr["train_score"], 0.9)
        self.assertEqual(pr["test_score"], 0.8)
        self.assertIsNone(pr["error"])

    def test_low_score_when_below_floor_no_error(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d,
                        grades={"train_score": 0.1, "test_score": 0.1},
                        results={"results": [{"case_id": "c1"}]})
            pr = eval_all.read_phase_result("design", d)
        self.assertEqual(pr["status"], "low_score")
        self.assertIsNone(pr["error"])

    def test_errored_is_distinct_from_low_score(self):
        # A phase that both crashed AND scored low must report errored, not low_score.
        with tempfile.TemporaryDirectory() as d:
            self._write(d,
                        grades={"train_score": 0.0, "test_score": 0.0},
                        results={"results": [{"case_id": "c1", "error": "boom"}]})
            pr = eval_all.read_phase_result("design", d)
        self.assertEqual(pr["status"], "errored")
        self.assertEqual(pr["error"], "boom")

    def test_reads_baseline_score(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d,
                        grades={"train_score": 0.7, "test_score": 0.7},
                        results={"results": []},
                        baseline={"test_score": 0.9})
            pr = eval_all.read_phase_result("design", d)
        self.assertEqual(pr["baseline_score"], 0.9)


class AggregateTest(unittest.TestCase):
    def test_phase_level_vs_suite_level_fields_distinct(self):
        phase_results = [
            {"phase": "a", "status": "ok", "train_score": 0.9, "test_score": 0.5,
             "error": None, "results_dir": "a", "baseline_score": 0.9},  # drop 0.4 -> regress
            {"phase": "b", "status": "ok", "train_score": 0.8, "test_score": 0.8,
             "error": None, "results_dir": "b", "baseline_score": 0.8},  # no drop
        ]
        summary = eval_all.aggregate(phase_results, 0.05)
        # phase-level field
        self.assertEqual(summary["phase_regressions"], ["a"])
        # suite-level field is distinct (mean baseline 0.85 vs mean test 0.65 -> drop 0.2)
        self.assertTrue(summary["suite_regression"])
        self.assertIn("phases", summary)
        self.assertIn("a", summary["phases"])
        self.assertIn("suite_aggregate", summary)
        self.assertIn("train_score", summary["suite_aggregate"])
        self.assertIn("test_score", summary["suite_aggregate"])

    def test_no_regression_when_within_threshold(self):
        phase_results = [
            {"phase": "a", "status": "ok", "train_score": 0.8, "test_score": 0.78,
             "error": None, "results_dir": "a", "baseline_score": 0.8},  # drop 0.02 < 0.05
        ]
        summary = eval_all.aggregate(phase_results, 0.05)
        self.assertEqual(summary["phase_regressions"], [])
        self.assertFalse(summary["suite_regression"])

    def test_errored_phases_distinct_from_regressions(self):
        phase_results = [
            {"phase": "a", "status": "errored", "train_score": 0.0, "test_score": 0.0,
             "error": "boom", "results_dir": "a", "baseline_score": 0.9},
            {"phase": "b", "status": "low_score", "train_score": 0.1, "test_score": 0.1,
             "error": None, "results_dir": "b", "baseline_score": None},
        ]
        summary = eval_all.aggregate(phase_results, 0.05)
        self.assertEqual(summary["errored_phases"], ["a"])
        # errored phase is excluded from the regression comparison
        self.assertNotIn("a", summary["phase_regressions"])


class RegressionExitCodeTest(unittest.TestCase):
    """Drive main() in --regression-only mode against a populated results tree."""

    def _make_tree(self, base, phase, test_score, baseline=None, error=None):
        agents = Path(base) / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        (agents / f"qrspi-{phase}.md").write_text("agent")
        suite = {"name": "s", "cases": [
            {"id": "c1", "phase": phase, "prompt": "p", "assertions": []}]}
        suite_path = Path(base) / "suite.json"
        suite_path.write_text(json.dumps(suite))
        results_root = Path(base) / "results" / "all"
        phase_dir = results_root / phase
        phase_dir.mkdir(parents=True, exist_ok=True)
        (phase_dir / "grades.json").write_text(
            json.dumps({"train_score": test_score, "test_score": test_score}))
        results = {"results": [{"case_id": "c1", "error": error}]}
        (phase_dir / "results.json").write_text(json.dumps(results))
        if baseline is not None:
            (phase_dir / "baseline.json").write_text(
                json.dumps({"test_score": baseline}))
        return suite_path, agents, results_root

    def test_nonzero_exit_on_regression(self):
        # We bypass the subprocess single-agent path by pre-populating the
        # phase dir and pointing the driver at it; drive() re-runs run_phase,
        # so instead we exercise the aggregation + exit-code logic directly via
        # read_phase_result + aggregate + _has_regression (main's gate).
        with tempfile.TemporaryDirectory() as base:
            _, _, results_root = self._make_tree(
                base, "design", test_score=0.4, baseline=0.9)
            pr = eval_all.read_phase_result("design", str(results_root / "design"))
            summary = eval_all.aggregate([pr], eval_all.REGRESSION_THRESHOLD)
            self.assertTrue(eval_all._has_regression(summary))

    def test_zero_exit_when_no_regression(self):
        with tempfile.TemporaryDirectory() as base:
            _, _, results_root = self._make_tree(
                base, "design", test_score=0.88, baseline=0.9)
            pr = eval_all.read_phase_result("design", str(results_root / "design"))
            summary = eval_all.aggregate([pr], eval_all.REGRESSION_THRESHOLD)
            self.assertFalse(eval_all._has_regression(summary))


class ReportAllGuardIntegrationTest(unittest.TestCase):
    """Slice-1 integration: a POPULATED results/all/ must not be enumerated."""

    def test_all_subtree_excluded_even_with_grades(self):
        with tempfile.TemporaryDirectory() as base:
            results = Path(base) / "results"
            # A real version dir.
            (results / "v1").mkdir(parents=True)
            (results / "v1" / "grades.json").write_text(
                json.dumps({"train_score": 0.5, "test_score": 0.5,
                            "timestamp": "t", "cases": []}))
            # The consolidated all/ dir, populated by eval_all (top-level grades-
            # looking summary AND a per-phase grades.json nested under all/).
            (results / "all").mkdir(parents=True)
            (results / "all" / "grades.json").write_text(
                json.dumps({"train_score": 0.9, "test_score": 0.9,
                            "timestamp": "t", "cases": []}))
            (results / "all" / "design").mkdir()
            (results / "all" / "design" / "grades.json").write_text(
                json.dumps({"train_score": 0.9, "test_score": 0.9,
                            "timestamp": "t", "cases": []}))

            versions = report.load_version_results(str(results))
            names = [v["version"] for v in versions]
        self.assertIn("v1", names)
        self.assertNotIn("all", names)


if __name__ == "__main__":
    unittest.main()
