#!/usr/bin/env python3
"""Unit tests for qrspi_critic_synthesize.synthesize — the pure M-lens verdict reducer.
Stdlib-only, assert-based, no third-party deps, no test runner.
Run: python3 scripts/qrspi_critic_synthesize_test.py

Covers (ref: structure §Slice 1 tests, plan §1.6, OQ2, §New Types SynthesizedVerdict):
  - all-pass            ⇒ pass:true, union of findings
  - one-fail            ⇒ pass:false (all-pass AND)
  - duplicate-across-lenses ⇒ exact-string deduped union (first-seen order)
  - empty/malformed lens entry ⇒ coerced fail-closed to NOT-passed, contributes no findings
  - optional lens-tagging ({text, lens}) when a lens identifier is present
  - reuse of the landed parse_critic_verdict (string lens replies coerce)
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_critic_synthesize import decide_round, synthesize  # noqa: E402

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


# --- all-pass ⇒ pass:true, union of findings --------------------------------
check("all lenses pass, no findings ⇒ pass:true, empty findings",
      synthesize([{"pass": True, "findings": []},
                  {"pass": True, "findings": []}]),
      {"pass": True, "findings": []})

check("all lenses pass but carry nits ⇒ pass:true, union preserved (untagged)",
      synthesize([{"pass": True, "findings": ["nit a"]},
                  {"pass": True, "findings": ["nit b"]}]),
      {"pass": True, "findings": ["nit a", "nit b"]})

# --- one-fail ⇒ pass:false (all-pass AND) -----------------------------------
check("one failing lens among passing ⇒ pass:false (all-pass AND)",
      synthesize([{"pass": True, "findings": []},
                  {"pass": False, "findings": ["dropped AC3"]},
                  {"pass": True, "findings": []}]),
      {"pass": False, "findings": ["dropped AC3"]})

check("all lenses fail ⇒ pass:false, union of all findings",
      synthesize([{"pass": False, "findings": ["x"]},
                  {"pass": False, "findings": ["y"]}]),
      {"pass": False, "findings": ["x", "y"]})

# --- duplicate-across-lenses ⇒ exact-string deduped union (first-seen order) -
check("identical finding from two lenses ⇒ deduped to one (first-seen order)",
      synthesize([{"pass": False, "findings": ["scope drift", "missing edge case"]},
                  {"pass": False, "findings": ["scope drift", "no rollback note"]}]),
      {"pass": False,
       "findings": ["scope drift", "missing edge case", "no rollback note"]})

check("exact-string dedup is case/whitespace sensitive (different strings kept)",
      synthesize([{"pass": False, "findings": ["Scope Drift"]},
                  {"pass": False, "findings": ["scope drift"]}]),
      {"pass": False, "findings": ["Scope Drift", "scope drift"]})

# --- empty/malformed lens entry ⇒ fail-closed NOT-passed, no findings --------
check("empty verdict list ⇒ pass:false (no lens vouched)",
      synthesize([]),
      {"pass": False, "findings": []})

check("non-list input ⇒ pass:false fail-closed",
      synthesize("garbage"),
      {"pass": False, "findings": []})

check("malformed lens entry (not a dict) ⇒ NOT-passed, no findings; drags pass false",
      synthesize([{"pass": True, "findings": ["ok finding"]},
                  None]),
      {"pass": False, "findings": ["ok finding"]})

check("empty dict lens entry ⇒ NOT-passed (missing pass defaults false), no findings",
      synthesize([{"pass": True, "findings": []},
                  {}]),
      {"pass": False, "findings": []})

check("lens entry with scalar (non-list) findings ⇒ wrapped, still counted",
      synthesize([{"pass": False, "findings": "single"}]),
      {"pass": False, "findings": ["single"]})

# --- string lens reply coerces via the landed parse_critic_verdict ----------
check("string lens reply (raw JSON text) is parsed via landed parse_critic_verdict",
      synthesize(['{"pass": true, "findings": ["from-string"]}']),
      {"pass": True, "findings": ["from-string"]})

check("garbage string lens reply ⇒ fail closed to NOT-passed, no findings",
      synthesize(["the lens stalled"]),
      {"pass": False, "findings": []})

# --- optional lens-tagging when a lens identifier is present ----------------
check("lens identifier present ⇒ bare-string findings get {text, lens} tag",
      synthesize([{"pass": False, "lens": "completeness",
                   "findings": ["missing AC2"]}]),
      {"pass": False,
       "findings": [{"text": "missing AC2", "lens": "completeness"}]})

check("mixed tagged/untagged lenses ⇒ each finding tagged per its own lens",
      synthesize([{"pass": False, "lens": "edge-alignment", "findings": ["scope drift"]},
                  {"pass": False, "findings": ["bare nit"]}]),
      {"pass": False,
       "findings": [{"text": "scope drift", "lens": "edge-alignment"}, "bare nit"]})

check("already-tagged {text, lens} finding kept verbatim; dedup keys on text",
      synthesize([{"pass": False, "lens": "simplicity",
                   "findings": [{"text": "overbuilt", "lens": "simplicity"}]},
                  {"pass": False, "lens": "other", "findings": ["overbuilt"]}]),
      {"pass": False,
       "findings": [{"text": "overbuilt", "lens": "simplicity"}]})

check("name key also serves as lens identifier",
      synthesize([{"pass": False, "name": "internal-consistency",
                   "findings": ["dangling ref"]}]),
      {"pass": False,
       "findings": [{"text": "dangling ref", "lens": "internal-consistency"}]})

# --- no lens privileged: order of lenses does not change pass outcome --------
check("lens order does not change pass outcome (no privilege) — fail first",
      synthesize([{"pass": False, "findings": ["a"]},
                  {"pass": True, "findings": []}]),
      {"pass": False, "findings": ["a"]})


# --- decide_round: synthesize + next_action in one (the panel-worker entry) -
# All lenses pass on a non-final round ⇒ converged, no residuals.
check("decide_round: all pass, round 0 of 2 ⇒ converged",
      decide_round([{"pass": True, "findings": []},
                    {"pass": True, "findings": []}], 0, 2),
      {"action": "converged", "pass": True,
       "synthesized_findings": [], "residual_findings": []})

# A failing lens with rounds remaining ⇒ revise, findings carried as residual.
check("decide_round: one fail, round 0 of 2 ⇒ revise with carried findings",
      decide_round([{"pass": True, "findings": []},
                    {"pass": False, "findings": ["dropped AC3"]}], 0, 2),
      {"action": "revise", "pass": False,
       "synthesized_findings": ["dropped AC3"],
       "residual_findings": ["dropped AC3"]})

# A failing lens on the FINAL allowed round ⇒ cap_reached, residual surfaced.
check("decide_round: fail on final round (round 1 of 2) ⇒ cap_reached",
      decide_round([{"pass": False, "findings": ["still missing rollback"]}], 1, 2),
      {"action": "cap_reached", "pass": False,
       "synthesized_findings": ["still missing rollback"],
       "residual_findings": ["still missing rollback"]})

# Lens-tagged findings flow through decide_round into synthesized + residual.
check("decide_round: lens-tagged findings carried into residual on revise",
      decide_round([{"pass": False, "lens": "completeness",
                     "findings": ["missing AC2"]}], 0, 2),
      {"action": "revise", "pass": False,
       "synthesized_findings": [{"text": "missing AC2", "lens": "completeness"}],
       "residual_findings": [{"text": "missing AC2", "lens": "completeness"}]})

# Empty verdict list fails closed ⇒ never converged (revise while rounds remain).
check("decide_round: empty verdicts fails closed ⇒ revise (not converged)",
      decide_round([], 0, 2),
      {"action": "revise", "pass": False,
       "synthesized_findings": [], "residual_findings": []})


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
