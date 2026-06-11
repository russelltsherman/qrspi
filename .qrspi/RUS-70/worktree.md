# Work Tree — Land excludes the tip slice on multi-slice stacks, producing half-landed stacks

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T16 → T17 → T18

## Session 1 — Slice 1: Land verifier script + tests

**Load:** structure.md §New Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_land_verify.py` with self-locating preamble (repo root from `__file__`, `scripts/` importable for `qrspi_pr_state.py`) | — | §1.1 | S | pending |
| T2 | Add `verify_landed(stackState) -> LandVerdict` — reuse `is_stack_fully_merged`; landed ⇒ empty `openBranches`, else `incomplete` naming non-MERGED branches | T1 | §1.2 | M | pending |
| T3 | Add `main(ticketId) -> int` CLI — gather merge state via `stack_merge_state(prefer="merged")`, call `verify_landed`, print JSON, exit 0/non-zero | T2 | §1.3 | M | pending |
| T4 | Add `if __name__ == "__main__"` guard — read ticket id from `sys.argv[1]`, `sys.exit(main(...))` | T3 | §1.4 | S | pending |
| T5 | Create `scripts/qrspi_land_verify_test.py` — stdlib `unittest`, reuse branch fixture + `_node` GraphQL stubs | T4 | §1.5 | S | pending |
| T6 | Add fully-merged case — both branches MERGED ⇒ `landed`, empty `openBranches` | T5 | §1.6 | S | pending |
| T7 | Add partial-incomplete case — slice-1 MERGED, slice-2 OPEN ⇒ `incomplete`, `openBranches == ["RUS-1/slice-2"]` | T6 | §1.7 | S | pending |
| T8 | Add all-OPEN case — both OPEN ⇒ `incomplete`, `openBranches` names both | T7 | §1.8 | S | pending |
| T9 | Run `python3 scripts/qrspi_land_verify_test.py` — expect all three cases pass | T8 | §1.9 | S | pending |
| T10 | **Verify Slice 1** — tests green; `verify_landed` reuses `is_stack_fully_merged`; `incomplete` names OPEN branches | T9 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (new verifier script + tests, self-contained). Fresh context for Slice 2, which edits a different file (`qrspi_resolve.py`) with its own test suites.

## Session 2 — Slice 2: Expose tip/slice metadata on the envelope root

**Load:** structure.md §Modified Types, structure.md §Envelope contract, plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Modify `scripts/qrspi_resolve.py` `build_envelope()` — add root-level `tip` (from `pick_tip()`) and `slices` (from `slice_numbers()`); additive only, all existing fields unchanged | T10 | §2.11 | M | pending |
| T12 | Modify `scripts/qrspi_resolve_test.py` — assert envelope root `tip == "<ticket>/slice-<maxN>"`, `slices` is ascending list, pre-existing root fields unchanged | T11 | §2.12 | S | pending |
| T13 | Modify `scripts/qrspi_resolve_state_test.py` — update fixtures only where additive field breaks exact-equality; no `decision()` behavioral edits | T11 | §2.13 | S | pending |
| T14 | Run `python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_resolve_state_test.py` — expect both green, envelope shows `tip`/`slices` | T12, T13 | §2.14 | S | pending |
| T15 | **Verify Slice 2** — both suites pass; envelope carries root `tip`/`slices`; `decision` dict untouched; pre-existing root fields unchanged | T14 | §2.15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (envelope metadata exposed). Fresh context for Slice 3, which consumes both prior slices' outputs (the verifier from Slice 1, the `slices` envelope field from Slice 2) to wire the land loop and Done gate.

## Session 3 — Slice 3: Bottom-up land loop + Done gate wiring

**Load:** structure.md §Land loop contract, structure.md §doLand Done gate, plan.md §Slice 3, impl-log.md §Slice 1 + §Slice 2 (notes only)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Modify `.claude/skills/qrspi-work/SKILL.md` `## action: land` — replace single `gt checkout slice-1`/`gt merge` with ascending k=1..maxN loop over envelope `slices`; keep pre-land `gt submit` refresh; fix "merges bottom-up" comment; preserve `<id>/design` fallback | T15 | §3.16 | M | pending |
| T17 | Modify `.claude/workflows/qrspi-batch.js` `doLand` — gate Done on `qrspi_land_verify.py <ticketId>`; `landed` ⇒ Done; `incomplete` ⇒ stop `ok:false`, defer to next pass; log half-landed distinctly from not-started skip | T16 | §3.17 | M | pending |
| T18 | **Verify Slice 3** — Slice 1+2 suites green; live N>1 land merges every slice (none OPEN), verifier returns `landed`; forced-OPEN tip ⇒ `incomplete` and `doLand` stops `ok:false`; comment corrected; `<id>/design` fallback intact | T17 | §3.18 | L | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice. Implementation complete after T18; proceed to PR phase.
