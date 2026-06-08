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
    pullRequests(headRefName:$head, first:5, states:OPEN, orderBy:{field:CREATED_AT, direction:DESC}) {
      nodes {
        number
        reviewDecision
        reviewThreads(first:100) { nodes { isResolved } }
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


def parse_pr_nodes(nodes):
    """Reduce the GraphQL pullRequests.nodes list for one head branch to the
    normalized PR shape. No open PR -> prExists False.

    GitHub's reviewDecision is null until a review exists; we normalize null to
    None so the resolver treats it as 'awaiting review' (not approved)."""
    if not nodes:
        return {"prExists": False, "number": None,
                "reviewDecision": None, "unresolvedThreads": 0}
    node = nodes[0]
    threads = (node.get("reviewThreads") or {}).get("nodes", [])
    return {
        "prExists": True,
        "number": node.get("number"),
        "reviewDecision": node.get("reviewDecision"),
        "unresolvedThreads": unresolved_thread_count(threads),
    }


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


def build_state(owner, repo, ticket, assigned, linear_status, trunk="main"):
    lines = _git_branches(ticket)
    branches = branch_set(lines)
    snums = slice_numbers(lines)

    # A phase exists only if its branch carries real work (>=1 commit ahead of trunk).
    # This filters out the empty placeholder branch worktree-setup leaves on a fresh
    # ticket — see real_branches() for the regression this prevents.
    ahead = {b: _commits_ahead(b, trunk) for b in branches}
    real = real_branches(branches, ahead)

    def phase_pr(name):
        head = "%s/%s" % (ticket, name)
        exists = head in real
        pr = parse_pr_nodes(_query_pr(owner, repo, head)) if exists else \
            {"prExists": False, "number": None, "reviewDecision": None, "unresolvedThreads": 0}
        pr["branchExists"] = exists
        return pr

    real_snums = [n for n in snums if ("%s/slice-%d" % (ticket, n)) in real]
    slices = []
    for n in real_snums:
        head = "%s/slice-%d" % (ticket, n)
        pr = parse_pr_nodes(_query_pr(owner, repo, head))
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
    args = parser.parse_args()

    state = build_state(args.owner, args.repo, args.ticket, args.assigned, args.linear_status,
                        trunk=args.trunk)
    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
