# PR: RUS-35 Fix stale agent-path example in run_loop.sh header

**Ticket:** RUS-35
**Design:** design.md @ 2026-06-09T00:00:00Z (revision-1)
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

The `#   Example:` comment in `run_loop.sh` documented a copy-paste invocation
pointing at `.qrspi/agents/01-questions.md` — a path that does not exist on disk
(neither the `.qrspi/agents/` directory nor the `01-questions.md` filename). Agent
files actually live at `.claude/agents/qrspi-<phase>.md`. This PR corrects that
single example line to `.claude/agents/qrspi-questions.md` so the documented command
is copy-pasteable and resolves to a real file. The change is strictly doc-only: one
comment line, no executable code, arg parsing, or control-flow change (per RQ2 "keep
scope"). Reviewers should focus on (a) the LAND-ORDERING CONSTRAINT — this ticket
must land **after** the runtime ticket that makes `run_eval.execute_single()`
functional (RQ1), so AC1's invocation is live at land time — and (b) confirming no
other `.qrspi/agents/` reference remains.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `./run_loop.sh .claude/agents/qrspi-questions.md evals/suite.json` runs without errors (once the runtime ticket lands) | `run_loop.sh:10` (`#   Example:` body) | Manual: `test -f .claude/agents/qrspi-questions.md && echo OK` → prints `OK` (documented path resolves to an existing file) |
| AC2: Header comment references the correct path | `run_loop.sh:10` | Manual: corrected line reads `.claude/agents/qrspi-questions.md` (see diff) |
| AC3: Any other `.qrspi/agents/` references in the script are updated | `run_loop.sh` (whole file) | Manual: `grep -n ".qrspi/agents/" run_loop.sh` → empty (exit 1, no stale reference remains) |

## Changes by Slice

### Slice 1: Correct the stale agent-path example comment

| File | Change | Lines |
|------|--------|-------|
| `run_loop.sh` | ⚠️ modified | +1, -1 |

The following files in the diff are QRSPI workflow artifacts (phase outputs), not
product code:

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-35/questions.md` | ✨ new (Questions phase) | +53 |
| `.qrspi/RUS-35/research.md` | ✨ new (Research phase) | +256 |
| `.qrspi/RUS-35/design.md` | ✨ new (Design phase) | +178 |
| `.qrspi/RUS-35/structure.md` | ✨ new (Structure phase) | +65 |
| `.qrspi/RUS-35/plan.md` | ✨ new (Plan phase) | +63 |
| `.qrspi/RUS-35/worktree.md` | ✨ new (Worktree phase) | +22 |
| `.qrspi/RUS-35/impl-log.md` | ✨ new (Implementation phase) | +34 |

## Testing Summary

- [x] Slice 1: stale-reference check — `grep -n ".qrspi/agents/" run_loop.sh` — returns empty (exit 1), no stale reference remains
- [x] Slice 1: path-resolution check — `test -f .claude/agents/qrspi-questions.md && echo OK` — prints `OK`
- [x] Manual verification: the corrected example line is copy-pasteable; only the agent-path segment changed, `evals/suite.json 5 0.85` is unchanged

No automated gate (ShellCheck/CI) exists for this script; per design Decision 3
Option A, manual grep + documented dry invocation is the acceptance evidence,
proportionate to a one-line comment fix.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | impl-log records no deviations from structure.md or plan.md |

Note: the literal target string `.qrspi/agents/01-questions.md` appears on line 10
within the full example line (the plan's "Current"/"After" quotes omitted the
`./run_loop.sh ` prefix), but the edit anchored on the unique literal string as
instructed (Decision 1), so the correct line was matched. This is the planned
string-anchored behavior, not a deviation.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Edit targets line 9 (per ticket) instead of actual line 10, missing the stale path | mitigated — edit anchored on unique literal string; `grep -n ".qrspi/agents/" run_loop.sh` returns empty post-edit | Revert the one-line change in `run_loop.sh` |
| "Runs without errors" misread as "produces real eval results" | accepted — AC1 scoped to shell driver completing; executor is a placeholder, unchanged by this ticket | n/a (documentation framing) |
| A second `.qrspi/agents/` reference is missed | mitigated — post-edit grep confirms exactly zero occurrences remain | Revert the one-line change |
| AC1 invocation cannot be exercised until the runtime ticket lands | accepted/fixed by RQ1 — merge ordering is fixed: this ticket lands **after** the runtime ticket; AC2/AC3 verifiable now | Hold the stack; do not land ahead of the runtime ticket |

## Open Items

- **LAND-ORDERING CONSTRAINT (human-attention gate, RQ1):** This ticket must land
  AFTER the runtime ticket that makes `run_eval.execute_single()` functional, so
  AC1's documented invocation is live (not merely compilable) at land time. This is a
  cross-ticket orchestration constraint, not a code change — flagged for human
  attention at stack-ordering / land time (ref: structure.md §Unverified Assumptions;
  design.md §Dependency & Merge Ordering / RQ1).
- No `SKILL_PATH` existence guard was added (Decision 2 Option A) and no ShellCheck/CI
  gate was introduced (Decision 3 Option A) — deliberately out of scope per RQ2. If
  regression protection is later wanted, a follow-up ticket could add a ShellCheck
  config or smoke test (no `.github/` CI exists today to run it).
