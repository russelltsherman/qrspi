#!/usr/bin/env python3
"""Pure judge-base selector for the QRSPI generation-side N-select design stage (RUS-59).

Why this exists
---------------
The Stage-1 (design) N-select runs the design produce agent under N orthogonal framings
(mvp-first / risk-first / extensibility-first), then a *judge* agent scores the N candidates
and names, per non-winning candidate, the strong ideas worth grafting into the winner. Before
the JS orchestrator (`runDesignSelectLoop`) can copy the winner and conditionally run the graft
agent, the judge output must be reduced to ONE authoritative selection: which candidate wins,
and which runner-up ideas to graft. That reduction is the only deterministic, unit-testable
piece of the stage, so it lives here as a pure, stdlib-only function with no agent / IO / git
coupling (mirroring qrspi_critic_synthesize.py — ref: structure §Contracts, Decision 3). The JS
glue keeps only the untestable fan-out / judge / graft spawns and delegates this reduction to
`select` below via a worker (the JS sandbox cannot run python).

Selection rule (ref: structure §Contracts, plan §2):
  - `winner` = the candidate id with the highest `score`. Deterministic tie-break = lowest
    candidate index (first appearance in `scores`). The judge's own `winner` field, if any, is
    ignored — the selector computes the winner deterministically from scores so the result is
    reproducible regardless of judge framing.
  - `scores` is echoed through unchanged (the orchestrator surfaces per-candidate scores in the
    doDesign summary, AC2 scores half).
  - `graftDirectives` = the exact-string-deduped union of `graft_ideas` from all NON-winning
    candidates (the winner's own `graft_ideas` are excluded), preserving first-seen order. Empty
    when no runner-up carries a distinctive idea ⇒ graft is a downstream no-op.

Fail-closed: an empty / non-JSON / structurally-malformed input raises SelectError, which the
CLI driver renders as an error envelope on stdout and exits non-zero. A garbled judge reply can
never silently yield a partial or arbitrary winner (ref: structure §Contracts, plan §3).
"""

import json
import sys


class SelectError(ValueError):
    """Raised on empty or malformed judge input. The CLI driver renders this as an error
    envelope and exits non-zero (fail-closed)."""


def select(judge_output):
    """Reduce judge output to one authoritative selection.

    `judge_output` is the parsed judge reply:
        { "scores": [ {candidate, score, rationale, graft_ideas?: [str]}, ... ], "winner"?: str }

    Returns:
        { "winner": str, "scores": list, "graftDirectives": [str] }
      - `winner`: candidate id with the highest `score`; ties broken by lowest index.
      - `scores`: echoed through unchanged.
      - `graftDirectives`: deduped `graft_ideas` from all non-winning candidates (winner's own
        excluded), first-seen order.

    Raises SelectError when the input is not a dict, `scores` is missing / not a list / empty, or
    any score entry is not a dict or lacks a usable `candidate` / numeric `score`.

    Signature: select(judge_output: dict) -> dict
    """
    if not isinstance(judge_output, dict):
        raise SelectError("judge output must be a JSON object")

    scores = judge_output.get("scores")
    if not isinstance(scores, list) or not scores:
        raise SelectError("judge output 'scores' must be a non-empty list")

    # Validate every entry up front so a single malformed candidate fails the whole
    # selection (fail-closed) rather than being silently skipped.
    for idx, entry in enumerate(scores):
        if not isinstance(entry, dict):
            raise SelectError("score entry %d is not an object" % idx)
        candidate = entry.get("candidate")
        if not isinstance(candidate, str) or not candidate:
            raise SelectError("score entry %d lacks a non-empty 'candidate'" % idx)
        score = entry.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise SelectError("score entry %d lacks a numeric 'score'" % idx)

    # Winner = highest score; tie-break = lowest index (first appearance). Iterating in order
    # and using strict `>` keeps the first-seen (lowest-index) candidate on a tie.
    winner_idx = 0
    winner_score = scores[0]["score"]
    for idx in range(1, len(scores)):
        if scores[idx]["score"] > winner_score:
            winner_score = scores[idx]["score"]
            winner_idx = idx
    winner = scores[winner_idx]["candidate"]

    # graftDirectives = deduped graft_ideas from every NON-winning candidate, first-seen order.
    graft_directives = []
    seen = set()
    for idx, entry in enumerate(scores):
        if idx == winner_idx:
            continue
        ideas = entry.get("graft_ideas")
        if not isinstance(ideas, list):
            continue
        for idea in ideas:
            if not isinstance(idea, str) or not idea:
                continue
            if idea in seen:
                continue
            seen.add(idea)
            graft_directives.append(idea)

    return {"winner": winner, "scores": scores, "graftDirectives": graft_directives}


# --- thin CLI ---------------------------------------------------------------
# A deterministic stdin->stdout shim so the JS orchestrator (which cannot run python in its
# sandbox) can invoke the pure `select` reducer via a worker, exactly like
# qrspi_critic_synthesize.py exposes `synthesize`. The pure function above is unchanged; this
# only exposes it.
#
#   printf '%s' '<json judge output>' | python3 qrspi_design_select.py
#
# Reads the judge output (a JSON object) from stdin and prints { winner, scores, graftDirectives }
# as JSON on success (exit 0). On empty / unparseable / malformed input it prints an error
# envelope { "error": <message> } to stdout and exits non-zero (fail-closed).
def main(argv=None):
    raw = sys.stdin.read()
    try:
        if not raw.strip():
            raise SelectError("empty input")
        try:
            judge_output = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise SelectError("input is not valid JSON: %s" % exc)
        result = select(judge_output)
    except SelectError as exc:
        json.dump({"error": str(exc)}, sys.stdout)
        print()
        return 1

    json.dump(result, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
