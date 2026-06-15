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
        commits(last:1) {
          nodes {
            commit {
              message
              statusCheckRollup {
                state
                contexts(first:100) {
                  nodes {
                    __typename
                    ... on CheckRun { name conclusion detailsUrl }
                    ... on StatusContext { context state targetUrl }
                  }
                }
              }
            }
          }
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


def _head_commit(pr_node):
    """The head (last) commit node from a PR's commits(last:1) selection, or {} if
    absent. Guarded like unresolved_thread_count so a missing commits selection (e.g.
    an empty parse, or a hermetic test node without commits) degrades to {} rather
    than crashing."""
    commits = ((pr_node or {}).get("commits") or {}).get("nodes") or []
    return (commits[-1] or {}).get("commit") or {} if commits else {}


def check_rollup_state(pr_node):
    """Normalize a PR head commit's statusCheckRollup.state to a CiState string.

    Pure (unit-tested). Maps the GitHub StatusState enum:
        SUCCESS              -> "green"
        FAILURE | ERROR      -> "red"
        PENDING | EXPECTED   -> "pending"
        null / absent / any  -> "none"
    A null rollup (no checks configured) or an absent commits/rollup selection
    (a committed-but-not-yet-PR'd slice, or an empty parse) yields "none". Guarded
    against missing keys exactly like unresolved_thread_count (ref: Contracts;
    structure §New Types CiState). `pr_node` is the parsed GraphQL PR node."""
    rollup = _head_commit(pr_node).get("statusCheckRollup") or {}
    state = rollup.get("state")
    if state == "SUCCESS":
        return "green"
    if state in ("FAILURE", "ERROR"):
        return "red"
    if state in ("PENDING", "EXPECTED"):
        return "pending"
    return "none"


_CI_REVISE_ATTEMPT_RE = re.compile(r"^CI-Revise-Attempt:\s*(\d+)\s*$", re.MULTILINE)


def ci_revise_attempt(message):
    """Parse the `CI-Revise-Attempt: N` trailer from a head-commit message -> int.

    Pure (unit-tested). The durable, observable-from-GitHub consecutive-red-CI
    counter (Decision 2 Option C). Absent or malformed (non-integer / no trailer)
    -> 0; guarded like the other parsers so a None/empty message yields 0. If the
    trailer appears more than once the last occurrence wins (mirroring git trailer
    semantics). `message` is the head-commit message string (ref: Contracts;
    structure §New Types CI-Revise-Attempt)."""
    matches = _CI_REVISE_ATTEMPT_RE.findall(message or "")
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except (TypeError, ValueError):
        return 0


def _failing_checks(pr_node):
    """The failing check entries from a PR head commit's statusCheckRollup contexts,
    as a list of {name, detailsUrl} dicts. Pure; guarded for absent selections.

    A CheckRun is failing iff its conclusion is FAILURE/ERROR/TIMED_OUT/CANCELLED/
    STARTUP_FAILURE/ACTION_REQUIRED; a StatusContext is failing iff its state is
    FAILURE/ERROR. The check name comes from CheckRun.name or StatusContext.context;
    the URL from CheckRun.detailsUrl or StatusContext.targetUrl. Empty unless there
    are failing checks (the populated parse only attaches this when ciState=="red")."""
    rollup = _head_commit(pr_node).get("statusCheckRollup") or {}
    nodes = (rollup.get("contexts") or {}).get("nodes") or []
    out = []
    for c in nodes:
        c = c or {}
        typename = c.get("__typename")
        if typename == "CheckRun":
            if (c.get("conclusion") or "") in (
                    "FAILURE", "ERROR", "TIMED_OUT", "CANCELLED",
                    "STARTUP_FAILURE", "ACTION_REQUIRED"):
                out.append({"name": c.get("name"), "detailsUrl": c.get("detailsUrl")})
        elif typename == "StatusContext":
            if (c.get("state") or "") in ("FAILURE", "ERROR"):
                out.append({"name": c.get("context"), "detailsUrl": c.get("targetUrl")})
    return out


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
                "commentTargets": [],
                "ciState": "none", "ciFailingChecks": [], "ciReviseAttempt": 0}
    threads = (node.get("reviewThreads") or {}).get("nodes", [])
    targets = unaddressed_reviewer_comments(node, bot_login) if bot_login else []
    # Additive CI fields (ref: structure §Modified Types, plan §1.6-1.7). ciState is
    # the normalized rollup; ciFailingChecks is empty unless red; ciReviseAttempt is
    # the EFFECTIVE consecutive-red counter — the parsed trailer forced to 0 whenever
    # ciState != "red" (the not-red->0 reset). Inert to consumers that don't read them.
    ci_state = check_rollup_state(node)
    failing = _failing_checks(node) if ci_state == "red" else []
    if ci_state == "red":
        attempt = ci_revise_attempt(_head_commit(node).get("message"))
    else:
        attempt = 0
    return {
        "prExists": True,
        "number": node.get("number"),
        "reviewDecision": node.get("reviewDecision"),
        "unresolvedThreads": unresolved_thread_count(threads),
        "merged": bool(node.get("merged")),
        "state": node.get("state"),
        "mergedAt": node.get("mergedAt"),
        "commentTargets": targets,
        "ciState": ci_state,
        "ciFailingChecks": failing,
        "ciReviseAttempt": attempt,
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


def branch_present(branch, ahead, merged_pr, exists_locally):
    """Whether a phase branch should report branchExists: true.

    Distinguishes the two reasons a branch can be 0 commits ahead of trunk:

      * 0 ahead because EMPTY placeholder — worktree setup created the branch at
        trunk with no artifact commit yet (the regression real_branches() guards;
        see its docstring). Still rejected: no real phase has run.
      * 0 ahead because the work LANDED — the branch's commits merged into trunk,
        so rev-list main..<branch> is now 0 even though a real phase ran. This is
        the partially-landed-stack case (RUS-67): the resolver was emitting a
        spurious entry_blocked "No design branch" because the landed design branch
        read as absent. Now reported present (ref: design.md Decision 3A, OQ2).

    A branch is present iff it carries real work (>=1 commit ahead of trunk) OR it
    has a positive merged-PR signal — `merged_pr` is truthy when GitHub reports a
    MERGED PR for the head ref (the merged-PR signal from stack_merge_state /
    select_pr(prefer="merged"), the merged-ancestor source of truth). The merged-PR
    signal is the discriminator between the two 0-ahead cases.

    `exists_locally` (the branch is still in `git branch --list`) is accepted for
    contract symmetry but is deliberately NOT a sufficient positive signal on its
    own: the empty placeholder ALSO exists locally, so admitting a 0-ahead branch on
    bare local existence would re-admit it (the explicit Risk "re-admits the
    empty-placeholder design branch"). Presence therefore gates on real work or a
    merged-PR signal only; exists_locally is retained as a documented no-op input so
    a future caller can tighten the gate without a signature change."""
    if ahead > 0:
        return True
    if merged_pr:
        return True
    return False


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

    real_snums = [n for n in snums if ("%s/slice-%d" % (ticket, n)) in real]

    # The ticket "looks in-flight" when at least one slice branch still carries live
    # work. In that window an absent/pruned PHASE head (design/plan) is most likely a
    # head GitHub reaped after its PR merged — not an un-started ticket — so we re-query
    # it for merge state (Decision 2, Risk row 3). The guard bounds `gh` calls: a
    # present branch is queried as before, and a NOT-in-flight ticket (no live slices)
    # never fires the extra re-query.
    looks_in_flight = bool(real_snums)

    def phase_pr(name):
        head = "%s/%s" % (ticket, name)
        real_work = head in real          # >=1 commit ahead of trunk (a live phase)
        local = head in branches          # still in `git branch --list`
        # Query GitHub when the branch carries real work, still exists locally, or the
        # ticket looks in-flight (a live slice implies an absent phase head was reaped
        # after its PR merged — re-query it for merge state). A not-in-flight ticket
        # with no local/real phase branch never queries, bounding gh calls.
        # (RUS-67 landed-ancestor signal × RUS-69 pruned-head re-query.)
        if real_work or local or looks_in_flight:
            nodes = _query_pr(owner, repo, head)
        else:
            nodes = []
        merged_node = select_pr(nodes, prefer="merged")
        merged_pr = bool(merged_node and merged_node.get("merged"))
        if real_work or local:
            # Branch is known to git. Parse its PR and let branch_present decide
            # presence: real work OR a landed-ancestor merge signal marks it present,
            # while a 0-ahead empty placeholder is rejected — so a partially-landed
            # stack stops emitting a spurious entry_blocked "No design branch"
            # (RUS-67, design.md Decision 3A, OQ2).
            pr = parse_pr_nodes(nodes, bot_login=bot)
            pr["branchExists"] = branch_present(
                head, ahead.get(head, 0), merged_pr, local)
        elif looks_in_flight:
            # Absent/pruned head while slices are live: GitHub reaped it after its PR
            # merged. The GraphQL query is by headRefName, so it still returns nodes
            # for a deleted ref. Build from an empty parse and inject only the merged
            # fields via select_pr(prefer="merged") ("any MERGED node wins") to avoid
            # the index-0 masking class, mirroring qrspi_cleanup.py (RUS-69 Decision 2,
            # Risk row 5). The head is gone from git, so branchExists stays False and
            # the resolver reads the merge signal from phases.<phase>.merged instead.
            pr = parse_pr_nodes([], bot_login=bot)
            if merged_node is not None and merged_node.get("merged") is True:
                pr["merged"] = True
                pr["number"] = merged_node.get("number")
                pr["state"] = merged_node.get("state")
                pr["mergedAt"] = merged_node.get("mergedAt")
            pr["branchExists"] = False
        else:
            pr = parse_pr_nodes([], bot_login=bot)
            pr["branchExists"] = False
        return pr

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

    design_phase = phase_pr("design")
    plan_phase = phase_pr("plan")

    # Stack-level started/merged verdict (Decision 2 Option B): a clean read for the
    # resolver's entry gate, aggregated from the per-phase merge signals. `started` is
    # True once any work exists (a real phase branch or a re-queried merged head);
    # `merged` mirrors the design phase's merge signal (the entry gate keys on design).
    # design_already_landed already reads phases.design.merged directly, so this verdict
    # is additive observability — no consumer is forced onto it.
    stack_started = bool(real) or bool(design_phase.get("merged")) or bool(plan_phase.get("merged"))
    stack_merged = bool(design_phase.get("merged"))

    return {
        "ticketId": ticket,
        "assigned": assigned,
        "linearStatus": linear_status,
        "blockedOpen": blocked_open,
        "blockedBy": list(blocked_by or []),
        "stack": {
            "started": stack_started,
            "merged": stack_merged,
        },
        "phases": {
            "design": design_phase,
            "plan": plan_phase,
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
