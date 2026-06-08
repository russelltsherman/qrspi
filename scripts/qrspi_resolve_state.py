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
    wait            active phase PR exists, not approved, no unresolved threads
    revise          active phase PR has unresolved threads to address (manual)
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
            "reason": kw.get("reason", ""),
        }
        return out

    # 1. Entry gate — nothing exists yet. Linear is read ONLY here.
    if "design" not in existing:
        if state.get("assigned") and state.get("linearStatus") == "Selected":
            return decision("run_design", phase="design",
                            reason="Entry gate satisfied (assigned + Selected); no design branch yet.")
        return decision("entry_blocked",
                        reason="No design branch and ticket is not assigned+Selected; nothing begins.")

    # 2. Reset check — lowest existing phase carrying CHANGES_REQUESTED wins.
    cr = [p for p in existing if phase_changes_requested(phases, p)]
    if cr:
        k = min(cr, key=_order)
        above = [p for p in existing if _order(p) > _order(k)]
        if above:
            return decision("reset", resetToPhase=k, discardPhases=above,
                            reason="Changes requested on %s; discard downstream (%s) and return to %s."
                                   % (k, ", ".join(above), k))
        # k is the highest existing phase: nothing to discard, revise in place.
        return decision("revise", phase=k,
                        reason="Changes requested on %s (top phase); revise in place." % k)

    # 3. Active phase = highest existing phase.
    active = max(existing, key=_order)

    if active != "implementation":
        pr = phases[active]
        if not pr.get("prExists"):
            return decision("submit", phase=active,
                            reason="%s branch exists but its PR has not been submitted." % active)
        if pr.get("unresolvedThreads", 0) > 0:
            return decision("revise", phase=active,
                            reason="%s PR has %d unresolved review thread(s) to address."
                                   % (active, pr["unresolvedThreads"]))
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
        return decision("revise", phase="implementation",
                        reason="One or more slice PRs have unresolved review threads.")
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
