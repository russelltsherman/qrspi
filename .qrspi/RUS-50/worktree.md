# Work Tree — qrspi resolver: respect Linear blockedBy relations at the entry gate

**Plan basis:** plan.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T9 → T10 → T11 (Slice 1 plumbing → resolver gate → tests pass → checkpoint) → T13 → T14 → T15 → T16 (Slice 2 worker classification → e2e verify)

## Session 1 — Slice 1: Resolver blockedOpen gate + state plumbing + tests

**Load:** structure.md §Contracts (`build_state`, `resolve`, `qrspi_resolve.py argparse`, `qrspi_pr_state.py standalone CLI argparse`, `contains` NEW test helper), plan.md §Slice 1, design §Delta + AC1–AC4 + RD2/RD4
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add `blocked_open=False` / `blocked_by=None` kwargs to `build_state(...)` in `scripts/qrspi_pr_state.py`; write `blockedOpen` / `blockedBy` into returned state dict | — | §1.1 | S | pending |
| T2 | Extend entry-gate branch in `scripts/qrspi_resolve_state.py` — when assigned + Selected + `blockedOpen` truthy, return `entry_blocked` with reason folding in every `blockedBy` identifier; else `run_design` | T1 | §1.2 | M | pending |
| T3 | Add `--blocked-open` / `--blocked-by` to `scripts/qrspi_resolve.py` argparse; forward into `build_state(...)` call | T1 | §1.3 | S | pending |
| T4 | Add matching `--blocked-open` / `--blocked-by` to `scripts/qrspi_pr_state.py` standalone CLI argparse; thread into its `build_state(...)` call | T1 | §1.4 | S | pending |
| T5 | Extend `state(...)` factory in `scripts/qrspi_resolve_state_test.py` with `blockedOpen=False` / `blockedBy=None` params | T2 | §1.5 | S | pending |
| T6 | Add `contains(reason, needle) -> bool` substring-assertion helper to `scripts/qrspi_resolve_state_test.py` | T5 | §1.6 | S | pending |
| T7 | Add resolver cases to `scripts/qrspi_resolve_state_test.py` — blocked+Selected→`entry_blocked` (assert via `contains`), unblocked+Selected→`run_design`, in-flight+blocked→unchanged | T6 | §1.7 | M | pending |
| T8 | Add `build_state(..., blocked_open=True, blocked_by=["RUS-99"])` case to `scripts/qrspi_pr_state_test.py`; assert `blockedOpen`/`blockedBy` keys; confirm defaults keep callers green | T1 | §1.8 | S | pending |
| T9 | Run `python3 scripts/qrspi_resolve_state_test.py` — all cases pass | T7 | §1.9 | S | pending |
| T10 | Run `python3 scripts/qrspi_pr_state_test.py` — all cases pass | T8 | §1.10 | S | pending |
| T11 | **Verify Slice 1** — checkpoint: run both test files; manual `qrspi_resolve.py --assigned --linear-status Selected --blocked-open --blocked-by RUS-99` → `entry_blocked` with `RUS-99` in reason; dropping `--blocked-open` → `run_design` | T9, T10 | §1.11–1.12 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (Python resolver + tests) complete and verified. Slice 2 touches a different surface (`.claude/workflows/qrspi-batch.js` resolve prompt) and needs no Python implementation detail loaded — fresh context keeps utilization low and avoids carrying test-file noise.

## Session 2 — Slice 2: Resolve-worker blocker classification (MCP read → flag reduction)

**Load:** structure.md §Slice 2 (Files touched), plan.md §Slice 2, design §Delta + RD1/RD3/RD4 + Risk Register rows 2–3, impl-log.md §Slice 1 (CLI flag names `--blocked-open`/`--blocked-by` only)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Extend resolve-prompt step 1 in `.claude/workflows/qrspi-batch.js` to read `blockedBy` relations from `mcp__linear__get_issue` (plus any per-blocker follow-up read for status type; verify payload shape live, RD1) | T11 | §2.13 | M | pending |
| T14 | In the resolve prompt, classify each blocker as open unless status type is `completed`/`canceled`; treat unknown/unrecognized as open (RD3, fail toward blocking) | T13 | §2.14 | M | pending |
| T15 | In resolve-prompt step 3, conditionally append `--blocked-open` only on positive open-blocker detection and pass all open-blocker ids via `--blocked-by`; absent/empty/unreadable → omit → `run_design` (fail-safe, RD4) | T14 | §2.15 | M | pending |
| T16 | **Verify Slice 2** — manual e2e: open-blocker ticket → `entry_blocked` naming blocker(s); all-`completed`/`canceled` or relation-less → flag omitted → `run_design`; confirm RD1 payload shape (one call vs per-blocker read) | T15 | §2.16 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. Both slices implemented and verified; stack ready for PR. No further session required.
