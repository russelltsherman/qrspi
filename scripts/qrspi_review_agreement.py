#!/usr/bin/env python3
"""Pure agreement reducer for the QRSPI on-demand review panels (RUS-89, AC2).

Why this exists
---------------
The `/review-*` commands run a read-only review panel over a phase artifact and
emit a panel `{pass}` verdict, then compare it against the human's PR
`reviewDecision` (the GitHub review state) to surface whether the panel and the
human AGREE. That comparison is the only piece worth unit-testing, so it lives
here as a pure, stdlib-only function with no agent / IO / git coupling —
mirroring `qrspi_critic_synthesize.py` / `qrspi_critic_metrics.py` (ref:
structure.md §Contracts, design.md Decision 4, §Delta).

Record shape (ref: structure.md §New Types `AgreementResult`):
  AgreementResult {
    panelVerdict: "pass" | "fail",
    humanVerdict: "approved" | "changes_requested" | "commented" | null,
    agreement:    "agree" | "disagree" | "pending"
  }

Mapping rules (ref: design.md Decision 4):
  - panelVerdict: True -> "pass", False -> "fail".
  - humanVerdict: normalize the GitHub reviewDecision string (case-insensitive)
    "APPROVED"           -> "approved"
    "CHANGES_REQUESTED"  -> "changes_requested"
    "COMMENTED"          -> "commented"
    None / absent        -> None        (no human review yet)
    anything else        -> None        (unknown decision: no decisive verdict)
  - agreement:
    None  human decision        -> "pending"  (never a false disagreement)
    "commented"                 -> "pending"  (a comment is NOT a decisive verdict)
    "agree"  when (pass + approved) or (fail + changes_requested)
    "disagree" otherwise (pass + changes_requested, fail + approved)

Pure: no IO, no subprocess. NEVER raises — an unrecognized human decision is
treated as "no decisive verdict" (humanVerdict None, agreement "pending") rather
than an error, so the record builder can always proceed.
"""

PANEL_PASS = "pass"
PANEL_FAIL = "fail"

HUMAN_APPROVED = "approved"
HUMAN_CHANGES_REQUESTED = "changes_requested"
HUMAN_COMMENTED = "commented"

AGREE = "agree"
DISAGREE = "disagree"
PENDING = "pending"

# GitHub reviewDecision string -> normalized humanVerdict (case-insensitive lookup).
_DECISION_MAP = {
    "approved": HUMAN_APPROVED,
    "changes_requested": HUMAN_CHANGES_REQUESTED,
    "commented": HUMAN_COMMENTED,
}


def compute(panel_pass, human_decision):
    """Reduce a panel verdict + a human reviewDecision to an AgreementResult.

    Args:
        panel_pass: the panel's boolean verdict (True -> pass, False -> fail).
        human_decision: the GitHub PR reviewDecision string (e.g. "APPROVED",
            "CHANGES_REQUESTED", "COMMENTED"), or None when no human review
            exists yet. Case-insensitive; an unrecognized value normalizes to
            None (no decisive verdict).

    Returns:
        AgreementResult dict {panelVerdict, humanVerdict, agreement}.

    Pure: never raises.
    """
    panel_verdict = PANEL_PASS if panel_pass else PANEL_FAIL

    human_verdict = None
    if isinstance(human_decision, str):
        human_verdict = _DECISION_MAP.get(human_decision.strip().lower())

    agreement = _derive_agreement(panel_pass, human_verdict)

    return {
        "panelVerdict": panel_verdict,
        "humanVerdict": human_verdict,
        "agreement": agreement,
    }


def _derive_agreement(panel_pass, human_verdict):
    """Derive the agreement category. Pure.

    No decisive human verdict (None or "commented") -> "pending" (never a false
    disagreement). Otherwise "agree" when the panel and human concur on
    pass<->approved / fail<->changes_requested, else "disagree".
    """
    if human_verdict is None or human_verdict == HUMAN_COMMENTED:
        return PENDING
    if panel_pass and human_verdict == HUMAN_APPROVED:
        return AGREE
    if (not panel_pass) and human_verdict == HUMAN_CHANGES_REQUESTED:
        return AGREE
    return DISAGREE


if __name__ == "__main__":
    # Smoke block: read panel_pass from argv (default "true") and a human decision
    # from a second optional arg (default None), then print the compute result as
    # JSON. `python3 scripts/qrspi_review_agreement.py` runs the pass+None smoke,
    # which must print agreement "pending" (ref: structure.md Slice 1 verify).
    import json
    import sys

    arg_pass = sys.argv[1] if len(sys.argv) > 1 else "true"
    panel_pass = str(arg_pass).strip().lower() in ("1", "true", "pass", "yes")
    human_decision = sys.argv[2] if len(sys.argv) > 2 else None

    json.dump(compute(panel_pass, human_decision), sys.stdout)
    print()
