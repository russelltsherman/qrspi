# Implementation Log — Bring the /review-* on-demand review family up to manual-review depth

## Session 1 — Slice 1

**Timestamp:** 2026-06-18T02:44:22Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 42 passed, 0 failed
- `python3 scripts/run_tests.py critic` → 6 passed, 0 failed
- `python3 scripts/run_tests.py synopsis` → 1 passed, 0 failed

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- T8 (`qrspi_critic_summary.py`) confirmed a NO-OP, as the plan anticipated (step 8 / Unverified Assumption 1): `summarize` already reads every row field via `.get()` and buckets per-lens on the bare `rnd["lens"]`. The new optional `axes`/`nonBlockingNotes` row fields are inert to its math, so no source change was made — only the backward-compat test (T9) was added.

**Notes for next session:**

- New config constants in `scripts/qrspi_critics_config.py` (all importable):
  - `DEFAULT_REVIEW_DESIGN_LENSES = ("completeness", "internal-consistency", "edge-alignment", "simplicity", "design-review")` — ORDERED tuple; DISTINCT from the batch `DEFAULT_DESIGN_LENSES` (four lenses, no `design-review`).
  - `DEFAULT_REVIEW_PLAN_LENSES = ("plan-review", "plan-fidelity", "plan-completeness")`
  - `DEFAULT_REVIEW_IMPL_LENSES = ("impl-review", "impl-fidelity", "impl-completeness")`
  - `KNOWN_PLAN_LENSES` / `KNOWN_IMPL_LENSES` — `set(...)` allow-lists of the two panels.
  - Lens id → agent mapping is `qrspi-<phase>-critic-<lens-id>`. Plan/impl ids are phase-qualified (e.g. `plan-fidelity` → `qrspi-plan-critic-plan-fidelity`). The Slice 2 agent FILENAMES must therefore be `qrspi-plan-critic-plan-fidelity.md`, `qrspi-plan-critic-plan-completeness.md`, `qrspi-impl-critic-impl-fidelity.md`, `qrspi-impl-critic-impl-completeness.md` — NOTE the worktree.md task table (T14/T16/T18/T20) lists shorter names (`qrspi-plan-critic-fidelity.md` etc.); the structure.md/plan.md authoritative names (phase-qualified) are the ones that resolve correctly. Follow structure.md/plan.md, not the worktree.md filename shorthand.

- New module `scripts/qrspi_review_synopsis.py` (pure stdlib, no I/O). Public API the Slice 3+ skills will call:
  - `partition_decision_readiness(verdict_array) -> (panel_array, decision_readiness_verdict_or_None)` — splits the `decision-readiness` lens element out of the pre-reduction verdict array so it never reaches `qrspi_critic_synthesize.py`. Returns `None` for the DR verdict when the lens is absent.
  - `render_synopsis(verdict_array, decision_readiness, terminal_action) -> str` — Markdown synopsis: an axis-enumeration table (one row per lens: `| <lens> | PASS|FAIL | <blockingCount> |`), an "Advisory (non-blocking)" section (union of each lens's `nonBlockingNotes`, omitted if empty), a "Decision readiness (blocking for human)" section (DR `blockingDecisions`, omitted if DR is None or has no blocking items), and a `**Terminal action:** <x>` line. Accepts `decision_readiness=None`.
  - `ledger_row_fields(verdict_array) -> {"axes": [{"lens","pass","blockingCount"}], "nonBlockingNotes": [str]}` — the additive `critic-metrics.jsonl` fields. Per plan step 34, MERGE this dict onto the row dict returned by `qrspi_review_record.build_record(...)` before appending the metrics row (it is NOT a `build_record` parameter).
  - `DECISION_READINESS_LENS = "decision-readiness"` — the lens-id constant the partition keys on.

- `LensVerdict` shape consumed by these helpers: `{"lens": str, "pass": bool, "findings": [str], "nonBlockingNotes": [str](optional)}`. `findings` is the BLOCKING channel (drives `blockingCount`); `nonBlockingNotes` is advisory only. `blockingCount` = `len(findings)`.

- `DecisionReadinessVerdict` shape: `{"lens": "decision-readiness", "blockingDecisions": [{"question": str, "rationale": str}], "answerable": [{"question": str}]}`.

---
