# PR: RUS-80 Test + document the phase/slice resume guarantee

**Ticket:** RUS-80
**Design:** design.md @ 2026-06-14T00:00:00Z
**Structure:** structure.md @ 2026-06-15T00:00:00Z

## Summary

This change locks in and documents QRSPI's existing phase/slice resume guarantee — the
capability already existed in code but was under-tested as a *resume* contract and
undocumented as a guarantee. It adds two net-new assertions to `scripts/qrspi_resolve_test.py`
(a non-contiguous `slice_branches` case for AC2 and a `build_envelope` existing-map passthrough
block for AC3), resume-framing comments on the existing deterministic-helper blocks, and a new
"Resume guarantee" section to `docs/testing-dynamic-workflows.md` that embeds the
`probe-agent-failure.js` result verbatim and the transient-retry-classifier withdrawal
rationale. **There is no runtime change** — `qrspi-batch.js` and every Python module under test
are untouched (a hard ticket constraint). Reviewer focus: confirm the honest scoping is
acceptable — the deterministic Python tests assert only the *inputs* to the resume decision
(`detect_existing`, `slice_branches`/`pick_tip`, `build_envelope` passthrough); the skip *act*
itself lives in the harness-coupled JS `runPhase` early-return and the LLM `alreadyCommitted`
flag, both of which are documented as inspection-only, not unit-tested.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Resume semantics are unit-tested (present/missing/zero-byte skip map) — ALREADY MET | `scripts/qrspi_resolve.py:detect_existing` (pre-existing) | `scripts/qrspi_resolve_test.py` `detect_existing` block (`:68–84`, pre-existing) |
| AC2: Slice-boundary resume is unit-tested (gap-agnostic enumeration) | `scripts/qrspi_resolve.py:slice_branches` / `pick_tip` (pre-existing) | `scripts/qrspi_resolve_test.py` `check("slice_branches non-contiguous", …)` (net-new) |
| AC3: A re-run does not recompute persisted upstream phases (skip-map passthrough) | `scripts/qrspi_resolve.py:build_envelope` `existing` field (pre-existing) | `scripts/qrspi_resolve_test.py` `check("AC3 build_envelope carries the existing skip-map verbatim (passthrough)", …)` + seeded-layout sanity checks (net-new) |
| AC4: The guarantee is documented | `docs/testing-dynamic-workflows.md` "Resume guarantee" section (net-new) | Manual read (doc) |
| AC5: Probe is committed or its result captured | `docs/testing-dynamic-workflows.md` "Why no transient-retry classifier exists" — probe result captured verbatim (capture-in-doc branch chosen; probe file NOT committed) | Manual read (doc) |
| AC6: Both run under `run_tests.py` and CI; suite stays green | New tests are `scripts/*_test.py`, auto-discovered by `scripts/run_tests.py` (CI gate `.github/workflows/tests.yml`) | `python3 scripts/run_tests.py` → 31 files passed, 0 failed |

## Changes by Slice

### Slice 1: Lock in and document the resume guarantee

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve_test.py` | ⚠️ modified | +42, -0 |
| `docs/testing-dynamic-workflows.md` | ⚠️ modified | +84, -0 |

Net-new test assertions: one non-contiguous `slice_branches` case (AC2); one
`build_envelope` existing-map passthrough block seeding a `<tmp>/.qrspi/<ticket>/` layout
with 4 sanity/passthrough checks (AC3); resume-framing comments on the existing
`detect_existing`/`pick_tip`/`slice_branches` blocks. No new imports — all helpers
(`detect_existing`, `slice_branches`, `pick_tip`, `build_envelope`, `ARTIFACTS`, `check`)
were already imported. Doc: new "Resume guarantee" section with phase/slice boundary framing,
the "non-empty present, not structurally valid" caveat, the inspection-only note for both the
JS phase-skip and per-slice `alreadyCommitted`, and the verbatim probe result with the
classifier-withdrawal rationale.

**Note on the diff:** `git diff main...HEAD --stat` also lists the seven `.qrspi/RUS-80/*.md`
workflow artifacts (design, plan, questions, research, structure, worktree, impl-log) carried
on the design/plan phase commits of the stack. These are QRSPI process artifacts, not part of
this slice's deliverable; the only source/doc changes are the two files above.

## Testing Summary

- [x] Slice 1: targeted unit tests — `python3 scripts/run_tests.py resolve` — 2 test files passed, 0 failed
- [x] Slice 1: focused harness — `python3 scripts/qrspi_resolve_test.py` — 86 assertions passed, 0 failed (was 81; +5 net-new: 1 non-contiguous `slice_branches` + 4 AC3 passthrough/sanity)
- [x] Full regression suite (AC6) — `python3 scripts/run_tests.py` — 31 test files passed, 0 failed
- [x] Manual verification: `docs/testing-dynamic-workflows.md` contains the "Resume guarantee" section with the embedded verbatim probe result, the classifier-withdrawal rationale, and the "non-empty present" caveat

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `.claude/workflows/probe-agent-failure.js` (optional, OQ1) | Optionally committed | NOT committed | Structure default is capture-in-doc (AC5 "or captured verbatim" branch); the probe result is embedded verbatim in `docs/testing-dynamic-workflows.md`. Committing the file was left to human discretion and not elected. |

No contract/type signatures changed (tests-and-docs only, per the ticket's hard constraint).

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `detect_existing`'s byte-count gate skips a present-but-garbage (1-byte/malformed) artifact on re-run, since it never validates content | accepted (recorded, not fixed) — out of scope (no runtime change allowed); the doc's "non-empty present, not structurally valid" caveat records the limitation explicitly | Revert the doc/test commit; no runtime behavior to roll back |
| Slice resume is decided by the non-deterministic setup-agent `alreadyCommitted` flag, not a pure helper, so unit tests can cover only the deterministic helpers, not the actual per-slice skip | accepted as designed — tests scoped to deterministic helpers; the doc states the slice-skip decision is LLM-made and verified by inspection, mirroring the AC3 JS-inspection caveat | n/a (documentation only) |
| The `ARTIFACTS` list is duplicated verbatim in `qrspi_resolve.py` and `qrspi_persist.py` and must stay in sync | mitigated — the existing `detect_existing` key-set assertion against `ARTIFACTS` is kept; duplication is a pre-existing condition, not introduced here | n/a |
| Committing `probe-agent-failure.js` could appear to add a runtime artifact, brushing the "no new runtime behavior" constraint | avoided — probe file not committed; its result is captured in the doc as evidence only | n/a |

Overall rollback: this PR is tests-and-docs only with zero runtime change, so reverting the
single implementation commit (`06110b0`) fully and safely removes all behavior-neutral
additions.

## Open Items

- **OQ1 (human call):** Whether to commit `probe-agent-failure.js` into `.claude/workflows/`
  for first-hand in-repo evidence (currently untracked in the main checkout). Default
  capture-in-doc branch was taken; committing it remains an option.
- **OQ2 (human call):** Whether the resume guarantee should also be cross-linked from
  `CLAUDE.md`'s codebase-conventions section for discoverability. Not done; unresolved.
- **OQ3 (human call):** Whether lock-in + documentation of an already-correct, already-mostly-
  tested behavior justifies a full design→plan→slice stack vs. a single small PR or folding
  into another ticket. Surfaced in design.md; the single-slice structure reflects the thinness
  but does not resolve the call.
- **Deferred tech debt (not introduced here):** unit-testing the actual skip *act* (JS
  `runPhase` early-return and per-slice `alreadyCommitted`) is impossible without refactoring
  the harness-coupled `qrspi-batch.js`; documented as inspection-only, consistent with the
  existing deferral of JS unit coverage.
