#!/usr/bin/env python3
"""FF-only trunk-sync helper: fetch origin and fast-forward local ``main`` to ``origin/main``.

Why this exists
---------------
The qrspi-batch orchestrator cuts every ticket's worktree off the MAIN checkout's local
``main``. When a prior ticket lands while a dependent ticket is still in flight, the
local ``main`` in the main checkout can be one (or more) commits behind ``origin/main``,
so the next worktree is cut from a stale trunk and the dependent ticket is built on the
wrong base. This helper reconciles local ``main`` to ``origin/main`` with a strict
fast-forward, refusing (fail-loud) to do anything that could destroy work or land on the
wrong branch:

- a non-``main`` HEAD in the main checkout (refuse before any fetch/merge),
- a dirty working tree (refuse before any fetch/merge),
- a failed ``git fetch`` (surface verbatim),
- a divergent local ``main`` that is not fast-forwardable (surface verbatim).

The decision space is a pure classifier (``classify_sync``) so it is exhaustively unit
testable with no I/O; the impure shell (``_run``/``main``) reads git state, feeds the
classifier, performs the FF merge only on the ``"updated"`` token, and prints a single
``SyncEnvelope`` JSON object on stdout.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, updated, from, to, error? }
  - ``from``/``to`` are short SHAs of local ``main`` before/after the (potential) advance.
  - ``updated`` is true only on an actual FF advance, false on already-current.
  - on any fail-loud path: ``ok:false`` + a verbatim ``error``.
Exit code: 0 when ``ok`` else 1.
"""

import json
import subprocess
import sys
import os

# ENGINE_ROOT: the dir holding this engine's scripts/ (derived from __file__) — used ONLY
# for sibling imports, never a host path. REPO_ROOT: the HOST checkout root we operate on,
# resolved through the shared qrspi_paths.resolve_repo_root() (git-common-dir first, so it
# is the MAIN checkout even when invoked from a worktree).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402


def classify_sync(head_branch, fetch_rc, dirty_porcelain, local_sha, origin_sha, is_ancestor):
    """Pure decision: map observed git state to exactly one sync token. No I/O.

    Precedence (pinned by structure.md Contracts → classify_sync, OQ2-RESOLVED):
      1. ``head_branch != "main"`` (incl. ``None``/detached) → ``"not-on-main"`` — the
         HEAD-on-``main`` guard, checked FIRST so the working-tree-touching FF merge is
         never attempted off ``main`` (Risk Register row 1, OQ1).
      2. ``dirty_porcelain`` non-empty after strip → ``"dirty"`` — checked before any
         fetch/merge so uncommitted work is never destroyed.
      3. ``fetch_rc != 0`` → ``"fetch-failed"``.
      4. ``local_sha == origin_sha`` → ``"already-current"``.
      5. ``not is_ancestor`` (local ``main`` not an ancestor of ``origin/main``) → ``"divergent"``.
      6. otherwise → ``"updated"`` (clean FF advance available).
    """
    if head_branch != "main":
        return "not-on-main"
    if dirty_porcelain.strip():
        return "dirty"
    if fetch_rc != 0:
        return "fetch-failed"
    if local_sha == origin_sha:
        return "already-current"
    if not is_ancestor:
        return "divergent"
    return "updated"


def build_envelope(token, repo_root, head_branch, dirty_porcelain, fetch_detail,
                   local_sha, origin_sha):
    """Pure token → SyncEnvelope mapping (structure.md Contracts → token→field mapping).

    ``repo_root`` is threaded into every envelope. ``dirty_porcelain`` / ``fetch_detail``
    carry the verbatim context spliced into the ``dirty`` / ``fetch-failed`` error
    messages respectively.
    """
    if token == "updated":
        return {
            "ok": True, "repoRoot": repo_root, "updated": True,
            "from": local_sha, "to": origin_sha,
        }
    if token == "already-current":
        return {
            "ok": True, "repoRoot": repo_root, "updated": False,
            "from": local_sha, "to": local_sha,
        }
    if token == "not-on-main":
        where = head_branch if head_branch else "detached HEAD"
        return {
            "ok": False, "repoRoot": repo_root, "updated": False,
            "from": None, "to": None,
            "error": "main checkout HEAD is not on 'main' (on %s); refusing FF-only sync" % where,
        }
    if token == "dirty":
        return {
            "ok": False, "repoRoot": repo_root, "updated": False,
            "from": local_sha, "to": None,
            "error": "main working tree dirty + porcelain lines:\n%s" % dirty_porcelain,
        }
    if token == "fetch-failed":
        return {
            "ok": False, "repoRoot": repo_root, "updated": False,
            "from": local_sha, "to": None,
            "error": "git fetch origin failed, %s" % fetch_detail,
        }
    if token == "divergent":
        return {
            "ok": False, "repoRoot": repo_root, "updated": False,
            "from": local_sha, "to": origin_sha,
            "error": "local main diverged from origin/main; not fast-forwardable",
        }
    # Unreachable for the six pinned tokens; fail loud if a new token slips through.
    return {
        "ok": False, "repoRoot": repo_root, "updated": False,
        "from": None, "to": None,
        "error": "unknown sync token %r" % token,
    }


def _run(argv):
    """Impure shell: read git state, classify, FF-advance on ``updated``, print envelope.

    The HEAD-on-``main`` read happens FIRST so a non-``main`` HEAD short-circuits to
    ``ok:false`` BEFORE any ``git fetch`` or ``git merge`` is attempted (Decision 1
    Option A, Risk Register row 1, OQ1). Returns 0 when the envelope is ``ok`` else 1.
    """
    repo_root = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

    # HEAD-on-main guard FIRST (no fetch/merge if not on main). symbolic-ref prints the
    # branch short name on a normal HEAD and exits non-zero (with -q) on a detached HEAD;
    # empty output / non-zero rc ⇒ detached ⇒ head_branch=None ⇒ not-on-main.
    head = subprocess.run(
        ["git", "symbolic-ref", "--short", "-q", "HEAD"],
        cwd=repo_root, capture_output=True, text=True)
    head_branch = (head.stdout or "").strip()
    if head.returncode != 0 or not head_branch:
        head_branch = None

    if head_branch != "main":
        token = classify_sync(head_branch, 0, "", None, None, True)
        envelope = build_envelope(token, repo_root, head_branch, "", "", None, None)
        print(json.dumps(envelope))
        return 0 if envelope["ok"] else 1

    # Dirty-tree guard before any fetch/merge.
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root, capture_output=True, text=True)
    dirty_porcelain = status.stdout or ""

    # Fetch origin (capture rc + stderr for the verbatim fetch-failed message).
    fetch = subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_root, capture_output=True, text=True)
    fetch_rc = fetch.returncode
    fetch_detail = "rc=%d stderr: %s" % (fetch_rc, (fetch.stderr or "").strip())

    local_sha = _rev_parse(repo_root, "main")
    origin_sha = _rev_parse(repo_root, "origin/main")

    # is_ancestor: local main is an ancestor of origin/main ⇒ fast-forwardable.
    anc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "main", "origin/main"],
        cwd=repo_root, capture_output=True, text=True)
    is_ancestor = anc.returncode == 0

    token = classify_sync(head_branch, fetch_rc, dirty_porcelain, local_sha, origin_sha, is_ancestor)

    if token == "updated":
        merge = subprocess.run(
            ["git", "merge", "--ff-only", "origin/main"],
            cwd=repo_root, capture_output=True, text=True)
        if merge.returncode != 0:
            # The classifier said FF-able but the merge failed: surface verbatim, fail loud.
            envelope = {
                "ok": False, "repoRoot": repo_root, "updated": False,
                "from": local_sha, "to": origin_sha,
                "error": "git merge --ff-only origin/main failed, rc=%d stderr: %s"
                         % (merge.returncode, (merge.stderr or "").strip()),
            }
            print(json.dumps(envelope))
            return 1

    envelope = build_envelope(token, repo_root, head_branch, dirty_porcelain,
                              fetch_detail, local_sha, origin_sha)
    print(json.dumps(envelope))
    return 0 if envelope["ok"] else 1


def _rev_parse(repo_root, ref):
    """Short SHA of ``ref`` in ``repo_root``, or ``None`` when git cannot resolve it."""
    res = subprocess.run(
        ["git", "rev-parse", "--short", ref],
        cwd=repo_root, capture_output=True, text=True)
    out = (res.stdout or "").strip()
    if res.returncode != 0 or not out:
        return None
    return out


def main():
    sys.exit(_run(sys.argv))


if __name__ == "__main__":
    main()
