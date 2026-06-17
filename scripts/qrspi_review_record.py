#!/usr/bin/env python3
"""Pure agreement-extended ledger record builder for on-demand review (RUS-89, AC2).

Why this exists
---------------
The `/review-*` commands append a ledger row per reviewed phase that is a
SUPERSET of the batch critic's `CriticStepMetrics`: the same
`{phase, rounds, terminalAction}` base PLUS an `agreement` block (the
AgreementResult from `qrspi_review_agreement.compute`) and a
`mode: "on-demand-review"` discriminator that lets ledger consumers tell
on-demand review rows apart from the batch panel's rows (ref: structure.md
§New Types `ReviewRecord`, design.md Decision 3).

This reuses `qrspi_critic_metrics.build_record` for the base shape rather than
re-deriving the `rounds` reduction — that builder takes the per-lens/per-round
VERDICTS (each {lens, pass, findings}) and derives the
`{lens, pass, findingsCount}` rounds itself; it does NOT accept a pre-built
rounds list. So this reducer forwards the round verdicts (plus terminalAction
and phase) to it, then wraps the returned record with the `agreement` block and
`mode` (ref: plan.md Slice 1 §4 signature reconciliation).

Record shape (ref: structure.md §New Types `ReviewRecord`):
  ReviewRecord {
    phase: str,
    rounds: [{lens, pass, findingsCount}],
    terminalAction: str,
    agreement: AgreementResult,
    mode: "on-demand-review"
  }

Pure: no IO, no subprocess. Raises only `ValueError` on an invalid
terminalAction (propagated verbatim from the underlying builder, which is
fail-closed).
"""

import os
import sys

# Sibling import of the base builder, robust to invocation cwd (mirrors the
# other scripts' self-locating import preamble).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qrspi_critic_metrics  # noqa: E402

MODE_ON_DEMAND_REVIEW = "on-demand-review"


def build_record(phase, rounds, terminal_action, agreement):
    """Build the agreement-extended ReviewRecord.

    Args:
        phase: the phase label this review row belongs to (e.g. "design").
        rounds: the per-lens/per-round VERDICT list (each {lens, pass, findings})
            forwarded to `qrspi_critic_metrics.build_record`, which derives the
            `{lens, pass, findingsCount}` rounds shape. (Named `rounds` to match
            the Contract; it is the verdict list the base builder reduces.)
        terminal_action: one of the base builder's VALID_TERMINAL_ACTIONS;
            `ValueError` otherwise (fail-closed, propagated).
        agreement: the AgreementResult dict from `qrspi_review_agreement.compute`,
            embedded verbatim.

    Returns:
        ReviewRecord dict — the base `{phase, rounds, terminalAction}` plus the
        embedded `agreement` block and `mode: "on-demand-review"`.

    Pure: raises only `ValueError` on an invalid terminal_action.
    """
    record = qrspi_critic_metrics.build_record(
        rounds, terminal_action, phase=phase)
    record["agreement"] = agreement
    record["mode"] = MODE_ON_DEMAND_REVIEW
    return record
