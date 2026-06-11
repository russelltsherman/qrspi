# Work Tree — Implement meta-agent diagnosis + revision loop

**Plan basis:** plan.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T1 → T2 → T3 → T4 → T6 → T7 → T9 → T10 → T15 → T16 → T18 → T22 → T23

> Critical path = the shared seam (Slice 1) gates the two meta-agent consumers (Slices 2 & 3), which both gate the Slice 5 loop run. Slice 4 (report.py guard) is independent of the seam and runs in parallel with Slices 2–3, so it is off the critical path.

## Session 1

**Load:** structure.md §Types, structure.md §Contracts (single shared LLM-invocation seam), plan.md §Slice 1
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/meta_agent.py` module + docstring (Decision 1, Option A: wrapper over `using-claude-cli` subprocess) | — | §1.1 | S | pending |
| T2 | Implement `complete(system, user) -> str` shelling out to the claude-cli path, returning raw model text | T1 | §1.2 | M | pending |
| T3 | Add defensive failure handling: subprocess error / non-zero exit yields logged no-result sentinel, no crash | T2 | §1.3 | S | pending |
| T4 | Create `scripts/meta_agent_test.py` (mocks subprocess seam: normal call returns text; failure returns sentinel) | T3 | §1.4 | S | pending |
| T5 | **Verify Slice 1** — `python3 scripts/meta_agent_test.py` (both asserts pass) | T4 | §1.6 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (shared seam) complete. Fresh context for Slice 2, which consumes the seam but does not need its implementation details — only its `complete()` contract.

## Session 2

**Load:** structure.md §Contracts (`complete()` seam, `DiagnosisResult`), structure.md §Types, plan.md §Slice 2, impl-log.md §Slice 1 (notes only — `complete()` signature + sentinel)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Modify `scripts/diagnose.py` — rewrite `categorize_failure` body to call `meta_agent.complete`, parse `{category, rationale}`, preserve keys consumed by `produce_diagnosis` (AC1) | T5 | §2.7 | L | pending |
| T7 | Keep `ALL_PASSING` / empty-failures short-circuit ahead of any `complete` call (passing cases make no model invocation) | T6 | §2.8 | S | pending |
| T8 | Handle `complete` no-result/unparseable return defensively (no-edit/no-category fallback + logged error) | T6 | §2.9 | S | pending |
| T9 | Add `--dry-run` flag: emit diagnosis with no side effects beyond the diagnosis file | T6 | §2.10 | S | pending |
| T10 | Create `scripts/diagnose_test.py` (mocks `complete`: grounded parse; short-circuit no-call; `--dry-run` writes nothing extra) | T7, T8, T9 | §2.11 | M | pending |
| T11 | **Verify Slice 2** — `python3 scripts/diagnose_test.py` (all asserts pass) | T10 | §2.13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete. Slice 3 touches a different module (`revise.py`) and only needs the `complete()` seam contract, not diagnose.py internals. Fresh context keeps the window lean.

## Session 3

**Load:** structure.md §Contracts (`complete()` seam, `EditProposal`, `AnchorCheck`, `apply_revisions`), structure.md §Types, plan.md §Slice 3, impl-log.md §Slice 1 (notes only — `complete()` signature)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Modify `scripts/revise.py` — rewrite `propose_revisions` to call `meta_agent.complete`, parse concrete `{old_text, new_text, description}` anchored edits (AC2, Decision 2) | T5 | §3.14 | L | pending |
| T13 | Add `verify_anchor(skill_text, old_text) -> AnchorCheck` returning `{ok, reason ∈ missing/ambiguous/ok}` (Decision 3) | T12 | §3.15 | M | pending |
| T14 | Run `verify_anchor` per edit before applying; skip + log `missing`/`ambiguous`; pass only `ok` edits to `apply_revisions` | T13 | §3.16 | M | pending |
| T15 | Leave `apply_revisions` mechanically unchanged (first-occurrence replace; now receives verified edits only) | T14 | §3.17 | S | pending |
| T16 | Make `revise_skill` return `revised` (not `pending_meta_agent`) when ≥1 verified edit lands (AC2) | T15 | §3.18 | S | pending |
| T17 | Make `revision-log.json` read-only under `--dry-run` (no append) | T12 | §3.19 | S | pending |
| T18 | Create `scripts/revise_test.py` (mocks `complete`: edit applies → `revised`; missing skipped; ambiguous skipped; `--dry-run` no log mutation) | T16, T17 | §3.20 | M | pending |
| T19 | **Verify Slice 3** — `python3 scripts/revise_test.py` (all asserts pass) | T18 | §3.22 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete. Slice 4 is independent of the meta-agent seam (pure regression-guard logic in `report.py`) — fresh context loads only report.py contracts.

## Session 4

**Load:** structure.md §Contracts (`build_ledger_entry`, `detect_regressions`), structure.md §Types, plan.md §Slice 4
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T20 | Modify `scripts/report.py` — extend `build_ledger_entry` with version-level `test_score`-drop guard (drop > 0.05 → alert in `report["alerts"]` + `ledger.json`); complements existing per-case 0.2 guard (AC4) | — | §4.23 | M | pending |
| T21 | Create `scripts/report_test.py` over synthetic version sequences (> 0.05 drop alerts in both; ≤ 0.05 does not) | T20 | §4.24 | M | pending |
| T22 | **Verify Slice 4** — `python3 scripts/report_test.py` (both asserts pass) | T21 | §4.26 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 complete. Slice 5 wires the empirical loop and depends on the Slice 2 + Slice 3 consumers being in place; its e2e checkpoint is BLOCKED on an external dependency. Fresh context loads the gating note and loop wiring only.

## Session 5

**Load:** structure.md §Unverified Assumptions, plan.md §Slice 5 (incl. gating NOTE), plan.md §Rollback Notes, impl-log.md §Slice 2 + §Slice 3 (notes only)
**Estimated context:** ~18% of window

> **GATED SLICE — surface to reviewer before implementing.** Plan §Slice 5 NOTE: `run_eval.py`/`grade.py` are stubs producing zeros, so the AC3 empirical-convergence checkpoint cannot pass until the real runtime/judge lands. Fixture authoring (T23–T24) is in scope; the e2e checkpoint (T25) is BLOCKED and validated only via the mocked Slice 2–3 unit tests until that dependency resolves. Fixture content + convergence target are unresolved (OQ5) — confirm with reviewer before authoring.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T23 | Create `evals/fixtures/<under-specified-skill>` — deliberately under-specified prompt for convergence validation (content + target unresolved per OQ5; confirm with reviewer) | T11, T19 | §5.27 | M | blocked-pending-reviewer |
| T24 | Create `evals/golden/<convergence-golden>` — golden output, only if the loop run path consumes a golden file | T23 | §5.28 | S | blocked-pending-reviewer |
| T25 | **Verify Slice 5** — `bash run_loop.sh` against fixture (BLOCKED on stubbed runtime/judge; until unblocked validate via `python3 scripts/diagnose_test.py && python3 scripts/revise_test.py`) | T24 | §5.29 | M | blocked-external-dep |

--- SESSION BOUNDARY ---
**Reason:** All slices complete. Fresh context for the PR-summary phase, which loads no implementation detail beyond the impl logs.

## Notes

- **Off-critical-path parallelism:** Slice 4 (Session 4 / T20–T22) shares no module with Slices 1–3 and depends on nothing in them. It may be implemented at any point after Slice 1, independent of Slices 2–3 — sequenced 4th here only for a clean session order.
- **Shared-seam fan-out:** T5 (Slice 1 verified) is the single dependency that unblocks both T6 (Slice 2) and T12 (Slice 3). Those two consumer slices are otherwise independent of each other.
- **Rollback (per plan §Rollback Notes):** preserve the original `categorize_failure` heuristic body in the T6 commit diff; snapshot `SKILL_PATH` before any live loop run (Slices 14–18 make `run_loop.sh` overwrite in place, no backup); OQ2 (wiring the commented `git checkout HEAD~1` rollback) unresolved — confirm with reviewer.
- Step numbering: plan "Total steps: 26" excludes the gated Slice 5 steps (27–29); they are carried here as T23–T25 for completeness.
