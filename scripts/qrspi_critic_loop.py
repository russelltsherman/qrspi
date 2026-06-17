#!/usr/bin/env python3
"""Pure critic-loop decision core for the QRSPI design-panel and coherence critic loops.

Why this exists
---------------
The QRSPI critic loops (`runCriticPanelLoop` — the design panel — and `runCoherenceCritic`,
the JS glue in `.claude/workflows/qrspi-batch.js`) spawn critic agent(s) per round against a
produced artifact, then must decide whether it has CONVERGED (latest round passed), needs
another REVISE round, or has hit its per-phase round CAP and must surface its residual
findings into the finalize PR body. (The single-edge `runCriticLoop` that also drove this
core was retired in RUS-88; the convergence math is unchanged.) That decision is the one
piece of the loop worth unit-testing, so it lives here as a pure stdlib-only module with no
agent or IO coupling (ref: design.md Decision 3, Pattern 7, Q12/Q13). The JS glue keeps only
the untestable agent-spawn mechanics and delegates the converge/continue/cap decision to
`next_action` below.

Two functions:
  - `parse_critic_verdict(text)` — fail-closed parser. The critic verdict is contractually
    a runner-validated `{pass: bool, findings: [...]}` (Decision 2 Option A, frontier model
    + StructuredOutput schema), but this is retained as a DEFENSIVE backstop for the residual
    weak-model-stall risk: an unreadable/empty/malformed verdict is treated as NOT-passed
    (mirroring `parseLandVerdict` → `incomplete`). It never raises (ref: design Decision 2, Q11).
  - `next_action(verdicts, round, max_rounds)` — given the already-parsed verdict(s) for the
    current round plus the round index and the per-phase cap, returns the converge/revise/
    cap_reached action and any residual findings to surface (ref: design §Delta, AC2, AC4).

Both functions take already-parsed dicts / plain text; neither touches the filesystem,
the agent runner, or git — so the whole decision is verifiable by the `_test.py` sibling
with zero dependency on `agent()` or the JS orchestrator.
"""

import argparse
import json
import re
import sys


def _coerce_verdict(obj):
    """Coerce an arbitrary parsed object into the canonical `{pass: bool, findings: list}`
    shape, failing closed. Pure helper shared by parse_critic_verdict and next_action's
    latest-verdict read. A non-dict, or a dict missing/garbling the fields, yields a
    NOT-passed verdict with whatever findings could be salvaged (else an empty list)."""
    if not isinstance(obj, dict):
        return {"pass": False, "findings": []}
    passed = bool(obj.get("pass", False))
    findings = obj.get("findings", [])
    if not isinstance(findings, list):
        # A scalar (e.g. a single string finding) is wrapped; anything else ⇒ empty.
        findings = [findings] if findings else []
    return {"pass": passed, "findings": findings}


def parse_critic_verdict(text):
    """Fail-closed parser: extract a JSON object from `text` and coerce it to the canonical
    `{pass: bool, findings: list}` verdict. On malformed / empty / non-JSON / unreadable
    input, return `{"pass": False, "findings": []}`. NEVER raises.

    This is a defensive backstop only — the primary path is runner schema validation
    (Decision 2 Option A). An unreadable verdict is treated as NOT-passed so a garbled
    critic reply can never silently mark an artifact converged (ref: design Decision 2, Q11).

    Signature: parse_critic_verdict(text: str) -> dict
    """
    if not isinstance(text, str) or not text.strip():
        return {"pass": False, "findings": []}

    # Try the whole string first; fall back to the first {...} object embedded in prose
    # (the critic may wrap its JSON in commentary). Both attempts fail closed.
    candidates = [text]
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidates.append(match.group(0))

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        return _coerce_verdict(obj)

    return {"pass": False, "findings": []}


def next_action(verdicts, round, max_rounds):
    """Decide the loop's next move from the current round's parsed verdict(s).

    `verdicts` is the list of already-parsed `{pass, findings}` verdict dicts produced this
    round (a single-critic edge yields a one-element list — OQ2). The LATEST verdict (last
    element) is authoritative for this round. Returns:

        {"action": "converged"|"revise"|"cap_reached", "residual_findings": [...]}

      - "converged"   when the latest verdict's `pass` is truthy. No residual findings.
      - "cap_reached" when the latest verdict did NOT pass and this is the final allowed
                      round (`round + 1 >= max_rounds`); the latest verdict's findings are
                      surfaced as `residual_findings` for the finalize PR body.
      - "revise"      otherwise (not passed, rounds remain). The latest findings are carried
                      as `residual_findings` so the reviser has the critic's guidance.

    Fails closed: an empty/garbled verdict list, or a non-dict latest verdict, reads as
    NOT-passed (via _coerce_verdict), so a missing verdict can never report "converged"
    (ref: design §Delta, AC2, AC4, Decision 2/3, Q11).

    Signature: next_action(verdicts: list, round: int, max_rounds: int) -> dict
    """
    latest = _coerce_verdict(verdicts[-1]) if isinstance(verdicts, list) and verdicts else {
        "pass": False, "findings": []}

    if latest["pass"]:
        return {"action": "converged", "residual_findings": []}

    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}

    return {"action": "revise", "residual_findings": list(latest["findings"])}


# --- thin CLI (RUS-55 Slice 3) ---------------------------------------------
# A deterministic stdin->stdout shim so the JS orchestrator (which cannot run python in its
# sandbox) can invoke the pure `next_action` decision via a worker, exactly like the other
# qrspi_*.py scripts. The pure functions above are unchanged; this only exposes them.
#
#   printf '%s' '<json verdicts array>' | python3 qrspi_critic_loop.py --round R --max-rounds M
#
# Reads a JSON ARRAY of verdict dicts from stdin (each entry is run through _coerce_verdict /
# parse_critic_verdict so a malformed entry fails closed to NOT-passed, never raising), then
# prints `next_action(verdicts, round, max_rounds)` as JSON: { action, residual_findings }.
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Decide the critic loop's next action from stdin verdict(s) (self-contained CLI)")
    parser.add_argument("--round", type=int, required=True,
                        help="Current 0-based round index")
    parser.add_argument("--max-rounds", type=int, required=True,
                        help="Per-phase round cap (>=1)")
    args = parser.parse_args(argv)

    raw = sys.stdin.read()
    verdicts = []
    try:
        parsed = json.loads(raw) if raw.strip() else []
    except (ValueError, TypeError):
        parsed = []
    if isinstance(parsed, list):
        # Coerce each element fail-closed: a dict goes through _coerce_verdict; anything else
        # is run through the text parser (which also fails closed to NOT-passed).
        for entry in parsed:
            if isinstance(entry, dict):
                verdicts.append(_coerce_verdict(entry))
            else:
                verdicts.append(parse_critic_verdict(entry if isinstance(entry, str) else ""))

    decision = next_action(verdicts, args.round, args.max_rounds)
    json.dump(decision, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
