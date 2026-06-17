#!/usr/bin/env python3
"""Pure reducer for QRSPI critic-step metrics (RUS-77, AC-INSTR).

Why this exists
---------------
A single critic *step* — one panel loop in ``runCriticPanelLoop`` (the design
panel, in ``qrspi-batch.js``) — runs N rounds of M per-lens verdicts and then
terminates. (The single-edge ``runCriticLoop`` that also emitted these records was
retired in RUS-88; the reduction is unchanged.) To make the critic effective-or-not
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
``runCriticPanelLoop`` (the single-edge ``runCriticLoop`` that shared this enum was
retired in RUS-88; the terminations are unchanged):
  - ``converged``   — decision.action == 'converged'
  - ``cap_reached`` — decision.action == 'cap_reached'
  - ``exhausted``   — the defensive ``ok:true`` tail, loop ran out of rounds
                      without an explicit decision return
  - ``aborted``     — any ``ok:false`` early return (verdict / decision / reviser
                      failure) — so aborted steps STILL emit a
                      record and AC-INSTR base rates are not biased toward
                      successful terminations.
``revise`` is deliberately NOT in the enum: it is a mid-loop continuation
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


# --- thin CLI (RUS-77 Slice 2) ---------------------------------------------
# A deterministic stdin->stdout shim so the JS orchestrator (which cannot run python
# in its sandbox) can invoke the pure `build_record` reducer via a worker, exactly
# like qrspi_critic_synthesize.py exposes `synthesize`. The pure function above is
# unchanged; this only exposes it so the slice-2 wiring can derive `findingsCount`
# in Python (never in JS — ref: impl-log Slice 1 notes) before handing the BARE
# CriticStepMetrics record to qrspi_metrics_append.py for the envelope + append.
#
#   printf '%s' '<json verdicts array>' \
#     | python3 qrspi_critic_metrics.py --terminal-action <action> [--phase <p>]
#
# Reads a JSON ARRAY of per-round/per-lens verdict entries (each {lens, pass,
# findings}) from stdin, builds the canonical CriticStepMetrics record, and prints
# it as JSON on stdout. An invalid --terminal-action fails CLOSED (exit 2 via the
# ValueError from build_record); a non-array / unparseable stdin reduces to the
# empty rounds list (a terminated step that ran zero captured rounds — still a valid
# record carrying the terminalAction). `usage` is intentionally NOT exposed: the
# live path supplies no per-lens token usage (OQ2), so the cost fields stay absent.
def main(argv=None):
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Reduce one critic step's verdicts (stdin JSON array) to a "
                    "CriticStepMetrics record (self-contained CLI)")
    parser.add_argument("--terminal-action", required=True,
                        help="One of %s" % sorted(VALID_TERMINAL_ACTIONS))
    parser.add_argument("--phase", default=None,
                        help="Phase label this critic step belongs to")
    args = parser.parse_args(argv)

    raw = sys.stdin.read()
    try:
        verdicts = json.loads(raw) if raw.strip() else []
    except (ValueError, TypeError):
        verdicts = []
    if not isinstance(verdicts, list):
        verdicts = []

    # build_record raises ValueError on an invalid terminalAction (fail-closed);
    # let it propagate to a non-zero exit so the JS worker surfaces the failure.
    record = build_record(verdicts, args.terminal_action, phase=args.phase)
    json.dump(record, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
