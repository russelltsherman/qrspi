#!/usr/bin/env python3
"""Unit tests for qrspi_critic_synthesize.synthesize — the pure multi-lens reducer that
folds M per-lens `{pass, findings}` verdicts into one authoritative round verdict.
Stdlib-only, assert-based via check(), no test runner.
Run: python3 scripts/qrspi_critic_synthesize_test.py

Covers (ref: structure §Slice 1 tests, plan §4, OQ2, Q11/Q12):
  - all lenses pass                ⇒ pass:true, no findings
  - one lens fails                 ⇒ pass:false, deduped union of all findings (AND semantics)
  - duplicate finding across lenses ⇒ deduped to one (exact-string union, first-seen order)
  - empty / malformed / non-dict lens entry ⇒ coerced NOT-passed, contributes no findings
  - optional lens-tagging of bare-string findings; pre-tagged findings pass through
  - reuse of the LANDED parse_critic_verdict (string entries coerce identically)
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_critic_synthesize import synthesize  # noqa: E402
from qrspi_critic_loop import parse_critic_verdict  # noqa: E402

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


# --- all lenses pass ⇒ pass:true, no findings -------------------------------
check("all four lenses pass ⇒ pass:true, no findings",
      synthesize([
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
      ]),
      {"pass": True, "findings": []})

check("all-pass lenses carrying nit findings ⇒ pass:true but findings still unioned",
      synthesize([
          {"pass": True, "findings": ["nit a"]},
          {"pass": True, "findings": ["nit b"]},
      ]),
      {"pass": True, "findings": ["nit a", "nit b"]})

# --- five-lens reduction (RUS-82: design-review is the fifth panel lens) -----
# The AND-reducer is unchanged by the new lens — it must still pass only when ALL five
# (the four edge-fidelity lenses + the new node-validity `design-review` lens) pass, and
# fail when any single one fails (here: design-review).
check("all five lenses pass (incl. design-review) ⇒ pass:true, no findings",
      synthesize([
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
          {"pass": True, "findings": []},
      ]),
      {"pass": True, "findings": []})

check("five lenses, only design-review fails ⇒ pass:false with its finding (AND over 5)",
      synthesize([
          {"pass": True, "findings": [], "lens": "completeness"},
          {"pass": True, "findings": [], "lens": "internal-consistency"},
          {"pass": True, "findings": [], "lens": "edge-alignment"},
          {"pass": True, "findings": [], "lens": "simplicity"},
          {"pass": False, "findings": ["false codebase claim: merge_lens_findings() absent"], "lens": "design-review"},
      ]),
      {"pass": False, "findings": [{"text": "false codebase claim: merge_lens_findings() absent", "lens": "design-review"}]})

# --- one lens fails ⇒ pass:false (AND semantics), union of findings ---------
check("one failing lens among passing ⇒ pass:false with that lens's findings",
      synthesize([
          {"pass": True, "findings": []},
          {"pass": False, "findings": ["dropped AC3"]},
          {"pass": True, "findings": []},
      ]),
      {"pass": False, "findings": ["dropped AC3"]})

check("multiple failing lenses ⇒ pass:false, ordered union of all findings",
      synthesize([
          {"pass": False, "findings": ["f1"]},
          {"pass": False, "findings": ["f2", "f3"]},
      ]),
      {"pass": False, "findings": ["f1", "f2", "f3"]})

# --- duplicate finding across lenses ⇒ deduped (exact-string, first-seen) ----
check("identical finding from two lenses ⇒ deduped to one, first-seen order",
      synthesize([
          {"pass": False, "findings": ["same issue", "only A"]},
          {"pass": False, "findings": ["same issue", "only B"]},
      ]),
      {"pass": False, "findings": ["same issue", "only A", "only B"]})

# --- empty / malformed / non-dict lens entry ⇒ coerced NOT-passed, no findings
check("empty verdict list ⇒ fail closed (no lens attested) ⇒ pass:false, no findings",
      synthesize([]),
      {"pass": False, "findings": []})

check("a non-dict (None) lens entry ⇒ coerced NOT-passed, contributes nothing",
      synthesize([
          {"pass": True, "findings": []},
          None,
      ]),
      {"pass": False, "findings": []})

check("a malformed-dict lens entry (missing pass) ⇒ NOT-passed, findings preserved",
      synthesize([
          {"pass": True, "findings": []},
          {"findings": ["salvaged"]},
      ]),
      {"pass": False, "findings": ["salvaged"]})

check("a lens entry with non-list findings ⇒ scalar wrapped (landed coercion)",
      synthesize([
          {"pass": False, "findings": "single"},
      ]),
      {"pass": False, "findings": ["single"]})

# --- optional lens-tagging ---------------------------------------------------
check("a lens carrying a `lens` id ⇒ its bare-string findings are wrapped {text, lens}",
      synthesize([
          {"pass": False, "findings": ["missing X"], "lens": "completeness"},
      ]),
      {"pass": False, "findings": [{"text": "missing X", "lens": "completeness"}]})

check("tagged + untagged lenses ⇒ each finding tagged only when its lens is identified",
      synthesize([
          {"pass": False, "findings": ["a"], "lens": "simplicity"},
          {"pass": False, "findings": ["b"]},
      ]),
      {"pass": False, "findings": [{"text": "a", "lens": "simplicity"}, "b"]})

check("dedupe keys on finding TEXT across tagged/untagged ⇒ first-seen wins",
      synthesize([
          {"pass": False, "findings": ["dup"], "lens": "edge-alignment"},
          {"pass": False, "findings": ["dup"]},
      ]),
      {"pass": False, "findings": [{"text": "dup", "lens": "edge-alignment"}]})

check("a pre-structured {text, lens} finding passes through unchanged and dedupes by text",
      synthesize([
          {"pass": False, "findings": [{"text": "pre", "lens": "internal-consistency"}]},
          {"pass": False, "findings": ["pre"]},
      ]),
      {"pass": False, "findings": [{"text": "pre", "lens": "internal-consistency"}]})

# --- reuse of the landed parse_critic_verdict: string entries coerce the same -
check("a JSON-string lens entry is coerced via the landed parse_critic_verdict",
      synthesize(['{"pass": false, "findings": ["from string"]}']),
      {"pass": False, "findings": ["from string"]})

check("a garbage-string lens entry ⇒ landed parser fails it closed (NOT-passed, no findings)",
      synthesize(["the lens stalled"]),
      {"pass": False, "findings": []})

# Assert the reuse is real: a string entry's synthesis matches parse_critic_verdict's
# own coercion (no re-implemented coercion path in synthesize).
_pv = parse_critic_verdict('{"pass": true, "findings": ["x"]}')
check("synthesize of a single passing string entry matches parse_critic_verdict's coercion",
      synthesize(['{"pass": true, "findings": ["x"]}']),
      {"pass": _pv["pass"], "findings": _pv["findings"]})

# --- never raises on a battery of garbage -----------------------------------
for bad in [[], [None], [42], ["not json"], [{"x": 1}], [{"pass": True}], None, "not a list"]:
    total += 1
    try:
        out = synthesize(bad)
        if isinstance(out, dict) and "pass" in out and isinstance(out.get("findings"), list):
            print("ok: synthesize(%r) returned a well-formed verdict without raising" % (bad,))
        else:
            failures += 1
            print("FAIL: synthesize(%r) returned a malformed result: %r" % (bad, out))
    except Exception as exc:  # noqa: BLE001 - synthesize must never raise
        failures += 1
        print("FAIL: synthesize(%r) RAISED %r" % (bad, exc))


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
