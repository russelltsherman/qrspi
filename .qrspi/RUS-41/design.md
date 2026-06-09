# Design — Build multi-agent eval driver

**Ticket:** RUS-41
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** revised (reviewer answers to OQ1–OQ4 incorporated as decisions)

## Current State

`run_loop.sh` is a single-agent optimization loop, not a multi-agent driver; it takes four positional args (`SKILL_PATH`, `EVAL_SUITE`, `MAX_ITER=5`, `TARGET_SCORE=0.85`) plus `TRIALS`/`WORKERS` env vars, and has NO flags — `--phase`, `--all`, `--regression-only` do not exist today (ref: Q1, Q4). The target agent is identified solely by the raw `SKILL_PATH` file path, passed straight to `python3 scripts/run_eval.py --skill` per iteration into `results/v${i}` output dirs (ref: Q1). There is no agent-discovery code anywhere; the 8 phase agents exist on disk and match `.claude/agents/qrspi-*.md` exactly, with the phase name being the filename stem after `qrspi-` (ref: Q5).

Fixtures are loaded per test case by `run_eval.py:build_messages`, not per agent, with each path guarded by `os.path.exists` and silently skipped if absent; suite paths are written relative to `evals/` but `run_loop.sh` runs from repo root, so fixtures are currently loaded as empty — a latent, unsurfaced path bug (ref: Q2, Q10). The single shared `evals/suite.json` holds all 15 cases tagged with a `phase` field whose 8 values match the 8 agent files 1:1; no per-phase suite files exist, so a phase driver must FILTER the shared suite by `case["phase"]` (ref: Q5, Q15).

Per-run output is a single `results.json` from `run_eval.py`, then `grades.json` from `grade.py` (keys `train_score`/`test_score`/`train_test_gap`/`cases[]`), then `report.py` aggregates across `results/v*/grades.json` into `report.json`+`ledger.json`; `results/all/` does not exist anywhere in the repo (ref: Q3, Q8). `report.py` treats EVERY immediate `results/` subdir containing a `grades.json` as a version, so a new `results/all/` subdir would be wrongly enumerated unless excluded (ref: Q3, Q11).

There is NO exit-code convention: all eval scripts exit 0 except on uncaught exceptions, and `run_loop.sh` encodes pass/fail only as JSON data (`break` on target met, `continue` on regression), never as a process exit code — CI propagation must be built new (ref: Q6). The loop distinguishes a regression iteration (the `continue` branch, no revision) from a revision iteration (fall-through to Steps 3–4, `diagnose.py`+`revise.py`) by a 0.05 suite-level score-drop check; `--regression-only` must short-circuit before Step 3 (ref: Q7). Two regression thresholds coexist: 0.05 suite-level in the loop and 0.2 per-case in `report.py:detect_regressions` (ref: Q7).

An execution failure is INDISTINGUISHABLE from a legitimate low score at grading time — `grade.py` never inspects `result.error`, so a crashed agent scores ~0; the only failure signal is a printed `ERROR`/`EXCEPTION` line and the `error` key in `results.json` (ref: Q9). `timeout_ms` is plumbed but never enforced (ref: Q9). A structurally broken suite hard-fails via `ValueError`, but missing fixtures degrade silently (ref: Q10). Re-entering an output dir is idempotent-by-overwrite with no cleanup — stale sibling files persist and `revise.py` appends rather than overwrites (ref: Q11).

Tests follow a stdlib-only `unittest` convention: a `<module>_test.py` sibling, bare-name import (CWD=`scripts/`), `tempfile` isolation, run via `python3 scripts/<module>_test.py`; the five eval scripts have NO tests today and there is NO e2e/smoke test for `run_loop.sh` (ref: Q12, Q13). Output is JSON-as-state-bus + stdout-as-human-log: `grade.py` prints a train/test summary block and `report.py` prints an aggregate block with `ALERT:` lines, scores formatted `:.4f` (ref: Q14). No phase dimension exists in any output — `grade.py` partitions only by `split` (train/test) and drops `phase` from its emitted `case_grade`; the `phase` field on each suite case is the latent key for any phase-level signal (ref: Q15).

## Desired End State

A new multi-agent driver enumerates `.claude/agents/qrspi-*.md`, runs each phase against its filtered slice of the shared suite, aggregates per-phase scores, and emits a consolidated report at `results/all/`, distinguishing phase-level from suite-level regressions and propagating a non-zero exit code in CI mode.

- **AC1 — "`./scripts/eval_all.sh` (or `python3 scripts/eval_all.py`) runs the suite against every agent and emits a consolidated report."** A new entrypoint accepts `--all` (glob all 8 agents, ref: Q5), `--phase <name>` (map name → `.claude/agents/qrspi-<name>.md`, ref: Q4), and runs each agent against the suite filtered to `case["phase"] == <name>` (ref: Q5). Each phase writes to its own subdir `results/all/<phase>/` (distinct subdir prevents overwrite, ref: Q8) and a top-level `results/all/summary.json` is written as a separate file (ref: Q8).
- **AC2 — "CI-friendly mode exits non-zero on any regression."** `--regression-only` runs exactly one iteration per agent with no revision step (short-circuits before Step 3, ref: Q7) and the driver explicitly `sys.exit`s non-zero on any detected regression — new behavior, since no exit-code convention exists today (ref: Q6).
- **AC3 — "The report distinguishes phase-level regressions from suite-level regressions."** The summary groups scores by `phase` (the latent suite key, ref: Q15) for phase-level signal, and computes a suite-level aggregate across all phases; the two are reported as distinct fields. A crashed agent must be surfaced distinctly from a low score by inspecting `results[].error` (ref: Q9), and the `results/all/` subdir must be excluded from `report.py`'s version enumeration (ref: Q3, Q11).

## Delta

- **New file `scripts/eval_all.py`** — the multi-agent driver. Discovers agents via `glob('.claude/agents/qrspi-*.md')` deriving `phase = stem.removeprefix('qrspi-')` (ref: Q5); maps `--phase <name>` → `.claude/agents/qrspi-<name>.md` (ref: Q4); filters the shared suite by `case["phase"]` (ref: Q5); invokes the existing single-agent path per phase into `results/all/<phase>/` (ref: Q8); reads each phase's `grades.json` + `results.json` `error` fields (ref: Q9); writes `results/all/summary.json`; `sys.exit(1)` on regression in `--regression-only` (ref: Q6).
- **New file `scripts/eval_all_test.py`** — stdlib-only `unittest` sibling, bare-name import, `tempfile` isolation, `python3 scripts/eval_all_test.py` (ref: Q12). Covers: agent discovery/glob, phase→path mapping, suite filtering by phase, summary aggregation (phase-level vs suite-level), error-vs-low-score distinction, and exit-code-on-regression.
- **Optional `scripts/eval_all.sh`** — thin wrapper delegating to `eval_all.py` so the AC1 `./scripts/eval_all.sh` invocation works (ref: Q4); a Python-only entrypoint also satisfies AC1 ("or `python3 scripts/eval_all.py`").
- **New output layout `results/all/<phase>/{results.json,grades.json}` + `results/all/summary.json`** — designed, not discovered; `summary.json` carries per-phase scores and a suite-level aggregate (ref: Q3, Q8). `report.py`'s subdir enumerator must exclude `results/all/` (or the driver must write outside `results/`) to avoid it being read as a version (ref: Q3, Q11).
- **Latent fixture path bug (ref: Q2):** the suite's `fixtures/...` paths do not resolve from repo root; the driver should either run with CWD=`evals/` or pass resolved paths so per-phase runs load real context — surface, do not silently inherit.

## Pattern Decisions

### Decision 1: Implementation language (shell vs Python)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Python `eval_all.py` (+ optional thin `.sh`) | Matches the testable stdlib-`unittest` convention (ref: Q12); real glob/filter/aggregate logic is unit-testable; clean `sys.exit` for CI (ref: Q6) | Two files if `.sh` alias also wanted |
| B | Pure bash `eval_all.sh` extending `run_loop.sh` | Mirrors existing loop's idiom | Shell logic is hard to unit-test; no existing shell test harness (ref: Q13); aggregation/JSON in bash is brittle |

**Recommendation:** Option A
**Rationale:** The ticket allows shell or Python; the only testing convention in the repo is stdlib `unittest` on Python modules (ref: Q12), and there is no shell test harness at all (ref: Q13). Python makes the discovery/filter/aggregate logic directly testable and gives a clean exit-code path for CI (ref: Q6). A thin `eval_all.sh` shim can satisfy the literal `./scripts/eval_all.sh` AC if desired.
**NEW PATTERN?** No — follows the existing `scripts/*.py` + `_test.py` sibling pattern (ref: Q12).

### Decision 2: Per-phase suite handling

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Filter the shared `suite.json` in-memory by `case["phase"]` before each run | Single source of truth; matches the 1:1 phase↔case mapping already present (ref: Q5) | Driver owns the filter; must construct a valid sub-suite (preserve `name`/`cases` to pass `load_suite`, ref: Q10) |
| B | Pre-split into per-phase suite files on disk | Reuses `--suite` as-is | No per-phase files exist (ref: Q5); duplicates data; drift risk |

**Recommendation:** Option A
**Rationale:** Per-phase suite files do not exist and the shared suite already tags every case with `phase` (ref: Q5, Q15). Filtering in-memory keeps one source of truth; the sub-suite must retain top-level `name`/`cases` or `load_suite` raises `ValueError` (ref: Q10).
**NEW PATTERN?** Yes — no code groups or filters by `phase` today (`grade.py` even drops it, ref: Q15). Justified: the phase dimension is the core thing this ticket adds, and the raw material (`case["phase"]`) already exists.

### Decision 3: Output layout and `report.py` collision

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `results/all/<phase>/` per phase + `results/all/summary.json`, and exclude `results/all/` from `report.py`'s enumerator | Per-subdir aggregation mirrors `report.py` (ref: Q8); distinct subdir avoids overwrite (ref: Q8) | Must touch `report.py` to exclude the new dir (ref: Q3, Q11) |
| B | Write under a sibling dir outside `results/` (e.g. `results-all/`) | Zero risk of `report.py` mis-enumeration (ref: Q11) | Diverges from the ticket's stated `results/all/` path |

**Recommendation:** Option A
**Rationale:** The ticket explicitly names `results/all/`. `report.py` scans every `results/` subdir with a `grades.json` as a version (ref: Q3, Q11), so the driver must give each phase a distinct subdir (no overwrite, ref: Q8) AND `report.py` must skip the `all/` subtree. The summary is a separate `summary.json` so it is never confused with a phase's `grades.json` (ref: Q8).
**NEW PATTERN?** Yes — `results/all/` is a designed layout with no on-disk precedent (ref: Q3). Justified by the consolidated-report AC.

### Decision 4: Failure vs low-score surfacing

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Driver inspects each phase's `results.json` `error` fields and marks the phase `errored` distinctly from `low_score` in the summary | Closes the Q9 gap that makes a crash indistinguishable from a 0 score | Driver reads `results.json`, not just `grades.json` |
| B | Trust `grades.json` score only | Simplest | A crashed agent silently reports as a legitimate 0 across 8 agents (ref: Q9) |

**Recommendation:** Option A
**Rationale:** `grade.py` never reads `result.error`, so an execution failure scores identically to a real low score (ref: Q9). Iterating 8 agents amplifies this — the driver must inspect `results[].error` to report harness health honestly, which is the ticket's "overall harness health" goal.
**NEW PATTERN?** Yes — no existing code distinguishes error from low score (ref: Q9). Justified: required to report harness health, not just scores.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fixtures silently load empty due to CWD/path mismatch, so all phases score ~0 and the report looks healthy-but-zero (ref: Q2, Q10) | high | high | Run per-phase invocation with CWD=`evals/` or resolve fixture paths in the driver; assert non-empty context or warn on a skipped fixture (ref: Q10) |
| `report.py` enumerates `results/all/` as a version, corrupting the ledger (ref: Q3, Q11) | high | med | Exclude `results/all/` from the `report.py` subdir scan; cover with a unit test |
| Harness is a non-functional placeholder — stub `execute_single` returns empty output, so even a correct driver yields all-zero scores (ref: Q13) | high | med | Scope this ticket to plumbing (discovery, filtering, aggregation, exit code, layout) and validate that, not real scores; document the stub dependency |
| A crashed agent scores as a legitimate 0, hiding regressions across 8 agents (ref: Q9) | med | high | Driver inspects `results[].error` and marks `errored` distinct from `low_score` in the summary (Decision 4) |
| Sub-suite filtering drops `name`/`cases` and trips `load_suite`'s `ValueError`, aborting the whole `--all` run under `pipefail` (ref: Q10) | med | med | Construct the filtered sub-suite preserving top-level `name`/`cases`; unit-test the filter; isolate per-phase failures so one bad phase does not abort the suite |
| Two regression thresholds (0.05 loop, 0.2 report) create ambiguity over which defines a "regression" for CI exit (ref: Q7) | med | med | Pick and document one threshold for `--regression-only` CI; make it a named constant covered by a test |

## Resolved Questions

The design originally carried four open questions (OQ1–OQ4). The reviewer answered each one
inline on the design PR; those answers are now incorporated as binding decisions and the
questions are closed. Each bullet names the original question, the reviewer's verbatim
answer-word, and the resulting decision so the answer is traceable to the thread that raised it.

- **OQ1 — regression baseline for `--regression-only` (absolute floor vs drop-vs-previous) →
  reviewer: *drop*.** This is **not** a blocking design question and is **dropped**. The driver
  adopts the single documented threshold called out in the Risk Register (a named constant
  covered by a test) for the `--regression-only` CI exit; the precise baseline-vs-floor mechanics
  are an implementation detail settled in the plan/structure phase, not an open design decision.
  (Lands against the Risk Register row "Two regression thresholds … create ambiguity over which
  defines a regression for CI exit", whose mitigation already pins one documented threshold.)
- **OQ2 — fix the latent fixture path bug in this ticket, or surface and defer? → reviewer:
  *defer*.** The driver does **not** fix the latent fixture path bug (ref: Q2) here — fixing it
  would change scores for every existing single-agent run, which is out of scope. The driver
  **surfaces** it (warning on a skipped/empty fixture) and defers the actual path fix to a
  separate ticket, consistent with the Risk Register mitigation (assert non-empty context / warn
  rather than silently inherit).
- **OQ3 — is modifying `report.py` to exclude `results/all/` in scope, or write outside
  `results/`? → reviewer: *modify*.** Modifying `report.py` to exclude `results/all/` from its
  version enumeration **is in scope** (Decision 3, Option A — the chosen approach). The ticket
  explicitly names `results/all/`, so the driver writes there and `report.py`'s subdir scan is
  modified to skip the `all/` subtree, covered by a unit test. Option B (writing outside
  `results/`) is rejected.
- **OQ4 — ship now against the stubbed harness, or wait for the runtime to be wired in? →
  reviewer: *the runtime will be wired*.** This ships **now** against the stubbed harness as
  plumbing-only validation (discovery, filtering, aggregation, exit code, layout — verified by
  unit tests, not real scores). The runtime will be wired in later; this ticket does not block on
  it. The stub dependency is documented (Risk Register).
