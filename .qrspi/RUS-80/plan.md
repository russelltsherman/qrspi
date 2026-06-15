# Implementation Plan — Test + document the existing phase/slice resume guarantee

**Structure basis:** structure.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total steps:** 8

## Slice 1: Lock in and document the resume guarantee

This slice is tests-and-docs only. No runtime change to `qrspi-batch.js` or any
Python module under test. All test helpers (`detect_existing`, `slice_branches`,
`pick_tip`, `build_envelope`, `ARTIFACTS`, `check`) are already imported in
`scripts/qrspi_resolve_test.py` — no new imports are added (ref: structure.md §Contracts,
design.md §Decision 1).

### Core Logic

1. ⚠️ Modify `scripts/qrspi_resolve_test.py` — add the single net-new non-contiguous
   `slice_branches` assertion (AC2) beside the existing `slice_branches` block,
   using the already-imported `slice_branches` and `check(...)` harness.
   - **Current:** `slice_branches` asserted for empty, plan/design-only, contiguous-ascending,
     and out-of-order-contiguous cases only (ref: design.md §Already covered, lines :104–113).
   - **After:** plus `check("slice_branches non-contiguous",
     slice_branches({"RUS-1/slice-1", "RUS-1/slice-3"}, "RUS-1"),
     ["RUS-1/slice-1", "RUS-1/slice-3"])` — the one combination currently unasserted
     (ref: structure.md §Slice 1 AC2, design.md §Decision 1).

2. ⚠️ Modify `scripts/qrspi_resolve_test.py` — add the net-new AC3 `build_envelope`
   passthrough block. Use `tempfile.TemporaryDirectory()` + `os.makedirs(<tmp>/.qrspi/<ticket>/)`,
   seed at least one non-empty upstream artifact, build the `existing` map via
   `detect_existing(<tmp>/.qrspi/<ticket>)`, then assert the map is carried verbatim
   onto the envelope via `build_envelope`.
   - **Current:** no test seeds a `<tmp>/.qrspi/<ticket>/` layout and asserts the
     `existing` map onto a built envelope (ref: design.md §AC3, line :26).
   - **After:** a block asserting `check("build_envelope existing passthrough",
     build_envelope(..., existing=that_map)["existing"], that_map)` — a passthrough
     identity check, NOT a behavioral skip proof; the JS `runPhase` early-return that
     consumes the map is inspection-only and is not unit-tested (ref: structure.md §Slice 1 AC3,
     design.md §Decision 2). Supply the remaining `build_envelope` arguments per its
     existing call surface (`decision`, etc.); the assertion targets only the `existing` field.

3. ⚠️ Modify `scripts/qrspi_resolve_test.py` — add resume-framing comments on the
   existing `detect_existing`, `pick_tip`, and `slice_branches` blocks so the resume
   contract reads as one cohesive unit. No new assertions, no new imports.
   - **Current:** existing blocks carry no resume-contract framing.
   - **After:** brief comments noting each block covers part of the resume guarantee
     (ref: structure.md §Slice 1 "optionally add resume-framing comments", design.md §Delta).

### Documentation

4. ⚠️ Modify `docs/testing-dynamic-workflows.md` — add a "Resume guarantee" section
   framed as Python-tested core plus thin JS skip, consistent with the existing
   Functional-Core/Imperative-Shell thesis.
   - **Current:** the doc says nothing about resume/skip semantics (ref: design.md §Current State, line :18).
   - **After:** a section stating resume is phase- and slice-boundary by design; a
     mid-phase/mid-slice `agent()` `null` correctly recomputes that unit because
     `persistArtifact` is the post-validation gate; no signature-based classifier
     exists because the seam yields a bare `null`; the guarantee is "non-empty present",
     not "structurally valid"; and the phase-skip (JS `runPhase` early-return) and
     per-slice skip (`alreadyCommitted`) are inspection-only, not unit-tested
     (ref: structure.md §Slice 1 AC4, design.md §Decision 3, Risk Register).

5. ⚠️ Modify `docs/testing-dynamic-workflows.md` — embed the probe result verbatim
   into the "Resume guarantee" section (AC4/AC5).
   - **Current:** no probe evidence in the doc.
   - **After:** the transcribed probe result (invalid model id → `agent()` returns a
     bare `null` with the error message discarded; classifier/allowlist/backoff
     unbuildable and withdrawn) plus the classifier-withdrawal rationale, copied
     from design.md §Probe Evidence (lines :90–94) (ref: structure.md §Slice 1 AC5).

### Verify Slice 1

6. **Checkpoint:** `python3 scripts/run_tests.py resolve`
   - [ ] The resolver test passes, exercising the new non-contiguous `slice_branches`
     assertion (step 1) and the `build_envelope` passthrough assertion (step 2).

7. **Checkpoint:** `python3 scripts/run_tests.py`
   - [ ] The full suite stays green (AC6) — no regressions in any `scripts/*_test.py`.

8. **Checkpoint (manual read):** open `docs/testing-dynamic-workflows.md`
   - [ ] Contains a "Resume guarantee" section.
   - [ ] Section includes the embedded probe result, the classifier-withdrawal rationale,
     and the "non-empty present, not structurally valid" caveat.
   - [ ] Section notes phase-skip and per-slice skip are inspection-only.

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this plan.
- Steps 1–3 (test edits) and steps 4–5 (doc edits): revert via `git checkout --
  scripts/qrspi_resolve_test.py docs/testing-dynamic-workflows.md` (or drop the commit);
  no runtime state is touched, so reversal is fully local and side-effect-free.
- Optional probe file `.claude/workflows/probe-agent-failure.js` (OQ1, human discretion)
  is deliberately excluded from this plan's verification path; if a human elects to
  commit it, removing it is a plain `git rm` with no dependents.
