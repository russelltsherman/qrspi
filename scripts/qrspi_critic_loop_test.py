#!/usr/bin/env python3
"""Unit tests for qrspi_critic_loop pure decision core: next_action's converge/revise/
cap_reached decision and parse_critic_verdict's fail-closed parsing. Stdlib-only,
assert-based, no third-party deps, no test runner.
Run: python3 scripts/qrspi_critic_loop_test.py

Covers (ref: structure §Slice 1 tests, plan §1.5-1.8, AC2/AC4, Q11):
  - pass-first-round  ⇒ converged on round 0, no revise (AC4)
  - fail→revise→pass  ⇒ revise then converged (AC2)
  - fail at cap        ⇒ cap_reached surfacing residual findings (AC2, AC4)
  - malformed/empty/garbage verdict ⇒ fail closed to NOT-passed, never raises (Q11)
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_critic_loop import (  # noqa: E402
    next_action,
    parse_critic_verdict,
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


# --- next_action: passing verdict at round 0 ⇒ converged, no revise (AC4) ---
check("passing verdict at round 0 ⇒ converged, no residual findings",
      next_action([{"pass": True, "findings": []}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})

check("passing verdict discards any findings on the verdict (converged carries none)",
      next_action([{"pass": True, "findings": ["a nit"]}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})

# --- next_action: fail→revise→pass sequence (AC2) ---------------------------
# Round 0, not passed, rounds remain ⇒ revise (carrying the critic's findings).
check("non-passing verdict at round 0 with rounds remaining ⇒ revise",
      next_action([{"pass": False, "findings": ["dropped req X"]}], round=0, max_rounds=2),
      {"action": "revise", "residual_findings": ["dropped req X"]})

# Next round, now passing ⇒ converged.
check("passing verdict on the next round ⇒ converged",
      next_action([{"pass": True, "findings": []}], round=1, max_rounds=2),
      {"action": "converged", "residual_findings": []})

# --- next_action: non-passing at the cap ⇒ cap_reached + residual (AC2, AC4) -
check("non-passing verdict at round == max_rounds-1 ⇒ cap_reached with residual findings",
      next_action([{"pass": False, "findings": ["still missing Y"]}],
                  round=1, max_rounds=2),
      {"action": "cap_reached", "residual_findings": ["still missing Y"]})

check("cap_reached at max_rounds=1 on the very first round",
      next_action([{"pass": False, "findings": ["never satisfied"]}],
                  round=0, max_rounds=1),
      {"action": "cap_reached", "residual_findings": ["never satisfied"]})

# Fail closed: an empty verdict list reads as NOT-passed (never "converged").
check("empty verdict list at the cap ⇒ cap_reached, not converged",
      next_action([], round=1, max_rounds=2),
      {"action": "cap_reached", "residual_findings": []})

check("empty verdict list with rounds remaining ⇒ revise, not converged",
      next_action([], round=0, max_rounds=2),
      {"action": "revise", "residual_findings": []})

# The LATEST (last) verdict is authoritative when more than one is supplied.
check("latest verdict is authoritative (last element wins)",
      next_action([{"pass": False, "findings": ["old"]},
                   {"pass": True, "findings": []}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})

# round/max_rounds accept str-coercible values (defensive int()).
check("round/max_rounds are int-coerced",
      next_action([{"pass": False, "findings": ["z"]}], round="1", max_rounds="2"),
      {"action": "cap_reached", "residual_findings": ["z"]})


# --- parse_critic_verdict: fail-closed parsing (Q11) ------------------------
check("well-formed verdict parses to canonical shape",
      parse_critic_verdict('{"pass": true, "findings": ["a", "b"]}'),
      {"pass": True, "findings": ["a", "b"]})

check("verdict embedded in prose is extracted",
      parse_critic_verdict('Here is my verdict:\n{"pass": false, "findings": ["x"]}\nDone.'),
      {"pass": False, "findings": ["x"]})

check("empty string ⇒ fail closed to NOT-passed",
      parse_critic_verdict(""),
      {"pass": False, "findings": []})

check("whitespace-only string ⇒ fail closed",
      parse_critic_verdict("   \n\t  "),
      {"pass": False, "findings": []})

check("non-JSON garbage ⇒ fail closed",
      parse_critic_verdict("the critic stalled and said nothing useful"),
      {"pass": False, "findings": []})

check("malformed JSON (truncated) ⇒ fail closed",
      parse_critic_verdict('{"pass": true, "findings": ['),
      {"pass": False, "findings": []})

check("empty JSON object ⇒ NOT-passed (missing pass defaults false)",
      parse_critic_verdict("{}"),
      {"pass": False, "findings": []})

check("JSON null ⇒ fail closed (not a dict)",
      parse_critic_verdict("null"),
      {"pass": False, "findings": []})

check("JSON list ⇒ fail closed (not a dict)",
      parse_critic_verdict('["pass", "findings"]'),
      {"pass": False, "findings": []})

check("None input ⇒ fail closed, never raises",
      parse_critic_verdict(None),
      {"pass": False, "findings": []})

check("pass present but findings is a scalar string ⇒ wrapped into a list",
      parse_critic_verdict('{"pass": false, "findings": "single finding"}'),
      {"pass": False, "findings": ["single finding"]})

check("truthy non-bool pass is coerced to bool",
      parse_critic_verdict('{"pass": 1, "findings": []}'),
      {"pass": True, "findings": []})

# Belt-and-suspenders: a battery of garbage inputs must never raise.
for bad in ["", "   ", "}{", "not json", "{pass:true}", "[1,2,3]", "42", "true",
            None, 12345, '{"findings": "x"}']:
    total += 1
    try:
        out = parse_critic_verdict(bad)
        if isinstance(out, dict) and out.get("pass") is False:
            print("ok: parse_critic_verdict(%r) failed closed without raising" % (bad,))
        else:
            failures += 1
            print("FAIL: parse_critic_verdict(%r) did not fail closed: %r" % (bad, out))
    except Exception as exc:  # noqa: BLE001 - the whole point is it must never raise
        failures += 1
        print("FAIL: parse_critic_verdict(%r) RAISED %r" % (bad, exc))


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
