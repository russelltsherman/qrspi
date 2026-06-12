#!/usr/bin/env python3
"""Unit tests for qrspi_paths — the shared engine-root / host-root resolver.

Stdlib-only, assert-based (same convention as qrspi_pr_body_test.py et al.). The git and
gh subprocess calls are stubbed by swapping ``qrspi_paths.subprocess.run`` with a fake, so
the precedence and validation logic is exercised without a real repo or network.

Cases (ref: structure.md Slice 1 Verification; design.md Risk Register row 2, Q11):
  (a) explicit repo_root flag wins over git-common-dir
  (b) git-common-dir is used when no flag — DIVERGENCE: a synthetic checkout distinct
      from the (real) engine dir resolves to the checkout
  (c) __file__ fallback is returned when git is unavailable
  (d) a wrong/stale root raises HostRootError (gh repo view stubbed to mismatch)
  (e) engine_root() returns the module's own dir, independent of cwd / host root

Run: python3 scripts/qrspi_paths_test.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import qrspi_paths  # noqa: E402
from qrspi_paths import (  # noqa: E402
    engine_root,
    resolve_repo_root,
    HostRootError,
)

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


def check_raises(label, exc_type, fn):
    global failures, total
    total += 1
    try:
        fn()
    except exc_type:
        print("ok: %s" % label)
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print("FAIL: %s\n   raised %s, want %s" % (label, type(exc).__name__, exc_type.__name__))
    else:
        failures += 1
        print("FAIL: %s\n   did not raise %s" % (label, exc_type.__name__))


class _FakeCompleted:
    """Stand-in for subprocess.CompletedProcess with just the fields the resolver reads."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _install_fake_run(handler):
    """Swap qrspi_paths.subprocess.run with `handler(cmd, **kwargs) -> _FakeCompleted`.

    Returns a restore() callable. `handler` may return None to signal "git/gh not found"
    (we translate that into the OSError that the real subprocess raises for a missing
    binary, so the module's OSError handling is exercised)."""
    real = qrspi_paths.subprocess.run

    def fake_run(cmd, **kwargs):
        result = handler(cmd, **kwargs)
        if result is None:
            raise OSError("fake: command not found: %r" % (cmd[0],))
        return result

    qrspi_paths.subprocess.run = fake_run

    def restore():
        qrspi_paths.subprocess.run = real

    return restore


def _is_git_common_dir(cmd):
    return cmd[:2] == ["git", "rev-parse"] and "--git-common-dir" in cmd


def _is_gh_repo_view(cmd):
    return cmd[:3] == ["gh", "repo", "view"]


# --- (e) engine_root independent of cwd / host root -------------------------
# engine_root() is derived purely from __file__, so it must equal this test file's own
# directory (scripts/) regardless of the process cwd. Prove it by changing cwd.
_expected_engine = os.path.dirname(os.path.abspath(qrspi_paths.__file__))
check("(e) engine_root() is the module's own dir", engine_root(), _expected_engine)

_orig_cwd = os.getcwd()
try:
    os.chdir("/tmp")
    check("(e) engine_root() unchanged after cwd change", engine_root(), _expected_engine)
finally:
    os.chdir(_orig_cwd)


# --- (a) explicit repo_root flag wins over git-common-dir -------------------
# Both a flag AND a (different) git-common-dir are available; the flag must win. gh
# validation succeeds for the flag's path.
_FLAG_ROOT = "/synthetic/flag-checkout"
_GIT_ROOT = "/synthetic/git-checkout"


def _handler_flag_wins(cmd, **kwargs):
    if _is_git_common_dir(cmd):
        return _FakeCompleted(0, os.path.join(_GIT_ROOT, ".git") + "\n")
    if _is_gh_repo_view(cmd):
        # Validation passes regardless of which root it is asked to validate.
        return _FakeCompleted(0, "octo/host-repo\n")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_flag_wins)
try:
    check("(a) explicit repo_root flag wins over git-common-dir",
          resolve_repo_root(repo_root=_FLAG_ROOT, cwd="/anywhere"),
          os.path.abspath(_FLAG_ROOT))
finally:
    _restore()


# --- (b) git-common-dir used when no flag; DIVERGENCE from engine dir -------
# No flag → the resolver uses git-common-dir. The synthetic checkout it resolves is
# DISTINCT from the real engine dir (this test file's scripts/ dir), proving host root
# and engine root diverge correctly — the Q11 gap.
def _handler_git_used(cmd, **kwargs):
    if _is_git_common_dir(cmd):
        return _FakeCompleted(0, os.path.join(_GIT_ROOT, ".git") + "\n")
    if _is_gh_repo_view(cmd):
        return _FakeCompleted(0, "octo/host-repo\n")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_git_used)
try:
    _resolved = resolve_repo_root(cwd="/some/worktree")
    check("(b) git-common-dir used when no flag", _resolved, _GIT_ROOT)
    # The divergence assertion: the resolved host root is NOT the engine dir.
    check("(b) host root diverges from engine root",
          _resolved != engine_root(), True)
finally:
    _restore()


# --- (c) __file__ fallback when git unavailable -----------------------------
# git returns nothing (or is missing) and no flag is given → fall back to the engine's
# parent dir, unvalidated. We make git "not found" (handler returns None → OSError) and
# assert no gh validation is attempted on the fallback.
def _handler_no_git(cmd, **kwargs):
    if _is_git_common_dir(cmd):
        return None  # simulate missing git binary
    if _is_gh_repo_view(cmd):
        raise AssertionError("fallback root must NOT be validated")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_no_git)
try:
    check("(c) __file__ fallback when git unavailable",
          resolve_repo_root(cwd="/outside/any/repo"),
          os.path.dirname(engine_root()))
finally:
    _restore()


# Also: git present but returns rc!=0 / empty (cwd outside a repo) → same fallback.
def _handler_git_rc1(cmd, **kwargs):
    if _is_git_common_dir(cmd):
        return _FakeCompleted(128, "", "not a git repository")
    if _is_gh_repo_view(cmd):
        raise AssertionError("fallback root must NOT be validated")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_git_rc1)
try:
    check("(c) __file__ fallback when git returns non-zero",
          resolve_repo_root(cwd="/outside/any/repo"),
          os.path.dirname(engine_root()))
finally:
    _restore()


# --- (d) wrong/stale root raises HostRootError ------------------------------
# A flag is supplied but gh repo view fails for it (stale/wrong root). Must raise rather
# than return silently.
def _handler_gh_mismatch(cmd, **kwargs):
    if _is_git_common_dir(cmd):
        return _FakeCompleted(0, os.path.join(_GIT_ROOT, ".git") + "\n")
    if _is_gh_repo_view(cmd):
        return _FakeCompleted(1, "", "not a github repository")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_gh_mismatch)
try:
    check_raises("(d) stale --repo-root raises HostRootError",
                 HostRootError,
                 lambda: resolve_repo_root(repo_root=_FLAG_ROOT, cwd="/x"))
    check_raises("(d) wrong git-common-dir root raises HostRootError",
                 HostRootError,
                 lambda: resolve_repo_root(cwd="/x"))
finally:
    _restore()


# Also: gh succeeds but returns an EMPTY nameWithOwner (no GitHub remote) → raise.
def _handler_gh_empty(cmd, **kwargs):
    if _is_gh_repo_view(cmd):
        return _FakeCompleted(0, "\n")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_gh_empty)
try:
    check_raises("(d) empty nameWithOwner raises HostRootError",
                 HostRootError,
                 lambda: resolve_repo_root(repo_root=_FLAG_ROOT))
finally:
    _restore()


# --- validate=False skips the gate ------------------------------------------
# When validation is disabled, a flag is returned without invoking gh at all.
def _handler_no_gh_allowed(cmd, **kwargs):
    if _is_gh_repo_view(cmd):
        raise AssertionError("gh must NOT be called when validate=False")
    raise AssertionError("unexpected command: %r" % (cmd,))


_restore = _install_fake_run(_handler_no_gh_allowed)
try:
    check("validate=False returns flag without gh validation",
          resolve_repo_root(repo_root=_FLAG_ROOT, validate=False),
          os.path.abspath(_FLAG_ROOT))
finally:
    _restore()


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
