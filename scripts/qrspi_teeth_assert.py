#!/usr/bin/env python3
"""Pure majority/marker decision core for the QRSPI teeth eval (RUS-78, AC-Teeth-eval).

Why this exists
---------------
The teeth eval feeds the REAL design-critic panel a single deliberately-flawed
`design.md` fixture (carrying three labelled defects) and asserts each *owning*
lens still catches its defect — proving the cost-reduced (digest-ON) panel keeps
its teeth, non-vacuously. The agent spawning and per-trial fan-out are inherently
non-deterministic and live in the opt-in Workflow runner
(`.claude/workflows/qrspi-teeth-eval.js`), off the CI gate.

The ONE deterministic, testable piece of that eval is the decision math: given
per-lens trial verdicts + the expected per-lens markers + a majority threshold,
decide whether each lens "caught" its defect often enough. That math lives here
as a pure, stdlib-only function (mirroring qrspi_critic_synthesize.py), so it runs
inside `run_tests.py`/CI as Slice 3's deterministic test contribution while the
spawning stays off CI (structure §Contracts "Teeth-eval assertion contract").

Catch rule (deterministic substring test on the verdict)
--------------------------------------------------------
A verdict is the panel lens's `{pass: bool, findings: list[str]}` reply. A trial
"catches" its defect iff BOTH hold:
  - `pass is False` (the lens did NOT rubber-stamp the flawed design), AND
  - the lens's expected marker string appears as a substring of SOME finding.
This turns "the lens names its defect" into a deterministic substring assertion
against the verdict, since each defect embeds a unique quotable marker the owning
lens must cite (structure §Contracts teeth lens->defect ownership map).

A lens passes the eval iff `caught >= threshold` (default majority, >=2-of-3).
`overallPass` is True iff every evaluated lens passes.

Fail-closed
-----------
A malformed verdict (not a dict, missing `pass`, non-list `findings`, non-string
finding) reads as NOT a catch — a garbled lens reply can never silently count as
catching its defect.

CLI (stdin -> stdout, the synthesizeVerdicts worker pattern)
------------------------------------------------------------
A thin `main(argv)` reads the trials-by-lens JSON object on stdin and the markers
JSON + threshold from args, then prints the report JSON, so the Workflow runner
(which cannot run python in its sandbox) can invoke this via a worker:

    printf '%s' '<trials_by_lens json>' \\
      | python3 scripts/qrspi_teeth_assert.py --markers '<markers json>' --threshold 2

Output: { perLens: { lens: { caught, total, pass } }, overallPass: bool }.
"""

import argparse
import json
import sys


# --- pure helpers (unit-tested) --------------------------------------------

def _is_catch(verdict, marker):
    """Return True iff ``verdict`` catches its defect for ``marker``.

    A catch requires the lens to have FAILED the design (``pass is False``) AND to
    have cited the defect's unique ``marker`` as a substring of some finding.
    Fail-closed: a non-dict verdict, a verdict whose ``pass`` is not exactly
    ``False``, a non-list ``findings``, or a non-string ``marker`` all read as NOT
    a catch. Pure: no IO, never raises."""
    if not isinstance(verdict, dict):
        return False
    if verdict.get("pass") is not False:
        return False
    if not isinstance(marker, str) or not marker:
        return False
    findings = verdict.get("findings")
    if not isinstance(findings, list):
        return False
    for finding in findings:
        if isinstance(finding, str) and marker in finding:
            return True
    return False


def evaluate(trials_by_lens, markers, threshold=2):
    """Decide, per lens, whether it caught its defect by a majority threshold.

    Args:
      trials_by_lens: ``{lens: [verdict, ...]}`` — each verdict is the lens's
        ``{pass, findings}`` reply for one trial.
      markers: ``{lens: marker_str}`` — the unique quotable marker the owning lens
        must cite to count as catching its defect.
      threshold: minimum number of catching trials for a lens to pass (default 2,
        the >=2-of-3 majority). Coerced to ``int``; a non-int/<=0 value falls back
        to 2 (a non-positive threshold would let a lens "pass" with zero catches,
        defeating the eval).

    Returns ``{"perLens": {lens: {"caught": int, "total": int, "pass": bool}},
    "overallPass": bool}`` where a lens passes iff ``caught >= threshold`` and
    ``overallPass`` is True iff EVERY evaluated lens passes (an empty lens set
    reads as ``overallPass: False`` — no lens attested, fail closed).

    Only lenses present in ``markers`` are evaluated (a marker is required to
    define a catch); a lens with no trials reads as ``caught: 0`` (fails). Pure:
    no IO, never raises.

    Signature: evaluate(trials_by_lens: dict, markers: dict, threshold: int = 2) -> dict
    """
    try:
        threshold = int(threshold)
    except (TypeError, ValueError):
        threshold = 2
    if threshold <= 0:
        threshold = 2

    if not isinstance(trials_by_lens, dict):
        trials_by_lens = {}
    if not isinstance(markers, dict):
        markers = {}

    per_lens = {}
    for lens, marker in markers.items():
        verdicts = trials_by_lens.get(lens)
        if not isinstance(verdicts, list):
            verdicts = []
        caught = sum(1 for v in verdicts if _is_catch(v, marker))
        per_lens[lens] = {
            "caught": caught,
            "total": len(verdicts),
            "pass": caught >= threshold,
        }

    overall = bool(per_lens) and all(v["pass"] for v in per_lens.values())
    return {"perLens": per_lens, "overallPass": overall}


# --- thin CLI (stdin -> stdout worker shim) --------------------------------
# A deterministic stdin->stdout shim so the Workflow runner (which cannot run python
# in its sandbox) can invoke the pure `evaluate` core via a worker, exactly like
# qrspi_critic_synthesize.py exposes `synthesize`. The pure function is unchanged;
# this only exposes it.
#
#   printf '%s' '<trials_by_lens json>' \
#     | python3 qrspi_teeth_assert.py --markers '<markers json>' --threshold 2
#
# Reads the trials-by-lens JSON object from stdin and the markers JSON + threshold
# from args, then prints the report JSON: { perLens, overallPass }. A non-object /
# unparseable stdin or markers reduces to the empty mapping ⇒ fail-closed
# { "perLens": {}, "overallPass": false }.
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Decide per-lens majority/marker catch for the teeth eval "
                    "(trials-by-lens on stdin, markers + threshold as args)")
    parser.add_argument("--markers", required=True,
                        help="JSON object mapping lens -> expected marker string")
    parser.add_argument("--threshold", type=int, default=2,
                        help="Minimum catching trials for a lens to pass (default 2)")
    args = parser.parse_args(argv)

    raw = sys.stdin.read()
    try:
        trials_by_lens = json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        trials_by_lens = {}
    try:
        markers = json.loads(args.markers) if args.markers.strip() else {}
    except (ValueError, TypeError):
        markers = {}

    result = evaluate(trials_by_lens, markers, args.threshold)
    json.dump(result, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
