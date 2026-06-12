#!/usr/bin/env python3
"""Stage a revise worker's edits and amend them into the frontier phase commit IN PLACE,
then VERIFY the amend actually captured the changes.

Why this exists
---------------
The QRSPI `revise` action (qrspi-batch.js `doRevise`) addresses a formal
CHANGES_REQUESTED on a frontier phase PR by editing the phase's own artifacts/code,
amending the phase commit (keeping its subject), and re-requesting review. The amend
step used to be hand-rolled worker shell: "Amend the phase commit IN PLACE with
`gt modify --no-interactive`". That command stages NOTHING — `gt modify` only amends
already-staged content — so a worker that edited `design.md` and then ran
`gt modify --no-interactive` amended a commit with an empty index: the edits stayed in
the working tree, the unchanged commit got pushed, and `gt submit` succeeding let the
worker report `ok:true`. The revisions never reached the PR (observed on RUS-53 #161).

Every other amend in this harness is a self-locating one-shot script with a built-in
success gate (qrspi_persist.py is the per-phase persistence gate; qrspi_pr_body.py is the
slice-body amend) precisely because the weak worker model botches multi-step git. The
revise amend was the lone exception. This script closes that gap with the SAME design:

- Self-locating: repo root is derived from the git-common-dir (falling back to __file__),
  never typed by the worker, which mangles the "qrspi" path token across multi-step shell.
- Stages EVERY edit in the worktree EXCEPT generated caches (__pycache__/, *.pyc) — code
  and artifacts are the deliverable, matching the slice-commit worker's staging rule.
- Amends with `gt modify --no-interactive -m <existing message verbatim>`, preserving the
  commit's exact subject and trailer block (so the PR title/body are unchanged).
- VERIFIES the amend: it FAILS (ok:false) if the working tree is left dirty after the
  amend (staging missed something) OR the commit OID did not change (nothing was captured
  — you cannot address review feedback with no change). This turns the silent no-op into a
  hard stop the workflow catches, instead of a false success.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, ticket, branch, worktreeDir, oldOid, newOid, dirty[], error? }
"""

import argparse
import json
import os
import re
import subprocess
import sys

# ENGINE_ROOT: the dir holding this engine's scripts/ (from __file__) — used ONLY for
# sibling imports. REPO_ROOT: the HOST checkout root all host paths key off, resolved via
# the shared qrspi_paths.resolve_repo_root() (git-common-dir first — the MAIN checkout even
# from a worktree, where __file__ would point at the worktree's own copy; __file__ parent
# last resort). validate=False keeps gh off the import path. This collapses the script's
# former private git-common-dir copy onto the shared resolver — behavior-preserving
# (ref: design.md Decision 2, §Delta).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

# Generated caches are never the deliverable and must not be staged into a phase commit
# (matches the slice-commit worker's "never stage __pycache__/ or *.pyc" rule). They are
# also filtered out of the post-amend dirtiness check so leftover caches do not read as a
# failed amend.
_CACHE_RE = re.compile(r"(^|/)__pycache__/|\.pyc$")

# git pathspec excludes so `git add -A` skips caches in a single deterministic command.
_ADD_CMD = [
    "git", "add", "-A", "--", ".",
    ":(exclude)**/__pycache__/**",
    ":(exclude)**/*.pyc",
]


# --- pure helpers (unit-tested) --------------------------------------------

def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; computed here, never typed by the
    model. Matches qrspi_pr_body.worktree_path / qrspi_persist."""
    return os.path.join(repo_root, ".worktrees", ticket)


def is_cache_path(path):
    """True if `path` is a generated cache (under __pycache__/ or a .pyc). Pure."""
    return bool(_CACHE_RE.search(path or ""))


def dirty_paths(porcelain_text):
    """Parse `git status --porcelain` output into the list of changed paths, EXCLUDING
    generated caches. Pure, so the dirtiness verdict is unit-testable without git.

    Porcelain v1 format is "XY <path>"; the path starts at column 3. A rename shows
    "orig -> new" — we keep the post-arrow path (the one that would still be unstaged).
    """
    paths = []
    for line in (porcelain_text or "").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        # Porcelain may quote paths with odd characters; strip surrounding quotes.
        if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
            path = path[1:-1]
        if path and not is_cache_path(path):
            paths.append(path)
    return paths


def classify_modify(rc, stdout, stderr):
    """Map a `gt modify` (rc, stdout, stderr) to (ok, error). Pure, so the success/
    failure decision is unit-testable without running gt. Mirrors qrspi_pr_body."""
    if rc == 0:
        return True, None
    msg = (stderr or "").strip() or (stdout or "").strip() or "gt modify failed (rc=%d)" % rc
    return False, msg


def verify_amend(staged, dirty):
    """Decide whether the amend genuinely captured the worker's edits. Pure — this is the
    gate that turns the old silent no-op into a hard failure.

    `staged` is whether `git diff --cached` saw any staged content right before the amend
    (i.e. the worker actually changed tracked/added files). `dirty` is the list of
    non-cache paths still changed AFTER the amend.

    NOTE: we deliberately do NOT compare commit OIDs — `gt modify`/`git commit --amend`
    bumps the committer timestamp, so the OID changes on every amend even when the tree is
    byte-identical. "Were there staged changes" is the timestamp-independent truth.

    Returns (ok, error):
      - not staged          -> the index was empty at amend time, so the commit captured
        nothing. A revise with no committed change cannot have addressed the feedback
        (this is the exact RUS-53 bug: edited file left unstaged). Fail.
      - dirty after amend   -> staging missed files that are still in the working tree;
        the edits did not all make it into the commit. Fail.
      - staged AND clean    -> success.
    """
    if not staged:
        return False, (
            "no staged changes at amend time — the commit captured nothing, so no review "
            "feedback was actually addressed (the original revise bug: edits left unstaged, "
            "or only ignored/cache files changed)."
        )
    if dirty:
        return False, (
            "amend did not capture all edits — working tree still dirty after "
            "`gt modify`: %s. Some changes were not staged into the commit." % ", ".join(dirty)
        )
    return True, None


def build_envelope(ticket, branch, worktree_dir, ok=True, old_oid=None, new_oid=None,
                   dirty=None, error=None, repo_root=None):
    """Assemble the JSON envelope the qrspi-batch revise worker consumes. Pure."""
    env = {
        "ok": ok,
        "repoRoot": repo_root if repo_root is not None else REPO_ROOT,
        "ticket": ticket,
        "branch": branch,
        "worktreeDir": worktree_dir,
        "oldOid": old_oid,
        "newOid": new_oid,
        "dirty": list(dirty or []),
    }
    if error is not None:
        env["error"] = error
    return env


# --- subprocess-backed mechanics (not unit-tested; manual e2e) -------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def head_oid(worktree):
    """Current HEAD commit OID in the worktree, or None on error."""
    rc, out, err = _run(["git", "rev-parse", "HEAD"], cwd=worktree)
    if rc != 0:
        return None, (err or out).strip()
    return out.strip(), None


def read_head_message(worktree):
    """Full commit message (%B) of the currently checked-out HEAD."""
    rc, out, err = _run(["git", "log", "-1", "--format=%B"], cwd=worktree)
    if rc != 0:
        return None, (err or out).strip()
    return out, None


def stage_and_amend(worktree, branch):
    """Check out `branch`, stage every edit (excluding caches), amend the commit in place
    keeping its exact message, and verify the amend captured the changes.

    Returns (ok, old_oid, new_oid, dirty, error).
    """
    rc, out, err = _run(["gt", "checkout", branch, "--no-interactive"], cwd=worktree)
    if rc != 0:
        return False, None, None, [], ("gt checkout %s failed: %s" % (branch, (err or out).strip()))

    old_oid, oid_err = head_oid(worktree)
    if old_oid is None:
        return False, None, None, [], ("could not read HEAD for %s: %s" % (branch, oid_err))

    existing, msg_err = read_head_message(worktree)
    if existing is None:
        return False, old_oid, None, [], ("could not read commit message for %s: %s" % (branch, msg_err))

    rc, out, err = _run(_ADD_CMD, cwd=worktree)
    if rc != 0:
        return False, old_oid, None, [], ("git add failed: %s" % (err or out).strip())

    # Did staging actually capture anything? `git diff --cached --quiet` exits 0 when the
    # index matches HEAD (nothing staged) and 1 when there are staged changes. This is the
    # timestamp-independent test for "the worker changed real content" — checked BEFORE
    # the amend so an empty revise is a hard stop, not a no-op commit.
    rc_staged, _, _ = _run(["git", "diff", "--cached", "--quiet"], cwd=worktree)
    staged = rc_staged != 0
    if not staged:
        ok, error = verify_amend(staged, [])
        return ok, old_oid, old_oid, [], error

    # Preserve the existing message verbatim (subject + trailer block). With the edits now
    # staged, `gt modify` folds them into the commit and auto-restacks any descendants.
    rc, out, err = _run(["gt", "modify", "--no-interactive", "-m", existing], cwd=worktree)
    ok, error = classify_modify(rc, out, err)
    if not ok:
        return False, old_oid, None, [], error

    new_oid, oid_err = head_oid(worktree)
    if new_oid is None:
        return False, old_oid, None, [], ("could not read HEAD after amend: %s" % oid_err)

    # --untracked-files=all expands untracked directories to individual files, so the
    # per-file cache filter in dirty_paths can drop a __pycache__/*.pyc instead of seeing
    # a collapsed "?? dir/" entry. (In this repo caches are gitignored and never appear,
    # but this keeps the gate correct regardless of ignore state.)
    rc, out, err = _run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=worktree)
    if rc != 0:
        return False, old_oid, new_oid, [], ("git status failed: %s" % (err or out).strip())
    dirty = dirty_paths(out)

    ok, error = verify_amend(staged, dirty)
    return ok, old_oid, new_oid, dirty, error


def main():
    parser = argparse.ArgumentParser(
        description="Stage + amend a revise worker's edits into the phase commit, with a "
                    "verification gate (self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-53")
    parser.add_argument("--branch", required=True,
                        help="Phase branch to amend, e.g. RUS-53/design, RUS-53/plan, "
                             "or RUS-53/slice-2")
    args = parser.parse_args()

    repo_root = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
    worktree = worktree_path(repo_root, args.ticket)

    if not os.path.isdir(worktree):
        env = build_envelope(args.ticket, args.branch, worktree, ok=False,
                             error="worktree not found: %s" % worktree, repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    ok, old_oid, new_oid, dirty, error = stage_and_amend(worktree, args.branch)
    env = build_envelope(args.ticket, args.branch, worktree, ok=ok, old_oid=old_oid,
                         new_oid=new_oid, dirty=dirty, error=error, repo_root=repo_root)
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
