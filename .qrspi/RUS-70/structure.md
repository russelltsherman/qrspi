# Structure Outline — Land excludes the tip slice on multi-slice stacks, producing half-landed stacks

**Design basis:** design.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

- `LandVerdict { status: "landed" | "incomplete", openBranches: list[str] }` — the deterministic result returned by `qrspi_land_verify.py`, serialized as JSON to stdout. `landed` requires `is_stack_fully_merged` true; `incomplete` names every non-MERGED slice branch.

## Modified Types

- Resolver envelope (dict returned by `build_envelope()` in `qrspi_resolve.py`) — add **root-level** fields `tip: str` (the `<ticket>/slice-<maxN>` branch from `pick_tip()`) and `slices: list[str]` (the ascending slice branches from `slice_numbers()`), additive alongside `repoRoot`/`worktreeDir`/`existing`/`decision`/`reviewers`/`teamReviewers`/`ticketContent` (ref: design.md §Delta, RQ3). `decision()` in `qrspi_resolve_state.py` is unchanged.

## Contracts

- `verify_landed(stackState): LandVerdict` — pure verdict function in `qrspi_land_verify.py`; given gathered per-branch merge state, returns `landed` iff `is_stack_fully_merged(...)` else `incomplete` with OPEN branch names. Reuses `stack_merge_state` / `is_stack_fully_merged` from `qrspi_pr_state.py` (ref: design.md §Decision 2).
- `main(ticketId) -> int` (CLI entry, `qrspi_land_verify.py`) — self-locating like its siblings; gathers per-branch PR state for the ticket via `qrspi_pr_state.py` and prints the `LandVerdict` JSON; exit 0 on `landed`, non-zero on `incomplete`.
- Envelope contract — `build_envelope()` emits `tip` and `slices` at the root so the land worker iterates the slice list from the envelope instead of reconstructing `<id>/slice-1` from the ticket id (ref: design.md §Decision 1, RQ3).
- Land loop contract (`.claude/skills/qrspi-work/SKILL.md` `## action: land`) — for k = 1..maxN in ascending order: `gt checkout <id>/slice-<k>` then `gt merge --no-interactive`, preceded once by `gt submit --publish --stack --no-edit --no-interactive`; `<id>/design` single-merge fallback for plan-only features with no slices (ref: design.md §Delta, RQ1).
- `doLand` Done gate (`qrspi-batch.js`) — after `fin.ok`, invoke `qrspi_land_verify.py`; `landed` ⇒ report Done; `incomplete` ⇒ stop with `ok:false`, defer to next batch pass, no in-pass retry (ref: design.md §Delta, RQ2).

## Slice 1: Land verifier script + tests

**Goal:** A self-locating `qrspi_land_verify.py` that, given a ticket id, returns a deterministic `landed`/`incomplete` verdict over the stack's per-branch MERGED state — fully verifiable in isolation against the existing N=2 fixtures, independent of any orchestration wiring.
**Files touched:**

- ✨ `scripts/qrspi_land_verify.py` — gather per-branch PR state via `qrspi_pr_state.py`; `verify_landed()` returns `LandVerdict`; CLI prints JSON, exit non-zero on `incomplete`.
- ✨ `scripts/qrspi_land_verify_test.py` — stdlib-only sibling reusing `["RUS-1/slice-1","RUS-1/slice-2"]` + `_node(prNumber, state, merged)` stubs: fully-merged ⇒ `landed`; slice-2 OPEN ⇒ `incomplete` naming `RUS-1/slice-2`; all-OPEN ⇒ `incomplete`.
**Verification:**
- [ ] `python3 scripts/qrspi_land_verify_test.py` passes (landed, partial-incomplete, all-open cases).
**Context cost:** S
**Depends on:** none

## Slice 2: Expose tip/slice metadata on the envelope root

**Goal:** `build_envelope()` carries `tip` and `slices` at the envelope root, verifiable in isolation by the resolver's own tests, so a downstream worker can read the slice list from the contract.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve.py` — in `build_envelope()`, add root-level `tip` (from `pick_tip()`) and `slices` (from `slice_numbers()`); additive, `decision` untouched.
- ⚠️ `scripts/qrspi_resolve_test.py` — assert `tip`/`slices` present and correct for a multi-slice stack; assert existing root fields unchanged.
- ⚠️ `scripts/qrspi_resolve_state_test.py` — adjust only if fixtures break from the additive field (no behavior change to `decision()`).
**Verification:**
- [ ] `python3 scripts/qrspi_resolve_test.py` and `python3 scripts/qrspi_resolve_state_test.py` pass; envelope shows `tip`/`slices` at root.
**Context cost:** M
**Depends on:** none

## Slice 3: Bottom-up land loop + Done gate wiring

**Goal:** The land action merges slice-by-slice bottom-up through the real tip and gates Done on the verifier — the end-to-end fix. Consumes the envelope `slices` (Slice 2) and the verifier (Slice 1); verified live on an N>1 stack landing all slices to MERGED with no slice left OPEN.
**Files touched:**

- ⚠️ `.claude/skills/qrspi-work/SKILL.md` (`## action: land`, ~lines 446-452) — replace single `gt checkout <id>/slice-1` + one `gt merge` with the ascending k=1..maxN `gt checkout`/`gt merge --no-interactive` loop over the envelope `slices`; keep the `gt submit --publish --stack --no-edit --no-interactive` pre-land refresh; correct the misleading "merges bottom-up" comment; keep `<id>/design` single-merge fallback for slice-less features.
- ⚠️ `.claude/workflows/qrspi-batch.js` (`doLand`, ~lines 807-812) — after `fin.ok`, invoke `qrspi_land_verify.py`; `landed` ⇒ Done; `incomplete` ⇒ stop `ok:false`, defer to next pass; distinguish half-landed `skip` from not-started `skip` in logs.
**Verification:**
- [ ] Slices 1 and 2 tests still green.
- [ ] Live N>1 end-to-end land (AC3): every slice PR reaches MERGED, none OPEN; `qrspi_land_verify.py` returns `landed`; a forced OPEN tip yields `incomplete` and `doLand` stops with `ok:false` rather than reporting Done.
**Context cost:** M
**Depends on:** Slice 1, Slice 2

---

## Unverified Assumptions

- **`gt merge --no-interactive` restacks/merges upward per slice such that an ascending per-slice loop lands the whole stack** — the design states the bottom-up loop "lands every slice deterministically," but `gt merge`'s exact downstack/upstack branch consumption is undocumented in-repo (design.md §Risk Register, ref Q3/Q10). The per-slice loop is the chosen mitigation, but its correctness can only be confirmed by the Slice 3 live N>1 run, not by any unit test.
- **`pick_tip()`/`slice_numbers()` return a contiguous, linear ascending slice list for every real stack** — `pick_tip` assumes max-N is the true tip; a non-contiguous or non-linear stack could mis-anchor the loop (design.md §Risk Register, ref Q2/Q9). The verifier (Slice 1) catches a mis-anchor by naming OPEN branches, but the design names no concrete guard inside the loop itself.
- **Re-running land on an already-partially-landed stack re-attempts only the open tip cleanly** — explicitly out of scope (resolver `entry_blocked` hazard, design.md §Risk Register, ref Q9); RQ2 defers to the next batch pass rather than solving in-pass. No code in this structure addresses the leftover; it is documented for a separate resolver ticket.
