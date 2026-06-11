# Implementation Plan — Land excludes the tip slice on multi-slice stacks, producing half-landed stacks

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: Land verifier script + tests

### Setup

1. ✨ Create `scripts/qrspi_land_verify.py` — new self-locating tested helper (sibling to `qrspi_resolve.py`/`qrspi_cleanup.py`). Add the standard self-locating preamble that resolves the repo root from `__file__` and makes `scripts/` importable so `qrspi_pr_state.py` can be imported, matching the established convention.

### Core Logic

2. ✨ Add `verify_landed(stackState) -> LandVerdict` to `scripts/qrspi_land_verify.py` — pure verdict function. Reuse `is_stack_fully_merged(stackState)` from `qrspi_pr_state.py`: return `{"status": "landed", "openBranches": []}` when it returns true; otherwise return `{"status": "incomplete", "openBranches": [...]}` naming every non-MERGED slice branch. `LandVerdict` is a plain dict `{ status: "landed" | "incomplete", openBranches: list[str] }` (ref: structure.md New Types / Contracts; design.md §Delta, Decision 2).

3. ✨ Add `main(ticketId) -> int` CLI entry to `scripts/qrspi_land_verify.py` — gather per-branch PR merge state for the ticket via `qrspi_pr_state.py` (`stack_merge_state`, `prefer="merged"`), call `verify_landed()`, `print(json.dumps(verdict))` to stdout, and return exit 0 on `landed` / non-zero on `incomplete` (ref: structure.md Contracts; design.md §Delta).

4. ✨ Add the `if __name__ == "__main__"` guard to `scripts/qrspi_land_verify.py` — read the ticket id from `sys.argv[1]` and `sys.exit(main(ticketId))`, matching the sibling scripts' invocation convention.

### Tests

5. ✨ Create `scripts/qrspi_land_verify_test.py` — stdlib-only `unittest` sibling. Reuse the existing `["RUS-1/slice-1","RUS-1/slice-2"]` branch fixture and `_node(prNumber, state, merged)` GraphQL stubs (ref: structure.md Slice 1; design.md §Delta).

6. ✨ Add the fully-merged case to `scripts/qrspi_land_verify_test.py` — both slice branches MERGED ⇒ `verify_landed()` returns `status == "landed"` with empty `openBranches`.

7. ✨ Add the partial-incomplete case to `scripts/qrspi_land_verify_test.py` — slice-1 MERGED, slice-2 OPEN ⇒ `status == "incomplete"` and `openBranches == ["RUS-1/slice-2"]`.

8. ✨ Add the all-OPEN case to `scripts/qrspi_land_verify_test.py` — both branches OPEN ⇒ `status == "incomplete"` and `openBranches` names both branches.

9. Run: `python3 scripts/qrspi_land_verify_test.py`
   - **Expected:** all three cases pass (landed, partial-incomplete, all-open).

### Verify Slice 1

10. **Checkpoint:** `python3 scripts/qrspi_land_verify_test.py`
    - [ ] Tests pass for the landed, partial-incomplete, and all-open cases.
    - [ ] `verify_landed` reuses `is_stack_fully_merged` from `qrspi_pr_state.py` (no duplicated merge logic).
    - [ ] `incomplete` verdicts name the OPEN slice branches.

---

## Slice 2: Expose tip/slice metadata on the envelope root

### Core Logic

11. ⚠️ Modify `scripts/qrspi_resolve.py` — in `build_envelope()`, add root-level fields `tip` and `slices`.
    - **Current:** envelope dict carries `ok`, `repoRoot`, `worktreeDir`, `existing`, `decision`, `commentTargets`, `reviewers`, `teamReviewers`, `ticketContent` (no tip / slice list).
    - **After:** additionally sets root-level `tip: str` from `pick_tip()` (the `<ticket>/slice-<maxN>` branch) and `slices: list[str]` from `slice_numbers()` (ascending slice branches); additive only, `decision` and all existing fields unchanged (ref: structure.md Modified Types / Envelope contract; design.md §Delta, RQ3).

### Tests

12. ⚠️ Modify `scripts/qrspi_resolve_test.py` — add assertions that, for a multi-slice stack, the envelope has root-level `tip` and `slices` with correct values, and that the existing root fields are unchanged.
    - **Current:** resolver tests assert the existing envelope fields only.
    - **After:** also assert `envelope["tip"] == "<ticket>/slice-<maxN>"`, `envelope["slices"]` is the ascending branch list, and pre-existing root fields are byte-for-byte unchanged.

13. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — adjust fixtures only if the additive root field breaks an exact-equality assertion; `decision()` behavior is unchanged, so make no behavioral edits.
    - **Current:** state tests assert `decision()` output and may compare full envelope/decision structures.
    - **After:** fixtures updated only where the additive `tip`/`slices` field would otherwise fail an equality check; no change to `decision()` expectations.

14. Run: `python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - **Expected:** both suites pass; envelope shows `tip`/`slices` at root.

### Verify Slice 2

15. **Checkpoint:** `python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - [ ] Both suites pass.
    - [ ] Envelope carries root-level `tip` and `slices`; `decision` dict is untouched.
    - [ ] All pre-existing root fields unchanged.

---

## Slice 3: Bottom-up land loop + Done gate wiring

### Core Logic

16. ⚠️ Modify `.claude/skills/qrspi-work/SKILL.md` (`## action: land`, ~lines 446-452) — replace the single hard-coded `gt checkout <id>/slice-1` + one `gt merge` with an ascending k = 1..maxN loop over the envelope `slices`: for each slice, `gt checkout <id>/slice-<k>` then `gt merge --no-interactive`. Keep the pre-land `gt submit --publish --stack --no-edit --no-interactive` refresh. Correct the misleading "merges bottom-up" comment to describe the explicit per-slice ascending loop. Keep the `<id>/design` single-merge fallback for slice-less (plan-only) features.
    - **Current:** `gt checkout <ticket-id>/slice-1` then a single `gt merge --no-interactive`, with a comment claiming `gt merge` "merges bottom-up" — lands slice-1 + plan + design only, leaving slices 2..N OPEN on N>1 stacks.
    - **After:** explicit ascending per-slice `gt checkout`/`gt merge --no-interactive` loop over the envelope `slices`, preceded once by the `gt submit --publish --stack --no-edit --no-interactive` refresh, with an accurate comment and the `<id>/design` fallback preserved (ref: structure.md Land loop contract; design.md §Delta, AC2, RQ1).

17. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`doLand`, ~lines 807-812) — after `fin.ok` and before reporting Done, invoke `scripts/qrspi_land_verify.py <ticketId>`; on `landed` ⇒ report Done; on `incomplete` ⇒ stop with `ok:false` and defer to the next batch pass (no in-pass auto-retry). Distinguish a half-landed `skip` from a not-started `skip` in the logs.
    - **Current:** after `fin.ok`, `doLand` projects Done from the worker's self-reported `newStatus` with no independent MERGED check; a half-landed stack reports Done while cleanup logs a benign `skip`.
    - **After:** Done is gated on `qrspi_land_verify.py` returning `landed`; `incomplete` stops the land with `ok:false`, defers to the next pass, and logs the half-landed state distinctly from a not-started `skip` (ref: structure.md doLand Done gate; design.md §Delta, AC3, RQ2).

### Verify Slice 3

18. **Checkpoint:** `python3 scripts/qrspi_land_verify_test.py && python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_resolve_state_test.py`, then a live N>1 end-to-end land (AC3).
    - [ ] Slice 1 and Slice 2 test suites still green.
    - [ ] Live N>1 land: every slice PR reaches MERGED, none left OPEN; `qrspi_land_verify.py` returns `landed`.
    - [ ] Forced-OPEN tip yields `incomplete` and `doLand` stops with `ok:false` rather than reporting Done.
    - [ ] The misleading "merges bottom-up" comment is corrected; `<id>/design` fallback still lands slice-less features.

---

## Rollback Notes

- **Step 16** (`.claude/skills/qrspi-work/SKILL.md` `## action: land`): revert to the prior single `gt checkout <id>/slice-1` + one `gt merge` block to restore the previous (defective but known) land behavior. Pure prose/instruction change — no data or remote state altered by the revert itself.
- **Step 17** (`.claude/workflows/qrspi-batch.js` `doLand`): revert the verifier-gated Done block to restore the worker-self-report Done path. Behavioral revert only; no migration or stored state involved.
- **No DB migrations, config-file changes, or destructive operations** in this plan. The live land run (Step 18) merges real PRs via `gt merge`; merges are not auto-undone — a mis-anchored or partial land surfaces as `incomplete` (verifier) and is deferred to the next batch pass per RQ2 rather than auto-reverted (the partially-landed-stack cleanup is explicitly out of scope; tracked for the separate resolver ticket).
