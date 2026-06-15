# Structure Outline — Test + document the existing phase/slice resume guarantee

**Design basis:** design.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## New Types

None. This ticket is tests-and-docs only; no runtime types are added or changed
(ref: design.md §Delta — "No new files for runtime, no config module, no classifier").

## Modified Types

None. No runtime change to `qrspi-batch.js` or any Python module under test
(ref: design.md §Delta hard constraint).

## Contracts

These are the **existing, already-imported** helpers the net-new tests assert
against. No signatures change; they are listed so the test additions reference a
stable surface (ref: design.md §Current State, §Decision 1, §Decision 2).

- `detect_existing(qrspi_dir: str) -> dict[str, bool]` — maps each of the six
  `ARTIFACTS` names to `os.path.getsize(<qrspi_dir>/<name>.md) > 0`; any `OSError`
  → `False`. Already fully asserted (AC1 — no net-new work).
- `slice_branches(branches: set[str], ticket: str) -> list[str]` — formats present
  `slice-<n>` numbers into ascending `<ticket>/slice-<n>` names; gap-agnostic.
  Net-new: ONE non-contiguous assertion (AC2).
- `pick_tip(snums: list[int]) -> int` — returns `max(snums)`. Already asserted
  including non-contiguous/out-of-order (AC2 — no net-new work).
- `build_envelope(..., existing: dict, decision: ...) -> dict` — stores `existing`
  **verbatim** on the envelope's `existing` field with no derivation. Net-new:
  passthrough identity assertion (AC3).
- `ARTIFACTS: list[str]` — the six-name artifact list; `detect_existing`'s key set
  must equal it (already asserted — keep).
- `check(name, got, want)` — the stdlib assert harness all assertions use.

## Slice 1: Lock in and document the resume guarantee

**Goal:** The resume guarantee is asserted at every deterministic seam the design
identifies as net-new, and documented as a durable contract — all verifiable by
running the existing test suite green and reading the new doc section. This is the
entire ticket; the design's net-new scope (one `slice_branches` assertion + one
`build_envelope` passthrough block + a doc section + the transcribed probe result)
is cohesive and mutually-contextual — the doc explains why the tests are thin, and
the tests are what the doc points to — so it is one unit of work with no internal
testability boundary (ref: design.md §Delta, OQ3).

**Files touched:**

- ⚠️ `scripts/qrspi_resolve_test.py` — add (AC2) a single non-contiguous
  `slice_branches` assertion: `slice_branches({"RUS-1/slice-1", "RUS-1/slice-3"},
  "RUS-1") == ["RUS-1/slice-1", "RUS-1/slice-3"]`; add (AC3) a worktree-layout
  block that `os.makedirs(<tmp>/.qrspi/<ticket>/)`, seeds upstream artifacts,
  builds the `existing` map via `detect_existing`, and asserts
  `build_envelope(..., existing=that_map)["existing"] == that_map` (passthrough
  identity, NOT a behavioral skip proof); optionally add resume-framing comments
  on the existing `detect_existing`/`pick_tip`/`slice_branches` blocks. No new
  imports — all helpers already imported (ref: design.md §Decision 1, §Decision 2).
- ⚠️ `docs/testing-dynamic-workflows.md` — add a "Resume guarantee" section: resume
  is phase- and slice-boundary by design; a mid-phase/mid-slice `agent()` `null`
  correctly recomputes that unit because `persistArtifact` is the post-validation
  gate; no signature-based classifier exists because the seam yields a bare `null`;
  the guarantee is "non-empty present", not "structurally valid"; the phase-skip
  (JS `runPhase` early-return) and per-slice skip (`alreadyCommitted`) are
  inspection-only, not unit-tested. Embed the probe result verbatim (AC4, AC5)
  (ref: design.md §Delta, §Decision 3, Risk Register).
- ✨ (optional, human discretion — OQ1) `.claude/workflows/probe-agent-failure.js`
  — commit the existing untracked probe file as the evidentiary artifact. Default
  is to NOT add it (capture its result in the doc instead); only include if a human
  elects the "committed" branch of AC5. Left out of the verification path.

**Verification:**

- [ ] `python3 scripts/run_tests.py resolve` passes, exercising the new
  non-contiguous `slice_branches` and `build_envelope` passthrough assertions.
- [ ] `python3 scripts/run_tests.py` (full suite) stays green (AC6).
- [ ] `docs/testing-dynamic-workflows.md` contains a "Resume guarantee" section
  with the embedded probe result, the classifier-withdrawal rationale, and the
  "non-empty present" caveat (manual read).

**Context cost:** S
**Depends on:** none

---

## Unverified Assumptions

- **AC3's "honest" framing is a passthrough, not a guarantee proof.** The design
  is explicit that no deterministic Python test can assert AC3's behavioral
  contract (the skip lives in JS `runPhase`). The `build_envelope` passthrough
  assertion is real but thin. If a reviewer expects AC3 to *prove* skip behavior,
  the design's scope (inspection-only for the JS seam) must be re-litigated before
  planning — this is design-level, not resolvable in structure.
- **Whole-stack justification (design OQ3).** The design openly questions whether
  this thin, lock-in-only work warrants a full design→plan→slice stack vs. a single
  small PR or folding into another ticket. The single-slice structure here reflects
  that thinness but does not resolve the human call; it should be confirmed before
  planning proceeds.
- **Probe file disposition (design OQ1).** Whether `probe-agent-failure.js` is
  committed (AC5 "committed" branch) or only its result captured (AC5 "or captured"
  branch) is a human decision. The optional file in Slice 1 is gated on that call;
  structure assumes the capture-in-doc default.
- **Cross-link to CLAUDE.md (design OQ2).** Whether the resume guarantee is also
  cross-linked from `CLAUDE.md`'s codebase-conventions section is unresolved; not
  mapped to a slice file change pending that decision.
