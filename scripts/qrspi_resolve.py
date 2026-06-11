#!/usr/bin/env python3
"""One-shot QRSPI resolve: worktree setup + PR-state gather + decision in a SINGLE
deterministic command.

Why this exists
---------------
The qrspi-batch RESOLVE worker used to perform this as a hand-typed sequence of
~6 shell steps (locate repo root, set up the worktree, `gh repo view`, then
`qrspi_pr_state.py | qrspi_resolve_state.py`, then probe artifact files). Every
step contains the literal token "qrspi" in a path or repo name. A small local
model (qwen3.6:35b via Ollama) could not reproduce that token reliably and
spiralled — it mangled `qrspi` into `qrpi`, `qrpi-spi`, `qrpi-skills`,
`qrpi_pr_state.py`, etc., across 120+ failing commands and never produced a
decision.

The fix is to make the path-sensitive work deterministic. This script computes
EVERYTHING path-related from its own location (`__file__`), so the only thing the
caller types is this one invocation. It reuses the tested pure logic
(`qrspi_pr_state.build_state`, `qrspi_resolve_state.resolve`) rather than
re-deriving it. Any infrastructure error is reported ONCE as `ok:false` with the
verbatim message — never retried — so a weak model cannot thrash on it.

The caller still supplies the two Linear facts a script cannot read
(`--assigned`, `--linear-status`) and stages the ticket title/body it fetched via
MCP to a token-free file; we emit that file's PATH (`ticketContentPath`), not its
body, so the design phase reads it file->file and the fragile text never round-trips
through the worker's stdout echo. Everything else is handled here.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, worktreeDir, existing{...booleans}, decision{...}, error? }
"""

import argparse
import json
import os
import subprocess
import sys

# The script lives at <repo-root>/scripts/qrspi_resolve.py, so the repo root is
# two levels up. Deriving it from __file__ (not cwd, not an argument) is the whole
# point: it removes the path the model kept corrupting.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

from qrspi_pr_state import build_state, branch_set, slice_numbers  # noqa: E402
from qrspi_resolve_state import resolve  # noqa: E402

ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]

# Optional, gitignored override file (see .qrspi/config.example.json). Keeping the
# default resolution at "@me" (the authenticated GitHub user) means a freshly cloned
# harness needs NO config and ships NO hard-coded username — the thing that makes it
# shareable. The file override only exists for teams that want a *designated*
# reviewer or team slug instead of self-review.
REVIEWER_CONFIG = ["config.json"]  # relative to <repo>/.qrspi/


# --- pure helpers (unit-tested) --------------------------------------------

def _split_csv(value):
    """Split a comma-separated string into trimmed, non-empty tokens. None -> []."""
    return [tok.strip() for tok in (value or "").split(",") if tok.strip()]


def _as_token_list(value):
    """Coerce a config value (CSV string OR list) into trimmed, non-empty tokens."""
    if value is None:
        return []
    if isinstance(value, str):
        return _split_csv(value)
    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe_ci(items):
    """De-duplicate case-insensitively, preserving first-seen order/casing."""
    seen, out = set(), []
    for it in items:
        key = it.lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def select_source(config, key, default):
    """Resolve one reviewer source: config[key] when present (CSV string OR list),
    else default. Reviewers are config-file only — there is no env override. To opt
    out entirely, set the key to [] in config. Pure, so it is unit-testable."""
    if isinstance(config, dict) and key in config:
        return _as_token_list(config[key])
    return list(default)


def references_me(config):
    """True iff the chosen individual-reviewer source contains the @me sentinel, so
    the caller knows it must look up the authenticated login before resolving."""
    raw = select_source(config, "reviewers", ["@me"])
    return any(tok.lower() == "@me" for tok in raw)


def resolve_reviewers(config, me_login):
    """Resolve (individual_reviewers, team_reviewers) from config, with the @me
    default.

    - Individual reviewers default to ["@me"]; the @me sentinel expands to
      `me_login` (dropped if me_login is falsy — e.g. gh is unauthenticated).
    - Team reviewers default to [] (Graphite --team-reviewers slugs).
    Both lists are de-duplicated case-insensitively. Pure given me_login, so the
    whole matrix is unit-testable without touching gh."""
    raw_revs = select_source(config, "reviewers", ["@me"])
    revs = []
    for tok in raw_revs:
        if tok.lower() == "@me":
            if me_login:
                revs.append(me_login)
        else:
            revs.append(tok)
    teams = select_source(config, "teamReviewers", [])
    return _dedupe_ci(revs), _dedupe_ci(teams)

def parse_name_with_owner(name_with_owner):
    """Split gh's `nameWithOwner` ("owner/repo") into (owner, repo). Tolerates a
    trailing newline. Raises ValueError on anything that is not exactly one '/'."""
    s = (name_with_owner or "").strip()
    parts = s.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("expected 'owner/repo', got %r" % name_with_owner)
    return parts[0], parts[1]


def detect_existing(qrspi_dir):
    """Map each QRSPI artifact -> True iff `<qrspi_dir>/<name>.md` exists and is
    non-empty. A missing directory yields all-False. Pure given a path, so it is
    unit-testable against a temp dir."""
    out = {}
    for name in ARTIFACTS:
        path = os.path.join(qrspi_dir, "%s.md" % name)
        try:
            out[name] = os.path.getsize(path) > 0
        except OSError:
            out[name] = False
    return out


def pick_tip(branches, ticket):
    """Pick the highest existing phase branch to reuse a worktree on, newest phase
    first: slice-N (largest N) > plan > design. Returns the bare branch name or
    None if the ticket has no branch yet. Pure, so it is unit-testable.

    `branches` is the normalized set from branch_set(); existence here is plain
    (any branch), NOT the trunk-ahead 'real' gate the resolver uses — for checking
    out a worktree we want whatever branch is actually there."""
    snums = slice_numbers(branches)
    if snums:
        return "%s/slice-%d" % (ticket, max(snums))
    for phase in ("plan", "design"):
        name = "%s/%s" % (ticket, phase)
        if name in branches:
            return name
    return None


def comment_targets_of(decision):
    """The per-phase comment-target list to surface at the TOP LEVEL of the envelope.

    The gather (qrspi_pr_state.build_state) already self-resolves the authenticated
    bot login and attaches `commentTargets` to every phase/slice, and the resolver
    folds the active phase's targets into `decision["commentTargets"]` when it emits
    `respond_comment`. We re-emit exactly those targets as a top-level `commentTargets`
    field because the `decision` dict's key set is fixed and the consumer
    (qrspi-batch doRespondComment) iterates `r.commentTargets` directly. Pure: a
    None/empty decision (e.g. the ok:false error envelope) yields []. Only the
    respond_comment decision carries a non-empty list."""
    if not isinstance(decision, dict):
        return []
    targets = decision.get("commentTargets")
    return targets if isinstance(targets, list) else []


def build_envelope(worktree_dir, decision, existing, ok=True, error=None,
                   reviewers="", team_reviewers="", ticket_content_path=""):
    """Assemble the JSON envelope the qrspi-batch resolveTicket() step consumes.
    Pure; `repoRoot` is always the module-level REPO_ROOT this script derived.

    `reviewers`/`team_reviewers` are comma-joined strings ready to drop straight
    behind `gt submit --reviewers`/`--team-reviewers` (empty string => omit the
    flag), so the JS finalize prompts never carry a hard-coded username.

    `commentTargets` is re-emitted at the TOP LEVEL (mirroring the active phase's
    targets the resolver folded into `decision`) so the respond_comment consumer
    iterates `r.commentTargets` without reaching into `decision`. It is [] for every
    non-respond_comment decision (additive; unknown to old consumers, which ignore it).

    `ticket_content_path` is the token-free file the caller staged the Linear
    title+body to. We emit the PATH, never the body: the design-phase agents Read
    that file directly (file->file), so the fragile ticket text — which routinely
    carries Linear `<issue ...>RUS-N</issue>` mention tags — never travels through
    the weak resolve worker's verbatim stdout echo, where a model HTML-escapes
    `>`->`&gt;` and corrupts the JSON the orchestrator must parse (RUS-69). The
    envelope thus stays angle-bracket-free for ANY ticket and any content."""
    env = {
        "ok": ok,
        "repoRoot": REPO_ROOT,
        "worktreeDir": worktree_dir,
        "existing": existing,
        "decision": decision,
        "commentTargets": comment_targets_of(decision),
        "reviewers": reviewers,
        "teamReviewers": team_reviewers,
        "ticketContentPath": ticket_content_path,
    }
    if error is not None:
        env["error"] = error
    return env


# --- subprocess-backed mechanics (not unit-tested) -------------------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def _gh_name_with_owner():
    rc, out, err = _run(["gh", "repo", "view", "--json", "nameWithOwner",
                         "-q", ".nameWithOwner"], cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("gh repo view failed: %s" % (err.strip() or out.strip()))
    return out.strip()


def _gh_authenticated_login():
    """The login of the gh-authenticated user (the human running the harness), or
    None if gh is unauthenticated. This is what @me expands to — so the default is
    'request review from whoever is running this', with no username in the repo."""
    rc, out, _ = _run(["gh", "api", "user", "-q", ".login"], cwd=REPO_ROOT)
    login = out.strip()
    return login if (rc == 0 and login) else None


def _read_reviewer_config():
    """Parse the optional, gitignored <repo>/.qrspi/config.json. Missing or invalid
    file -> {} (the @me default takes over). Never raises — reviewer resolution is
    best-effort and must not break a resolve."""
    path = os.path.join(REPO_ROOT, ".qrspi", *REVIEWER_CONFIG)
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def load_reviewers():
    """Resolve (reviewers_csv, team_reviewers_csv) from .qrspi/config.json, falling
    back to the @me default, looking up the authenticated login only when @me is
    actually referenced. Never raises; returns ("", "") if nothing resolves so the
    flag is simply omitted."""
    config = _read_reviewer_config()
    me_login = _gh_authenticated_login() if references_me(config) else None
    revs, teams = resolve_reviewers(config, me_login)
    return ",".join(revs), ",".join(teams)


def _existing_branches(ticket):
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()


def setup_worktree(ticket, trunk="main", create_design=False):
    """Provision the ticket's worktree at <repo>/.worktrees/<ticket> and return its
    path. Idempotent.

    - Existing worktree dir -> reuse as-is.
    - No worktree but a phase branch exists -> check it out on the stack tip.
    - No branch at all:
        * create_design=True  -> create a fresh <ticket>/design off trunk and track
          it in Graphite (the run_design entry path).
        * create_design=False -> create NOTHING; just return the (not-yet-existing)
          path. Resolve must stay read-only for actions like entry_blocked, so we
          never leave a stray branch/worktree behind for a ticket we won't act on.

    Raises RuntimeError with the verbatim git/gt error on failure — the caller turns
    that into a single ok:false envelope rather than retrying."""
    worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")
    worktree = os.path.join(worktrees_dir, ticket)

    if os.path.isdir(worktree):
        return worktree  # reuse

    tip = pick_tip(_existing_branches(ticket), ticket)
    if tip:
        os.makedirs(worktrees_dir, exist_ok=True)
        rc, _, err = _run(["git", "worktree", "add", worktree, tip], cwd=REPO_ROOT)
        if rc != 0:
            raise RuntimeError("git worktree add (reuse %s) failed: %s" % (tip, err.strip()))
        return worktree

    if not create_design:
        return worktree  # read-only: nothing to act on, create nothing

    # run_design on a brand-new ticket: create the design branch off trunk and track it.
    os.makedirs(worktrees_dir, exist_ok=True)
    rc, _, err = _run(["git", "worktree", "add", "-b", "%s/design" % ticket, worktree, trunk],
                      cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("git worktree add -b %s/design failed: %s" % (ticket, err.strip()))
    rc, _, err = _run(["gt", "track", "--parent", trunk, "--no-interactive"], cwd=worktree)
    if rc != 0:
        raise RuntimeError("gt track --parent %s failed: %s" % (trunk, err.strip()))
    return worktree


def main():
    parser = argparse.ArgumentParser(
        description="One-shot QRSPI resolve (worktree + PR state + decision)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    parser.add_argument("--assigned", action="store_true",
                        help="Ticket is assigned to a user (from Linear, supplied by caller)")
    parser.add_argument("--linear-status", default="",
                        help="Current Linear status name (from Linear, supplied by caller)")
    parser.add_argument("--ticket-content-file", default="",
                        help="Path to a token-free file holding the ticket title+body the "
                             "caller staged; this PATH is emitted as ticketContentPath (the "
                             "body is NOT embedded) so the design phase reads it file->file "
                             "and the fragile text never round-trips through the worker echo")
    parser.add_argument("--trunk", default="main", help="Trunk branch (default: main)")
    parser.add_argument("--blocked-open", action="store_true",
                        help="At least one open Linear blocker was detected (from Linear, supplied by caller)")
    parser.add_argument("--blocked-by", action="append", default=[],
                        help="Identifier of an open blocker (repeatable; comma-joined values also accepted). "
                             "From Linear, supplied by caller.")
    args = parser.parse_args()

    ticket_content_path = args.ticket_content_file
    blocked_by = [tok.strip() for raw in args.blocked_by for tok in raw.split(",") if tok.strip()]

    # Any infrastructure failure -> ONE ok:false envelope with the verbatim error.
    # Never partial-retry: a clean stop is what keeps a weak model from spiralling.
    try:
        # Decide first (read-only: build_state reads shared git refs + gh, no worktree
        # needed), THEN provision the worktree only as the decision requires — so an
        # entry_blocked ticket never leaves a stray branch behind.
        owner, repo = parse_name_with_owner(_gh_name_with_owner())
        state = build_state(owner, repo, args.ticket, args.assigned, args.linear_status,
                            trunk=args.trunk, blocked_open=args.blocked_open,
                            blocked_by=blocked_by)
        decision = resolve(state)
        worktree = setup_worktree(args.ticket, trunk=args.trunk,
                                  create_design=(decision["action"] == "run_design"))
        existing = detect_existing(os.path.join(worktree, ".qrspi", args.ticket))
        reviewers, team_reviewers = load_reviewers()
        env = build_envelope(worktree, decision, existing, ok=True,
                             reviewers=reviewers, team_reviewers=team_reviewers,
                             ticket_content_path=ticket_content_path)
    except Exception as exc:  # noqa: BLE001 - any failure is reported, not retried
        worktree = os.path.join(REPO_ROOT, ".worktrees", args.ticket)
        env = build_envelope(worktree, None,
                             {name: False for name in ARTIFACTS},
                             ok=False, error="%s: %s" % (type(exc).__name__, exc),
                             ticket_content_path=ticket_content_path)

    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if env["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
