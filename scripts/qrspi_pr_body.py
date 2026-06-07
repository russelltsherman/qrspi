#!/usr/bin/env python3
"""Author a slice PR's body INTO its branch commit message, so Graphite seeds the
PR description at creation time.

Why this exists
---------------
Graphite (`gt submit`) has no `--body`/`--body-file` flag in any version this repo
runs (1.8.x): the ONLY non-interactive way to set a PR description is to let Graphite
seed it from the branch's commit message when it *creates* the PR. That is exactly how
the design/plan PRs already get their bodies (their heredoc commit message becomes the
PR body). The implementation phase was the lone exception — it created slice commits
with a subject-only message and then tried to attach the body afterward with
`gh pr edit ... --body`. That post-hoc edit fails: the gh-authenticated token is a
fine-grained PAT owned by a *different* personal account than the repo owner, so it can
READ the public repo but every authenticated PR write returns
`403 Resource not accessible by personal access token`. (Graphite's own GitHub-App
credential — a separate auth path — is what makes `gt submit` itself succeed.)

So the fix is to stop writing PR bodies through gh entirely and author them at the one
write path that works: the commit message Graphite reads at creation. This script sets
the slice commit's message to `<existing subject> + <body file contents> + <existing
trailer>` and amends it via `gt modify -m` (which auto-restacks the slices above it).
The caller's subsequent `gt submit --publish --stack` then creates each slice PR with
the body already in place — no gh write, no 403.

Same one-shot, self-locating design as qrspi_persist.py / qrspi_restack.py: the repo
root is derived from __file__ (never typed by the weak worker model, which mangles the
"qrspi" path token across multi-step shell), and the whole operation is a single
deterministic command the finalize worker invokes verbatim.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, ticket, slice, branch, worktreeDir, subject, bytes, error? }
"""

import argparse
import json
import os
import re
import subprocess
import sys

# The script lives at <repo-root>/scripts/qrspi_pr_body.py, so the repo root is two
# levels up. Deriving it from __file__ (not cwd, not an argument) removes the path a
# weak worker model keeps corrupting. This is the FALLBACK root; main() prefers the
# git-common-dir root (below) so the script is correct whether invoked from the main
# checkout OR from inside a linked worktree (where __file__ would point at the worktree's
# own copy and mis-resolve <worktree>/.worktrees/<ticket>).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)

# A git trailer line: "Token: value" / "Co-Authored-By: ...". Used to keep the existing
# trailer block (e.g. the Co-Authored-By line) at the BOTTOM of the message when we
# splice the PR body between the subject and the trailer.
_TRAILER_RE = re.compile(r"^[A-Za-z][A-Za-z-]*:\s+\S")


# --- pure helpers (unit-tested) --------------------------------------------

def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; computed here, never typed by the
    model. Matches qrspi_restack.worktree_path / qrspi_persist."""
    return os.path.join(repo_root, ".worktrees", ticket)


def slice_branch(ticket, n):
    """Branch name for a ticket's slice N (`<ticket>/slice-<N>`). Pure."""
    return "%s/slice-%d" % (ticket, int(n))


def split_subject_trailers(message):
    """Split an existing one-commit message into (subject, trailer_lines).

    subject       = the first line, stripped.
    trailer_lines = the contiguous block of trailer lines ("Token: value") at the very
                    end of the message (e.g. the Co-Authored-By line), in order. Any
                    body between subject and that block is discarded — this script
                    re-authors the body. Pure, so the splice is unit-testable without git.
    """
    lines = (message or "").splitlines()
    if not lines:
        return "", []
    subject = lines[0].strip()
    trailers = []
    for ln in reversed(lines[1:]):
        s = ln.strip()
        if not s:
            # A blank line above an already-collected trailer block ends it; blanks
            # below the body (before we hit any trailer) are skipped.
            if trailers:
                break
            continue
        if _TRAILER_RE.match(s):
            trailers.append(s)
        else:
            # First non-blank, non-trailer line from the bottom => end of trailer block.
            break
    trailers.reverse()
    return subject, trailers


def compose_message(existing_message, body_text):
    """Build the new commit message: subject, blank, PR body, blank, trailer block.

    Preserves the commit's existing subject and trailer (whatever Claude-version trailer
    the commit was created with) and splices `body_text` (the pr-summary) in between, so
    Graphite uses subject as the PR title and the body as the PR description. Pure;
    returns a newline-terminated message. `body_text` is stripped of surrounding
    whitespace so we control the spacing.
    """
    subject, trailers = split_subject_trailers(existing_message)
    parts = [subject, "", (body_text or "").strip()]
    if trailers:
        parts += ["", "\n".join(trailers)]
    return "\n".join(parts).rstrip() + "\n"


def classify_modify(rc, stdout, stderr):
    """Map a `gt modify` (rc, stdout, stderr) to (ok, error). Pure, so the success/
    failure decision is unit-testable without running gt."""
    if rc == 0:
        return True, None
    msg = (stderr or "").strip() or (stdout or "").strip() or "gt modify failed (rc=%d)" % rc
    return False, msg


def build_envelope(ticket, slice_n, branch, worktree_dir, ok=True, subject=None,
                   bytes_=0, error=None, repo_root=None):
    """Assemble the JSON envelope the qrspi-batch finalize worker consumes. Pure;
    `repoRoot` defaults to the module-level REPO_ROOT (the __file__-derived fallback) and
    is set to the git-common-dir root by main()."""
    env = {
        "ok": ok,
        "repoRoot": repo_root if repo_root is not None else REPO_ROOT,
        "ticket": ticket,
        "slice": int(slice_n),
        "branch": branch,
        "worktreeDir": worktree_dir,
        "subject": subject,
        "bytes": int(bytes_),
    }
    if error is not None:
        env["error"] = error
    return env


# --- subprocess-backed mechanics (not unit-tested; manual e2e) -------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def resolve_repo_root():
    """The MAIN repo root, correct from any cwd inside the repo (including a linked
    worktree). `git --git-common-dir` returns the shared .git dir (the MAIN repo's, even
    when cwd is a worktree), whose parent is the main root — so worktree_path() always
    points at <main>/.worktrees/<ticket>, never <worktree>/.worktrees/<ticket>. Falls
    back to the __file__-derived REPO_ROOT if git can't answer (e.g. cwd outside a repo,
    in which case the caller invoked us by absolute main path and __file__ is correct)."""
    rc, out, _ = _run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    common = (out or "").strip()
    if rc == 0 and common:
        return os.path.dirname(common)
    return REPO_ROOT


def read_head_message(worktree):
    """Full commit message (%B) of the currently checked-out HEAD in the worktree."""
    rc, out, err = _run(["git", "log", "-1", "--format=%B"], cwd=worktree)
    if rc != 0:
        return None, (err or out).strip()
    return out, None


def set_body(worktree, branch, body_text):
    """Check out the slice branch and amend its commit message to splice in the PR body.

    `gt modify -m` amends the current branch's single commit message (nothing is staged,
    so only the message changes) and automatically restacks the slices above it. Returns
    (ok, subject, error).
    """
    rc, out, err = _run(["gt", "checkout", branch, "--no-interactive"], cwd=worktree)
    if rc != 0:
        return False, None, ("gt checkout %s failed: %s" % (branch, (err or out).strip()))

    existing, msg_err = read_head_message(worktree)
    if existing is None:
        return False, None, ("could not read commit message for %s: %s" % (branch, msg_err))

    subject, _ = split_subject_trailers(existing)
    message = compose_message(existing, body_text)

    rc, out, err = _run(["gt", "modify", "--no-interactive", "-m", message], cwd=worktree)
    ok, error = classify_modify(rc, out, err)
    return ok, subject, error


def main():
    parser = argparse.ArgumentParser(
        description="Splice a PR body into a QRSPI slice commit message (self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    parser.add_argument("--slice", type=int, default=1,
                        help="Slice number whose commit message receives the body (default 1)")
    parser.add_argument("--body-file", default=None,
                        help="Path to the body file. Relative paths resolve against the "
                             "ticket worktree. Default: <worktree>/.qrspi/<ticket>/pr-summary.md")
    args = parser.parse_args()

    repo_root = resolve_repo_root()
    worktree = worktree_path(repo_root, args.ticket)
    branch = slice_branch(args.ticket, args.slice)

    if not os.path.isdir(worktree):
        env = build_envelope(args.ticket, args.slice, branch, worktree, ok=False,
                             error="worktree not found: %s" % worktree,
                             repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    # Default to the canonical pr-summary path so the caller need not type the
    # "qrspi"-laden artifact path (the script owns it, like qrspi_persist.py).
    body_path = args.body_file or os.path.join(".qrspi", args.ticket, "pr-summary.md")
    if not os.path.isabs(body_path):
        body_path = os.path.join(worktree, body_path)
    if not os.path.isfile(body_path):
        env = build_envelope(args.ticket, args.slice, branch, worktree, ok=False,
                             error="body file not found: %s" % body_path,
                             repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    with open(body_path, "r", encoding="utf-8") as fh:
        body_text = fh.read()
    if not body_text.strip():
        env = build_envelope(args.ticket, args.slice, branch, worktree, ok=False,
                             error="body file is empty: %s" % body_path,
                             repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    ok, subject, error = set_body(worktree, branch, body_text)
    env = build_envelope(args.ticket, args.slice, branch, worktree, ok=ok,
                         subject=subject, bytes_=len(body_text.encode("utf-8")),
                         error=error, repo_root=repo_root)
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
