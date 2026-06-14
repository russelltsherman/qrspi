#!/usr/bin/env python3
"""Tests for check_workflows.js (the Workflow-script syntax gate).

Stdlib-only, unittest-based. Run with:
    python3 scripts/check_workflows_test.py

Drives the Node gate as a subprocess against fixtures and asserts its exit-code
contract. Skips automatically when `node` is unavailable so the Python suite
stays green on node-less machines (CI runners have Node preinstalled).
"""

import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
GATE = os.path.join(SCRIPT_DIR, "check_workflows.js")
REAL_WORKFLOW = os.path.join(REPO_ROOT, ".claude", "workflows", "qrspi-batch.js")
NODE = shutil.which("node")

# A minimal but harness-shaped script: module-level `export const meta`, an
# injected-global reference, top-level await, and a top-level return — all of
# which are illegal in a plain Node module but valid the way the harness loads it.
VALID_WORKFLOW = (
    "export const meta = { name: 'x', description: 'y' }\n"
    "log('hi')\n"
    "const data = await agent('do a thing')\n"
    "return { ok: true, data }\n"
)

# Same shape but with a genuine syntax error (unbalanced paren) in the body.
BROKEN_WORKFLOW = (
    "export const meta = { name: 'x', description: 'y' }\n"
    "const data = await agent('do a thing'\n"   # missing close paren
    "return { ok: true }\n"
)


def _run(*args):
    return subprocess.run([NODE, GATE, *args], capture_output=True, text=True)


@unittest.skipIf(NODE is None, "node not installed")
class CheckWorkflowsGate(unittest.TestCase):
    def test_real_workflow_passes(self):
        # The committed orchestrator must always pass its own gate.
        proc = _run(REAL_WORKFLOW)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_valid_harness_shaped_file_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ok.js")
            with open(p, "w") as fh:
                fh.write(VALID_WORKFLOW)
            proc = _run(p)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_broken_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bad.js")
            with open(p, "w") as fh:
                fh.write(BROKEN_WORKFLOW)
            proc = _run(p)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("FAIL", proc.stdout + proc.stderr)

    def test_no_args_fails(self):
        proc = _run()
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
