# Structure Outline — Fix run_loop.sh agent path references

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

None. This is a documentation-string correction; no data structures are introduced.

## Modified Types

None. No types, function signatures, arg parsing, or control flow change (ref: design.md §Delta).

## Contracts

None. The change is confined to a single comment line in `run_loop.sh`. The
existing runtime contract is unchanged and stated here only for reference (not
modified by this ticket):

- `run_loop.sh <SKILL_PATH> <EVAL_SUITE> [max_iter=5] [target_score=0.85]` — driver
  passes `SKILL_PATH` verbatim as `--skill` to `run_eval.py` / `diagnose.py` /
  `revise.py`; path is used as-is (no `cd`/`realpath`), i.e. "run from repo root"
  (ref: design.md §Current State). **Unchanged by this ticket.**

## Slice 1: Correct the stale agent-path example comment

**Goal:** The header `#   Example:` comment in `run_loop.sh` names an on-disk agent
file, so the documented invocation is copy-pasteable and `grep -n ".qrspi/agents/"
run_loop.sh` returns empty. This is the entire feature delivered end-to-end as one
testable change.
**Files touched:**

- ⚠️ `run_loop.sh` — in the `#   Example:` body (research-confirmed line 10), replace
  the unique literal string `.qrspi/agents/01-questions.md` with
  `.claude/agents/qrspi-questions.md`; the rest of the example line
  (`evals/suite.json 5 0.85`) is correct and stays. Anchor on the literal string, not
  the line number, to sidestep the ticket's line-9/line-10 discrepancy
  (ref: design.md §Delta, Decision 1).
**Verification:**
- [ ] `grep -n ".qrspi/agents/" run_loop.sh` returns empty (no stale reference remains).
- [ ] The corrected example path resolves to an existing file:
      `test -f .claude/agents/qrspi-questions.md` succeeds.
- [ ] Record both checks as the manual acceptance evidence in the PR (no automated
      gate exists for this script; ref: design.md §Decision 3 Option A).
**Context cost:** S
**Depends on:** none

---

## Unverified Assumptions

- **Merge/land ordering is gated behind a "runtime ticket" (RQ1).** The design states
  this ticket must land *after* the ticket that makes `run_eval.execute_single()`
  functional, so AC1's documented invocation is live (not merely compilable) at land
  time. This is a cross-ticket orchestration constraint, not a code artifact — it
  cannot be mapped to any type, file, or interface in this structure. The structure
  here delivers AC2/AC3 (the comment fix), which are independently verifiable now; the
  AC1 "runs without errors" live check depends on the external runtime ticket and is
  out of scope for this slice. Flagged for human attention at land/stack-ordering time.
- **AC1 "runs without errors" semantics.** Per design, the eval runtime is a
  placeholder (`execute_single()` returns empty output / zeroed metrics), so "without
  errors" means the shell driver completes — not that meaningful evaluation occurs. No
  code in this slice changes that; the assumption is recorded so the AC1 dry-invocation
  check is not misread as validating real eval results.
