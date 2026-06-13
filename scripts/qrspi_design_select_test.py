#!/usr/bin/env python3
"""Unit tests for qrspi_design_select.select — the pure judge-base selector that folds judge
output into one authoritative {winner, scores, graftDirectives}. Stdlib-only, assert-based via
check(), no test runner.
Run: python3 scripts/qrspi_design_select_test.py

Covers (ref: structure §Slice 1 Verification, plan §5/§6):
  - single-winner: highest score selected; winner's own graft_ideas excluded
  - tie: deterministic lowest-index tie-break
  - all-pass / multi-candidate: deduped runner-up graft_ideas, first-seen order
  - no-runners-up: empty graftDirectives ⇒ graft is a downstream no-op
  - empty input ⇒ fail-closed (SelectError raised; CLI exits non-zero with error envelope)
  - malformed input ⇒ fail-closed (SelectError raised; CLI exits non-zero with error envelope)
  - the judge's own `winner` field is ignored (selector computes deterministically)
"""

import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_design_select import select, SelectError  # noqa: E402

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


def check_raises(label, fn):
    global failures, total
    total += 1
    try:
        fn()
    except SelectError:
        print("ok: %s" % label)
        return
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print("FAIL: %s\n   raised non-SelectError: %r" % (label, exc))
        return
    failures += 1
    print("FAIL: %s\n   did not raise" % label)


# --- single-winner: highest score selected, winner's own graft excluded -----
single = {
    "scores": [
        {"candidate": "mvp-first", "score": 9, "rationale": "best", "graft_ideas": ["w-idea"]},
        {"candidate": "risk-first", "score": 5, "rationale": "ok", "graft_ideas": ["r-idea"]},
        {"candidate": "extensibility-first", "score": 7, "rationale": "good", "graft_ideas": ["e-idea"]},
    ],
}
r = select(single)
check("single-winner: highest score wins", r["winner"], "mvp-first")
check("single-winner: winner's own graft_ideas excluded; runner-ups deduped in order",
      r["graftDirectives"], ["r-idea", "e-idea"])
check("single-winner: scores echoed through unchanged", r["scores"], single["scores"])

# --- tie: deterministic lowest-index tie-break ------------------------------
tie = {
    "scores": [
        {"candidate": "risk-first", "score": 8, "graft_ideas": []},
        {"candidate": "mvp-first", "score": 8, "graft_ideas": ["m-idea"]},
        {"candidate": "extensibility-first", "score": 8, "graft_ideas": ["e-idea"]},
    ],
}
rt = select(tie)
check("tie ⇒ lowest-index candidate wins", rt["winner"], "risk-first")
check("tie ⇒ both non-winners' graft_ideas grafted (winner is index 0)",
      rt["graftDirectives"], ["m-idea", "e-idea"])

# --- dedup of duplicate graft_ideas across runner-ups, first-seen order -----
dup = {
    "scores": [
        {"candidate": "a", "score": 10, "graft_ideas": ["x"]},
        {"candidate": "b", "score": 2, "graft_ideas": ["dup", "uniq-b"]},
        {"candidate": "c", "score": 3, "graft_ideas": ["dup", "uniq-c"]},
    ],
}
check("duplicate runner-up graft_ideas deduped to first-seen order",
      select(dup)["graftDirectives"], ["dup", "uniq-b", "uniq-c"])

# --- no-runners-up: single candidate ⇒ empty graftDirectives ----------------
solo = {"scores": [{"candidate": "only", "score": 4, "graft_ideas": ["ignored-own"]}]}
rs = select(solo)
check("single candidate ⇒ it is the winner", rs["winner"], "only")
check("no runner-ups ⇒ empty graftDirectives (graft no-op)", rs["graftDirectives"], [])

# --- runner-ups present but no graft_ideas ⇒ empty graftDirectives ----------
no_ideas = {
    "scores": [
        {"candidate": "a", "score": 9},
        {"candidate": "b", "score": 1, "graft_ideas": []},
    ],
}
check("runner-up with empty/absent graft_ideas ⇒ empty graftDirectives",
      select(no_ideas)["graftDirectives"], [])

# --- judge's own `winner` field is ignored; selector is authoritative -------
override = {
    "winner": "loser",
    "scores": [
        {"candidate": "loser", "score": 1},
        {"candidate": "actual", "score": 9},
    ],
}
check("judge 'winner' field ignored; highest score wins", select(override)["winner"], "actual")

# --- float scores supported -------------------------------------------------
floats = {"scores": [{"candidate": "a", "score": 7.5}, {"candidate": "b", "score": 7.6}]}
check("float scores: highest float wins", select(floats)["winner"], "b")

# --- fail-closed: empty / malformed input -----------------------------------
check_raises("empty dict ⇒ SelectError", lambda: select({}))
check_raises("non-dict input ⇒ SelectError", lambda: select([]))
check_raises("scores not a list ⇒ SelectError", lambda: select({"scores": "nope"}))
check_raises("empty scores list ⇒ SelectError", lambda: select({"scores": []}))
check_raises("score entry not a dict ⇒ SelectError",
             lambda: select({"scores": ["bad"]}))
check_raises("score entry missing candidate ⇒ SelectError",
             lambda: select({"scores": [{"score": 1}]}))
check_raises("score entry empty candidate ⇒ SelectError",
             lambda: select({"scores": [{"candidate": "", "score": 1}]}))
check_raises("score entry missing numeric score ⇒ SelectError",
             lambda: select({"scores": [{"candidate": "a"}]}))
check_raises("score entry non-numeric score ⇒ SelectError",
             lambda: select({"scores": [{"candidate": "a", "score": "high"}]}))
check_raises("score entry bool score ⇒ SelectError (bool is not a numeric score)",
             lambda: select({"scores": [{"candidate": "a", "score": True}]}))


# --- CLI driver: fail-closed exit codes via subprocess ----------------------
def run_cli(stdin_text):
    proc = subprocess.run(
        [sys.executable, os.path.join(_HERE, "qrspi_design_select.py")],
        input=stdin_text, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


rc, out = run_cli(json.dumps(single))
check("CLI: well-formed input exits 0", rc, 0)
check("CLI: well-formed input emits winner", json.loads(out)["winner"], "mvp-first")

rc, out = run_cli("")
check("CLI: empty stdin exits non-zero (fail-closed)", rc != 0, True)
check("CLI: empty stdin emits error envelope", "error" in json.loads(out), True)

rc, out = run_cli("{not json")
check("CLI: malformed JSON exits non-zero (fail-closed)", rc != 0, True)
check("CLI: malformed JSON emits error envelope", "error" in json.loads(out), True)

rc, out = run_cli(json.dumps({"scores": []}))
check("CLI: empty scores exits non-zero (fail-closed)", rc != 0, True)


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
