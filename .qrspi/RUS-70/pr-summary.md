# PR: RUS-70 Land all slices bottom-up; gate Done on a MERGED verifier

**Ticket:** RUS-70
**Design:** design.md @ 2026-06-11T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

The `land` action hard-coded `gt checkout <id>/slice-1` then a single `gt merge`, which landed slice-1 + plan + design but left the upstack slices 2..N OPEN on multi-slice stacks — producing half-landed stacks that nonetheless self-reported Done. This PR replaces the single hard-coded merge with an explicit ascending per-slice bottom-up loop, exposes the computed tip/slice list on the resolver envelope root so the worker stops reconstructing branch names from the ticket id, and adds a new self-locating `qrspi_land_verify.py` whose `landed`/`incomplete` verdict now gates the `doLand` Done projection (an `incomplete` land stops with `ok:false` and defers to the next batch pass rather than projecting Done). Reviewer focus: (1) the `doLand` Done-gate wiring in `qrspi-batch.js` and its fail-closed `parseLandVerdict`; (2) the corrected land loop prose in `SKILL.md`, especially the preserved `<id>/design` single-merge fallback for slice-less features; (3) that the live N>1 end-to-end land (AC3) remains an unverified orchestrator/manual step — it is deferred, not covered by unit tests.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: all N slice PRs merged in one land, none left open; any OPEN slice fails the land | `scripts/qrspi_land_verify.py:verify_landed` (reuses `is_stack_fully_merged`) + `.claude/workflows/qrspi-batch.js:doLand` Done gate | `scripts/qrspi_land_verify_test.py` (landed / partial-incomplete / all-open) |
| AC2: land merges every slice slice-by-slice bottom-up, not a single hard-coded lower slice | `.claude/skills/qrspi-work/SKILL.md` `## action: land` ascending k=1..maxN `gt checkout`/`gt merge` loop over envelope `slices`; `scripts/qrspi_resolve.py:slice_branches` + `build_envelope(slices=...)` | `scripts/qrspi_resolve_test.py` (root `tip`/`slices` + `slice_branches` cases) |
| AC3: multi-slice land verified end-to-end; half-landed surfaces as a distinct failure, Done gated on MERGED truth | `.claude/workflows/qrspi-batch.js:doLand` → `runLandVerify`/`parseLandVerdict` (incomplete ⇒ `ok:false`, defer, no cleanup) | `scripts/qrspi_land_verify_test.py` (incomplete naming OPEN branch); live N>1 land DEFERRED (see Open Items) |

## Changes by Slice

### Slice 1: Land verifier script + tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_land_verify.py` | new | +125 |
| `scripts/qrspi_land_verify_test.py` | new | +79 |

### Slice 2: Expose tip/slice metadata on the envelope root

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve.py` | modified | +24, -2 |
| `scripts/qrspi_resolve_test.py` | modified | +33, -0 |

### Slice 3: Bottom-up land loop + Done gate wiring

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/qrspi-work/SKILL.md` | modified | +14, -4 |
| `.claude/workflows/qrspi-batch.js` | modified | +53, -0 |

### Phase artifacts (non-code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-70/questions.md` | new | +51 |
| `.qrspi/RUS-70/research.md` | new | +387 |
| `.qrspi/RUS-70/design.md` | new | +87 |
| `.qrspi/RUS-70/structure.md` | new | +67 |
| `.qrspi/RUS-70/plan.md` | new | +100 |
| `.qrspi/RUS-70/worktree.md` | new | +58 |
| `.qrspi/RUS-70/impl-log.md` | new | +80 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_land_verify_test.py` — 4 passed, 0 failed (landed, partial-incomplete, all-open, empty-stack edge)
- [x] Slice 2: unit tests — `python3 scripts/qrspi_resolve_test.py` — 74 passed, 0 failed (new root `tip`/`slices` + `slice_branches` cases)
- [x] Slice 2: regression — `python3 scripts/qrspi_resolve_state_test.py` — 39 passed, 0 failed (no fixture edits needed; additive root field)
- [x] Slice 3: syntax — `node --check .claude/workflows/qrspi-batch.js` — JS-SYNTAX-OK (parses after `doLand` Done-gate wiring)
- [ ] AC3 live N>1 end-to-end land — DEFERRED to orchestrator/manual (destructive `gt merge` against remote; forbidden to the slice agent)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `qrspi_land_verify_test.py` cases | landed, partial-incomplete, all-open (3) | + empty-stack edge (4) | Additive only; documents `is_stack_fully_merged({}) == False` boundary; the three mandated cases all present and pass; no contract change |
| `qrspi_resolve_state_test.py` | adjust fixtures only if additive root field breaks an exact-equality assertion | left untouched, re-run green | The condition did not occur — the state test never imports/compares the envelope (`tip`/`slices` live on `build_envelope`, not `decision()`); plan step 13 scoped the edit as conditional |
| Envelope `slices` field shape | slice count / slice list | full ascending branch names `["<id>/slice-1", ...]` (not bare ints) | Lets the land loop `gt checkout` each element directly; consistent with the structure contract's "ascending slice branches" |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `gt merge`'s exact downstack branch-consumption is undocumented in-repo | mitigated (RQ1 bottom-up per-slice loop removes the single-`gt merge` dependency) + verifier gate; **live N>1 confirmation still outstanding** | Revert SKILL.md land-action loop to prior single `gt checkout slice-1` + `gt merge` |
| `pick_tip` assumes max-N is the true tip; non-linear/non-contiguous stack could mis-anchor | accepted/mitigated — reuses tested `slice_numbers`/`pick_tip`; verifier names OPEN branches so a mis-anchor surfaces as `incomplete` rather than silent | Revert `qrspi_resolve.py` envelope additions |
| Re-running land on an already-partially-landed stack may not cleanly re-attempt only the open tip (resolver hazard) | accepted — out of scope; per RQ2 `incomplete` stops with `ok:false` and defers to next pass (no in-pass retry); leftover documented for the separate resolver ticket | N/A (no in-pass retry introduced) |
| `gt submit --stack` overwrites an approved remote head | mitigated — `--no-edit` preserved, no `--force` added; force ops stay in cleanup | N/A |
| New root-level envelope field breaks existing resolver tests/consumers | mitigated — additive root-level only; `decision()` untouched; `qrspi_resolve_state_test.py` unaffected | Revert `qrspi_resolve.py` + `qrspi_resolve_test.py` |
| `doLand` projects Done on an ambiguous/unparseable land verdict | newly-mitigated — `parseLandVerdict` fails CLOSED (missing/unknown ⇒ `incomplete`), so Done is never projected on ambiguity | Revert `doLand` gate in `qrspi-batch.js` |

## Open Items

- **AC3 live N>1 end-to-end land is unverified** (deferred, T18): requires a real multi-slice stack with approved PRs and a destructive `gt merge` against the remote, which is forbidden to the slice agent. Must be observed during a real batch land pass / orchestrator run — confirm every slice PR reaches MERGED and a forced-OPEN tip yields `incomplete` + `ok:false` (not Done).
- **Partially-landed-stack re-attempt is out of scope** (resolver `entry_blocked "No design branch"` hazard): RQ2 defers an `incomplete` land to the next batch pass; cleanly re-attempting only the open tip is left for a separate resolver ticket.
- **`pick_tip` non-contiguous/non-linear stack guard**: no concrete in-loop guard added; the verifier catches a mis-anchor after the fact by naming OPEN branches. A linearity assertion inside the loop could be a follow-up hardening.
