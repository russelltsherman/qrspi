#!/usr/bin/env python3
"""Resolve the next QRSPI action from PR review state.

This is the pure-logic heart of the PR-gated lifecycle (see
docs/qrspi-pr-gated-lifecycle-design.md, sections 4 and 5). Given a ticket's
entry-gate state and the per-phase branch/PR review state, it returns the single
action the orchestrator should take. It performs NO I/O of its own — the caller
(the qrspi-work SKILL or the qrspi-batch workflow) gathers the state via gh/gt and
feeds it in, then executes the returned decision. Keeping the decision pure makes
it unit-testable without GitHub or Linear.

Phase order is design -> plan -> implementation. design and plan are single PRs;
implementation is a stack of slice PRs reviewed as a whole.

The implementation phase is COMPLETE only when every planned slice is committed AND
its terminal artifact pr-summary.md is committed on the stack. Slices are mandatory:
optionality is NOT honored (N planned slices means N required). A short or unfinished
stack routes back to `advance -> implementation` to build the rest, never `submit`.

Predicates (design doc §5):
    READY(pr)             reviewDecision == "APPROVED" AND unresolvedThreads == 0
    RESET_TRIGGER(pr)     reviewDecision == "CHANGES_REQUESTED"

Decision actions:
    entry_blocked   not assigned+Selected and no design branch yet -> do nothing
    run_design      entry gate satisfied, no design branch -> build the design phase
    submit          active phase complete, its branch exists but its PR does not -> submit it
    wait            active phase PR exists but is not actionable autonomously: it is
                    awaiting review, OR it carries unresolved review threads but NO formal
                    change request. Unresolved threads cannot be cleared here (GitHub thread
                    mutations 403 on this cross-owned repo — see the gh-cross-account note),
                    so a thread-only PR is left for the reviewer to resolve rather than
                    looping an autonomous revise that can never satisfy the thread gate.
    revise          a frontier phase PR carries a formal CHANGES_REQUESTED AND/OR >=1
                    unaddressed reviewer comment (commentTargets) -> address the feedback
                    in place (AUTONOMOUS). This is the UNIFIED feedback action (revise +
                    the former respond_comment): the worker evaluates each comment's intent
                    and reacts per comment (answer / apply+amend / decline), replying
                    in-thread, and — only when a formal change request is present
                    (changeRequested True) — also addresses the review summary and
                    re-requests review. Re-requesting flips reviewDecision back to
                    REVIEW_REQUIRED, so the next pass returns `wait` instead of re-firing;
                    that decision flip is the only loop-safe termination signal we have
                    (threads can't be auto-resolved). A comment-only PR (no formal change
                    request, even when APPROVED) is answered in place without re-requesting,
                    and is slotted ahead of the wait/APPROVED sinks so an approved-but-
                    commented PR is answered, not waited on. Thread resolution is always
                    left to the reviewer. changeRequested can be True only on the frontier
                    (a non-frontier CHANGES_REQUESTED routes to `reset`, below).
    advance         active phase READY and not the top phase -> build the next phase;
                    OR implementation exists but is unfinished -> build the rest
    land            implementation stack fully READY -> land the whole stack
    reset           an upstream phase has CHANGES_REQUESTED -> discard downstream,
                    return to that phase for revision (automatic discard, decision 10)
"""

import argparse
import json
import sys

PHASES = ["design", "plan", "implementation"]

# The legal action vocabulary the resolver may emit. `revise` is the UNIFIED
# feedback action: it subsumes the former `respond_comment` (RUS-54) so a phase PR
# carrying a formal CHANGES_REQUESTED and/or unaddressed reviewer comments is handled
# by one action that evaluates each comment's intent and re-requests review only when
# a formal change request is present.
ACTIONS = (
    "entry_blocked",
    "run_design",
    "submit",
    "wait",
    "revise",
    "advance",
    "land",
    "reset",
)


def _order(phase):
    return PHASES.index(phase)


def phase_exists(phases, name):
    """A phase exists once its branch exists. implementation 'exists' once any
    slice branch exists."""
    return bool(phases.get(name, {}).get("branchExists", False))


def _pr_ready(pr):
    return pr.get("reviewDecision") == "APPROVED" and pr.get("unresolvedThreads", 0) == 0


def _pr_changes_requested(pr):
    return pr.get("reviewDecision") == "CHANGES_REQUESTED"


def _impl_slices(phases):
    return phases.get("implementation", {}).get("slices", []) or []


def phase_changes_requested(phases, name):
    """True if phase `name` carries a formal CHANGES_REQUESTED. For implementation,
    a change request on ANY slice PR counts (the stack is reviewed as a whole)."""
    if name == "implementation":
        return any(_pr_changes_requested(s) for s in _impl_slices(phases))
    return _pr_changes_requested(phases.get(name, {}))


def design_already_landed(state):
    """True only when a real merge signal says the design phase has already landed
    (its branch pruned), even though `branchExists` is False — so the entry gate must
    NOT mistake a merged-and-pruned design for an un-started ticket.

    Strictly additive: returns True ONLY on a genuine merge signal. The signal is the
    per-phase `phases.design.merged` flag (populated by build_state when an absent
    design head has a MERGED PR — Slice 2), or, if present, a stack-level
    `started`/`merged` verdict. A genuinely un-started ticket (no merge signal) yields
    False, so its entry-gate decision is unchanged (ref: design.md Decision 1 Option A,
    AC2 constraint, Risk row 1)."""
    phases = state.get("phases", {})
    if phases.get("design", {}).get("merged"):
        return True
    stack = state.get("stack", {})
    if isinstance(stack, dict) and stack.get("merged"):
        return True
    return bool(state.get("merged"))


def phase_comment_targets(phases, name):
    """The unaddressed reviewer comments carried by phase `name`. For implementation,
    the comment targets across ALL slice PRs are aggregated (the stack is reviewed as
    a whole). Empty list when none (ref: AC1, structure Contracts respond_comment)."""
    if name == "implementation":
        out = []
        for s in _impl_slices(phases):
            out.extend(s.get("commentTargets") or [])
        return out
    return phases.get(name, {}).get("commentTargets") or []


def resolve(state):
    """Pure decision function. Returns a decision dict (see module docstring)."""
    phases = state.get("phases", {})
    existing = [p for p in PHASES if phase_exists(phases, p)]

    def decision(action, **kw):
        out = {
            "action": action,
            "phase": kw.get("phase"),
            "nextPhase": kw.get("nextPhase"),
            "resetToPhase": kw.get("resetToPhase"),
            "discardPhases": kw.get("discardPhases", []),
            "commentTargets": kw.get("commentTargets", []),
            "changeRequested": kw.get("changeRequested", False),
            "reason": kw.get("reason", ""),
        }
        return out

    # 1. Entry gate — nothing exists yet. Linear is read ONLY here.
    #
    # A design branch absent because the design PR already MERGED (branch pruned) is NOT
    # an un-started ticket: the stack is mid-land with upper slice PRs still open. Consult
    # the merge signal first and, when design has already landed, fall through to the
    # active-phase/`land` logic below rather than declaring entry_blocked/run_design — the
    # bug this slice fixes (ref: design.md Decision 1 Option A, §Delta; RUS-69). The
    # fall-through is safe only while some other phase still exists (an open slice keeps
    # `implementation` in `existing`); if the merge signal fired but `existing` is empty,
    # there is no active phase to land, so the entry gate still applies.
    if "design" not in existing and not (design_already_landed(state) and existing):
        if state.get("assigned") and state.get("linearStatus") == "Selected":
            # Even a satisfied entry gate is held when Linear reports an OPEN blocker
            # (blockedBy relation). Fold every open-blocker identifier into the reason so
            # the held ticket names what it waits on (RD4).
            if state.get("blockedOpen"):
                blockers = state.get("blockedBy") or []
                joined = ", ".join(blockers) if blockers else "an unnamed blocker"
                return decision("entry_blocked",
                                reason="Entry gate satisfied (assigned + Selected) but blocked by "
                                       "open Linear blocker(s): %s; held until they close." % joined)
            return decision("run_design", phase="design",
                            reason="Entry gate satisfied (assigned + Selected); no design branch yet.")
        return decision("entry_blocked",
                        reason="No design branch and ticket is not assigned+Selected; nothing begins.")

    # 2. Reset check — a CHANGES_REQUESTED on a NON-frontier phase discards everything
    # downstream and returns there. Only the lowest CHANGES_REQUESTED phase matters; if it
    # has nothing downstream it IS the frontier and falls through to the unified feedback
    # handler below (addressed in place rather than reset).
    cr = [p for p in existing if phase_changes_requested(phases, p)]
    if cr:
        k = min(cr, key=_order)
        above = [p for p in existing if _order(p) > _order(k)]
        if above:
            return decision("reset", resetToPhase=k, discardPhases=above,
                            reason="Changes requested on %s; discard downstream (%s) and return to %s."
                                   % (k, ", ".join(above), k))
        # else: a frontier change request — addressed in place by the unified handler below.

    # 2b. Unified feedback handler (revise + the former respond_comment, merged). The
    # lowest existing phase carrying a frontier CHANGES_REQUESTED OR >=1 unaddressed
    # reviewer comment is addressed IN PLACE by the revise worker: it evaluates each
    # comment's intent (answer / apply+amend / decline) and replies in-thread, and — only
    # when a formal change request is present (changeRequested) — also addresses the review
    # summary and re-requests review (which clears the CHANGES_REQUESTED). A non-frontier CR
    # never reaches here (it reset above), so changeRequested is True only on the frontier.
    # Runs AHEAD of the wait/APPROVED sinks so an approved-but-commented PR is answered, not
    # waited on, and fires even when the PR is APPROVED (ref: AC1; RUS-54; unify decision).
    feedback = [p for p in existing
                if phase_changes_requested(phases, p) or phase_comment_targets(phases, p)]
    if feedback:
        f = min(feedback, key=_order)
        cr_present = phase_changes_requested(phases, f)
        targets = phase_comment_targets(phases, f)
        if cr_present and targets:
            what = "a change request and unaddressed reviewer comment(s)"
        elif cr_present:
            what = "a change request"
        else:
            what = "unaddressed reviewer comment(s)"
        return decision("revise", phase=f,
                        commentTargets=targets,
                        changeRequested=cr_present,
                        reason="%s PR has %s; address in place%s." % (
                            f, what, " and re-request review" if cr_present else ""))

    # 3. Active phase = highest existing phase.
    active = max(existing, key=_order)

    if active != "implementation":
        pr = phases[active]
        if not pr.get("prExists"):
            return decision("submit", phase=active,
                            reason="%s branch exists but its PR has not been submitted." % active)
        if pr.get("unresolvedThreads", 0) > 0:
            # The reset check above already handled CHANGES_REQUESTED, so this is a PR with
            # lingering review threads but NO formal change request. Threads cannot be
            # resolved here (GitHub mutations 403 on this cross-owned repo), so an autonomous
            # revise could never clear the thread gate and would loop. Leave it for the
            # reviewer to resolve -> wait.
            return decision("wait", phase=active,
                            reason="%s PR has %d unresolved review thread(s) and no change "
                                   "request; left for the reviewer to resolve (threads cannot "
                                   "be auto-resolved here)." % (active, pr["unresolvedThreads"]))
        if pr.get("reviewDecision") != "APPROVED":
            return decision("wait", phase=active,
                            reason="%s PR awaiting review (reviewDecision=%s)."
                                   % (active, pr.get("reviewDecision")))
        nxt = PHASES[_order(active) + 1]
        return decision("advance", phase=active, nextPhase=nxt,
                        reason="%s PR approved and clean; advance to %s." % (active, nxt))

    # active == implementation: reviewed as a whole stack.
    #
    # COMPLETENESS GATE — slices are MANDATORY; optionality is NOT honored. The phase
    # is "done" only when every planned slice is committed AND its terminal artifact
    # pr-summary.md is committed on the stack (qrspi-pr writes pr-summary.md only after
    # the whole slice loop, so its presence means the phase ran to the end). A short
    # stack (fewer committed slice branches than the plan defines) or a missing
    # pr-summary means the phase is unfinished, so route back to advance->implementation
    # to build the rest (doImplementation resumes idempotently, skipping alreadyCommitted
    # slices). This is what separates "implementation in progress" from "implementation
    # done, PR(s) just not opened": the old code conflated them and emitted `submit` for
    # a half-built stack, whose finalize then hard-stopped on the absent pr-summary.md.
    impl = phases.get("implementation", {})
    slices = _impl_slices(phases)
    committed = len(slices)
    expected = impl.get("expectedSlices", committed)
    pr_summary = impl.get("prSummaryCommitted", False)
    if committed < expected or not pr_summary:
        return decision("advance", phase="implementation", nextPhase="implementation",
                        reason="Implementation incomplete (%d/%d slices committed, "
                               "pr-summary.md %s); finish the remaining work."
                               % (committed, expected,
                                  "committed" if pr_summary else "missing"))
    # Complete: every planned slice is committed and pr-summary.md is in the stack. Now
    # gate on PR existence/review exactly as before.
    if any(not s.get("prExists") for s in slices):
        return decision("submit", phase="implementation",
                        reason="Implementation complete; open the slice PR(s).")
    if any(s.get("unresolvedThreads", 0) > 0 for s in slices):
        # As in the design/plan case: a slice carrying CHANGES_REQUESTED is caught by the
        # reset check above and routed to revise. Reaching here means unresolved threads with
        # no change request, which we cannot auto-resolve, so leave them for the reviewer.
        return decision("wait", phase="implementation",
                        reason="One or more slice PRs have unresolved review threads and no "
                               "change request; left for the reviewer to resolve.")
    if any(s.get("reviewDecision") != "APPROVED" for s in slices):
        return decision("wait", phase="implementation",
                        reason="Not all slice PRs are approved yet.")
    return decision("land", phase="implementation",
                    reason="All phases approved and clean; land the whole stack bottom-up.")


def main():
    parser = argparse.ArgumentParser(description="Resolve the next QRSPI action from PR review state")
    parser.add_argument("--state", help="Path to a JSON state file. Reads stdin if omitted.")
    args = parser.parse_args()

    raw = open(args.state).read() if args.state else sys.stdin.read()
    state = json.loads(raw)

    out = resolve(state)
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
