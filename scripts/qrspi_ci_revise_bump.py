#!/usr/bin/env python3
"""Deterministically advance the `CI-Revise-Attempt: N` head-commit trailer by ONE on a
still-red phase/slice branch, then re-publish — the SOLE authority for the CI-failure
counter increment (RUS-83 / Option A').

Why this exists
---------------
RUS-81 added a consecutive-red-CI cap: a `CI-Revise-Attempt: N` head-commit trailer counts
consecutive red revises, and once it reaches `ciReviseCap` the resolver parks the PR
(red → `wait`) instead of looping forever. The +1 increment on the CI-failure path used to
live in the revise WORKER's hand-rolled prompt step ("read `git log -1 --format=%B`, rewrite
the trailer to <prior+1>, `gt modify -m`"). That made the counter advance CONDITIONAL on the
weak worker model (a) running the multi-step git correctly and (b) returning ok:true — so a
worker that failed to fix the build, or botched the trailer rewrite, could leave the count
flat, and the loop never reaches the cap (AC6 hole: the cap that is supposed to bound a
genuinely-stuck red PR never fires when the worker keeps failing).

This script closes that hole by making the increment DETERMINISTIC and UNCONDITIONAL: the
orchestrator (qrspi-batch.js `doRevise`) invokes it once per still-red branch on every red
revise pass, regardless of what the content worker did. It mirrors `qrspi_revise_amend.py`'s
trust model exactly:

- Self-locating: repo root is derived via the shared `qrspi_paths.resolve_repo_root()`
  (git-common-dir first — the MAIN checkout even from a worktree; __file__ parent last
  resort), never typed by the worker, which mangles the "qrspi" path token across shell.
- The trailer rewrite is a PURE function (`bump_ci_revise_trailer`) with the SAME parse
  semantics as the gather's `qrspi_pr_state.ci_revise_attempt` (the trailer is the shared
  serialization contract between writer and reader): absent ⇒ prior = 0, last-occurrence
  wins; the result carries EXACTLY one `CI-Revise-Attempt: <prior+1>` trailer with the
  subject and every other trailer byte-preserved.
- Applies the new message as a MESSAGE-ONLY amend (`gt modify --no-interactive -m`), with no
  file staging (this is the one place a bare `gt modify -m` is correct — only the message
  changes), then re-publishes the (re)stacked branch (`gt submit --publish --no-edit
  --no-interactive`, plus `--stack` for implementation), mirroring the worker's old step.
- VERIFIES the pushed head carries exactly one `CI-Revise-Attempt: <prior+1>` trailer and
  exits NON-ZERO (fail-closed, ok:false) on any failure — a count that could not advance is
  never silent.

Output: a single JSON envelope on stdout:
    { ok, branch, prior, new, error? }
"""

import argparse
import json
import os
import re
import subprocess
import sys

# ENGINE_ROOT: the dir holding this engine's scripts/ (from __file__) — used ONLY for
# sibling imports (qrspi_paths). REPO_ROOT is resolved via the shared resolver so a worktree
# invocation still keys host paths off the MAIN checkout root. validate=False keeps gh off
# the import path (mirrors qrspi_revise_amend.py).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

# The shared serialization contract with the gather (qrspi_pr_state._CI_REVISE_ATTEMPT_RE):
# a whole-line `CI-Revise-Attempt: N` trailer. MULTILINE so it matches per-line; the parse
# below takes the LAST occurrence (mirroring git trailer / gather semantics).
_CI_REVISE_ATTEMPT_RE = re.compile(r"^CI-Revise-Attempt:\s*(\d+)\s*$", re.MULTILINE)


# --- pure helpers (unit-tested) --------------------------------------------

def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; computed here, never typed by the
    model. Matches qrspi_revise_amend.worktree_path / qrspi_persist."""
    return os.path.join(repo_root, ".worktrees", ticket)


def parse_ci_revise_attempt(message):
    """Parse the `CI-Revise-Attempt: N` trailer from a head-commit message -> int.

    Pure. SAME semantics as the gather's qrspi_pr_state.ci_revise_attempt (the trailer is
    the shared serialization contract): absent or malformed -> 0; if the trailer appears
    more than once the LAST occurrence wins (mirroring git trailer semantics). A None/empty
    message yields 0."""
    matches = _CI_REVISE_ATTEMPT_RE.findall(message or "")
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except (TypeError, ValueError):
        return 0


def bump_ci_revise_trailer(message):
    """Return a new commit message with the `CI-Revise-Attempt` trailer advanced by one.

    Pure (unit-tested) — the deterministic increment core. Given a full commit message,
    parse the existing trailer (absent ⇒ prior = 0, last-occurrence wins), strip EVERY
    existing `CI-Revise-Attempt:` line, and append EXACTLY one `CI-Revise-Attempt: <prior+1>`
    trailer as the last line. The subject line and every other line/trailer are preserved
    byte-for-byte; only the `CI-Revise-Attempt` value changes and there is never a duplicate.

    Returns (new_message, prior, new_value)."""
    prior = parse_ci_revise_attempt(message)
    new_value = prior + 1

    # Strip all existing CI-Revise-Attempt lines, preserving every other line verbatim.
    text = message if message is not None else ""
    kept = [
        line for line in text.split("\n")
        if not _CI_REVISE_ATTEMPT_RE.match(line)
    ]

    # Drop trailing blank lines so the new trailer sits flush in the trailer block (and a
    # message that was nothing but the trailer collapses to just the new trailer), then
    # append the single new trailer.
    while kept and kept[-1].strip() == "":
        kept.pop()
    kept.append("CI-Revise-Attempt: %d" % new_value)

    return "\n".join(kept) + "\n", prior, new_value


def build_envelope(branch, ok=True, prior=None, new=None, error=None):
    """Assemble the JSON envelope the qrspi-batch doRevise consumes. Pure."""
    env = {
        "ok": ok,
        "branch": branch,
        "prior": prior,
        "new": new,
    }
    if error is not None:
        env["error"] = error
    return env


# --- subprocess-backed mechanics (not unit-tested; manual e2e) -------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def read_head_message(worktree):
    """Full commit message (%B) of the currently checked-out HEAD."""
    rc, out, err = _run(["git", "log", "-1", "--format=%B"], cwd=worktree)
    if rc != 0:
        return None, (err or out).strip()
    return out, None


def bump_and_publish(worktree, branch, stack):
    """Check out `branch`, advance its head's `CI-Revise-Attempt` trailer by one via a
    message-only amend, re-publish the (re)stacked branch, and VERIFY the pushed head
    carries exactly one trailer at <prior+1>.

    `stack` -> append `--stack` to the publish (implementation slices restack upward).

    Returns (ok, prior, new, error)."""
    rc, out, err = _run(["gt", "checkout", branch, "--no-interactive"], cwd=worktree)
    if rc != 0:
        return False, None, None, ("gt checkout %s failed: %s" % (branch, (err or out).strip()))

    existing, msg_err = read_head_message(worktree)
    if existing is None:
        return False, None, None, ("could not read commit message for %s: %s" % (branch, msg_err))

    new_message, prior, new_value = bump_ci_revise_trailer(existing)

    # Message-only amend: nothing is staged, only the commit message is rewritten. This is
    # the one place a bare `gt modify -m` is correct. Amending the message re-stacks
    # descendants (expected).
    rc, out, err = _run(["gt", "modify", "--no-interactive", "-m", new_message], cwd=worktree)
    if rc != 0:
        msg = (err or out).strip() or ("gt modify failed (rc=%d)" % rc)
        return False, prior, new_value, ("gt modify failed: %s" % msg)

    publish = ["gt", "submit", "--publish", "--no-edit", "--no-interactive"]
    if stack:
        publish.insert(2, "--stack")
    rc, out, err = _run(publish, cwd=worktree)
    if rc != 0:
        msg = (err or out).strip() or ("gt submit failed (rc=%d)" % rc)
        return False, prior, new_value, ("gt submit --publish failed: %s" % msg)

    # VERIFY: re-read the pushed head and confirm exactly one trailer at <prior+1>.
    pushed, verr = read_head_message(worktree)
    if pushed is None:
        return False, prior, new_value, ("could not re-read head after publish: %s" % verr)
    found = _CI_REVISE_ATTEMPT_RE.findall(pushed)
    if len(found) != 1:
        return False, prior, new_value, (
            "expected exactly one CI-Revise-Attempt trailer after bump, found %d: %r"
            % (len(found), found)
        )
    if int(found[0]) != new_value:
        return False, prior, new_value, (
            "head trailer is CI-Revise-Attempt: %s, expected %d" % (found[0], new_value)
        )

    return True, prior, new_value, None


def main():
    parser = argparse.ArgumentParser(
        description="Advance the CI-Revise-Attempt head-commit trailer by one on a still-red "
                    "branch, then re-publish (self-locating, fail-closed)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-83")
    parser.add_argument("--branch", required=True,
                        help="Branch to bump, e.g. RUS-83/design, RUS-83/plan, or "
                             "RUS-83/slice-2")
    parser.add_argument("--stack", action="store_true",
                        help="Append --stack to the publish (present for implementation "
                             "slices, absent for design/plan)")
    args = parser.parse_args()

    repo_root = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
    worktree = worktree_path(repo_root, args.ticket)

    if not os.path.isdir(worktree):
        env = build_envelope(args.branch, ok=False,
                             error="worktree not found: %s" % worktree)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    ok, prior, new, error = bump_and_publish(worktree, args.branch, args.stack)
    env = build_envelope(args.branch, ok=ok, prior=prior, new=new, error=error)
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
