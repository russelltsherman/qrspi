# PR: RUS-40 Meta-agent diagnosis + revision loop (AC1/2/4; AC3 gated)

**Ticket:** RUS-40
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-09T00:00:00Z

## Summary

Turns the optimization loop from a structural no-op into a working diagnose→revise→report
pipeline. A new shared `scripts/meta_agent.py` seam shells the meta-agent over the
`using-claude-cli` path; `diagnose.py` now produces transcript-grounded `{category, rationale}`
classifications instead of string-matching heuristics, and `revise.py` emits concrete,
anchor-verified `old_text`/`new_text` edits that `apply_revisions` applies mechanically so
`revise_skill` returns `revised` when edits land. `report.py` gains a version-level `>0.05`
`test_score`-drop alert. Reviewer focus: (1) the defensive no-result/JSON-parse contract on the
shared seam (`meta_agent.NO_RESULT == ""`, never raises into `set -euo pipefail`); (2) the new
anchor-safety pass (`verify_anchor`) that skips missing/ambiguous anchors so the live skill is
never mis-written; (3) **Slice 5 (AC3 empirical convergence) is intentionally NOT implemented** —
it is gated on the stubbed runtime/judge dependency and unresolved OQ5, and is surfaced here for a
reviewer decision before any fixture authoring.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `diagnose.py` produces transcript-grounded categorizations, not heuristics | `scripts/diagnose.py:categorize_failure` (via `scripts/meta_agent.py:complete`) | `scripts/diagnose_test.py` (7 passed) |
| AC2: `revise.py` produces concrete `old_text`/`new_text` edits `apply_revisions` can apply; `revise_skill` → `revised` | `scripts/revise.py:propose_revisions`, `verify_anchor`, `_verify_anchors`, `revise_skill` | `scripts/revise_test.py` (13 passed) |
| AC3: Empirical convergence — `run_loop.sh` yields monotonically non-decreasing `test_score` | **GATED / not implemented** (Slice 5) — blocked on stubbed `run_eval.py`/`grade.py` (AC3 ext. dep) + unresolved OQ5 fixture/target | Fallback: `scripts/diagnose_test.py` + `scripts/revise_test.py` (mocked loop wiring) — see Open Items |
| AC4: `report.py` flags version `test_score` drop `>0.05` in `alerts` + `ledger.json` | `scripts/report.py:build_ledger_entry` (`VERSION_SCORE_DROP_THRESHOLD = 0.05`) | `scripts/report_test.py` (7 passed) |
| Cross-cutting: dry-run for human review; rationale/edit trace captured | `diagnose.py` `--dry-run`; `revise.py` `--dry-run` (now read-only re: `revision-log.json`); `anchor_checks` provenance | `diagnose_test.py`, `revise_test.py` (dry-run no-mutation cases) |

## Changes by Slice

### Slice 1: Shared meta-agent invocation seam

| File | Change | Lines |
|------|--------|-------|
| `scripts/meta_agent.py` | new | +145 |
| `scripts/meta_agent_test.py` | new | +131 |

### Slice 2: Grounded diagnosis via meta-agent

| File | Change | Lines |
|------|--------|-------|
| `scripts/diagnose.py` | modified | +104, -39 |
| `scripts/diagnose_test.py` | new | +213 |

### Slice 3: Concrete revisions with anchor-safe apply

| File | Change | Lines |
|------|--------|-------|
| `scripts/revise.py` | modified | +198, -48 |
| `scripts/revise_test.py` | new | +301 |

### Slice 4: Version-level regression guard in report.py

| File | Change | Lines |
|------|--------|-------|
| `scripts/report.py` | modified | +32, -5 |
| `scripts/report_test.py` | new | +131 |

### Slice 5: Under-specified convergence fixture + empirical loop run

GATED — not implemented. No files changed (no `evals/fixtures/` or `evals/golden/` additions).
See Open Items.

## Testing Summary

- [x] Slice 1: unit — `python3 scripts/meta_agent_test.py` — 15 passed, 0 failed
- [x] Slice 2: unit — `python3 scripts/diagnose_test.py` — 7 passed, 0 failed
- [x] Slice 3: unit — `python3 scripts/revise_test.py` — 13 passed, 0 failed
- [x] Slice 4: unit — `python3 scripts/report_test.py` — 7 passed, 0 failed
- [x] Regression: `meta_agent_test.py` + `diagnose_test.py` re-run OK after Slice 3
- [ ] Slice 5: AC3 e2e — `bash run_loop.sh` monotonic `test_score` — BLOCKED (stubbed runtime/judge; OQ5)
- [x] Manual verification: loop wiring (diagnose↔revise) validated via mocked-seam unit tests; live
  meta-agent path degrades gracefully when `claude` binary/output is absent (returns `NO_RESULT`)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `meta_agent.complete` failure mode | "raises or returns a sentinel" | Returns sentinel `NO_RESULT == ""`, never raises | Sentinel chosen over raise so failures never crash the `set -euo pipefail` loop (design Risk: unparseable JSON) |
| `revise_skill` no-edit status | plan §3.18 mandates `revised` only on ≥1 edit | Zero verified edits → `no_changes` (not the removed `pending_meta_agent`) | `pending_meta_agent` is the obsolete placeholder being deleted; matches existing `ALL_PASSING` → `no_changes` branch |
| `categorize_failure` return | `{category, rationale}` | Adds single-element `categories` list mirroring grounded `category` | Keeps `produce_diagnosis`' group-by-category assembly unchanged (additive) |
| `build_ledger_entry` signature | extend for drop alert | Adds optional `previous_grades=None` param | Additive; both call sites already compute `prev_grades`; baseline (None) raises no alert |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Meta-agent drifts prompt, regressing untested behavior (subtle <0.05 drops) | accepted — AC4 catches large drops; dry-run + captured rationale enable review; per-edit snapshot NOT wired (OQ2 deferred) | Revert offending skill edit from `revision-log.json`; restore skill file from VCS |
| No real runtime/judge — AC3 unobservable | discovered-confirmed — Slice 5 e2e gated; logic validated via mocked unit tests only | Disable loop convergence gating until runtime/judge lands |
| Meta-agent returns missing/non-unique/overlapping anchor — silent mis-edit | mitigated — `verify_anchor` skips+logs `missing`/`ambiguous`; excluded from `apply_revisions`; `anchor_checks` provenance recorded | None needed at apply time (edit skipped, skill untouched) |
| Model output not valid JSON / unparseable | mitigated — defensive parse → `NO_RESULT`/`None` → no-edit fallback, logged to stderr; loop not crashed | N/A (no-op on parse failure) |
| In-place skill overwrite with no backup | accepted — snapshot/rollback (OQ2) deferred to hardening; `--dry-run` enables pre-apply review | Restore skill from VCS history |
| dry-run mutates `revision-log.json` | mitigated — `revise_skill` returns early under `--dry-run`; skill + log untouched (test-verified) | N/A |

## Open Items

- **AC3 / Slice 5 — blocked, reviewer decision required.** Fixture (`evals/fixtures/`) and golden
  (`evals/golden/`) NOT authored; the `run_loop.sh` empirical-convergence checkpoint not run.
  Blockers: (1) OQ5 — exact under-specified skill prompt content + convergence target (per-case 0.9
  vs loop 0.85 `TARGET_SCORE`) + whether the run path consumes a golden file at all; (2) AC3 external
  dependency — real runtime/judge replacing the zero-producing `run_eval.py`/`grade.py` stubs must
  land first. Recommend a follow-up ticket once the runtime/judge dependency is available.
- **OQ1 — model id / invocation auth.** Seam shells `claude -p --output-format text
  --append-system-prompt`; model selection left to CLI/env (optional `model=None` param). Confirm
  intended model id and that CLI auth exists in the loop's execution environment.
- **OQ2 — skill snapshot/rollback deferred.** The commented `git checkout HEAD~1` rollback in
  `run_loop.sh` was NOT wired; in-place overwrite still has no per-edit backup. Hardening follow-up.
- **OQ3 — score scale.** 0.05 guard implemented as a plain 0–1 absolute delta (no normalization),
  mirroring `check_promotion_criteria`. Confirm scale assumption or normalization need.
- **OQ4 — `regression_risk` inversion** (`diagnose.py` `"low" if difficulty == "hard"`) left
  untouched — not in scope this ticket; confirm whether it is a bug to fix separately.
