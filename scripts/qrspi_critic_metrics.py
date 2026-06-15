#!/usr/bin/env python3
"""Pure reducer for QRSPI critic-step metrics (RUS-77, AC-INSTR).

Why this exists
---------------
A single critic *step* — one edge-critic loop in ``runCriticLoop`` OR one panel
loop in ``runCriticPanelLoop`` (``qrspi-batch.js:710-773``) — runs N rounds of M
per-lens verdicts and then terminates. To make the critic effective-or-not
question measurable (AC-INSTR), each terminated step must be reduced to ONE
canonical machine-readable record (``CriticStepMetrics``) that a durable ledger
can carry. That reduction is the only piece of the instrumentation worth
unit-testing, so it lives here as a pure, stdlib-only function with no agent / IO
/ git coupling — mirroring ``qrspi_critic_synthesize.py`` (ref: structure.md
§Contracts, Decision 1, Option A).

Record shapes (ref: structure.md §New Types):
  - ``CriticRoundRecord  { lens: str, pass: bool, findingsCount: int }``
  - ``CriticStepMetrics  { phase: str, rounds: CriticRoundRecord[],
                           terminalAction: str, tokensIn?: int, tokensOut?: int }``

``terminalAction`` is validated against the four ACTUAL loop terminations in
``runCriticLoop`` / ``runCriticPanelLoop`` (``qrspi-batch.js:710-773``):
  - ``converged``   — decision.action == 'converged' (:743)
  - ``cap_reached`` — decision.action == 'cap_reached' (:747)
  - ``exhausted``   — the defensive ``ok:true`` tail, loop ran out of rounds
                      without an explicit decision return (:773)
  - ``aborted``     — any ``ok:false`` early return (verdict / decision / reviser
                      failure, :728/:739/:766) — so aborted steps STILL emit a
                      record and AC-INSTR base rates are not biased toward
                      successful terminations.
``revise`` is deliberately NOT in the enum: it is a mid-loop continuation (:749)
after which the loop re-critiques, never a terminal state, so a record is only
ever built once the loop has actually terminated. Anything else raises
``ValueError`` (fail-closed). (Note: ``design.md:76`` is stale — it lists only
``converged/cap_reached``; the four-value set here is the faithful one, flagged in
``structure.md:19``.)

Token cost ships UNMEASURED in this ticket
------------------------------------------
``tokensIn`` / ``tokensOut`` are OPTIONAL. Per OQ2 the harness exposes no
per-subagent token usage, so the slice-2 JS wiring supplies no ``usage`` and these
keys are NEVER populated in practice. The AC-INSTR "at what token cost" dimension
is therefore currently UNMET — the fields exist in the schema only so a future
ticket can populate them if the harness later exposes usage. They are emitted
ONLY when ``usage`` supplies them (absent by default).
"""

VALID_TERMINAL_ACTIONS = frozenset(
    {"converged", "cap_reached", "exhausted", "aborted"})


def build_record(verdicts, terminalAction, usage=None, phase=None):
    """Reduce one critic step's per-lens/per-round verdicts to a ``CriticStepMetrics``.

    Args:
        verdicts: list of per-lens/per-round dicts, each carrying ``lens``,
            ``pass`` and ``findings`` (a list). Each is mapped to a
            ``CriticRoundRecord`` ``{lens, pass: bool, findingsCount: len(findings)}``.
            BOTH the pass/fail flag AND the findings count are preserved per round
            (OQ4 — never collapsed into a single rate).
        terminalAction: one of ``VALID_TERMINAL_ACTIONS``. ``ValueError`` otherwise
            (``revise`` is rejected — it is non-terminal).
        usage: optional dict supplying ``tokensIn`` / ``tokensOut``. When ``None``
            (the live default per OQ2) those keys are ABSENT from the record.
        phase: the phase label this step belongs to (e.g. ``design``).

    Returns:
        ``{phase, rounds: [{lens, pass, findingsCount}, ...], terminalAction,
           tokensIn?, tokensOut?}`` — the canonical ``CriticStepMetrics`` dict.

    Pure: no IO, no subprocess. Raises only ``ValueError`` on an invalid
    ``terminalAction``.
    """
    if terminalAction not in VALID_TERMINAL_ACTIONS:
        raise ValueError(
            "invalid terminalAction %r; must be one of %s "
            "(revise is non-terminal and not permitted)"
            % (terminalAction, sorted(VALID_TERMINAL_ACTIONS)))

    rounds = []
    for entry in (verdicts or []):
        findings = entry.get("findings") or []
        rounds.append({
            "lens": entry.get("lens"),
            "pass": bool(entry.get("pass")),
            "findingsCount": len(findings),
        })

    record = {
        "phase": phase,
        "rounds": rounds,
        "terminalAction": terminalAction,
    }

    # Emit token fields ONLY when usage supplies them (absent by default per OQ2:
    # the live path has no per-lens token usage, so these stay unmeasured).
    if usage:
        if usage.get("tokensIn") is not None:
            record["tokensIn"] = usage["tokensIn"]
        if usage.get("tokensOut") is not None:
            record["tokensOut"] = usage["tokensOut"]

    return record
