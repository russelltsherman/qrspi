#!/usr/bin/env python3
"""Clear a stale closed/merged PR association so a QRSPI branch can be (re)submitted
under the SAME name as a brand-new PR -- deterministically and idempotently.

Why this exists
---------------
Graphite pins each branch to the first PR it opened, in the SHARED
`.git/.graphite_pr_info` cache (keyed by headRefName -> prNumber + state). After a
ticket's PR is merged, or a reset closes it, that association lingers locally. When
the same branch name is reused (a reset reopens `<id>/design`, or a previously
landed ticket is rerun), `gt submit --no-interactive` sees the dead PR and ABORTS
rather than guess:

    WARNING: PR for the following branch has already been merged or closed:
    > RUS-30/design - PR #79 (merged)
    ERROR: Aborting non-interactive submit.

`--force` does not help (it governs the force-push, not the association), and the
interactive "publish a new PR?" prompt is unreachable: gt collapses to
non-interactive whenever stdin is not a TTY (every agent), silently dropping any
piped selection. The previously-prescribed `gt rename <b>-stale && gt rename <b>`
roundtrip reaches the same end-state, but its FIXED temp name COLLIDES across cycles:
if a recovery is interrupted between its two renames, `<b>-stale` lingers and the next
cycle's `gt rename <b>-stale` dies on `branch already exists`.

This helper produces the roundtrip's net effect -- dropping the stale headRefName
entry from the cache -- but DIRECTLY and IDEMPOTENTLY: no temp branch, no collision,
same branch name, zero mutation of the stack tree. It removes ONLY entries whose
headRefName belongs to the ticket (`<id>/*`) AND whose state is MERGED or CLOSED; OPEN
associations and other tickets' entries are left untouched. Running it twice is a
no-op. If the cache file is absent or unparseable it degrades safely to a no-op -- the
later `gt submit` then aborts visibly exactly as it does today, never worse.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, prInfoPath, ticket, removed:[{headRefName,prNumber,state}], warning? }
"""

import argparse
import json
import os
import subprocess
import sys

# The script lives at <repo-root>/scripts/qrspi_clear_stale_pr.py, so the repo root is
# two levels up. Deriving it from __file__ (not cwd, not an argument) is the whole point:
# it removes the path a weak worker model keeps corrupting.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)

# Graphite marks an association dead with one of these PR states. We only ever drop a
# ticket's entry when it carries one of them -- never an OPEN association.
STALE_STATES = ("MERGED", "CLOSED")


# --- pure helpers (unit-tested) --------------------------------------------

def belongs_to_ticket(head_ref, ticket):
    """True iff `head_ref` is a branch under `<ticket>/` (e.g. RUS-3/design for RUS-3).
    Pure. The trailing slash is load-bearing: it stops ticket RUS-3 from matching
    RUS-30/design (prefix-without-slash would)."""
    return isinstance(head_ref, str) and head_ref.startswith(ticket + "/")


def prune_entries(data, ticket, stale_states=STALE_STATES):
    """Return (new_data, removed). Pure -- no I/O -- so the prune decision is unit-tested
    without touching gt or the filesystem.

    Removes every prInfos entry whose headRefName is under `<ticket>/` AND whose state is
    in `stale_states`. Everything else (OPEN entries, other tickets, malformed entries) is
    preserved. When nothing matches, returns the original `data` unchanged and removed=[]
    (so callers can skip the write -- the source of idempotency)."""
    if not isinstance(data, dict):
        return data, []
    infos = data.get("prInfos")
    if not isinstance(infos, list):
        return data, []
    removed, kept = [], []
    for p in infos:
        head_ref = p.get("headRefName") if isinstance(p, dict) else None
        state = p.get("state") if isinstance(p, dict) else None
        if belongs_to_ticket(head_ref, ticket) and state in stale_states:
            removed.append({"headRefName": head_ref, "prNumber": p.get("prNumber"),
                            "state": state})
        else:
            kept.append(p)
    if not removed:
        return data, []
    new_data = dict(data)
    new_data["prInfos"] = kept
    return new_data, removed


def prune_file(path, ticket):
    """Read the cache at `path`, prune the ticket's stale entries, and atomically write it
    back only when something changed. Returns (removed, warning).

    Degrades safely, never raising on an absent/garbled cache: a missing file is a clean
    no-op ([], None); an unreadable/unparseable file is left untouched and reported as a
    non-fatal `warning` so the caller does NOT hard-stop -- the later `gt submit` will
    abort visibly if a stale entry truly remains. Touches only the filesystem, so it is
    unit-testable against temp files."""
    if not os.path.exists(path):
        return [], None
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (ValueError, OSError) as exc:
        return [], "%s could not be read (%s); left untouched" % (path, exc)
    new_data, removed = prune_entries(data, ticket)
    if removed:
        tmp = path + ".qrspi-tmp"
        with open(tmp, "w") as fh:
            json.dump(new_data, fh, indent=2)
        os.replace(tmp, path)  # atomic: never leave a half-written cache
    return removed, None


# --- subprocess-backed mechanics (not unit-tested; manual e2e) -------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def pr_info_path(repo_root):
    """Absolute path to `.graphite_pr_info`. It lives in the SHARED git COMMON dir, not
    `<worktree>/.git` -- every worktree shares one common dir -- so we resolve it via
    `git rev-parse --git-common-dir`. That makes this correct whether the script runs as
    the main checkout's copy or a per-worktree copy. Falls back to `<repo_root>/.git` if
    git is unavailable."""
    rc, out, _ = _run(["git", "rev-parse", "--git-common-dir"], cwd=repo_root)
    common = out.strip() if rc == 0 and out.strip() else os.path.join(repo_root, ".git")
    if not os.path.isabs(common):
        common = os.path.join(repo_root, common)
    return os.path.join(os.path.abspath(common), ".graphite_pr_info")


# --- entrypoint ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Clear stale closed/merged PR associations for a QRSPI ticket so its "
                    "branches can be resubmitted under the same name (self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    args = parser.parse_args()

    path = pr_info_path(REPO_ROOT)
    removed, warning = prune_file(path, args.ticket)

    env = {
        "ok": True,  # absent/garbled cache degrades to a no-op, never a hard stop
        "repoRoot": REPO_ROOT,
        "prInfoPath": path,
        "ticket": args.ticket,
        "removed": removed,
    }
    if warning is not None:
        env["warning"] = warning

    json.dump(env, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
