#!/usr/bin/env python3
"""Unit tests for qrspi_provision — the just-in-time worktree (re-)provisioning step
every finalize worker runs first. Stdlib-only, assert-based, real git repos in tmp.
Run: python3 scripts/qrspi_provision_test.py

The point of this script (vs. resolve's setup_worktree, which it delegates to) is the
CONTENT-PRESERVING heal: an orphaned worktree must come back healthy WITHOUT losing the
uncommitted artifacts a prior phase agent persisted into it. That guarantee is what these
tests pin down — especially `orphan heal preserves an uncommitted artifact`, which is the
regression anchor for the design/plan/impl finalize data-loss the bare rmtree+recreate
self-heal would cause.
"""

import os
import subprocess
import sys
import tempfile

import qrspi_provision
from qrspi_provision import provision, worktree_path
from qrspi_resolve import worktree_is_healthy

failures = 0
total = 0


def check(name, got, want):
    global failures, total
    total += 1
    if got != want:
        print("FAIL: %s\n      expected %r\n      got      %r" % (name, want, got))
        failures += 1
    else:
        print("ok: %s" % name)


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


def _seed_repo(root):
    """A minimal repo on `main` with one commit and a `RUS-1/design` branch."""
    _git(["init", "-b", "main"], root)
    _git(["config", "user.email", "t@t.t"], root)
    _git(["config", "user.name", "t"], root)
    with open(os.path.join(root, "f.txt"), "w") as fh:
        fh.write("seed\n")
    _git(["add", "."], root)
    _git(["commit", "-m", "seed"], root)
    _git(["branch", "RUS-1/design"], root)


def _read(path):
    with open(path) as fh:
        return fh.read()


# --- worktree_path is pure --------------------------------------------------
check("worktree_path is the canonical .worktrees/<id> join",
      worktree_path("/repo", "RUS-9"), os.path.join("/repo", ".worktrees", "RUS-9"))


# --- provision dispositions over a real repo --------------------------------
with tempfile.TemporaryDirectory() as root:
    _seed_repo(root)
    wt = os.path.join(root, ".worktrees", "RUS-1")

    # 1. First call recreates the worktree from the branch tip.
    path, disp = provision("RUS-1", repo_root=root)
    check("provision returns the canonical worktree path", path, wt)
    check("first provision recreates from tip", disp, "recreated")
    check("recreated worktree is healthy", worktree_is_healthy(wt), True)
    head = subprocess.run(["git", "-C", wt, "rev-parse", "--abbrev-ref", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    check("recreated worktree is on the branch tip", head, "RUS-1/design")

    # 2. A healthy worktree is reused verbatim (no content churn).
    path2, disp2 = provision("RUS-1", repo_root=root)
    check("healthy worktree is reused", (path2, disp2), (wt, "reused"))

    # 3. THE regression anchor: orphan the worktree (admin dir gone) with an UNCOMMITTED
    #    artifact present, then provision — the artifact must survive the heal.
    art_dir = os.path.join(wt, ".qrspi", "RUS-1")
    os.makedirs(art_dir, exist_ok=True)
    art = os.path.join(art_dir, "design.md")
    with open(art, "w") as fh:
        fh.write("UNCOMMITTED DESIGN ARTIFACT\n")
    # Also dirty a tracked file to prove modifications (not just untracked) are preserved.
    with open(os.path.join(wt, "f.txt"), "w") as fh:
        fh.write("seed\nlocal uncommitted edit\n")

    import shutil as _sh
    _sh.rmtree(os.path.join(root, ".git", "worktrees", "RUS-1"))
    check("orphaned worktree dir still present on disk", os.path.isdir(wt), True)
    check("orphaned worktree detected unhealthy", worktree_is_healthy(wt), False)

    path3, disp3 = provision("RUS-1", repo_root=root)
    check("orphan provision heals in place", (path3, disp3), (wt, "healed"))
    check("healed worktree is healthy again", worktree_is_healthy(wt), True)
    check("orphan heal PRESERVES the uncommitted untracked artifact",
          os.path.isfile(art) and _read(art), "UNCOMMITTED DESIGN ARTIFACT\n")
    check("orphan heal PRESERVES the uncommitted tracked modification",
          _read(os.path.join(wt, "f.txt")), "seed\nlocal uncommitted edit\n")
    # The healed worktree is a live git tree: the preserved changes show as status
    # (-uall lists untracked files individually rather than collapsing the dir).
    porc = subprocess.run(["git", "-C", wt, "status", "--porcelain", "-uall"],
                          capture_output=True, text=True).stdout
    check("healed worktree sees the preserved artifact as untracked",
          ".qrspi/RUS-1/design.md" in porc, True)
    check("healed worktree sees the preserved tracked edit as modified",
          any(line.endswith("f.txt") and "M" in line for line in porc.splitlines()), True)


# --- no branch, no dir -> nothing to provision ------------------------------
with tempfile.TemporaryDirectory() as root2:
    _git(["init", "-b", "main"], root2)
    _git(["config", "user.email", "t@t.t"], root2)
    _git(["config", "user.name", "t"], root2)
    with open(os.path.join(root2, "f.txt"), "w") as fh:
        fh.write("seed\n")
    _git(["add", "."], root2)
    _git(["commit", "-m", "seed"], root2)
    # No RUS-2/* branch and no worktree dir.
    path, disp = provision("RUS-2", repo_root=root2)
    check("no branch + no dir -> disposition none", disp, "none")
    check("no branch + no dir -> no worktree created",
          os.path.isdir(os.path.join(root2, ".worktrees", "RUS-2")), False)


def run():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
