# Questions — Test + document the existing phase/slice resume guarantee (transient-retry classifier withdrawn)

**Ticket:** RUS-80
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `detect_existing` map each planning artifact (`questions, research, design, structure, plan, worktree`) to its `exists and non-empty` boolean, and what file path / read mechanism does it use to decide presence and non-emptiness?
  **Target:** `scripts/qrspi_resolve.py` (the `detect_existing` function)
- Q2: How does the orchestrator consume the artifact-existence map to skip an already-persisted phase, and where is that skip decision applied in the run loop?
  **Target:** `.claude/workflows/qrspi-batch.js` (the phase-skip consumption of `detect_existing`'s output)
- Q3: How does `persistArtifact` sequence relative to the producer and critic loop, such that it functions as the post-validation success gate that runs only after those pass?
  **Target:** `scripts/qrspi_persist.py` and the `runPhase`/`persistArtifact` path in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What is the signature and return shape of `slice_numbers` and `slice_branches`, and what input (`branch_set`) do they consume to derive the ascending slice set?
  **Target:** `scripts/qrspi_resolve.py` (the `slice_numbers` / `slice_branches` functions)
- Q5: What is the existing test structure and assertion style for `detect_existing` in the current resolver test, that a new resume-contract test would extend or sit as a sibling to?
  **Target:** the existing `qrspi_resolve` test under `scripts/*_test.py`

## State Management

- Q6: What persisted state on disk and in branch naming distinguishes a "done" phase or slice from one that must be (re)computed on a re-run, and where is that state read from?
  **Target:** the module responsible for resolve-time artifact + branch detection (`scripts/qrspi_resolve.py`)
- Q7: How is the resolver's decision / skip-map represented in its output envelope, and which fields encode that a persisted upstream phase is skippable?
  **Target:** `scripts/qrspi_resolve.py` (decision envelope construction)

## Edge Cases

- Q8: How does `detect_existing` treat a present-but-empty (zero-byte) artifact versus a missing artifact — does a truncated/aborted write yield `False` (recompute) rather than a false `True` (skip)?
  **Target:** `scripts/qrspi_resolve.py` (the non-empty check in `detect_existing`)
- Q9: When `agent()` returns a bare `null` mid-phase or mid-slice, what code path causes that phase/slice to be recomputed on re-run rather than trusting a half-written artifact?
  **Target:** the `agent()` failure handling and `persistArtifact` gate in `.claude/workflows/qrspi-batch.js`
- Q10: How do `slice_numbers` / `slice_branches` behave when `branch_set` contains a non-contiguous or partial set of slice branches (e.g. slice-1 and slice-3 present, slice-2 absent) — which next slice is derived?
  **Target:** `scripts/qrspi_resolve.py` (slice-set derivation logic)

## Testing

- Q11: How are existing resolver tests seeded against a temp worktree (pre-populated artifacts, fixture layout), so a new test can pre-seed persisted upstream artifacts and assert the skip-map marks those phases skippable?
  **Target:** the existing resolver test in `scripts/*_test.py` and its temp-worktree fixture setup
- Q12: How does `scripts/run_tests.py` discover and run each `scripts/*_test.py`, and how does `.github/workflows/tests.yml` invoke that same suite as the CI regression gate?
  **Target:** `scripts/run_tests.py` and `.github/workflows/tests.yml`

## Observability

- Q13: What does `probe-agent-failure.js` emit/record as the evidentiary output of the `agent()` failure seam (the bare `null` with discarded error message), and in what form is that result captured for citation in docs?
  **Target:** `.claude/workflows/probe-agent-failure.js`
- Q14: What does `docs/testing-dynamic-workflows.md` currently state about resume semantics and the `qrspi-batch.js` testing seam, that this ticket must extend to document the phase/slice-boundary resume guarantee?
  **Target:** `docs/testing-dynamic-workflows.md`
