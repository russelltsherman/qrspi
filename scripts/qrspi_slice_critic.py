#!/usr/bin/env python3
"""Pure diff-scope/skip reducer for the QRSPI per-slice code critic.

Why this exists
---------------
Stage 3 of the QRSPI critics work runs a per-slice edge critic inside the implementation
slice loop (`doImplementation` in `.claude/workflows/qrspi-batch.js`). Before spawning the
critic for a given slice, the orchestrator must decide two things deterministically:

  1. Whether to run the per-slice critic at all for this slice — it is SKIPPED when the slice
     is already committed (a resume of an in-progress stack, so the critic already ran) or when
     the ticket has only a single slice (no meaningful per-slice edge to critique).
  2. If it runs, the Graphite diff range `${diffBase}..${diffHead}` that scopes the critic to
     exactly this slice's change: slice 1's base is the `${id}/plan` branch it stacks on, slice
     N>1's base is the prior slice branch `${id}/slice-(N-1)`, and the head is always this
     slice's own branch `${id}/slice-N`.

That decision is the one piece worth unit-testing, so it lives here as a pure stdlib-only
module with no JS, Graphite, or critic-spawn coupling (ref: structure.md §Contracts;
design.md Decision 1A, Decision 5, Decision 7, Q10, Q11). The JS glue keeps only the
untestable agent-spawn / Graphite-diff mechanics and delegates the run/skip + diff-range
decision to `decide` below.

The single function:
  - `decide(setup, slice_index)` — given the `setup` blob (the list of slices with their
    `alreadyCommitted` flag plus the ticket `id`) and a 1-based slice index, returns the
    per-slice critic decision `{run, skipReason, diffBase, diffHead}`.

`decide` takes an already-parsed dict and returns a plain dict; it never touches the
filesystem, the agent runner, or git — so the whole decision is verifiable by the `_test.py`
sibling with zero dependency on the JS orchestrator.

A thin stdin->stdout CLI (mirroring `qrspi_critic_loop.py`) lets the JS orchestrator shell out
to read the JSON decision, exactly like the other qrspi_*.py scripts.
"""

import argparse
import json
import sys


def decide(setup, slice_index):
    """Decide whether to run the per-slice critic for slice `slice_index`, and if so the
    Graphite diff range that scopes it.

    `setup` is the per-implementation blob:

        {"id": "<ticket-id>", "slices": [ {"alreadyCommitted": bool}, ... ]}

    `slice_index` is 1-based (slice 1 is the first slice, which stacks on `${id}/plan`).

    Returns:

        {"run": bool,
         "skipReason": "alreadyCommitted" | "single-slice" | None,
         "diffBase": str | None,
         "diffHead": str | None}

      - SKIP "alreadyCommitted": when this slice is already committed (resume) — the critic
        already ran for it, so it is skipped. `run=False`, no diff range
        (ref: Decision 1A, Decision 5, Q10). Evaluated FIRST so a single committed slice
        skips with "alreadyCommitted" (the resume-skip intent), not "single-slice".
      - SKIP "single-slice": when the ticket has exactly one slice — there is no meaningful
        per-slice edge to critique. `run=False`, no diff range (ref: Decision 7, Q10).
      - RUN: otherwise — `run=True`, `skipReason=None`,
        `diffHead = "${id}/slice-{slice_index}"`, and
        `diffBase = "${id}/plan"` for slice 1 else `"${id}/slice-{slice_index-1}"`
        (ref: Decision 1A, Q11).

    Signature: decide(setup: dict, slice_index: int) -> dict
    """
    slices = setup.get("slices", []) if isinstance(setup, dict) else []
    ticket_id = setup.get("id") if isinstance(setup, dict) else None
    idx = int(slice_index)

    # Skip branch A — already committed (resume). Evaluated first so a single committed
    # slice yields "alreadyCommitted", matching the resume-skip intent of Q10.
    already = False
    if 1 <= idx <= len(slices):
        entry = slices[idx - 1]
        already = bool(entry.get("alreadyCommitted", False)) if isinstance(entry, dict) else False
    if already:
        return {"run": False, "skipReason": "alreadyCommitted", "diffBase": None, "diffHead": None}

    # Skip branch B — single-slice ticket (no per-slice edge to critique).
    if len(slices) == 1:
        return {"run": False, "skipReason": "single-slice", "diffBase": None, "diffHead": None}

    # Run branch — scope the critic to this slice's diff range.
    diff_head = "%s/slice-%d" % (ticket_id, idx)
    if idx == 1:
        diff_base = "%s/plan" % (ticket_id,)
    else:
        diff_base = "%s/slice-%d" % (ticket_id, idx - 1)
    return {"run": True, "skipReason": None, "diffBase": diff_base, "diffHead": diff_head}


# --- thin CLI -----------------------------------------------------------------
# A deterministic stdin->stdout shim so the JS orchestrator (which cannot run python in its
# sandbox) can invoke the pure `decide` decision via a worker, exactly like the other
# qrspi_*.py scripts. The pure function above is unchanged; this only exposes it.
#
#   printf '%s' '<json setup blob>' | python3 qrspi_slice_critic.py --slice-index N
#
# Reads the JSON `setup` blob from stdin, then prints
# `decide(setup, slice_index)` as JSON: { run, skipReason, diffBase, diffHead }.
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Decide the per-slice critic run/skip + diff range from a stdin setup blob")
    parser.add_argument("--slice-index", type=int, required=True,
                        help="1-based index of the slice to decide for")
    args = parser.parse_args(argv)

    raw = sys.stdin.read()
    try:
        setup = json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        setup = {}
    if not isinstance(setup, dict):
        setup = {}

    decision = decide(setup, args.slice_index)
    json.dump(decision, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
