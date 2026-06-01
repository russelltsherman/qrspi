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


# --- subprocess-backed gathering (not unit-tested) -------------------------

def _git_branches(ticket):
    res = subprocess.run(["git", "branch", "--list", "%s/*" % ticket],
                         capture_output=True, text=True)
    return res.stdout.splitlines()


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


def build_state(owner, repo, ticket, assigned, linear_status):
    lines = _git_branches(ticket)
    branches = branch_set(lines)
    snums = slice_numbers(lines)

    def phase_pr(name):
        head = "%s/%s" % (ticket, name)
        exists = head in branches
        pr = parse_pr_nodes(_query_pr(owner, repo, head)) if exists else \
            {"prExists": False, "number": None, "reviewDecision": None, "unresolvedThreads": 0}
        pr["branchExists"] = exists
        return pr

    slices = []
    for n in snums:
        head = "%s/slice-%d" % (ticket, n)
        pr = parse_pr_nodes(_query_pr(owner, repo, head))
        pr["n"] = n
        slices.append(pr)

    return {
        "ticketId": ticket,
        "assigned": assigned,
        "linearStatus": linear_status,
        "phases": {
            "design": phase_pr("design"),
            "plan": phase_pr("plan"),
            "implementation": {"branchExists": bool(snums), "slices": slices},
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
    args = parser.parse_args()

    state = build_state(args.owner, args.repo, args.ticket, args.assigned, args.linear_status)
    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
