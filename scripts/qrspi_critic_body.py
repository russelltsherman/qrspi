#!/usr/bin/env python3
"""Splice a critic's RESIDUAL FINDINGS into a phase / slice commit message, so Graphite
seeds the PR description with the critic's unresolved concerns at creation time.

Why this exists
---------------
A critic loop (the design-critic PANEL `runCriticPanelLoop`, or the whole-stack coherence
pass `runCoherenceCritic`, in `.claude/workflows/qrspi-batch.js`; the fidelity-only edge
loop was retired in RUS-88) runs produce -> critique -> revise on a phase artifact / stack.
When the loop hits its round cap WITHOUT the critic passing (`cap_reached`), the artifact is
still finalized — but the critic's residual findings (the requirements it judged still
dropped/distorted) must be surfaced to the human reviewer. The only non-interactive lever
for a PR body is the branch commit message Graphite reads at creation (`gt submit` has no
body flag — see qrspi_pr_body.py). The finalize workers create a SUBJECT-ONLY commit, so
this script amends that commit's message to append a "Residual critic findings" section.

Same one-shot, self-locating design as qrspi_pr_body.py / qrspi_persist.py: the repo root is
derived from __file__ (never typed by the weak worker model), and the residual findings are
read from a token-free staged file (the JS glue writes them there) rather than passed as a
shell argument — so fragile finding text never round-trips through heredoc shell-quoting.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, ticket, phase, branch, worktreeDir, subject, bytes, error? }
"""

import argparse
import json
import os
import re
import subprocess
import sys

ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

# A git trailer line: "Token: value" (e.g. the Co-Authored-By line). Used to keep the
# trailer block at the BOTTOM of the message when we splice the findings section above it.
_TRAILER_RE = re.compile(r"^[A-Za-z][A-Za-z-]*:\s+\S")

# The phase whose commit receives the findings -> its branch suffix. design/plan carry a
# fixed suffix; `slice` is parametric (the suffix is `slice-<N>`, resolved from --slice N)
# so the per-slice and whole-stack-coherence critic findings (RUS-58 Slice 2) can target
# `<ticket>/slice-N`. The `slice` value here is a placeholder marker; phase_branch() computes
# the real `slice-<N>` suffix from the slice index.
_PHASE_BRANCH = {"design": "design", "plan": "plan", "slice": "slice"}


# --- pure helpers (unit-tested) --------------------------------------------

def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; computed here, never typed by the model."""
    return os.path.join(repo_root, ".worktrees", ticket)


def phase_branch(ticket, phase, slice_index=None):
    """Branch name for a ticket's critic phase. Pure.

    design/plan -> `<ticket>/design` | `<ticket>/plan` (slice_index ignored).
    slice       -> `<ticket>/slice-<N>`, where N is the 1-based slice_index; a missing or
                   non-positive slice_index for the `slice` phase is a ValueError (the CLI
                   makes --slice required when --phase slice, but the pure helper guards too).
    """
    suffix = _PHASE_BRANCH.get(phase)
    if suffix is None:
        raise ValueError("unsupported critic phase: %r" % (phase,))
    if phase == "slice":
        try:
            n = int(slice_index)
        except (TypeError, ValueError):
            raise ValueError("phase 'slice' requires an integer --slice N, got %r"
                             % (slice_index,))
        if n < 1:
            raise ValueError("phase 'slice' requires a 1-based slice index >= 1, got %d" % n)
        return "%s/slice-%d" % (ticket, n)
    return "%s/%s" % (ticket, suffix)


def split_subject_trailers(message):
    """Split an existing one-commit message into (subject, body_lines, trailer_lines).

    subject       = the first line, stripped.
    trailer_lines = the contiguous trailer block ("Token: value") at the very end.
    body_lines    = everything between the subject and that trailer block, trailing/leading
                    blank lines trimmed (the EXISTING body is preserved — unlike qrspi_pr_body
                    which re-authors it — because the design/plan commit subject IS the body
                    today and we only APPEND the findings section).

    Pure, so the splice is unit-testable without git.
    """
    lines = (message or "").splitlines()
    if not lines:
        return "", [], []
    subject = lines[0].strip()
    rest = lines[1:]

    trailers = []
    cut = len(rest)
    for ln in reversed(rest):
        s = ln.strip()
        if not s:
            if trailers:
                break
            cut -= 1
            continue
        if _TRAILER_RE.match(s):
            trailers.append(s)
            cut -= 1
        else:
            break
    trailers.reverse()

    body = rest[:cut]
    # Trim leading/trailing blank lines from the body block.
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return subject, body, trailers


def render_findings_section(findings):
    """Render the residual findings as a markdown section. Pure. Empty/non-list -> ''."""
    if not isinstance(findings, list):
        return ""
    items = [str(f).strip() for f in findings if str(f).strip()]
    if not items:
        return ""
    lines = ["## Residual critic findings",
             "",
             "The edge-critic reached its review-round cap without these upstream "
             "requirements being fully resolved. They are surfaced here for the reviewer:",
             ""]
    lines += ["- %s" % it for it in items]
    return "\n".join(lines)


def compose_message(existing_message, findings):
    """Build the new commit message: subject, existing body, residual-findings section,
    trailer block. Preserves subject + body + trailer; appends the findings section between
    the body and the trailer. Pure; returns a newline-terminated message. If there are no
    renderable findings the message is returned unchanged (idempotent no-op)."""
    subject, body, trailers = split_subject_trailers(existing_message)
    section = render_findings_section(findings)
    parts = [subject]
    if body:
        parts += [""] + body
    if section:
        parts += ["", section]
    if trailers:
        parts += ["", "\n".join(trailers)]
    return "\n".join(parts).rstrip() + "\n"


def classify_modify(rc, stdout, stderr):
    """Map a `gt modify` (rc, stdout, stderr) to (ok, error). Pure."""
    if rc == 0:
        return True, None
    msg = (stderr or "").strip() or (stdout or "").strip() or "gt modify failed (rc=%d)" % rc
    return False, msg


def build_envelope(ticket, phase, branch, worktree_dir, ok=True, subject=None,
                   bytes_=0, error=None, repo_root=None):
    """Assemble the JSON envelope the qrspi-batch finalize worker consumes. Pure."""
    env = {
        "ok": ok,
        "repoRoot": repo_root if repo_root is not None else REPO_ROOT,
        "ticket": ticket,
        "phase": phase,
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
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def read_head_message(worktree):
    rc, out, err = _run(["git", "log", "-1", "--format=%B"], cwd=worktree)
    if rc != 0:
        return None, (err or out).strip()
    return out, None


def set_findings(worktree, branch, findings):
    """Check out the phase branch and amend its commit message to append the findings section.
    Returns (ok, subject, error)."""
    rc, out, err = _run(["gt", "checkout", branch, "--no-interactive"], cwd=worktree)
    if rc != 0:
        return False, None, ("gt checkout %s failed: %s" % (branch, (err or out).strip()))

    existing, msg_err = read_head_message(worktree)
    if existing is None:
        return False, None, ("could not read commit message for %s: %s" % (branch, msg_err))

    subject, _, _ = split_subject_trailers(existing)
    message = compose_message(existing, findings)

    rc, out, err = _run(["gt", "modify", "--no-interactive", "-m", message], cwd=worktree)
    ok, error = classify_modify(rc, out, err)
    return ok, subject, error


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Splice residual critic findings into a QRSPI design/plan commit message")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    parser.add_argument("--phase", required=True, choices=sorted(_PHASE_BRANCH),
                        help="Critic phase whose commit receives the findings "
                             "(design|plan|slice)")
    parser.add_argument("--slice", dest="slice_index", type=int, default=None,
                        help="1-based slice index, REQUIRED when --phase slice "
                             "(targets <ticket>/slice-N); ignored for design/plan.")
    parser.add_argument("--findings-file", required=True,
                        help="Path to a JSON file holding the residual findings (a JSON array "
                             "of strings). Relative paths resolve against the ticket worktree.")
    args = parser.parse_args(argv)

    if args.phase == "slice" and args.slice_index is None:
        parser.error("--slice N is required when --phase slice")

    repo_root = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
    worktree = worktree_path(repo_root, args.ticket)
    branch = phase_branch(args.ticket, args.phase, args.slice_index)

    if not os.path.isdir(worktree):
        env = build_envelope(args.ticket, args.phase, branch, worktree, ok=False,
                             error="worktree not found: %s" % worktree, repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    findings_path = args.findings_file
    if not os.path.isabs(findings_path):
        findings_path = os.path.join(worktree, findings_path)
    if not os.path.isfile(findings_path):
        env = build_envelope(args.ticket, args.phase, branch, worktree, ok=False,
                             error="findings file not found: %s" % findings_path,
                             repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    with open(findings_path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    try:
        findings = json.loads(raw) if raw.strip() else []
    except (ValueError, TypeError) as exc:
        env = build_envelope(args.ticket, args.phase, branch, worktree, ok=False,
                             error="findings file is not valid JSON: %s" % exc,
                             repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    section = render_findings_section(findings)
    if not section:
        # No residual findings (converged, or empty list) -> nothing to splice. Success
        # no-op so the caller need not branch on whether findings exist.
        env = build_envelope(args.ticket, args.phase, branch, worktree, ok=True,
                             subject=None, bytes_=0, repo_root=repo_root)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 0

    ok, subject, error = set_findings(worktree, branch, findings)
    env = build_envelope(args.ticket, args.phase, branch, worktree, ok=ok, subject=subject,
                         bytes_=len(section.encode("utf-8")), error=error, repo_root=repo_root)
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
