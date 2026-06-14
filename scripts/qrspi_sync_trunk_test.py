#!/usr/bin/env python3
"""Unit tests for qrspi_sync_trunk — the FF-only trunk-sync helper.

Stdlib-only, assert-based (same convention as qrspi_paths_test.py et al.). The pure
classifier (``classify_sync``) is exercised directly with no I/O; the impure ``_run``
path is exercised by swapping ``qrspi_sync_trunk.subprocess.run`` (and stubbing
``qrspi_paths.resolve_repo_root``) with fakes, so the token→envelope mapping and the
no-fetch/no-merge short-circuit are verified without a real repo or network.

Cases (ref: structure.md Slice 1 Files touched / Verification, plan.md steps 6–9, Q12):
  pure classifier — all six tokens:
    clean FF → "updated", already-current, divergence → "divergent", dirty → "dirty",
    fetch-failed → "fetch-failed", not-on-main (a non-"main" branch name AND a detached
    None HEAD) → "not-on-main"
  precedence orderings:
    not-on-main beats dirty; dirty beats fetch-failed
  impure mapping (_run via fake subprocess):
    updated path FF-advances and emits ok:true/updated:true; a non-"main" HEAD
    short-circuits to ok:false with NO git fetch and NO git merge ever invoked

Run: python3 scripts/qrspi_sync_trunk_test.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import qrspi_sync_trunk  # noqa: E402
import qrspi_paths  # noqa: E402
from qrspi_sync_trunk import classify_sync, build_envelope, _run  # noqa: E402

failures = 0
total = 0


def check(label, got, want):
    global failures, total
    total += 1
    if got == want:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))


# --- pure classifier: all six tokens ----------------------------------------

# Clean FF available: on main, fetch ok, clean tree, SHAs differ, local is ancestor.
check("classify clean FF -> updated",
      classify_sync("main", 0, "", "aaa", "bbb", True),
      "updated")

# Already current: SHAs equal.
check("classify already-current",
      classify_sync("main", 0, "", "aaa", "aaa", True),
      "already-current")

# Divergence: SHAs differ but local main is NOT an ancestor of origin/main.
check("classify divergence -> divergent",
      classify_sync("main", 0, "", "aaa", "bbb", False),
      "divergent")

# Dirty tree (on main, non-empty porcelain).
check("classify dirty -> dirty",
      classify_sync("main", 0, " M scripts/x.py\n", "aaa", "bbb", True),
      "dirty")

# Fetch failed (on main, clean tree, non-zero fetch rc).
check("classify fetch-failed",
      classify_sync("main", 1, "", "aaa", "bbb", True),
      "fetch-failed")

# Not-on-main: a non-"main" branch name.
check("classify not-on-main (branch name)",
      classify_sync("RUS-74/plan", 0, "", "aaa", "bbb", True),
      "not-on-main")

# Not-on-main: a detached (None) HEAD.
check("classify not-on-main (detached None HEAD)",
      classify_sync(None, 0, "", "aaa", "bbb", True),
      "not-on-main")


# --- precedence orderings ----------------------------------------------------

# not-on-main beats dirty: non-"main" branch AND dirty tree -> not-on-main.
check("precedence: not-on-main beats dirty",
      classify_sync("RUS-74/plan", 0, " M scripts/x.py\n", "aaa", "bbb", True),
      "not-on-main")

# dirty beats fetch-failed: dirty tree AND non-zero fetch rc -> dirty.
check("precedence: dirty beats fetch-failed",
      classify_sync("main", 1, " M scripts/x.py\n", "aaa", "bbb", True),
      "dirty")


# --- build_envelope token mapping (pure) ------------------------------------

check("envelope updated",
      build_envelope("updated", "/repo", "main", "", "", "aaa", "bbb"),
      {"ok": True, "repoRoot": "/repo", "updated": True, "from": "aaa", "to": "bbb"})

check("envelope already-current",
      build_envelope("already-current", "/repo", "main", "", "", "aaa", "aaa"),
      {"ok": True, "repoRoot": "/repo", "updated": False, "from": "aaa", "to": "aaa"})

check("envelope divergent",
      build_envelope("divergent", "/repo", "main", "", "", "aaa", "bbb"),
      {"ok": False, "repoRoot": "/repo", "updated": False, "from": "aaa", "to": "bbb",
       "error": "local main diverged from origin/main; not fast-forwardable"})

# not-on-main: from/to null; the offending ref is spliced verbatim.
_env_branch = build_envelope("not-on-main", "/repo", "RUS-74/plan", "", "", None, None)
check("envelope not-on-main from is null", _env_branch["from"], None)
check("envelope not-on-main to is null", _env_branch["to"], None)
check("envelope not-on-main ok false", _env_branch["ok"], False)
check("envelope not-on-main names the branch",
      "RUS-74/plan" in _env_branch["error"], True)

_env_detached = build_envelope("not-on-main", "/repo", None, "", "", None, None)
check("envelope not-on-main (detached) says 'detached HEAD'",
      "detached HEAD" in _env_detached["error"], True)


# --- impure _run path via fake subprocess + stubbed repo root ---------------

class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _install_fakes(handler):
    """Swap qrspi_sync_trunk.subprocess.run with `handler` and stub resolve_repo_root.

    Returns (restore, recorded_cmds) where recorded_cmds is the live list of every cmd
    the fake handler saw (so a test can assert what was / was NOT invoked)."""
    real_run = qrspi_sync_trunk.subprocess.run
    real_resolve = qrspi_paths.resolve_repo_root
    recorded = []

    def fake_run(cmd, **kwargs):
        recorded.append(cmd)
        return handler(cmd, **kwargs)

    qrspi_sync_trunk.subprocess.run = fake_run
    qrspi_paths.resolve_repo_root = lambda *a, **k: "/fake/repo"

    def restore():
        qrspi_sync_trunk.subprocess.run = real_run
        qrspi_paths.resolve_repo_root = real_resolve

    return restore, recorded


def _capture_stdout(fn):
    """Run fn(), returning (rc, stdout_text)."""
    import io
    buf = io.StringIO()
    real = sys.stdout
    sys.stdout = buf
    try:
        rc = fn()
    finally:
        sys.stdout = real
    return rc, buf.getvalue()


def _is(cmd, *prefix):
    return tuple(cmd[:len(prefix)]) == prefix


# Impure case 1: clean FF advance — on main, clean tree, fetch ok, SHAs differ, ancestor.
def _handler_updated(cmd, **kwargs):
    if _is(cmd, "git", "symbolic-ref"):
        return _FakeCompleted(0, "main\n")
    if _is(cmd, "git", "status"):
        return _FakeCompleted(0, "")
    if _is(cmd, "git", "fetch"):
        return _FakeCompleted(0)
    if _is(cmd, "git", "rev-parse") and "main" in cmd and "origin/main" not in cmd:
        return _FakeCompleted(0, "aaaaaaa\n")
    if _is(cmd, "git", "rev-parse") and "origin/main" in cmd:
        return _FakeCompleted(0, "bbbbbbb\n")
    if _is(cmd, "git", "merge-base"):
        return _FakeCompleted(0)  # is-ancestor: rc 0 => True
    if _is(cmd, "git", "merge"):
        return _FakeCompleted(0)
    raise AssertionError("unexpected cmd: %r" % (cmd,))


import json  # noqa: E402

restore, recorded = _install_fakes(_handler_updated)
try:
    rc, out = _capture_stdout(lambda: _run(["qrspi_sync_trunk.py"]))
    env = json.loads(out)
finally:
    restore()

check("impure updated: rc 0", rc, 0)
check("impure updated: ok true", env["ok"], True)
check("impure updated: updated true", env["updated"], True)
check("impure updated: from", env["from"], "aaaaaaa")
check("impure updated: to", env["to"], "bbbbbbb")
check("impure updated: repoRoot threaded", env["repoRoot"], "/fake/repo")
check("impure updated: a git merge was invoked",
      any(_is(c, "git", "merge", "--ff-only") for c in recorded), True)


# Impure case 2: non-"main" HEAD short-circuits to ok:false with NO fetch and NO merge.
def _handler_not_on_main(cmd, **kwargs):
    if _is(cmd, "git", "symbolic-ref"):
        return _FakeCompleted(0, "RUS-74/plan\n")
    # Any other command would mean we did NOT short-circuit — fail loud.
    raise AssertionError("short-circuit violated: ran %r after non-main HEAD" % (cmd,))


restore, recorded = _install_fakes(_handler_not_on_main)
try:
    rc, out = _capture_stdout(lambda: _run(["qrspi_sync_trunk.py"]))
    env = json.loads(out)
finally:
    restore()

check("impure not-on-main: rc 1", rc, 1)
check("impure not-on-main: ok false", env["ok"], False)
check("impure not-on-main: error names branch",
      "RUS-74/plan" in env["error"], True)
check("impure not-on-main: NO git fetch invoked",
      any(_is(c, "git", "fetch") for c in recorded), False)
check("impure not-on-main: NO git merge invoked",
      any(_is(c, "git", "merge") for c in recorded), False)
check("impure not-on-main: only symbolic-ref ran",
      all(_is(c, "git", "symbolic-ref") for c in recorded), True)


# Impure case 3: detached HEAD (symbolic-ref rc != 0) also short-circuits not-on-main.
def _handler_detached(cmd, **kwargs):
    if _is(cmd, "git", "symbolic-ref"):
        return _FakeCompleted(1, "", "fatal: ref HEAD is not a symbolic ref")
    raise AssertionError("short-circuit violated: ran %r after detached HEAD" % (cmd,))


restore, recorded = _install_fakes(_handler_detached)
try:
    rc, out = _capture_stdout(lambda: _run(["qrspi_sync_trunk.py"]))
    env = json.loads(out)
finally:
    restore()

check("impure detached: rc 1", rc, 1)
check("impure detached: ok false", env["ok"], False)
check("impure detached: error says 'detached HEAD'",
      "detached HEAD" in env["error"], True)
check("impure detached: NO fetch/merge",
      any(_is(c, "git", "fetch") or _is(c, "git", "merge") for c in recorded), False)


# --- summary -----------------------------------------------------------------

print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
