#!/usr/bin/env python3
"""Gather the PR review state the PR-gated resolver needs.

Emits the normalized state JSON consumed by qrspi_resolve_state.py. The branch
and PR queries shell out to `git` and `gh` (CLIs, not MCP — a script can run
them); the Linear bits (assigned, linearStatus) cannot come from a script, so the
caller passes them in via --assigned / --linear-status.

The mandatory mechanism from the design doc §6 — true resolved/unresolved thread
state — comes from GitHub GraphQL `reviewThreads { isResolved }`, NOT the REST
comments list (which can't tell resolved from unresolved). The GraphQL/JSON
parsing is pure and unit-tested; the subprocess calls are not.

Phase -> head branch:
    design          <ticket>/design
    plan            <ticket>/plan
    implementation  <ticket>/slice-<n>  (one PR per slice; reviewed as a stack)
"""

import argparse
import json
import re
import subprocess
import sys

PR_QUERY = """
query($owner:String!, $repo:String!, $head:String!) {
  repository(owner:$owner, name:$repo) {
    pullRequests(headRefName:$head, first:25, orderBy:{field:CREATED_AT, direction:DESC}) {
      nodes {
        number
        state
        merged
        mergedAt
        reviewDecision
        reviewThreads(first:100) {
          nodes {
            id
            isResolved
            comments(first:100) {
              nodes { databaseId body createdAt author { login } }
            }
          }
        }
        comments(first:100) {
          nodes { databaseId body createdAt author { login } }
        }
      }
    }
  }
}
"""


# --- pure parsers (unit-tested) --------------------------------------------

def unresolved_thread_count(review_threads):
    """Count threads whose isResolved is falsey. `review_threads` is the list of
    {isResolved: bool} nodes from the GraphQL reviewThreads field."""
    return sum(1 for t in (review_threads or []) if not t.get("isResolved"))


def _comment_login(comment):
    """The login of a comment's author, or "" if absent. Reads the API field
    author.login — never a regex over a JSON blob (ref: AC5, AC6, Decision 2)."""
    return ((comment or {}).get("author") or {}).get("login") or ""


def unaddressed_reviewer_comments(pr_node, bot_login):
    """Reviewer-authored comments on `pr_node` with no later bot reply in-thread.

    Pure function (unit-tested). Given a parsed PR node and the bot/authenticated
    login, returns a list of CommentTarget dicts:
        {commentId, author, body, threadType, threadId, lastReplyAuthor}

    Comment ids come from .databaseId and authors from author.login (API fields,
    never a JSON-blob regex). Any comment authored by bot_login is filtered out.

    Inline rule: comments in a RESOLVED thread are never unaddressed — the reviewer
    marked it done (RUS-69). In an unresolved thread, a reviewer comment is unaddressed
    iff no LATER comment in that same thread's comment chain is authored by bot_login.
    threadType="inline", threadId=the thread id, lastReplyAuthor=the last comment's
    author login.

    Top-level rule: a top-level reviewer comment is unaddressed iff no bot-authored
    top-level comment has a strictly greater createdAt. Both sets are ordered by
    createdAt ascending before comparison. threadType="toplevel", threadId=None,
    lastReplyAuthor=None (ref: AC5, AC6, Decision 1, Decision 2; plan §1.3-1.5)."""
    targets = []

    # --- inline (review-thread) comments ----------------------------------
    threads = ((pr_node or {}).get("reviewThreads") or {}).get("nodes", []) or []
    for thread in threads:
        # A resolved thread is addressed by definition — the reviewer marked it done,
        # so its comments are never reply targets regardless of who (if anyone) replied
        # in-thread. Skipping here stops the batch from replying into already-resolved
        # threads (RUS-69). Top-level comments below are not thread-resolvable.
        if thread.get("isResolved"):
            continue
        thread_id = thread.get("id")
        comments = (thread.get("comments") or {}).get("nodes", []) or []
        ordered = sorted(comments, key=lambda c: c.get("createdAt") or "")
        last_reply = _comment_login(ordered[-1]) if ordered else None
        for idx, c in enumerate(ordered):
            author = _comment_login(c)
            if author == bot_login:
                continue
            # Unaddressed iff no LATER comment in the thread is bot-authored.
            if any(_comment_login(later) == bot_login for later in ordered[idx + 1:]):
                continue
            targets.append({
                "commentId": c.get("databaseId"),
                "author": author,
                "body": c.get("body"),
                "threadType": "inline",
                "threadId": thread_id,
                "lastReplyAuthor": last_reply,
            })

    # --- top-level comments -----------------------------------------------
    top = ((pr_node or {}).get("comments") or {}).get("nodes", []) or []
    top_ordered = sorted(top, key=lambda c: c.get("createdAt") or "")
    latest_bot_created = None
    for c in top_ordered:
        if _comment_login(c) == bot_login:
            latest_bot_created = c.get("createdAt") or ""
    for c in top_ordered:
        author = _comment_login(c)
        if author == bot_login:
            continue
        created = c.get("createdAt") or ""
        # Addressed iff some bot top-level comment is strictly newer.
        if latest_bot_created is not None and latest_bot_created > created:
            continue
        targets.append({
            "commentId": c.get("databaseId"),
            "author": author,
            "body": c.get("body"),
            "threadType": "toplevel",
            "threadId": None,
            "lastReplyAuthor": None,
        })

    return targets


def select_pr(nodes, prefer):
    """Pick one PR node from the GraphQL pullRequests.nodes list for one head ref.

    A single named selection primitive over the fetched nodes so the two
    consumers (advancement vs merge/land) state their intent explicitly instead
    of both reaching for nodes[0] (ref: Contracts select_pr; Decision 1 Option C,
    Decision 2 Option A).

    prefer="active"  -> the advancement-facing PR: identity nodes[0] (newest by
                        CREATED_AT DESC), or None for an empty list. This reduces
                        to the current selection byte-for-byte for the common
                        single-PR case (AC3, Q10, OQ3).
    prefer="merged"  -> the merge/land-facing PR: the first node whose merged is
                        True if ANY fetched node is MERGED ("any MERGED node wins",
                        order-independent), else falls back to the active selection
                        so all-open/all-closed branches behave exactly as today
                        (AC1, Q8/Q9, Unverified Assumption 3).

    Any other prefer raises ValueError."""
    if prefer == "active":
        return nodes[0] if nodes else None
    if prefer == "merged":
        for node in (nodes or []):
            if node.get("merged") is True:
                return node
        return nodes[0] if nodes else None
    raise ValueError("unknown prefer: %r" % (prefer,))


def parse_pr_nodes(nodes, bot_login=None):
    """Reduce the GraphQL pullRequests.nodes list for one head branch to the
    normalized PR shape. No open PR -> prExists False.

    GitHub's reviewDecision is null until a review exists; we normalize null to
    None so the resolver treats it as 'awaiting review' (not approved).

    The merge fields (merged/state/mergedAt) are ADDITIVE: existing OPEN-path
    callers (resolver/restack) read only prExists/number/reviewDecision/
    unresolvedThreads and are unaffected (ref: Decision 1, Q2, Q7).

    `commentTargets` is also ADDITIVE: the list of unaddressed reviewer comments on
    the active PR (via unaddressed_reviewer_comments). It defaults to [] when no
    bot_login is supplied or there are no comments (ref: AC1, AC5, AC6; plan §1.6).

    Selection is the advancement-facing PR via select_pr(nodes, prefer="active")
    — identity nodes[0] — so this stays byte-for-byte the current behavior; the
    merge/land path uses prefer="merged" separately (ref: AC3, Q10, OQ3)."""
    node = select_pr(nodes, prefer="active")
    if node is None:
        return {"prExists": False, "number": None,
                "reviewDecision": None, "unresolvedThreads": 0,
                "merged": False, "state": None, "mergedAt": None,
                "commentTargets": []}
    threads = (node.get("reviewThreads") or {}).get("nodes", [])
    targets = unaddressed_reviewer_comments(node, bot_login) if bot_login else []
    return {
        "prExists": True,
        "number": node.get("number"),
        "reviewDecision": node.get("reviewDecision"),
        "unresolvedThreads": unresolved_thread_count(threads),
        "merged": bool(node.get("merged")),
        "state": node.get("state"),
        "mergedAt": node.get("mergedAt"),
        "commentTargets": targets,
    }


def stack_merge_state(branches, graphql_nodes):
    """Map each real branch to its merge status from MERGED-aware GraphQL results.

    `branches` is the list of real branch head-ref names for one ticket's stack.
    `graphql_nodes` maps a branch head-ref name -> the GraphQL pullRequests.nodes
    list returned for that head ref (the same shape parse_pr_nodes consumes). A
    branch whose head ref GitHub has ALREADY DELETED (post-merge ref cleanup) — or
    that simply has no PR node — is mapped to the documented sentinel
    {merged: False, prNumber: None, state: None}, so an absent ref never crashes
    the gather (ref: Contracts, OQ3).

    Per-branch merge status is sourced from the MERGED-preferring selection
    (select_pr(nodes, prefer="merged")) — "any fetched node is MERGED" wins — so a
    branch whose work merged reports merged: True even when a NEWER non-merged PR
    sits on the same head ref (the index-0 bug that stranded landed stacks). For
    an all-open/all-closed branch the scan falls back to the active selection, so
    merged stays False exactly as today (ref: AC1, AC2, AC5; Unverified Assumption 3).

    Returns the StackMergeState shape:
        { branch: { merged: bool, prNumber: int|None, state: str|None,
                    mergedByPr: int|None } }
    mergedByPr is purely additive observability — the number of the PR that drove
    the merged: True verdict (None when not merged); no consumer depends on it
    (ref: New Types note, Design Delta §1, Q13)."""
    out = {}
    for b in branches:
        nodes = (graphql_nodes or {}).get(b)
        if not nodes:
            out[b] = {"merged": False, "prNumber": None, "state": None,
                      "mergedByPr": None}
            continue
        node = select_pr(nodes, prefer="merged")
        merged = bool(node.get("merged"))
        out[b] = {
            "merged": merged,
            "prNumber": node.get("number"),
            "state": node.get("state"),
            "mergedByPr": node.get("number") if merged else None,
        }
    return out


def is_stack_fully_merged(merge_state):
    """True only when EVERY real branch's PR is merged (all-or-nothing, AC2).

    An empty stack returns False (nothing merged is not 'fully merged'), and any
    single unmerged branch makes the whole stack not-fully-merged."""
    if not merge_state:
        return False
    return all(entry.get("merged") for entry in merge_state.values())


def slice_numbers(branch_lines):
    """Extract slice numbers from `git branch --list` output lines for a ticket.
    Accepts raw lines like '  RUS-1/slice-2'. Returns a sorted unique int list."""
    nums = set()
    for line in branch_lines:
        m = re.search(r"/slice-(\d+)\s*$", line.strip())
        if m:
            nums.add(int(m.group(1)))
    return sorted(nums)


def count_plan_slices(plan_text):
    """Count the slices a plan DEFINES, from its `## Slice <n>:` headings.

    Slices are MANDATORY — an 'optional'/'gated'/'pending OQx' annotation on a heading
    does NOT reduce the count (optionality is not honored; see qrspi_resolve_state's
    completeness gate). Distinct slice NUMBERS are counted, so a repeated heading for
    the same slice counts once. Deeper subheadings like '### Verify Slice 1' are ignored
    (they are not top-level `## Slice` headings). Pure, so it is unit-testable."""
    nums = set()
    for line in (plan_text or "").splitlines():
        m = re.match(r"^##\s+Slice\s+(\d+)\b", line.strip())
        if m:
            nums.add(int(m.group(1)))
    return len(nums)


def branch_set(branch_lines):
    """Normalize `git branch --list` lines to a set of bare branch names.

    Strips the leading marker git prints: '* ' for the current branch, '+ ' for a
    branch checked out in another worktree (this is the one that bit us — ticket
    branches live in worktrees, so they always carry the '+' marker), or two spaces
    otherwise."""
    out = set()
    for line in branch_lines:
        name = line.strip().lstrip("*+ ").strip()
        if name:
            out.add(name)
    return out


def real_branches(branches, ahead_counts):
    """The branches that both exist AND carry real work — at least one commit ahead
    of trunk.

    Why this gate exists (regression): worktree setup creates a phase branch with
    `git worktree add -b <id>/design ... main`, so a brand-new ticket's design branch
    starts at the SAME commit as trunk with NO artifact commit yet. Plain branch
    existence then made the resolver read the design phase as complete-but-unsubmitted
    and return `submit` for a branch with nothing to submit — the submit worker thrashed
    against an empty branch (no diff to open a PR with) until it hit the tool-call cap.
    An empty placeholder (0 commits ahead of trunk) is NOT a real phase.

    `ahead_counts` maps branch name -> commits-ahead-of-trunk. A branch absent from the
    map, or mapped to 0, is treated as not-real. NOTE: the gate is trunk-relative, so it
    reliably catches an empty *design* branch (whose parent IS trunk). An empty *plan*
    or *slice* branch still carries its ancestors' commits and would read as real — a
    narrower case the commit workers already guard by committing before branching."""
    return {b for b in branches if ahead_counts.get(b, 0) > 0}


# --- subprocess-backed gathering (not unit-tested) -------------------------

def _git_branches(ticket):
    res = subprocess.run(["git", "branch", "--list", "%s/*" % ticket],
                         capture_output=True, text=True)
    return res.stdout.splitlines()


def _commits_ahead(branch, trunk):
    """Commits on `branch` not reachable from `trunk`. Returns 0 on any error (an
    unreadable or odd branch is treated as not-real rather than crashing the gather)."""
    res = subprocess.run(["git", "rev-list", "--count", "%s..%s" % (trunk, branch)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        return 0
    try:
        return int(res.stdout.strip())
    except ValueError:
        return 0


def _git_show(ref_path):
    """`git show <ref>:<path>` text, or "" on any error (missing file or ref). Read-only,
    so an absent artifact/branch degrades to an empty string rather than crashing."""
    res = subprocess.run(["git", "show", ref_path], capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def _file_in_tree(ref, path):
    """True iff `path` exists in `ref`'s committed tree (git cat-file -e). False on any
    error (missing file, missing ref, or no ref given)."""
    if not ref:
        return False
    res = subprocess.run(["git", "cat-file", "-e", "%s:%s" % (ref, path)],
                         capture_output=True, text=True)
    return res.returncode == 0


def _bot_login():
    """The gh-authenticated login (the bot whose replies "address" a comment), or
    "" on any error. Read-only; an unresolvable login degrades to no comment
    detection (commentTargets default []) rather than crashing the gather."""
    res = subprocess.run(["gh", "api", "user", "-q", ".login"],
                         capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else ""


def _query_pr(owner, repo, head):
    res = subprocess.run(
        ["gh", "api", "graphql",
         "-f", "query=%s" % PR_QUERY,
         "-F", "owner=%s" % owner, "-F", "repo=%s" % repo, "-F", "head=%s" % head],
        capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("gh graphql failed for %s: %s" % (head, res.stderr.strip()))
    data = json.loads(res.stdout)
    return data["data"]["repository"]["pullRequests"]["nodes"]


def build_state(owner, repo, ticket, assigned, linear_status, trunk="main",
                blocked_open=False, blocked_by=None):
    lines = _git_branches(ticket)
    branches = branch_set(lines)
    snums = slice_numbers(lines)
    bot = _bot_login()

    # A phase exists only if its branch carries real work (>=1 commit ahead of trunk).
    # This filters out the empty placeholder branch worktree-setup leaves on a fresh
    # ticket — see real_branches() for the regression this prevents.
    ahead = {b: _commits_ahead(b, trunk) for b in branches}
    real = real_branches(branches, ahead)

    def phase_pr(name):
        head = "%s/%s" % (ticket, name)
        exists = head in real
        pr = parse_pr_nodes(_query_pr(owner, repo, head), bot_login=bot) if exists else \
            parse_pr_nodes([], bot_login=bot)
        pr["branchExists"] = exists
        return pr

    real_snums = [n for n in snums if ("%s/slice-%d" % (ticket, n)) in real]
    slices = []
    for n in real_snums:
        head = "%s/slice-%d" % (ticket, n)
        pr = parse_pr_nodes(_query_pr(owner, repo, head), bot_login=bot)
        pr["n"] = n
        slices.append(pr)

    # Completeness signals for the resolver's mandatory-slice gate (read from git refs,
    # no worktree needed — consistent with the rest of this gather):
    #   expectedSlices      how many slices the plan DEFINES (`## Slice <n>:` headings on
    #                       the plan branch; optionality is not honored). 0 if unreadable.
    #   prSummaryCommitted  whether the phase's terminal artifact pr-summary.md is
    #                       committed on the top slice (qrspi-pr writes it only after the
    #                       whole slice loop, so it marks the phase ran to completion).
    top_slice = "%s/slice-%d" % (ticket, max(real_snums)) if real_snums else None
    plan_ref = "%s/plan" % ticket
    plan_src = plan_ref if plan_ref in branches else top_slice
    expected_slices = count_plan_slices(
        _git_show("%s:.qrspi/%s/plan.md" % (plan_src, ticket))) if plan_src else 0
    pr_summary_committed = _file_in_tree(top_slice, ".qrspi/%s/pr-summary.md" % ticket)

    return {
        "ticketId": ticket,
        "assigned": assigned,
        "linearStatus": linear_status,
        "blockedOpen": blocked_open,
        "blockedBy": list(blocked_by or []),
        "phases": {
            "design": phase_pr("design"),
            "plan": phase_pr("plan"),
            "implementation": {
                "branchExists": bool(real_snums),
                "slices": slices,
                "expectedSlices": expected_slices,
                "prSummaryCommitted": pr_summary_committed,
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Gather PR review state for the QRSPI resolver")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--assigned", action="store_true",
                        help="Ticket is assigned to a user (from Linear, supplied by caller)")
    parser.add_argument("--linear-status", default="",
                        help="Current Linear status name (from Linear, supplied by caller)")
    parser.add_argument("--trunk", default="main",
                        help="Trunk branch a phase branch must be ahead of to count as real (default: main)")
    parser.add_argument("--blocked-open", action="store_true",
                        help="At least one open Linear blocker was detected (from Linear, supplied by caller)")
    parser.add_argument("--blocked-by", action="append", default=[],
                        help="Identifier of an open blocker (repeatable; comma-joined values also accepted). "
                             "From Linear, supplied by caller.")
    args = parser.parse_args()

    blocked_by = [tok.strip() for raw in args.blocked_by for tok in raw.split(",") if tok.strip()]
    state = build_state(args.owner, args.repo, args.ticket, args.assigned, args.linear_status,
                        trunk=args.trunk, blocked_open=args.blocked_open, blocked_by=blocked_by)
    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
