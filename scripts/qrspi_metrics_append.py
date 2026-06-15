#!/usr/bin/env python3
"""Append one QRSPI critic-step metrics line to a per-ticket ledger (RUS-77).

Why this exists
---------------
Slice 1's pure reducer (``qrspi_critic_metrics.build_record``) emits a
``CriticStepMetrics`` record for one terminated critic step. This CLI is the
durable sink: it wraps that record in the ``CriticMetricsLedgerLine`` envelope
(adding ``ticketId`` + ``timestamp``) and APPENDS it as one JSON line to
``.qrspi/<id>/critic-metrics.jsonl`` inside the ticket's worktree, verifying the
write (non-empty) and failing CLOSED — modelled on ``qrspi_persist.py``.

Usage:
    python3 scripts/qrspi_metrics_append.py --ticket RUS-77 --record '<json>'

Path resolution (CRITICAL — mirrors qrspi_persist.py)
-----------------------------------------------------
The host checkout root is resolved via
``qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`` — git-common-dir
first, so it yields the MAIN checkout even when this script is invoked from a
worktree. This script lives at ``.worktrees/<id>/scripts/…`` in a worktree, so
self-locating the root from ``__file__`` would yield the WORKTREE root, and joining
``.worktrees/<id>/.qrspi/<id>/`` onto it would double-nest to
``.worktrees/<id>/.worktrees/<id>/.qrspi/…`` — a silent mis-persist the non-empty
verify would still pass (the exact failure class ``resolve_repo_root`` /
``qrspi_persist.py`` exist to prevent; see ``scripts/qrspi_persist.py:37-50``).
``validate=False`` keeps gh off the import path; the ledger path is computed off
the resolved root as ``<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl``.

Envelope authority
------------------
Per structure.md ``CriticMetricsLedgerLine``, the line is NOT the bare
``CriticStepMetrics`` record: this appender is the single envelope authority. It
injects ``ticketId`` (from ``--ticket``) and ``timestamp`` (generated at write
time, UTC ISO-8601) into a shallow copy of the parsed record; if the record
already carried those fields the appender's values win.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, ledger, lines, bytes, error? }
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ENGINE_ROOT: the dir holding this engine's scripts/ (derived from __file__) — used
# ONLY for sibling imports, never a host path. The HOST checkout root is resolved
# through qrspi_paths.resolve_repo_root (git-common-dir first) so the ledger lands in
# the MAIN checkout's worktree, never a double-nested phantom path.
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402


# --- pure helpers (unit-tested) --------------------------------------------

def ledger_path(repo_root, ticket):
    """Canonical per-ticket ledger path. Pure. The qrspi token lives ONLY here —
    computed by the script off the resolved host root, never typed by a model."""
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "critic-metrics.jsonl")


def wrap_envelope(record, ticket, timestamp, run_id):
    """Wrap a CriticStepMetrics ``record`` in the CriticMetricsLedgerLine envelope.

    Returns a shallow copy of ``record`` with ``ticketId``, ``timestamp`` and
    ``runId`` injected — the appender is the single envelope authority, so its
    values win over any pre-existing ``ticketId``/``timestamp``/``runId`` in the
    record. ``run_id`` is required and always lands as the string field ``runId``
    on every appended line (RUS-78). Pure."""
    line = dict(record)
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
    return line


def append_line(path, ledger_line):
    """Append ``ledger_line`` (a dict) as one JSON line to ``path``, creating the
    parent dir, then verify the file is non-empty. Returns ``(lines, bytes, error)``
    where error is None on success. Touches only the filesystem (no network /
    subprocess), so it is unit-testable against temp dirs. Fail-closed: a write that
    leaves the ledger empty returns an error."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0, 0, "ledger not written: %s" % path
    if size == 0:
        return 0, 0, "ledger is empty after append: %s" % path
    with open(path) as fh:
        lines = sum(1 for _ in fh)
    return lines, size, None


# --- entrypoint ------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Append one critic-step metrics line to a per-ticket ledger "
                    "(self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-77")
    parser.add_argument("--record", required=True,
                        help="A CriticStepMetrics record as a JSON string")
    parser.add_argument("--run-id", dest="run_id", required=True,
                        help="The orchestrator's per-invocation run id (always "
                             "stamped onto the appended line as runId)")
    args = parser.parse_args(argv)

    # Fail-closed on malformed input: exit non-zero, write nothing.
    try:
        record = json.loads(args.record)
    except (ValueError, TypeError) as exc:
        env = {"ok": False, "error": "invalid --record JSON: %s" % exc}
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1
    if not isinstance(record, dict):
        env = {"ok": False,
               "error": "--record must be a JSON object, got %s" % type(record).__name__}
        json.dump(env, sys.stdout, indent=2)
        print()
        return 1

    repo_root = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
    path = ledger_path(repo_root, args.ticket)
    timestamp = datetime.now(timezone.utc).isoformat()
    ledger_line = wrap_envelope(record, args.ticket, timestamp, args.run_id)
    lines, bytes_written, error = append_line(path, ledger_line)

    env = {
        "ok": error is None,
        "repoRoot": repo_root,
        "ledger": path,
        "lines": lines,
        "bytes": bytes_written,
    }
    if error is not None:
        env["error"] = error

    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
