# Work Tree — Wire up agent execution runtime in run_eval.py

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T18

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1, design.md §Delta
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/requirements.txt` with pinned `anthropic==0.49.0` | — | §1.1 | S | pending |
| T2 | Add `executed: bool = False` sentinel to `ExecutionResult` dataclass | — | §1.2 | S | pending |
| T3 | Add module-level `call_model` seam (local `anthropic` import, timeout, token normalization) | T2 | §1.3 | M | pending |
| T4 | Thread `model`/`max_tokens` from `suite.json` defaults through `run_suite` | T3 | §1.4 | M | pending |
| T5 | Rewrite `execute_single` body to call the seam and populate fields | T4 | §1.5 | M | pending |
| T6 | Add `--agent` as argparse alias for `--skill` | T5 | §1.6 | S | pending |
| T7 | Create `scripts/run_eval_test.py` (stdlib-only sibling, stubbed `call_model`) | T6 | §1.7 | S | pending |
| T8 | Add success-path assertion (populated output/tokens/transcript, executed==True) | T7 | §1.8 | S | pending |
| T9 | Add error-capture assertion (stub raises → result.error, executed==False) | T8 | §1.9 | S | pending |
| T10 | Add timeout assertion (timeout exception → result.error, executed==False) | T9 | §1.10 | S | pending |
| T11 | Add token-normalization assertion (`{input, output}` keys only) | T10 | §1.11 | S | pending |
| T12 | Run `python3 scripts/run_eval_test.py` (offline, no API key) | T11 | §1.12 | S | pending |
| T13 | **Verify Slice 1** — checkpoint: tests pass offline, no `anthropic` at import, `executed` field + `--agent` alias present | T12 | §1.13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (offline pure-logic runtime verified). Slice 2 is a live, network-dependent acceptance run against the real API — a fresh context avoids carrying Slice 1 edit detail and isolates the cost-incurring run.

## Session 2

**Load:** plan.md §Slice 2, design.md §AC4, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Confirm valid Anthropic API key present in SDK env var (no code change) | T13 | §2.14 | S | pending |
| T15 | Run documented `--skill` invocation against questions suite → fresh `--output` | T14 | §2.15 | S | pending |
| T16 | Inspect `results.json`: non-empty, all `executed==True`, real output/tokens/transcript | T15 | §2.16 | S | pending |
| T17 | Re-run substituting `--agent` for `--skill`; assert identical behavior | T16 | §2.17 | S | pending |
| T18 | **Verify Slice 2** — checkpoint: real results, within ~$20 ceiling, `--agent` ≡ `--skill` | T16 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Feature complete — both slices verified. No further sessions.
