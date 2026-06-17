#!/usr/bin/env python3
"""Producer-side contract conformance tests — run with `python3`.

Pins each Python producer of a JS↔Python orchestrator-seam envelope to its
committed well-formed golden under `scripts/fixtures/contract_seam/<seam>/`.
For every covered seam this asserts BOTH:

  (a) SHAPE — the producer's pure builder output carries the fixture's
      documented required fields; and
  (b) FORMATTING — the producer's serialized form byte-for-byte equals the
      committed `wellformed.json`.

Five seams (config, sync-trunk, land, ordered-tickets, critics) have a `main()`
that serializes from pure, in-memory state. `config` is pinned by invoking the real
producer as a subprocess (`python3 qrspi_config.py --key linearProject`) and
byte-matching its stdout, which directly pins `main()`; the other four reproduce that
exact `main()` `json.dumps`/`json.dump` call against the pure builder. Three seams
(resolve, restack, cleanup) are IO-bound — their `main()` inspects the live
worktree/git and cannot run headless — so formatting is pinned via
`json.dumps(builder_output, <same kwargs as main>)` against the pure builder.

KNOWN LIMITATION (the three IO-bound seams resolve / restack / cleanup): because
their `main()` cannot run headless, the kwargs below (`indent=2` + trailing
newline) are hardcoded to match what each `main()` does *today*. This does NOT
pin `main()`'s own `json.dump` call — a future edit to one of those serializers
(e.g. flipping `indent`, dropping the trailing newline) would NOT trip this test;
the test and `main()` would drift independently. For these three seams the
formatting guard degenerates to "json.dumps(indent=2) produces indent=2"; editing
the *fixture* or the kwargs here is what trips them. The five headless-`main()`
seams are fully pinned. This limitation is recorded in
`docs/testing-dynamic-workflows.md` (ref: structure.md Slice 2; plan.md step 22).

Pure cores imported per seam (confirmed at build time, resolving Unverified
Assumptions 1-3):
  resolve         -> qrspi_resolve.build_envelope + qrspi_resolve_state.resolve
  config          -> (no pure builder; main() invoked as a subprocess, stdout pinned)
  critics         -> qrspi_critics_config.default_phases
  sync-trunk      -> qrspi_sync_trunk.build_envelope
  land            -> qrspi_land_verify.verify_landed
  ordered-tickets -> qrspi_order_tickets.sort_tickets
  restack         -> qrspi_restack.build_envelope   (IO-bound; REPO_ROOT patched)
  cleanup         -> qrspi_cleanup._envelope        (IO-bound; REPO_ROOT patched)
"""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qrspi_resolve  # noqa: E402
import qrspi_resolve_state  # noqa: E402
import qrspi_critics_config  # noqa: E402
import qrspi_sync_trunk  # noqa: E402
import qrspi_land_verify  # noqa: E402
import qrspi_order_tickets  # noqa: E402
import qrspi_restack  # noqa: E402
import qrspi_cleanup  # noqa: E402

# Placeholder host checkout root the fixtures were pinned against (the producers
# emit `repoRoot`; the golden fixtures use this exact literal).
REPO = "/repo"

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures",
    "contract_seam",
)


def _read_fixture(seam, variant="wellformed"):
    """Read a fixture as raw text (byte-for-byte formatting comparison)."""
    with open(os.path.join(FIXTURES, seam, variant + ".json"), encoding="utf-8") as fh:
        return fh.read()


class ProducerShapeAndFormatTests(unittest.TestCase):
    """Each seam: builder output has the required fields (shape) AND its serialized
    form byte-matches the committed well-formed fixture (formatting)."""

    def test_resolve(self):
        # IO-bound seam: pin formatting via json.dumps(builder, indent=2) + "\n",
        # matching qrspi_resolve.main()'s json.dump(env, ..., indent=2) + print().
        state = {"assigned": True, "linearStatus": "Selected", "phases": {}}
        decision = qrspi_resolve_state.resolve(state)
        env = qrspi_resolve.build_envelope(
            worktree_dir=REPO + "/.worktrees/RUS-1",
            decision=decision,
            existing=["design"],
            repo_root=REPO,
            reviewers="@me",
            team_reviewers="",
            ticket_content_path=REPO + "/.worktrees/RUS-1/.qrspi/RUS-1/ticket.md",
            tip="RUS-1/design",
            slices=[],
        )
        # Shape: top-level envelope keys + the embedded decision's action. The CI-gated
        # revision feature (RUS-81 Slice 3) adds two additive top-level re-emit keys —
        # `ciFailing` (bool) and `ciFailingChecks` (list) — surfaced from the decision /
        # phase shape, defaulting to False/[] for this non-CI run_design decision. The
        # CI-revise-cap feature (RUS-83 Slice 3) adds one more additive re-emit key —
        # `ciRedBranches` (list) — the deterministic red-branch list for doRevise,
        # defaulting to [] for this non-CI decision.
        for key in ("ok", "repoRoot", "worktreeDir", "existing", "decision",
                    "commentTargets", "ciFailing", "ciFailingChecks", "ciRedBranches",
                    "reviewers", "teamReviewers", "ticketContentPath", "tip", "slices"):
            self.assertIn(key, env)
        self.assertIn("action", env["decision"])
        self.assertEqual(env["decision"]["action"], "run_design")
        self.assertEqual(env["ciFailing"], False)
        self.assertEqual(env["ciFailingChecks"], [])
        self.assertEqual(env["ciRedBranches"], [])
        # Formatting: byte-for-byte.
        self.assertEqual(json.dumps(env, indent=2) + "\n", _read_fixture("resolve"))

    def test_config(self):
        # qrspi_config has no pure builder, but its main() is a thin
        # print(json.dumps({"ok": True, "key": key, "value": value})). Invoking the
        # real producer as a subprocess and byte-matching its stdout to the fixture
        # actually pins main() — a renamed field, added indent, or changed key in
        # qrspi_config.py would trip this (a hand-copied literal would not).
        # `linearProject` is absent from the committed config / default-aware, so the
        # producer resolves DEFAULTS["linearProject"] == "QRSPI", matching the golden.
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "qrspi_config.py")
        proc = subprocess.run(
            [sys.executable, script, "--key", "linearProject"],
            capture_output=True, text=True, check=True,
        )
        # Shape: the produced envelope carries the documented required fields.
        env = json.loads(proc.stdout)
        for key in ("ok", "key", "value"):
            self.assertIn(key, env)
        # Formatting: the producer's stdout byte-for-byte equals the fixture.
        self.assertEqual(proc.stdout, _read_fixture("config"))

    def test_critics(self):
        # Headless main(): print(json.dumps({"ok", "phases", "warnings"})).
        phases = qrspi_critics_config.default_phases()
        env = {"ok": True, "phases": phases, "warnings": []}
        for key in ("ok", "phases", "warnings"):
            self.assertIn(key, env)
        # Two-phase shape (RUS-88 retired the edge critic; mirrors DEFAULT_CRITIC_PHASES
        # in qrspi-batch.js — design PANEL + implementation coherence pass only).
        self.assertEqual(
            set(env["phases"].keys()),
            {"design", "implementation"},
        )
        self.assertEqual(json.dumps(env) + "\n", _read_fixture("critics"))

    def test_sync_trunk(self):
        # Headless main(): print(json.dumps(build_envelope(...))).
        env = qrspi_sync_trunk.build_envelope(
            token="updated",
            repo_root=REPO,
            head_branch="main",
            dirty_porcelain="",
            fetch_detail="",
            local_sha="aaaaaaa",
            origin_sha="bbbbbbb",
        )
        for key in ("ok", "repoRoot", "updated", "from", "to"):
            self.assertIn(key, env)
        self.assertEqual(json.dumps(env) + "\n", _read_fixture("sync-trunk"))

    def test_land(self):
        # Headless main(): print(json.dumps(verify_landed(...))).
        verdict = qrspi_land_verify.verify_landed(
            {"RUS-1/slice-1": {"merged": True, "prNumber": 10,
                               "state": "MERGED", "mergedByPr": 10}}
        )
        for key in ("status", "openBranches"):
            self.assertIn(key, verdict)
        self.assertEqual(json.dumps(verdict) + "\n", _read_fixture("land"))

    def test_ordered_tickets(self):
        # Headless main(): json.dump(sort_tickets(...), sys.stdout) — NO print(),
        # so the serialized form has NO trailing newline (the only such fixture).
        tickets = [
            {"id": "RUS-1", "status": "Selected", "createdAt": "2026-01-01T00:00:00Z"},
            {"id": "RUS-2", "status": "Selected", "createdAt": "2026-01-02T00:00:00Z"},
        ]
        ordered = qrspi_order_tickets.sort_tickets(
            tickets, ["Selected", "Design Review", "Plan Review", "Code Review"]
        )
        # Shape: a top-level array of ticket dicts.
        self.assertIsInstance(ordered, list)
        for ticket in ordered:
            for key in ("id", "status", "createdAt"):
                self.assertIn(key, ticket)
        self.assertEqual(json.dumps(ordered), _read_fixture("ordered-tickets"))

    def test_restack(self):
        # IO-bound seam: pin formatting via json.dumps(builder, indent=2) + "\n",
        # matching qrspi_restack.main()'s json.dump(env, ..., indent=2) + print().
        # build_envelope embeds the module-level REPO_ROOT; patch it for the golden.
        original = qrspi_restack.REPO_ROOT
        qrspi_restack.REPO_ROOT = REPO
        try:
            env = qrspi_restack.build_envelope(
                ticket="RUS-1",
                worktree_dir=REPO + "/.worktrees/RUS-1",
                tip="RUS-1/slice-2",
                ok=True,
                restacked=True,
                submitted=True,
            )
        finally:
            qrspi_restack.REPO_ROOT = original
        for key in ("ok", "repoRoot", "ticket", "worktreeDir", "tip",
                    "restacked", "submitted"):
            self.assertIn(key, env)
        self.assertIsInstance(env["ok"], bool)
        self.assertEqual(json.dumps(env, indent=2) + "\n", _read_fixture("restack"))

    def test_cleanup(self):
        # IO-bound seam: pin formatting via json.dumps(builder, indent=2) + "\n",
        # matching qrspi_cleanup.main()'s json.dump(env, ..., indent=2) + print().
        # _envelope embeds the module-level REPO_ROOT; patch it for the golden.
        original = qrspi_cleanup.REPO_ROOT
        qrspi_cleanup.REPO_ROOT = REPO
        try:
            removed = {
                "worktree": True,
                "branches": ["RUS-1/design", "RUS-1/plan", "RUS-1/slice-1"],
                "remotes": ["RUS-1/design", "RUS-1/plan", "RUS-1/slice-1"],
            }
            env = qrspi_cleanup._envelope(
                ok=True,
                decision="cleanup",
                reason="stack fully merged; reaping worktree and branches",
                removed=removed,
                dry_run=False,
                failed_remotes=[],
            )
        finally:
            qrspi_cleanup.REPO_ROOT = original
        for key in ("ok", "repoRoot", "decision", "reason", "removed",
                    "failedRemotes", "dryRun"):
            self.assertIn(key, env)
        self.assertIsInstance(env["ok"], bool)
        self.assertIsInstance(env["decision"], str)
        # The additive failedRemotes pass-through (RUS-68) is pinned in the golden.
        self.assertEqual(env["failedRemotes"], [])
        self.assertEqual(json.dumps(env, indent=2) + "\n", _read_fixture("cleanup"))


if __name__ == "__main__":
    unittest.main()
