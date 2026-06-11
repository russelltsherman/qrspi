# Structure Outline — Build multi-agent eval driver

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

No language-level types (Python, stdlib-only, dict/JSON-shaped). The following
JSON record shapes are contracts, not classes:

- `PhaseResult { phase: str, status: "ok" | "errored" | "low_score", train_score: float, test_score: float, error: str | null, results_dir: str }`
  — one per agent/phase, derived from that phase's `results.json` (for `error`) + `grades.json` (for scores).
- `Summary { phases: { <phase>: PhaseResult }, suite_aggregate: { train_score: float, test_score: float }, phase_regressions: [str], suite_regression: bool, errored_phases: [str] }`
  — the consolidated `results/all/summary.json` payload (AC3: phase-level vs suite-level fields are distinct).

## Modified Types

- None. (`report.py`'s version-enumeration is a control-flow filter, not a type change — ref: design.md §Delta, Decision 3.)

## Contracts

Cross-slice / cross-module interfaces (pseudo-code signatures, not implementations):

- `discover_agents(agents_dir: str = ".claude/agents") -> list[str]` — glob `qrspi-*.md`, return phase names via `stem.removeprefix("qrspi-")` (ref: Q5).
- `phase_to_agent_path(phase: str, agents_dir: str) -> str` — map `--phase <name>` → `.claude/agents/qrspi-<name>.md` (ref: Q4).
- `filter_suite(suite: dict, phase: str) -> dict` — return a sub-suite preserving top-level `name` + filtered `cases` where `case["phase"] == phase`; must keep `name`/`cases` keys or `load_suite` raises `ValueError` (ref: Q10).
- `read_phase_result(phase: str, results_dir: str) -> PhaseResult` — read `<results_dir>/grades.json` (scores) + `results.json` (`error` fields); mark `errored` distinct from `low_score` (ref: Q9, Decision 4).
- `aggregate(phase_results: list[PhaseResult], regression_threshold: float) -> Summary` — compute per-phase signal + suite-level aggregate + regression flags (ref: AC3).
- `REGRESSION_THRESHOLD: float` — single named constant documenting the one threshold used for `--regression-only` CI exit (ref: Q7, Risk Register, OQ1).
- `main(argv) -> int` — CLI: `--all`, `--phase <name>`, `--regression-only`; returns/`sys.exit`s non-zero on regression in `--regression-only` mode (ref: Q6, AC2).
- `report.py` enumerator — MUST skip the `all/` subdir when scanning `results/` for versions (ref: Q3, Q11). This is the contract Slice 1 establishes and Slice 2 depends on.

## Slice 1: Guard `report.py` against the `results/all/` subtree

**Goal:** `report.py`'s version enumeration excludes `results/all/`, so the new consolidated-report layout (written in Slice 2) cannot be mis-read as a version and corrupt the ledger. Verifiable in isolation, before the driver exists, by constructing a `results/` tree with an `all/` sibling and asserting it is skipped.
**Files touched:**

- ⚠️ `scripts/report.py` — exclude the `all/` subdir from the `results/` subdir scan that enumerates versions (ref: Q3, Q11; design.md Decision 3, OQ3 → *modify*).
- ✨ `scripts/report_test.py` — stdlib-only `unittest` sibling: assert `results/all/` is NOT enumerated as a version, and that a normal `results/v*/` dir still is (regression guard). Bare-name import, `tempfile` isolation, run via `python3 scripts/report_test.py` (ref: Q12).
**Verification:**
- [ ] `python3 scripts/report_test.py` passes, including the new case proving `results/all/` is excluded and `results/v1/` is still counted.
**Context cost:** S
**Depends on:** none

## Slice 2: `eval_all.py` multi-agent driver + tests (+ optional shim)

**Goal:** A new entrypoint discovers the 8 phase agents, runs each against its phase-filtered slice of the shared suite into `results/all/<phase>/`, writes `results/all/summary.json` distinguishing phase-level from suite-level regressions and `errored` from `low_score`, and exits non-zero on regression in `--regression-only`. End-to-end testable via the unit suite against the stubbed harness (plumbing-only, per OQ4 — not real scores).
**Files touched:**

- ✨ `scripts/eval_all.py` — the driver. Implements `discover_agents`, `phase_to_agent_path`, `filter_suite`, `read_phase_result`, `aggregate`, `REGRESSION_THRESHOLD`, and `main` per the Contracts section. Invokes the existing single-agent path per phase into `results/all/<phase>/`; reads `grades.json` + `results.json` `error`; writes `results/all/summary.json`; `sys.exit(1)` on regression under `--regression-only` (ref: Q4, Q5, Q6, Q8, Q9). Surfaces (warns, does not fix) the latent empty-fixture condition (ref: Q2, OQ2 → *defer*). Isolates per-phase failures so one bad/errored phase does not abort the whole `--all` run (ref: Q10, Risk Register).
- ✨ `scripts/eval_all_test.py` — stdlib-only `unittest` sibling covering: agent discovery/glob, phase→path mapping, suite filtering by phase (preserving `name`/`cases`), summary aggregation (phase-level vs suite-level distinct fields), error-vs-low-score distinction, `results/all/` subdir excluded from `report.py` (integration with Slice 1), and exit-code-on-regression. Bare-name import, `tempfile` isolation, `python3 scripts/eval_all_test.py` (ref: Q12).
- ✨ `scripts/eval_all.sh` — optional thin wrapper delegating to `python3 scripts/eval_all.py "$@"` so the literal `./scripts/eval_all.sh` AC1 invocation works (ref: Q4). Shares this slice's verification; not independently testable.
**Verification:**
- [ ] `python3 scripts/eval_all_test.py` passes (all listed cases).
- [ ] Manual e2e: `python3 scripts/eval_all.py --all` writes `results/all/<phase>/` for each discovered agent and `results/all/summary.json`; `--regression-only` returns non-zero exit when a phase regresses (against the stubbed harness, plumbing only — ref: OQ4).
- [ ] `python3 scripts/report_test.py` still passes (Slice 1 guard holds once `results/all/` is actually populated).
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **Stubbed harness yields all-zero scores.** The design states `evals/`/`run_eval.py` is a non-functional placeholder whose `execute_single` returns empty output, so real scores will all be ~0 (ref: Q13, Risk Register, OQ4). This slicing validates plumbing (discovery, filter, aggregation, exit code, layout) via unit tests, NOT real-score correctness. Whether the manual e2e check can distinguish a true regression from the uniform-zero stub output is unverified until the runtime is wired in (the design explicitly defers that wiring).
- **Single regression threshold for CI exit.** OQ1 resolved to *drop* and the Risk Register pins "one documented threshold (a named constant covered by a test)," but the precise baseline mechanics (absolute floor vs drop-vs-previous, and which of the two existing thresholds — 0.05 loop vs 0.2 report — to adopt) are left to plan/structure as an implementation detail. `REGRESSION_THRESHOLD` is named as the contract, but its exact value/semantics are not pinned by the design and need to be chosen (and justified) during planning.
- **Exact `report.py` enumeration mechanism.** The design asserts `report.py` "treats every immediate `results/` subdir containing a `grades.json` as a version" (ref: Q3, Q11) and that excluding `all/` is the fix, but the precise code location/shape of that scan was not quoted. Slice 1 must locate it; if the enumerator's structure differs from the design's description, the exclusion approach may need adjustment.
- **`run_eval.py` single-agent invocation surface.** The driver "invokes the existing single-agent path per phase" (ref: design.md §Delta), but whether that is a subprocess call to `run_eval.py --skill` (as `run_loop.sh` does) or a Python import was not pinned. The Contracts assume the driver constructs a filtered sub-suite and drives `run_eval.py` per phase; the exact integration seam (subprocess vs import, and how the filtered sub-suite is passed) needs confirmation in planning.
