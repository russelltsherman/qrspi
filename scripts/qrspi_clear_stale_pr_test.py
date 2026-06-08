#!/usr/bin/env python3
"""Unit tests for qrspi_clear_stale_pr pure helpers (ticket-branch matching, the
prInfos prune transform, and the atomic file round-trip). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_clear_stale_pr_test.py

The subprocess-backed part (pr_info_path -> `git rev-parse --git-common-dir`) is
intentionally NOT tested here -- same convention as qrspi_restack_test.py /
qrspi_persist_test.py -- and is verified by a manual end-to-end run against a
deliberately-stale association.
"""

import json
import os
import sys
import tempfile

from qrspi_clear_stale_pr import (
    belongs_to_ticket,
    prune_entries,
    prune_file,
)

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


def entry(head_ref, state, pr=1):
    """A minimal prInfos entry -- only the fields the prune logic reads."""
    return {"headRefName": head_ref, "state": state, "prNumber": pr}


# --- belongs_to_ticket ------------------------------------------------------
check("design branch belongs to its ticket",
      belongs_to_ticket("RUS-3/design", "RUS-3"), True)
check("slice branch belongs to its ticket",
      belongs_to_ticket("RUS-3/slice-2", "RUS-3"), True)
check("trailing slash stops RUS-3 from matching RUS-30/design",
      belongs_to_ticket("RUS-30/design", "RUS-3"), False)
check("bare ticket name (no /phase) does not belong",
      belongs_to_ticket("RUS-3", "RUS-3"), False)
check("other ticket does not belong",
      belongs_to_ticket("RUS-9/design", "RUS-3"), False)
check("non-string head ref is safe (None)",
      belongs_to_ticket(None, "RUS-3"), False)


# --- prune_entries (pure) ---------------------------------------------------
check("MERGED entry for the ticket is removed",
      prune_entries({"prInfos": [entry("RUS-3/design", "MERGED", 79)]}, "RUS-3"),
      ({"prInfos": []}, [{"headRefName": "RUS-3/design", "prNumber": 79, "state": "MERGED"}]))

check("CLOSED entry for the ticket is removed",
      prune_entries({"prInfos": [entry("RUS-3/plan", "CLOSED", 80)]}, "RUS-3"),
      ({"prInfos": []}, [{"headRefName": "RUS-3/plan", "prNumber": 80, "state": "CLOSED"}]))

check("OPEN entry for the ticket is PRESERVED (data unchanged, nothing removed)",
      prune_entries({"prInfos": [entry("RUS-3/design", "OPEN")]}, "RUS-3"),
      ({"prInfos": [entry("RUS-3/design", "OPEN")]}, []))

check("MERGED entry for a DIFFERENT ticket is preserved",
      prune_entries({"prInfos": [entry("RUS-9/design", "MERGED")]}, "RUS-3"),
      ({"prInfos": [entry("RUS-9/design", "MERGED")]}, []))

check("RUS-30 merged entry is NOT pruned for ticket RUS-3 (prefix exactness)",
      prune_entries({"prInfos": [entry("RUS-30/design", "MERGED")]}, "RUS-3"),
      ({"prInfos": [entry("RUS-30/design", "MERGED")]}, []))

# Mixed cache: drop only this ticket's stale entries; keep its OPEN entry and others.
mixed = {"prInfos": [
    entry("RUS-3/design", "MERGED", 1),   # drop
    entry("RUS-3/plan", "OPEN", 2),       # keep (open)
    entry("RUS-3/slice-1", "CLOSED", 3),  # drop
    entry("RUS-9/design", "MERGED", 4),   # keep (other ticket)
]}
new_mixed, removed_mixed = prune_entries(mixed, "RUS-3")
check("mixed: kept entries are open RUS-3/plan + other-ticket RUS-9/design",
      new_mixed["prInfos"], [entry("RUS-3/plan", "OPEN", 2), entry("RUS-9/design", "MERGED", 4)])
check("mixed: removed exactly the two stale RUS-3 entries",
      [r["headRefName"] for r in removed_mixed], ["RUS-3/design", "RUS-3/slice-1"])

check("idempotent: re-pruning the already-pruned data removes nothing",
      prune_entries(new_mixed, "RUS-3"), (new_mixed, []))

# Malformed / defensive inputs never raise and never drop anything.
check("missing prInfos key -> unchanged",
      prune_entries({"other": 1}, "RUS-3"), ({"other": 1}, []))
check("prInfos not a list -> unchanged",
      prune_entries({"prInfos": "nope"}, "RUS-3"), ({"prInfos": "nope"}, []))
check("non-dict data -> unchanged",
      prune_entries(["x"], "RUS-3"), (["x"], []))
check("entry missing headRefName/state is preserved (no crash)",
      prune_entries({"prInfos": [{"prNumber": 5}]}, "RUS-3"),
      ({"prInfos": [{"prNumber": 5}]}, []))

# Returned data must not alias the input when a change is made (callers may keep both).
src = {"prInfos": [entry("RUS-3/design", "MERGED")]}
out, _ = prune_entries(src, "RUS-3")
check("prune does not mutate the caller's input dict",
      src, {"prInfos": [entry("RUS-3/design", "MERGED")]})
check("prune returns a distinct object when it changes data", out is src, False)


# --- prune_file (temp-file round-trip) --------------------------------------
def write_cache(obj):
    fd, path = tempfile.mkstemp(suffix=".graphite_pr_info")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh)
    return path


# missing file -> clean no-op
missing = os.path.join(tempfile.gettempdir(), "definitely-not-here-qrspi-test.json")
check("missing cache file is a clean no-op", prune_file(missing, "RUS-3"), ([], None))

# valid file with a stale entry -> removed, file rewritten, open entry kept
p = write_cache({"prInfos": [entry("RUS-3/design", "MERGED", 79), entry("RUS-3/plan", "OPEN", 2)]})
removed, warning = prune_file(p, "RUS-3")
check("file: stale entry reported removed", [r["headRefName"] for r in removed], ["RUS-3/design"])
check("file: no warning on a clean prune", warning, None)
with open(p) as fh:
    after = json.load(fh)
check("file: rewritten cache keeps only the OPEN entry",
      after, {"prInfos": [entry("RUS-3/plan", "OPEN", 2)]})
check("file: re-running on the pruned file removes nothing (idempotent)",
      prune_file(p, "RUS-3"), ([], None))
os.remove(p)

# unparseable file -> left untouched, non-fatal warning, no crash
bad = write_cache(None)
with open(bad, "w") as fh:
    fh.write("{ this is not json ]")
removed_bad, warning_bad = prune_file(bad, "RUS-3")
check("file: unparseable cache removes nothing", removed_bad, [])
check("file: unparseable cache yields a non-fatal warning", warning_bad is not None, True)
with open(bad) as fh:
    check("file: unparseable cache is left byte-for-byte untouched", fh.read(), "{ this is not json ]")
os.remove(bad)


print("\n%d passed, %d failed" % (total - failures, failures))
sys.exit(1 if failures else 0)
