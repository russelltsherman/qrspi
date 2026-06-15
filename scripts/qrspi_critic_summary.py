#!/usr/bin/env python3
"""Summarize a QRSPI critic-metrics ledger into a base-rate report (RUS-78, Slice 1).

Why this exists
---------------
``qrspi_metrics_append.py`` appends one ``CriticMetricsLedgerLine`` per terminated
critic step to a per-ticket ``critic-metrics.jsonl`` ledger. Each line now also
carries an explicit ``runId`` (RUS-78). This module is the read side: a pure
functional core (``load_ledger`` + ``summarize``) plus a thin CLI (``main``) that
reduces a ledger to a ``CriticSummary`` — the base-rate report that gates Ticket B.

Functional-core / imperative-shell idiom
----------------------------------------
``load_ledger`` / ``_read_lines`` / ``summarize`` are pure (no aggregation in the
loader; the math lives in ``summarize``); ``main`` is the only side-effecting shell
(reads a file, prints JSON). All are stdlib-only so they run under
``scripts/run_tests.py`` in CI.

CriticSummary shape (structure.md §New Types)
---------------------------------------------
    {
      "stepCount": int,
      "timestampSpan": {"start": str|None, "end": str|None},
      "dissentRate": float,
      "dissentRevisedRate": float,
      "terminalActionCounts": {action: count},
      "perLens": {lensKey: {"steps": int, "dissentRate": float}},
      "abortedRecords": int,
    }

A ``null`` lens (the single edge critic) is rolled under the literal key
``"edge"`` (structure.md Plan-phase pin: ``perLens`` key shape).

Usage:
    python3 scripts/qrspi_critic_summary.py [--run-id ID] [--since TS] \\
        [--ticket RUS-77] <ledger.jsonl>
"""

import argparse
import json
import sys


# --- pure core -------------------------------------------------------------

def _read_lines(path):
    """Single-pass ledger reader. Returns ``(good_lines, aborted_count)``.

    Reads ``path`` line by line; ``json.loads`` each non-empty line. On a
    ``json.JSONDecodeError`` the line is SKIPPED and the aborted-record counter is
    incremented (tolerating a trailing partial/truncated line). The good-line list
    holds only dicts; a parsed non-dict (e.g. a bare JSON array) is also counted as
    aborted, since a ledger line must be an envelope object. Pure w.r.t. its return
    value (only reads the filesystem)."""
    good = []
    aborted = 0
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                aborted += 1
                continue
            if not isinstance(obj, dict):
                aborted += 1
                continue
            good.append(obj)
    return good, aborted


def load_ledger(path):
    """Read ``critic-metrics.jsonl`` and return the list of good ledger-line dicts.

    Malformed lines (including a trailing partial line) are tolerated and skipped.
    Pure; no aggregation. The aborted-record count is exposed to the CLI via
    ``_read_lines`` (this keeps the structure contract ``load_ledger(path) ->
    list[dict]`` exact while preserving aborted counting)."""
    good, _aborted = _read_lines(path)
    return good


def _scope(lines, since=None, ticket=None, run_id=None):
    """Filter ledger lines by exact ``run_id``, exact ``ticket``, then ``since``
    (timestamp ``>=``). Each filter is applied only when its argument is given."""
    scoped = lines
    if run_id is not None:
        scoped = [ln for ln in scoped if ln.get("runId") == run_id]
    if ticket is not None:
        scoped = [ln for ln in scoped if ln.get("ticketId") == ticket]
    if since is not None:
        scoped = [ln for ln in scoped
                  if isinstance(ln.get("timestamp"), str)
                  and ln.get("timestamp") >= since]
    return scoped


def summarize(lines, since=None, ticket=None, run_id=None, aborted=0):
    """Aggregate scoped ledger lines into a ``CriticSummary`` dict. Pure.

    Scopes ``lines`` by exact ``run_id`` and/or the ``ticket``/``since`` window,
    then computes the base-rate metrics.

    A *round* is one entry in a line's ``rounds[]`` array; a round counts as
    **dissent** if ``round["pass"] is False`` OR ``round["findingsCount"] > 0``.

    ``dissentRevisedRate`` is a **named revise-attempted proxy**: it measures
    "a revise round was ATTEMPTED after dissent" — i.e. a ``pass:false`` round that
    is followed by a later round in the same step's ``rounds[]`` — NOT "the artifact
    changed". It is (count of ``pass:false`` rounds with a later round in their step)
    / (count of ``pass:false`` rounds).

    ``perLens`` is keyed by each round's ``lens`` string; a ``None`` lens (the single
    edge critic) rolls under the literal key ``"edge"``. ``abortedRecords`` is passed
    through from the loader (= ``aborted``)."""
    scoped = _scope(lines, since=since, ticket=ticket, run_id=run_id)

    # timestampSpan
    stamps = sorted(ln["timestamp"] for ln in scoped
                    if isinstance(ln.get("timestamp"), str))
    span = {
        "start": stamps[0] if stamps else None,
        "end": stamps[-1] if stamps else None,
    }

    # dissent / revise math + per-lens accumulation
    total_rounds = 0
    dissent_rounds = 0
    pass_false_rounds = 0
    pass_false_revised = 0
    per_lens = {}  # lensKey -> {"rounds": int, "dissent": int}
    terminal_counts = {}

    for line in scoped:
        rounds = line.get("rounds")
        if not isinstance(rounds, list):
            rounds = []
        n = len(rounds)
        for i, rnd in enumerate(rounds):
            if not isinstance(rnd, dict):
                continue
            total_rounds += 1
            is_pass_false = rnd.get("pass") is False
            is_dissent = is_pass_false or (rnd.get("findingsCount", 0) or 0) > 0
            if is_dissent:
                dissent_rounds += 1
            if is_pass_false:
                pass_false_rounds += 1
                if i < n - 1:  # a later round exists in this step
                    pass_false_revised += 1
            lens = rnd.get("lens")
            key = "edge" if lens is None else lens
            bucket = per_lens.setdefault(key, {"rounds": 0, "dissent": 0})
            bucket["rounds"] += 1
            if is_dissent:
                bucket["dissent"] += 1

        action = line.get("terminalAction")
        if action is not None:
            terminal_counts[action] = terminal_counts.get(action, 0) + 1

    dissent_rate = (dissent_rounds / total_rounds) if total_rounds else 0.0
    dissent_revised_rate = (
        (pass_false_revised / pass_false_rounds) if pass_false_rounds else 0.0)

    per_lens_out = {
        key: {
            "steps": b["rounds"],
            "dissentRate": (b["dissent"] / b["rounds"]) if b["rounds"] else 0.0,
        }
        for key, b in per_lens.items()
    }

    return {
        "stepCount": len(scoped),
        "timestampSpan": span,
        "dissentRate": dissent_rate,
        "dissentRevisedRate": dissent_revised_rate,
        "terminalActionCounts": terminal_counts,
        "perLens": per_lens_out,
        "abortedRecords": aborted,
    }


# --- entrypoint ------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Summarize a critic-metrics ledger into a base-rate report")
    parser.add_argument("--run-id", dest="run_id", default=None,
                        help="Scope to exactly this runId")
    parser.add_argument("--since", default=None,
                        help="Only lines with timestamp >= this ISO-8601 value")
    parser.add_argument("--ticket", default=None,
                        help="Scope to exactly this ticketId")
    parser.add_argument("ledger", help="Path to critic-metrics.jsonl")
    args = parser.parse_args(argv)

    lines, aborted = _read_lines(args.ledger)
    summary = summarize(lines, since=args.since, ticket=args.ticket,
                        run_id=args.run_id, aborted=aborted)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
