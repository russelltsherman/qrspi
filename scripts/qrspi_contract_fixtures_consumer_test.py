#!/usr/bin/env python3
"""Consumer-side contract-seam regression test (RUS-76, Slice 3).

The cross-language drift guard's CONSUMER half: pins each of the eight JS envelope
parsers in `.claude/workflows/qrspi-batch.js` to the committed
`scripts/fixtures/contract_seam/<seam>/*.json` fixtures, and asserts each parser's
distinct fail-closed / fail-open sentinel on the malformed variants.

Stdlib-only, unittest-based. Run with:
    python3 scripts/qrspi_contract_fixtures_consumer_test.py
or via the aggregating runner:
    python3 scripts/run_tests.py contract_fixtures_consumer

It drives the Node harness `scripts/contract_seam_runner.js` as a subprocess (the
JS sandbox cannot be imported into Python; the runner loads qrspi-batch.js the same
way the Workflow harness does and exposes the parsers via an in-memory shim). The
whole case SKIPS (does not fail) when `node` is unavailable, mirroring
check_workflows_test.py, so the Python suite stays green on node-less machines.

Coverage is the SEVEN surviving parsers (the critics seam was removed when the
autonomous batch stopped reading critics config):
parseResolveEnvelope, parseConfigEnvelope, parseSyncTrunkEnvelope, parseLandVerdict,
parseOrderedTickets, parseRestackEnvelope, parseCleanupEnvelope.
"""

import json
import os
import shutil
import subprocess
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
RUNNER = os.path.join(SCRIPT_DIR, "contract_seam_runner.js")
FIXTURES = os.path.join(SCRIPT_DIR, "fixtures", "contract_seam")
NODE = shutil.which("node")


def fixture(seam, variant):
    return os.path.join(FIXTURES, seam, f"{variant}.json")


def run_parser(parser, *fixtures):
    """Invoke the Node runner for `parser` over one-or-more fixture paths.

    Returns a list of the parser's results (the `result` field of each emitted
    {parser, fixture, result} record), in fixture order.
    """
    proc = subprocess.run(
        [NODE, RUNNER, parser, *fixtures],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"runner exited {proc.returncode} for {parser} {fixtures}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    records = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return [r["result"] for r in records]


def run_one(parser, seam, variant):
    """Convenience: run a single fixture and return just its result."""
    return run_parser(parser, fixture(seam, variant))[0]


@unittest.skipIf(NODE is None, "node not installed")
class SmokeLoad(unittest.TestCase):
    """The node:vm load-with-stubs recipe must expose the parsers without running
    the orchestration (the chief risk per design)."""

    def test_smoke_load_config_wellformed(self):
        result = run_one("parseConfigEnvelope", "config", "wellformed")
        self.assertEqual(result, {"ok": True, "key": "linearProject", "value": "QRSPI"})


@unittest.skipIf(NODE is None, "node not installed")
class WellFormedAcceptance(unittest.TestCase):
    """Each parser ACCEPTS its well-formed fixture (returns the parsed value, not a
    sentinel)."""

    def test_resolve_wellformed_accepted(self):
        result = run_one("parseResolveEnvelope", "resolve", "wellformed")
        self.assertTrue(result["ok"])
        self.assertEqual(result["decision"]["action"], "run_design")
        self.assertEqual(result["worktreeDir"], "/repo/.worktrees/RUS-1")
        # RUS-81 Slice 3: the consumer reads the additive top-level CI re-emit keys
        # (False/[] for this non-CI run_design envelope).
        self.assertEqual(result["ciFailing"], False)
        self.assertEqual(result["ciFailingChecks"], [])

    def test_resolve_prose_wrapped_accepted(self):
        # The brace-depth extractor locates the balanced object inside prose.
        result = run_one("parseResolveEnvelope", "resolve", "prose_wrapped")
        self.assertTrue(result["ok"])
        self.assertEqual(result["decision"]["action"], "run_design")

    def test_config_wellformed_accepted(self):
        result = run_one("parseConfigEnvelope", "config", "wellformed")
        self.assertEqual(result, {"ok": True, "key": "linearProject", "value": "QRSPI"})

    def test_sync_trunk_wellformed_accepted(self):
        result = run_one("parseSyncTrunkEnvelope", "sync-trunk", "wellformed")
        self.assertTrue(result["ok"])
        self.assertTrue(result["updated"])
        self.assertEqual(result["from"], "aaaaaaa")
        self.assertEqual(result["to"], "bbbbbbb")

    def test_sync_trunk_prose_wrapped_accepted(self):
        result = run_one("parseSyncTrunkEnvelope", "sync-trunk", "prose_wrapped")
        self.assertTrue(result["ok"])
        self.assertTrue(result["updated"])

    def test_land_wellformed_accepted(self):
        result = run_one("parseLandVerdict", "land", "wellformed")
        self.assertEqual(result, {"status": "landed", "openBranches": []})

    def test_ordered_tickets_wellformed_accepted(self):
        result = run_one("parseOrderedTickets", "ordered-tickets", "wellformed")
        self.assertIsInstance(result, list)
        self.assertEqual([t["id"] for t in result], ["RUS-1", "RUS-2"])

    def test_restack_wellformed_accepted(self):
        result = run_one("parseRestackEnvelope", "restack", "wellformed")
        self.assertTrue(result["ok"])
        self.assertTrue(result["restacked"])

    def test_cleanup_wellformed_accepted(self):
        result = run_one("parseCleanupEnvelope", "cleanup", "wellformed")
        self.assertTrue(result["ok"])
        self.assertEqual(result["decision"], "cleanup")
        # The additive RUS-68 failedRemotes pass-through is preserved.
        self.assertEqual(result["failedRemotes"], [])


@unittest.skipIf(NODE is None, "node not installed")
class MalformedFailModes(unittest.TestCase):
    """Each loud seam returns its DISTINCT fail-closed sentinel on malformed input;
    the silent seams return their fail-open value."""

    # --- loud seams: fail-closed-to-error {ok:false, error} -----------------
    def test_resolve_no_json_sentinel(self):
        result = run_one("parseResolveEnvelope", "resolve", "no_json")
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"])
        self.assertIn("resolve:", result["error"])

    def test_resolve_unknown_action_sentinel(self):
        result = run_one("parseResolveEnvelope", "resolve", "unknown_action")
        self.assertFalse(result["ok"])
        self.assertIn("unknown decision.action", result["error"])

    def test_config_missing_ok_sentinel(self):
        result = run_one("parseConfigEnvelope", "config", "missing_ok")
        self.assertFalse(result["ok"])
        self.assertIn("config:", result["error"])

    def test_config_wrong_type_sentinel(self):
        result = run_one("parseConfigEnvelope", "config", "wrong_type")
        self.assertFalse(result["ok"])
        self.assertIn("value not a string", result["error"])

    def test_sync_trunk_missing_field_sentinel(self):
        result = run_one("parseSyncTrunkEnvelope", "sync-trunk", "missing_field")
        self.assertFalse(result["ok"])
        self.assertIn("sync-trunk:", result["error"])

    def test_restack_missing_ok_sentinel(self):
        result = run_one("parseRestackEnvelope", "restack", "missing_ok")
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["error"], "restack: envelope missing ok flag")

    # --- cleanup: distinct sentinel uniquely carries decision:'skip' --------
    def test_cleanup_missing_decision_sentinel(self):
        result = run_one("parseCleanupEnvelope", "cleanup", "missing_decision")
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["decision"], "skip")
        self.assertEqual(result["error"], "cleanup: envelope missing decision")

    # --- land: fail-closed-to {status:'incomplete'} -------------------------
    def test_land_missing_field_sentinel(self):
        result = run_one("parseLandVerdict", "land", "missing_field")
        self.assertEqual(result["status"], "incomplete")

    # --- ordered-tickets: silent seam → null --------------------------------
    def test_ordered_tickets_malformed_null(self):
        result = run_one("parseOrderedTickets", "ordered-tickets", "malformed")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
