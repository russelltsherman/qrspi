#!/usr/bin/env python3
"""Unit tests for qrspi_resolve_state.resolve().

Stdlib-only, assert-based (no pytest dependency) to match the repo's script
conventions. Run with: python3 scripts/qrspi_resolve_state_test.py
Exits 0 if all pass, 1 on the first failure.
"""

import sys

from qrspi_resolve_state import resolve


def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0):
    return {"branchExists": branch, "prExists": pr,
            "reviewDecision": decision, "unresolvedThreads": threads}


def _impl(slices, expected=None, pr_summary=True):
    """Build an implementation phase. Defaults model a COMPLETE phase (pr-summary.md
    committed, expectedSlices == committed) so pre-existing review/land/reset cases
    are unaffected. Pass expected=/pr_summary= to exercise the completeness gate."""
    return {"branchExists": bool(slices), "slices": slices,
            "expectedSlices": len(slices) if expected is None else expected,
            "prSummaryCommitted": pr_summary}


def _slice(n, pr=True, decision="REVIEW_REQUIRED", threads=0):
    return {"n": n, "prExists": pr, "reviewDecision": decision, "unresolvedThreads": threads}


def state(assigned=True, linear="Selected", phases=None,
          blockedOpen=False, blockedBy=None):
    return {"ticketId": "RUS-1", "assigned": assigned, "linearStatus": linear,
            "blockedOpen": blockedOpen, "blockedBy": list(blockedBy or []),
            "phases": phases or {}}


def contains(reason, needle):
    """Substring assertion helper (RD2): True iff `needle` appears in `reason`.
    Lets a case assert each open-blocker identifier is named in the reason without
    pinning the full brittle reason string."""
    return needle in (reason or "")


CASES = []


def case(name, st, expect):
    CASES.append((name, st, expect))


# --- entry gate -------------------------------------------------------------
case("entry: not assigned -> blocked",
     state(assigned=False, linear="Selected", phases={}),
     {"action": "entry_blocked"})

case("entry: assigned but not Selected -> blocked",
     state(assigned=True, linear="Backlog", phases={}),
     {"action": "entry_blocked"})

case("entry: assigned + Selected -> run_design",
     state(assigned=True, linear="Selected", phases={}),
     {"action": "run_design", "phase": "design"})

# --- submit (branch exists, PR missing) -------------------------------------
case("design branch, no PR -> submit",
     state(phases={"design": _phase(branch=True, pr=False, decision=None)}),
     {"action": "submit", "phase": "design"})

# --- wait / revise on active phase ------------------------------------------
case("design PR under review, no threads -> wait",
     state(phases={"design": _phase(decision="REVIEW_REQUIRED")}),
     {"action": "wait", "phase": "design"})

# Unresolved threads WITHOUT a formal change request are no longer an autonomous revise:
# threads can't be resolved here (GitHub mutations 403 on this cross-owned repo), so firing
# revise would loop. They route to `wait` for the reviewer instead.
case("design PR approved but with unresolved threads -> wait (threads can't be auto-resolved)",
     state(phases={"design": _phase(decision="APPROVED", threads=2)}),
     {"action": "wait", "phase": "design"})

# --- advance ----------------------------------------------------------------
case("design approved+clean, no plan -> advance to plan",
     state(phases={"design": _phase(decision="APPROVED", threads=0)}),
     {"action": "advance", "phase": "design", "nextPhase": "plan"})

case("plan approved+clean, no impl -> advance to implementation",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED")}),
     {"action": "advance", "phase": "plan", "nextPhase": "implementation"})

case("design approved but plan under review -> wait on plan (frontier)",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="REVIEW_REQUIRED")}),
     {"action": "wait", "phase": "plan"})

# --- implementation completeness gate (slices mandatory; optionality NOT honored) ---
case("impl 1/2 slices, pr-summary missing -> advance to finish (was wrongly submit)",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, pr=False, decision=None)],
                                           expected=2, pr_summary=False)}),
     {"action": "advance", "phase": "implementation", "nextPhase": "implementation"})

case("impl 2/2 committed but pr-summary not committed -> advance to finish",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1), _slice(2)],
                                           expected=2, pr_summary=False)}),
     {"action": "advance", "phase": "implementation", "nextPhase": "implementation"})

case("impl complete (2/2 + pr-summary), PRs not opened -> submit",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, pr=False, decision=None),
                                            _slice(2, pr=False, decision=None)],
                                           expected=2, pr_summary=True)}),
     {"action": "submit", "phase": "implementation"})

case("impl all slices present + pr-summary but one slice PR missing -> submit",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="APPROVED"),
                                            _slice(2, pr=False, decision=None)],
                                           expected=2, pr_summary=True)}),
     {"action": "submit", "phase": "implementation"})

# --- implementation stack ---------------------------------------------------
case("all slices approved+clean -> land",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="APPROVED"),
                                            _slice(2, decision="APPROVED")])}),
     {"action": "land", "phase": "implementation"})

case("one slice not approved -> wait",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="APPROVED"),
                                            _slice(2, decision="REVIEW_REQUIRED")])}),
     {"action": "wait", "phase": "implementation"})

case("one slice has unresolved threads but no change request -> wait (reviewer resolves)",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="APPROVED", threads=1),
                                            _slice(2, decision="APPROVED")])}),
     {"action": "wait", "phase": "implementation"})

# --- reset (symmetric, decisions 7 & 8) -------------------------------------
case("design changes requested with plan+impl -> reset to design, discard both",
     state(phases={"design": _phase(decision="CHANGES_REQUESTED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="APPROVED")])}),
     {"action": "reset", "resetToPhase": "design",
      "discardPhases": ["plan", "implementation"]})

case("plan changes requested with impl -> reset to plan, discard implementation",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="CHANGES_REQUESTED"),
                   "implementation": _impl([_slice(1, decision="APPROVED")])}),
     {"action": "reset", "resetToPhase": "plan",
      "discardPhases": ["implementation"]})

case("implementation changes requested (top) -> revise in place, no discard",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="CHANGES_REQUESTED")])}),
     {"action": "revise", "phase": "implementation"})

# A formal change request OUTRANKS the threads->wait routing: a frontier PR that is
# CHANGES_REQUESTED *and* carries unresolved threads is still an autonomous revise (the
# worker addresses the feedback and re-requests review; the lingering thread is left to the
# reviewer). Guards against a future reorder that would let threads->wait swallow a CR.
case("impl CHANGES_REQUESTED with unresolved threads (top) -> revise (CR outranks threads)",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="CHANGES_REQUESTED", threads=3)])}),
     {"action": "revise", "phase": "implementation"})

case("design CHANGES_REQUESTED with unresolved threads (top) -> revise (CR outranks threads)",
     state(phases={"design": _phase(decision="CHANGES_REQUESTED", threads=2)}),
     {"action": "revise", "phase": "design"})

case("design AND plan changes requested -> reset to lowest (design)",
     state(phases={"design": _phase(decision="CHANGES_REQUESTED"),
                   "plan": _phase(decision="CHANGES_REQUESTED"),
                   "implementation": _impl([_slice(1, decision="APPROVED")])}),
     {"action": "reset", "resetToPhase": "design",
      "discardPhases": ["plan", "implementation"]})

case("design changes requested, only design exists -> revise (nothing above)",
     state(phases={"design": _phase(decision="CHANGES_REQUESTED")}),
     {"action": "revise", "phase": "design"})


# --- entry-gate blocker gate (RUS-50: respect Linear blockedBy at the entry gate) ---
# Blocked + assigned + Selected, no design branch -> entry_blocked; each open-blocker
# identifier is a substring of reason (RD4), asserted via the _reasonContains key.
case("entry: blocked + Selected -> entry_blocked, reason names the blocker",
     state(assigned=True, linear="Selected", phases={},
           blockedOpen=True, blockedBy=["RUS-99"]),
     {"action": "entry_blocked", "_reasonContains": ["RUS-99"]})

case("entry: blocked + Selected, multiple blockers -> entry_blocked, reason names each",
     state(assigned=True, linear="Selected", phases={},
           blockedOpen=True, blockedBy=["RUS-99", "RUS-100"]),
     {"action": "entry_blocked", "_reasonContains": ["RUS-99", "RUS-100"]})

# Unblocked + assigned + Selected, no design branch -> run_design (gate behaves as before).
case("entry: unblocked + Selected -> run_design",
     state(assigned=True, linear="Selected", phases={},
           blockedOpen=False, blockedBy=[]),
     {"action": "run_design", "phase": "design"})

# In-flight (design branch present) + blocked: the blocker gate only fires at the entry
# gate, so an already-started ticket's decision is UNCHANGED (AC3).
case("in-flight (design branch) + blocked -> unchanged (advance), blocker gate inert",
     state(assigned=True, linear="Selected",
           blockedOpen=True, blockedBy=["RUS-99"],
           phases={"design": _phase(decision="APPROVED", threads=0)}),
     {"action": "advance", "phase": "design", "nextPhase": "plan"})


def run():
    failures = 0
    for name, st, expect in CASES:
        got = resolve(st)
        ok = True
        for key, want in expect.items():
            if key == "_reasonContains":
                # Each needle must be a substring of the decision reason (RD2/RD4).
                missing = [n for n in want if not contains(got.get("reason", ""), n)]
                if missing:
                    print("FAIL: %s\n      reason missing %r\n      full reason: %r"
                          % (name, missing, got.get("reason")))
                    failures += 1
                    ok = False
                    break
                continue
            if got.get(key) != want:
                print("FAIL: %s\n      key %r: expected %r, got %r\n      full: %s"
                      % (name, key, want, got.get(key), got))
                failures += 1
                ok = False
                break
        if ok:
            print("ok: %s" % name)
    print("\n%d passed, %d failed (%d total)"
          % (len(CASES) - failures, failures, len(CASES)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
