#!/usr/bin/env python3
"""Just-in-time worktree (re-)provisioning, runnable as the FIRST step inside ANY
worktree-touching worker process.

Why this exists
---------------
Each qrspi-batch step runs as its OWN agent = its own sandbox process, and the
`.git/worktrees/<id>` admin metadata does NOT survive that agent/process boundary: the
`.worktrees/<id>` working dir persists (it lives in the working tree), but its admin dir
is pruned/lost, re-orphaning the worktree so the worker's first git/gt command dies with
`fatal: not a git repository`. `qrspi_restack.py` already closes this window with
`provision_worktree()` at the top of its OWN process — but the FINALIZE workers
(submit/design/plan/impl/land/revise) run as their own separate agents and had no
equivalent, which is exactly why a run could restack a ticket cleanly and then fail at
`gt submit` with `not a git repository`. This script gives every such worker the same
self-heal, to be run verbatim before any git/gt op.

Content preservation
---------------------
The resolver's `setup_worktree` self-heals an orphan by `rm -rf` + recreate-from-tip. That
is safe for the submit/land paths (their artifacts are already committed), but the
design/plan/impl finalize workers COMMIT artifacts that EARLIER phase agents persisted —
uncommitted — into the working dir (Fix A: stage to /tmp, move into `.worktrees/<id>`,
then the finalize worker commits). A bare rmtree+recreate at the top of those finalize
workers would destroy that just-persisted, not-yet-committed work. So when the orphaned
working dir is still present, this script SNAPSHOTS the working tree (minus the dead `.git`
pointer), lets `setup_worktree` recreate a clean worktree from the branch tip, then overlays
the snapshot back — restoring every uncommitted modification and untracked file while
committed-and-unchanged files are overwritten with byte-identical content (a harmless
no-op). The recreated `.git` is never touched.

Scope note: this reproduces uncommitted ADDITIONS and MODIFICATIONS (the artifact-persist
pattern). A rare uncommitted DELETION of a tracked file in the orphan is NOT reproduced
(the fresh checkout restores it) — not a QRSPI pattern, and called out for honesty.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, ticket, worktreeDir, disposition, error? }
where disposition is one of: "reused" | "healed" | "recreated" | "none".
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

# ENGINE_ROOT: dir holding this engine's scripts/ (from __file__) — used ONLY for sibling
# imports. REPO_ROOT: the HOST checkout root, resolved via the shared
# qrspi_paths.resolve_repo_root() (git-common-dir first — the MAIN checkout even from a
# worktree). Mirrors qrspi_resolve.py / qrspi_restack.py.
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402
from qrspi_resolve import (  # noqa: E402
    setup_worktree,
    worktree_is_healthy,
)

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)


def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; never typed by the model."""
    return os.path.join(repo_root, ".worktrees", ticket)


def _heal_preserving_content(ticket, worktree, repo_root):
    """Re-register an orphaned-but-present worktree dir WITHOUT losing uncommitted content.

    Snapshot the working tree (minus the dead `.git` pointer the recreate will rewrite),
    let `setup_worktree` rmtree+recreate a clean worktree from the branch tip, then overlay
    the snapshot back. Net effect: a healthy worktree whose working tree is byte-identical
    to the orphan it replaced — tip content plus every uncommitted change. See module
    docstring for the deletion-scope caveat."""
    backup = tempfile.mkdtemp(prefix="qrspi-provision-%s-" % ticket)
    snapshot = os.path.join(backup, "wt")
    try:
        # `.git` here is the worktree's gitlink FILE (orphaned/dead) — excluding it keeps the
        # snapshot from clobbering the fresh, correct `.git` the recreate writes.
        shutil.copytree(worktree, snapshot,
                        ignore=shutil.ignore_patterns(".git"), symlinks=True)
        setup_worktree(ticket, create_design=False, repo_root=repo_root)
        shutil.copytree(snapshot, worktree, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git"), symlinks=True)
    finally:
        shutil.rmtree(backup, ignore_errors=True)
    return worktree


def provision(ticket, repo_root=REPO_ROOT):
    """(Re-)provision the ticket's worktree IN THIS PROCESS, returning (path, disposition).

    - Healthy worktree -> reuse verbatim ("reused"); no content risk.
    - Orphaned worktree (dir present, admin metadata gone) -> content-preserving heal
      ("healed").
    - No dir but a branch exists -> recreate from the branch tip ("recreated").
    - No dir and no branch -> nothing to provision ("none"); the canonical (not-yet-existing)
      path is returned so a caller still gets a deterministic answer.

    Raises RuntimeError (from setup_worktree) when provisioning genuinely fails — the caller
    turns that into one ok:false envelope rather than retrying. create_design is always False:
    provisioning never creates a stray design branch (a branch always exists by finalize)."""
    worktree = worktree_path(repo_root, ticket)
    if os.path.isdir(worktree):
        if worktree_is_healthy(worktree):
            return worktree, "reused"
        return _heal_preserving_content(ticket, worktree, repo_root), "healed"
    # No working dir: delegate to setup_worktree, which recreates from the branch tip (or
    # returns the bare path when no branch exists). Disposition reflects which happened.
    setup_worktree(ticket, create_design=False, repo_root=repo_root)
    return worktree, ("recreated" if os.path.isdir(worktree) else "none")


def main():
    parser = argparse.ArgumentParser(
        description="Just-in-time QRSPI worktree (re-)provisioning (self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    parser.add_argument("--repo-root", default=None,
                        help="Explicit host checkout root override; else auto-detected.")
    args = parser.parse_args()

    try:
        repo_root = qrspi_paths.resolve_repo_root(args.repo_root, cwd=os.getcwd())
        worktree, disposition = provision(args.ticket, repo_root=repo_root)
        env = {
            "ok": True,
            "repoRoot": repo_root,
            "ticket": args.ticket,
            "worktreeDir": worktree,
            "disposition": disposition,
        }
    except Exception as exc:  # noqa: BLE001 — any failure is ONE ok:false envelope.
        env = {
            "ok": False,
            "ticket": args.ticket,
            "error": "worktree provisioning failed: %s" % exc,
        }
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if env["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
