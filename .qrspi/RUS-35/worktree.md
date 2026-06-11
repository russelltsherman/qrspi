# Work Tree — Fix run_loop.sh agent path references

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 (4 tasks; T2 fans into the three verification checkpoints T2a–T2c)

## Session 1

**Load:** structure.md §Slice 1, structure.md §Verification, plan.md §Slice 1, design.md §Delta, design.md §Decision 3
**Estimated context:** ~8% of window (single doc-only one-line edit + three grep/test checkpoints; no code reading beyond `run_loop.sh`)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | In `run_loop.sh`, replace the literal `.qrspi/agents/01-questions.md` with `.claude/agents/qrspi-questions.md` in the `#   Example:` comment; anchor on the literal string (not a line number), leave `evals/suite.json 5 0.85` unchanged; doc-only, no SKILL_PATH guard / ShellCheck / CI gate | — | §1.1 | S | pending |
| T2a | **Verify Slice 1** — `grep -n ".qrspi/agents/" run_loop.sh` returns empty (no stale reference remains) | T1 | §1.2 | S | pending |
| T2b | **Verify Slice 1** — `test -f .claude/agents/qrspi-questions.md && echo OK` prints `OK` (corrected path resolves to an existing file) | T1 | §1.3 | S | pending |
| T2c | **Verify Slice 1** — Record the empty-grep + `test -f` results as manual acceptance evidence in the PR body, and flag the cross-ticket land-ordering constraint (must land AFTER the runtime ticket making `run_eval.execute_single()` functional) | T2a, T2b | §1.4 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of plan. Single slice, single session; no further sessions. The land-ordering constraint in T2c is an orchestration gate for human attention, not a downstream task.
