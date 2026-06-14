#!/usr/bin/env python3
"""Unit tests for qrspi_slice_critic pure reducer: decide's run/skip + diff-range decision.
Stdlib-only, assert-based, no third-party deps, no test runner.
Run: python3 scripts/qrspi_slice_critic_test.py

Covers (ref: structure §Slice 1 §Verification, plan §1.4, Decision 1A/5/7, Q10/Q11):
  - slice 1, multi-slice, non-committed ⇒ run, diffBase=${id}/plan, diffHead=${id}/slice-1
  - slice N>1, multi-slice, non-committed ⇒ run, diffBase=${id}/slice-(N-1), diffHead=${id}/slice-N
  - alreadyCommitted slice ⇒ skip with reason "alreadyCommitted"
  - len(slices) == 1 ⇒ skip with reason "single-slice"
  - multi-slice non-committed run case asserts no skip reason set
  - precedence: a single committed slice yields "alreadyCommitted", not "single-slice"
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_slice_critic import decide  # noqa: E402

failures = 0
total = 0


def check(label, got, want):
    global failures, total
    total += 1
    if got == want:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))


# A multi-slice ticket, nothing committed yet.
MULTI = {"id": "RUS-58", "slices": [{"alreadyCommitted": False},
                                    {"alreadyCommitted": False},
                                    {"alreadyCommitted": False}]}

# --- run branch: slice 1 base is ${id}/plan ---------------------------------
check("slice 1, multi-slice, non-committed ⇒ run, diffBase=${id}/plan, diffHead=${id}/slice-1",
      decide(MULTI, 1),
      {"run": True, "skipReason": None,
       "diffBase": "RUS-58/plan", "diffHead": "RUS-58/slice-1"})

# --- run branch: slice N>1 base is the prior slice branch -------------------
check("slice 2, multi-slice, non-committed ⇒ run, diffBase=${id}/slice-1, diffHead=${id}/slice-2",
      decide(MULTI, 2),
      {"run": True, "skipReason": None,
       "diffBase": "RUS-58/slice-1", "diffHead": "RUS-58/slice-2"})

check("slice 3, multi-slice, non-committed ⇒ run, diffBase=${id}/slice-2, diffHead=${id}/slice-3",
      decide(MULTI, 3),
      {"run": True, "skipReason": None,
       "diffBase": "RUS-58/slice-2", "diffHead": "RUS-58/slice-3"})

# --- run case asserts NO skip reason is set --------------------------------
check("run case has skipReason None (explicitly not a skip)",
      decide(MULTI, 1)["skipReason"],
      None)

# --- skip branch A: alreadyCommitted ---------------------------------------
COMMITTED_MID = {"id": "RUS-58", "slices": [{"alreadyCommitted": False},
                                            {"alreadyCommitted": True},
                                            {"alreadyCommitted": False}]}
check("alreadyCommitted slice ⇒ skip with reason alreadyCommitted, no diff range",
      decide(COMMITTED_MID, 2),
      {"run": False, "skipReason": "alreadyCommitted", "diffBase": None, "diffHead": None})

# A committed slice 1 still skips with alreadyCommitted (resume of a started stack).
COMMITTED_FIRST = {"id": "RUS-58", "slices": [{"alreadyCommitted": True},
                                              {"alreadyCommitted": False}]}
check("alreadyCommitted slice 1 ⇒ skip alreadyCommitted (resume), not a run",
      decide(COMMITTED_FIRST, 1),
      {"run": False, "skipReason": "alreadyCommitted", "diffBase": None, "diffHead": None})

# --- skip branch B: single-slice -------------------------------------------
SINGLE = {"id": "RUS-58", "slices": [{"alreadyCommitted": False}]}
check("len(slices) == 1, non-committed ⇒ skip with reason single-slice",
      decide(SINGLE, 1),
      {"run": False, "skipReason": "single-slice", "diffBase": None, "diffHead": None})

# --- precedence: a single COMMITTED slice yields alreadyCommitted ----------
SINGLE_COMMITTED = {"id": "RUS-58", "slices": [{"alreadyCommitted": True}]}
check("single committed slice ⇒ alreadyCommitted precedence over single-slice",
      decide(SINGLE_COMMITTED, 1),
      {"run": False, "skipReason": "alreadyCommitted", "diffBase": None, "diffHead": None})


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
