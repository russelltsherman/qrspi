# Design — [DRYRUN] Add --list-cases flag to run_eval.py

**Ticket:** RUS-43
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

`scripts/run_eval.py` parses CLI arguments with `argparse`, constructing a single `ArgumentParser` inside `main()` and registering all flags immediately before `parse_args()` (ref: Q3). It accepts six optional flags and no positional arguments: `--skill`, `--suite`, `--output` (all `required=True`), plus `--trials`, `--workers`, `--timeout` with defaults (ref: Q4). No flag named `--list-cases`, `--list`, or `-l` currently exists, so there is no naming collision (ref: Q4).

The entrypoint flow is: `parse_args()` → build an `EvalConfig` dataclass → call `run_suite(config)` (ref: Q5). `run_suite` is where side effects begin — `os.makedirs(output_dir)`, a `ThreadPoolExecutor` dispatch, and a final `json.dump` to `results.json` (ref: Q6). The agent-execution path (`execute_single`) is currently an unfinished stub that produces empty output and does no real model work (ref: Q6).

Cases are loaded by `load_suite(suite_path) -> dict`, which reads the file, calls `json.load`, validates the top-level keys `name` and `cases` and the per-case keys `id`, `prompt`, `assertions`, then returns the whole parsed dict; cases live as a plain `list[dict]` at `suite["cases"]` (ref: Q1). `load_suite` is pure — only a file read and in-memory validation, no network, model, or write side effects (ref: Q6). The case identifier is the `id` key (e.g. `"case_001"`) and the phase is the `phase` key (e.g. `"questions"`); all 15 current cases populate both (ref: Q2). Critically, `phase` is NOT in the validated per-case key set, so the loader tolerates a phase-less case even though every current case has one (ref: Q9).

The script never calls `sys.exit` and does not import `sys`; success is implicit exit 0, validation failures raise `ValueError` (exit 1), and argparse errors exit 2 (ref: Q7). All console output goes to `stdout` via bare `print(...)`; there is no `stderr` use and no `logging` (ref: Q13). There is no test harness anywhere in the repository — no `tests/`, no `conftest.py`, no `pyproject.toml`, `requirements.txt`, or `Makefile` — though `python3` 3.14.2 and `pytest` 9.0.3 are importable in the environment (ref: Q11). Scanning all 15 cases found zero `id`/`phase` values containing tab, space, or newline characters (ref: Q10).

## Desired End State

After this change, `python3 scripts/run_eval.py --list-cases --suite evals/suite.json` prints one line per case in the form `<case_id>\t<phase>` (tab-separated) to stdout, then exits 0 without running any grading. Mapping each acceptance criterion to behavior:

- **AC1 — prints one line per case as `<case_id>\t<phase>`:** After arguments parse, when `--list-cases` is set, the code calls `load_suite(args.suite)`, iterates `suite["cases"]`, and prints `f"{case['id']}\t{phase}"` for each, where `phase` is read defensively as `case.get("phase", "")` to tolerate the loader's optional-phase contract (ref: Q9). Output lands on stdout, matching every existing `print` in the file (ref: Q13). The tab delimiter is unambiguous for current data (ref: Q10).
- **AC2 — flag exits 0 and runs no grading:** The `--list-cases` branch short-circuits immediately after `parse_args()` and BEFORE `EvalConfig` construction and `run_suite`, so `os.makedirs`, the executor, and `results.json` writes never run (ref: Q5, Q6). The branch returns from `main()` (implicit exit 0) or calls `sys.exit(0)`.
- **AC3 — existing no-flag behavior unchanged:** `--list-cases` defaults to false via `action="store_true"`; when absent, control falls through to the unchanged `EvalConfig` → `run_suite` path. The required-flag resolution (see Decision 2) must preserve the current behavior that a normal run still demands `--skill`, `--suite`, and `--output` (ref: Q4).

## Delta

- **Modify `scripts/run_eval.py`:**
  - Register a new boolean flag `parser.add_argument("--list-cases", action="store_true", ...)` alongside the existing flags (ref: Q3 convention, Q4 no collision).
  - Resolve the `required=True` conflict on `--skill`/`--suite`/`--output` so a listing-only invocation needs only `--suite` (see Decision 2).
  - Insert a short-circuit block after `parse_args()` and before `EvalConfig` construction: load the suite, print each `id`/`phase` line, exit 0 (ref: Q5).
  - If an explicit `sys.exit(0)` is chosen, add `import sys` (ref: Q7); otherwise return from `main()` for implicit 0.
- **New file (testing):** a test for `--list-cases` behavior, establishing the first test in the repo (ref: Q11). See Decision 4 for harness and Decision 3 for fixture choice.
- **No change to `load_suite`, `run_suite`, `execute_single`, `EvalConfig`, or `evals/suite.json`.**

## Pattern Decisions

### Decision 1: Where the listing logic lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline block inside `main()` after `parse_args()`, reusing `load_suite` | Minimal surface; matches stub-era simplicity; `load_suite` already pure (ref: Q6) | `main()` grows a branch |
| B | Extract a `list_cases(suite_path)` helper called from `main()` | Unit-testable without subprocess; isolates format | Adds a function for ~4 lines; no existing helper-per-mode precedent |

**Recommendation:** Option B
**Rationale:** A small `list_cases(suite_path) -> None` (or returning the formatted string) lets the test assert the listing directly without spawning a subprocess, which matters because no test harness exists yet (ref: Q11) and a pure helper is the cheapest thing to test first. It still reuses the pure `load_suite` (ref: Q1, Q6) and keeps `main()` to a one-line dispatch, consistent with the uniform `main()` structure across scripts (ref: Q3).
**NEW PATTERN?** No — `load_suite` reuse and stdlib-only helpers are already the norm (ref: Discovered Patterns).

### Decision 2: Resolving the `required=True` conflict

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Drop `required=True` on `--skill`/`--output`; validate manually in `main()` for the normal path | Lets `--list-cases --suite X` parse cleanly; single parser | Re-implements argparse's required-flag error; risk of weakening normal-run validation if not careful |
| B | Pre-scan `sys.argv` for `--list-cases` before building the parser; if present, use a parser requiring only `--suite` | Keeps `required=True` intact for normal runs | Two parser configs; pre-scan is a non-standard argparse idiom |
| C | Keep `--suite` required, drop only `--skill`/`--output` required, and after parse: if not `--list-cases`, error when `--skill`/`--output` missing | Minimal divergence; `--suite` stays mandatory for both modes (both need it) | Manual check for two flags in normal path |

**Recommendation:** Option C
**Rationale:** Both modes require `--suite`, so it stays `required=True`. Only `--skill` and `--output` are normal-run-only; dropping their `required` and adding an explicit guard (`if not args.list_cases and (not args.skill or not args.output): parser.error(...)`) preserves AC3's unchanged normal behavior while letting listing run with `--suite` alone (ref: Q4 — this is the single most important constraint surfaced by research). Using `parser.error()` keeps the argparse exit-2 convention for misuse (ref: Q7).
**NEW PATTERN?** Yes (minor) — manual post-parse validation is not used elsewhere; existing scripts rely purely on `required=True`. Justified because no existing pattern supports a single parser serving two flag-requirement modes; the alternatives (B's argv pre-scan) are more obscure.

### Decision 3: Test fixture source

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Point the test at the real `evals/suite.json`, assert against its 15 known pairs | Zero fixture authoring; exercises real data (ref: Q12) | Brittle — adding/editing a case breaks the test |
| B | Construct a small inline temp suite JSON in the test | Hermetic; stable against suite edits | Authors a throwaway fixture |

**Recommendation:** Option B
**Rationale:** A hermetic 2–3 case temp suite makes the test assert exact output independent of `suite.json` churn, and lets it cover the phase-less case path (ref: Q9) and the zero-case empty-output path (ref: Q8) that the real suite cannot. No fixture precedent exists to reuse (ref: Q12), so authoring one is unavoidable; inline keeps it minimal.
**NEW PATTERN?** Yes — this is the first test in the repository (ref: Q11). Justified: the ticket's "runs no grading / exits 0" criteria are verifiable only by test, and no harness exists to extend.

### Decision 4: Exit mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `return` from `main()` after listing (implicit exit 0) | No `import sys` needed; matches current implicit-0 success convention (ref: Q7) | Less explicit than sibling `check_scope.py` |
| B | Explicit `sys.exit(0)` after listing | Matches `check_scope.py:70` sibling pattern; unambiguous AC2 satisfaction | Requires adding `import sys` (ref: Q7) |

**Recommendation:** Option A
**Rationale:** `run_eval.py` already relies on implicit exit 0 for its success path and does not import `sys` (ref: Q7). A `return` from `main()` satisfies AC2's "exit 0" without adding an import, keeping the diff minimal and consistent with this file's own convention rather than importing the sibling's.
**NEW PATTERN?** No — implicit exit 0 is the file's established success convention (ref: Q7).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Relaxing `required=True` weakens normal-run validation, letting a no-flag run proceed without `--skill`/`--output` and crash deeper in `run_suite` | med | high | Decision 2 Option C adds an explicit post-parse guard that calls `parser.error()` (exit 2) when `--skill`/`--output` are missing in non-listing mode; cover with a test asserting the error path (ref: Q4, Q7) |
| A future phase-less case causes `KeyError` if listing reads `case["phase"]` directly | low | med | Read defensively as `case.get("phase", "")`; the loader's contract permits absent `phase` even though current data has none (ref: Q9) |
| Missing or malformed `--suite` file makes listing crash with an uncaught traceback (exit 1, not 0) | med | low | Inherits current `load_suite` behavior (ref: Q8); acceptable for a DRYRUN ticket, but note it — AC2's "exit 0" applies to the valid-suite path only |
| Tab in a future case `id` or `phase` corrupts the `\t`-delimited output | low | low | Current data is whitespace-free (ref: Q10); no mitigation needed now, flagged as a known format assumption |

## Open Questions

- OQ1: Should the listing apply only to the `--suite`-passed file, or default to `evals/suite.json` when `--suite` is omitted? Decision 2 keeps `--suite` required for both modes; confirm that is acceptable versus a convenience default. (ref: Q4, Q12 — two suite files coexist with no documented canonical one.)
- OQ2: Should `--list-cases` print a header line (suite name/version, reachable via the full dict from `load_suite` per ref: Q1, Q286) or strictly the bare `id\tphase` lines? The ticket specifies only the per-case lines; confirm no header is wanted.
- OQ3: Is a non-zero exit acceptable when `--suite` points at a missing/malformed file under `--list-cases`, or should that path be caught and reported cleanly? (ref: Q8)
