# Implementation Plan — Fix run_loop.sh agent path references

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 4

## Slice 1: Correct the stale agent-path example comment

**Goal:** The `#   Example:` comment in `run_loop.sh` names a real on-disk agent
file so the documented invocation is copy-pasteable and `grep -n ".qrspi/agents/"
run_loop.sh` returns empty (ref: structure.md Slice 1; design.md §Delta).

### Core Logic

1. ⚠️ Modify `run_loop.sh` — in the `#   Example:` body (research-confirmed line 10),
   replace the unique literal string `.qrspi/agents/01-questions.md` with
   `.claude/agents/qrspi-questions.md`. Anchor the edit on the literal string, NOT on a
   line number, to sidestep the ticket's line-9/line-10 discrepancy (ref: design.md
   §Delta, Decision 1). The remainder of the example line
   (`evals/suite.json 5 0.85`) is correct and must stay unchanged. This is the entire
   delta — strictly doc-only; do not add a `SKILL_PATH` guard or ShellCheck/CI gate
   (ref: design.md §Delta scope boundary, Decision 2 Option A, Decision 3 Option A).
   - **Current:** `#   Example: .qrspi/agents/01-questions.md evals/suite.json 5 0.85`
   - **After:** `#   Example: .claude/agents/qrspi-questions.md evals/suite.json 5 0.85`

### Tests

No automated gate covers this script (no test, ShellCheck config, or CI exists; ref:
design.md §Decision 3, Q10). Verification is manual per the project's documented
manual-e2e posture for the eval harness. No test file is created (ref: design.md
Decision 3 Option A).

### Verify Slice 1

2. **Checkpoint:** `grep -n ".qrspi/agents/" run_loop.sh`
   - [ ] Returns empty — no stale `.qrspi/agents/` reference remains in the file
     (ref: structure.md Verification; design.md §Desired End State).

3. **Checkpoint:** `test -f .claude/agents/qrspi-questions.md && echo OK`
   - [ ] Prints `OK` — the corrected example path resolves to an existing file
     (ref: structure.md Verification).

4. **Checkpoint:** Record both grep + path-resolution checks as manual acceptance
   evidence in the PR body.
   - [ ] PR body documents the empty-grep result and the `test -f` success as the
     acceptance evidence, since no automated gate exists (ref: structure.md
     Verification; design.md §Decision 3 Option A).
   - [ ] PR/stack notes flag the cross-ticket land-ordering constraint: this ticket
     must land AFTER the runtime ticket that makes `run_eval.execute_single()`
     functional, so AC1's documented invocation is live at land time (ref:
     structure.md §Unverified Assumptions; design.md §Dependency & Merge Ordering /
     RQ1). This is an orchestration gate for human attention, not a code change.

---

## Rollback Notes

- Step 1: To reverse, restore the original example line — replace
  `.claude/agents/qrspi-questions.md` back with `.qrspi/agents/01-questions.md` in the
  `#   Example:` comment of `run_loop.sh`. Single-line comment edit; no runtime,
  config, DB, or destructive state involved, so rollback is a trivial inverse string
  replacement.
