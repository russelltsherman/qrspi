# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: How does `scripts/run_eval.py` currently load and parse `evals/suite.json`, and what in-memory structure holds the parsed cases?

**Answer:** `load_suite(suite_path: str) -> dict` opens the file, calls `json.load`, validates top-level required keys (`name`, `cases`) and per-case required keys (`id`, `prompt`, `assertions`), then returns the whole parsed `dict`. The cases live as a plain Python `list[dict]` at `suite["cases"]`. There is no dataclass wrapper for cases — they remain raw dicts. `load_suite` is called from `run_suite` (`scripts/run_eval.py:148`), which assigns `cases = suite["cases"]` (`scripts/run_eval.py:158`).

**Evidence:**

```python
def load_suite(suite_path: str) -> dict:
    """Load and validate the eval suite definition."""
    with open(suite_path) as f:
        suite = json.load(f)

    required = {"name", "cases"}
    missing = required - set(suite.keys())
    if missing:
        raise ValueError(f"Suite missing required fields: {missing}")

    for case in suite["cases"]:
        case_required = {"id", "prompt", "assertions"}
        case_missing = case_required - set(case.keys())
        if case_missing:
            raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
    return suite
```

— `scripts/run_eval.py:42-58`
**Dependencies:** Standard library only (`json`, `open`). No upstream config object is needed to call `load_suite` — it takes a bare path string. Downstream: `run_suite` consumes the returned dict.
**Implicit contracts:** Validation enforces `id`, `prompt`, `assertions` per case but NOT `phase`. The function returns the entire suite dict (not just cases), so callers reach `suite["name"]` and `suite["cases"]` directly.

## Q2: What is the schema of `evals/suite.json` — specifically, what key holds the case identifier and what key holds the phase value that `--list-cases` must print?

**Answer:** Case identifier is the `id` key (string, e.g. `"case_001"`). Phase is the `phase` key (string, e.g. `"questions"`). All 15 cases in the current suite have both fields populated. Observed phase values: `questions`, `research`, `design`, `structure`, `plan`, `worktree`, `implement`, `pr`. The full set of keys present across cases is: `assertions, context, difficulty, id, name, phase, prompt, split, tags`. Top-level suite keys include `name`, `version`, `description`, `split`, `defaults`, `cases`.

**Evidence:**

```json
{
  "id": "case_001",
  "name": "questions_happy_path",
  "phase": "questions",
  "prompt": "Generate questions for the following ticket.",
  "context": { ... },
  "assertions": [ ... ]
}
```

— `evals/suite.json:13-18` (first case)

```
case_001 | questions
case_002 | questions
case_003 | research
...
case_013 | pr
case_014 | design
case_015 | questions
```

(programmatic dump of all 15 `id` | `phase` pairs)
**Dependencies:** None beyond the JSON file.
**Implicit contracts:** `id` is the assertion-engine key (`load_suite` requires it; `run_suite` uses `case["id"]` as a dict key in `futures` and in progress output). `phase` is informational/categorical — never validated, never required by `load_suite`.

## Q3: What argument-parsing mechanism does `run_eval.py` use (argparse, click, manual `sys.argv`), and where are existing flags registered?

**Answer:** `argparse`. The `argparse` module is imported at `scripts/run_eval.py:8`. A single `ArgumentParser` is constructed in `main()` at `scripts/run_eval.py:218` with all flags registered immediately after via `parser.add_argument(...)` calls at lines 219-224, followed by `args = parser.parse_args()` at line 225. This is the same pattern used by every sibling script (`check_scope.py`, `grade.py`, `diagnose.py`, `revise.py`, `report.py`).

**Evidence:**

```python
def main():
    parser = argparse.ArgumentParser(description="Run QRSPI eval suite")
    parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
    parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--trials", type=int, default=3, help="Trials per case (default: 3)")
    parser.add_argument("--workers", type=int, default=4, help="Max parallel workers (default: 4)")
    parser.add_argument("--timeout", type=int, default=120000, help="Timeout per execution in ms")
    args = parser.parse_args()
```

— `scripts/run_eval.py:217-225`
**Dependencies:** stdlib `argparse`.
**Implicit contracts:** Boolean flags elsewhere use `action="store_true"` (e.g. `revise.py:192` `--dry-run`). A `--list-cases` flag would follow that convention.

## Q4: What flags and positional arguments does `run_eval.py` accept today, and is there any existing flag whose naming or behavior conflicts with `--list-cases`?

**Answer:** Six optional flags, no positional arguments. Flags: `--skill` (required), `--suite` (required), `--output` (required), `--trials` (int, default 3), `--workers` (int, default 4), `--timeout` (int, default 120000). No flag named `--list-cases`, `--list`, `-l`, or any close variant exists. No naming or behavioral collision. CAVEAT: `--skill`, `--suite`, `--output` are all `required=True`, so an invocation supplying only `--list-cases --suite X` would currently fail argparse validation demanding `--skill` and `--output` unless the `required` enforcement is relaxed or `--list-cases` short-circuits before/around it. `--list-cases` logically needs only `--suite`.

**Evidence:** See Q3 evidence block — `required=True` on `--skill`, `--suite`, `--output` at `scripts/run_eval.py:219-221`.
**Dependencies:** None.
**Implicit contracts:** argparse enforces all three `required=True` flags before `main()` body runs. A `--list-cases` mode that only needs `--suite` cannot coexist with `required=True` on `--skill`/`--output` without a workaround (e.g. dropping `required=True` and validating manually, or a custom `parse_args` pre-scan). This is the single most important design constraint surfaced by research.

## Q5: What is the script's `main`/entrypoint structure, and at what point would a `--list-cases` short-circuit need to insert itself to exit before any grading begins?

**Answer:** Entrypoint is `main()` (`scripts/run_eval.py:217-236`), guarded by `if __name__ == "__main__": main()` at lines 239-240. `main()` parses args, builds an `EvalConfig` dataclass (`scripts/run_eval.py:227-234`), then calls `run_suite(config)` (`scripts/run_eval.py:236`). A `--list-cases` short-circuit should insert itself immediately after `args = parser.parse_args()` (line 225) and BEFORE the `EvalConfig` construction / `run_suite` call — it would `load_suite(args.suite)`, print the listing, and `return`/`sys.exit(0)`. Note: `run_suite` itself calls `load_suite` first (line 148), so listing logic can reuse `load_suite` without invoking any execution.

**Evidence:**

```python
    args = parser.parse_args()

    config = EvalConfig(
        skill_path=args.skill,
        suite_path=args.suite,
        output_dir=args.output,
        trials=args.trials,
        max_workers=args.workers,
        timeout_ms=args.timeout,
    )

    run_suite(config)
```

— `scripts/run_eval.py:225-236`
**Dependencies:** `EvalConfig` dataclass (`scripts/run_eval.py:32-39`), `run_suite` (`scripts/run_eval.py:146`).
**Implicit contracts:** Listing must happen before `run_suite` to avoid `os.makedirs(config.output_dir)` (`scripts/run_eval.py:152`) and the ThreadPoolExecutor work.

## Q6: Does loading `evals/suite.json` produce side effects (network calls, model invocations, file writes) before grading, such that a `--list-cases` path would still trigger them?

**Answer:** No. `load_suite` performs only a file read and JSON parse with in-memory validation (`scripts/run_eval.py:42-58`) — no network, no model calls, no writes. Side effects only begin inside `run_suite`: `os.makedirs(config.output_dir, exist_ok=True)` (`scripts/run_eval.py:152`), the `ThreadPoolExecutor` dispatch of `execute_single` (`scripts/run_eval.py:166-177`), and the final `json.dump` to `results.json` (`scripts/run_eval.py:210-211`). `execute_single` is currently a STUB — it does no real agent invocation (lines 117-137 are a placeholder writing empty output). Therefore a `--list-cases` path that calls only `load_suite` and prints is fully side-effect-free.

**Evidence:**

```python
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    ...
    messages = build_messages(case)
    result.output = ""
    result.files = []
    result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:117-135`
**Dependencies:** `run_suite` -> `os.makedirs`, `ThreadPoolExecutor`, `json.dump`.
**Implicit contracts:** `load_suite` is pure (read-only). Listing built on it inherits that purity.

## Q7: What exit-code conventions does `run_eval.py` use today for success and failure paths, against which the required `exit 0` for `--list-cases` must align?

**Answer:** `run_eval.py` does NOT call `sys.exit` anywhere — it relies on implicit exit 0 on normal completion of `main()`. Validation failures raise `ValueError` (`scripts/run_eval.py:50,56`), which propagate as uncaught exceptions producing a traceback and a non-zero exit (Python default exit code 1 for uncaught exceptions). `argparse` errors exit with code 2. There is no `import sys` in `run_eval.py` currently. By contrast, the sibling `scripts/check_scope.py:70` uses explicit `sys.exit(0 if result["passed"] else 1)`. For `--list-cases`, an explicit `sys.exit(0)` (or a `return` from `main()` yielding implicit 0) satisfies the "exit 0" requirement; adding `sys.exit(0)` would require adding `import sys`.

**Evidence:**

```python
    print(f"\nResults written to {output_path}")
    return output
```

— `scripts/run_eval.py:213-214` (run_suite returns normally; main returns implicitly -> exit 0)

```python
    sys.exit(0 if result["passed"] else 1)
```

— `scripts/check_scope.py:70` (sibling convention for explicit codes)
**Dependencies:** None. `sys` is NOT currently imported in `run_eval.py` (only in `check_scope.py` among grep hits).
**Implicit contracts:** Success = implicit 0. Failure = uncaught exception / argparse error. No explicit success exit call exists today.

## Q8: How does `run_eval.py` behave when `evals/suite.json` is missing, empty, or contains zero cases — and what would `--list-cases` print or return in those situations?

**Answer:**
- **Missing file:** `open(suite_path)` raises `FileNotFoundError`, uncaught -> traceback, exit 1.
- **Empty/invalid JSON:** `json.load` raises `json.JSONDecodeError`, uncaught -> exit 1.
- **Valid JSON missing `name` or `cases`:** `load_suite` raises `ValueError(f"Suite missing required fields: {missing}")` (`scripts/run_eval.py:50`), exit 1.
- **`cases` present but empty list (`[]`):** `load_suite` passes validation (the `for case in suite["cases"]` loop simply doesn't execute). `run_suite` then computes `total_runs = 0` and prints "Running 0 executions (0 cases x 3 trials)"; the ThreadPoolExecutor does nothing; it still writes an empty-results `results.json`. So zero cases is a tolerated, non-error state today.

For `--list-cases`: with zero cases it would print nothing (empty listing) and exit 0. Missing/malformed file would propagate the same exceptions unless the new code adds handling.

**Evidence:**

```python
    cases = suite["cases"]
    total_runs = len(cases) * config.trials
    print(f"Running {total_runs} executions ({len(cases)} cases x {config.trials} trials)")
```

— `scripts/run_eval.py:158-161`
**Dependencies:** `open`, `json.load`, `load_suite`.
**Implicit contracts:** Empty `cases` is valid (no guard against it). Missing file / bad JSON are unhandled and crash.

## Q9: What happens if a case in `evals/suite.json` lacks a `phase` field or has a malformed entry — does the current loader tolerate, skip, or raise on it?

**Answer:** The loader TOLERATES a missing `phase` field — `phase` is not in the per-case `case_required = {"id", "prompt", "assertions"}` set (`scripts/run_eval.py:53`), so a case with no `phase` passes validation. A case missing `id`, `prompt`, or `assertions` RAISES `ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")` (`scripts/run_eval.py:55-56`). All 15 current cases happen to have `phase` (verified programmatically — zero cases missing it), but nothing enforces this. Consequence for `--list-cases`: code that reads `case["phase"]` directly would `KeyError` on a phase-less case; `case.get("phase", "<default>")` would be safer.

**Evidence:**

```python
    for case in suite["cases"]:
        case_required = {"id", "prompt", "assertions"}
        case_missing = case_required - set(case.keys())
        if case_missing:
            raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
```

— `scripts/run_eval.py:52-56`
**Dependencies:** None.
**Implicit contracts:** `phase` is optional at the loader contract level despite being present in 100% of current data. Treat it as optionally-absent in new code.

## Q10: Does the ticket-required `<case_id>\t<phase>` tab-delimited format risk collision with existing tab or whitespace characters within case IDs or phase values in `evals/suite.json`?

**Answer:** No collision risk in current data. Programmatic scan of all 15 cases found ZERO `id` or `phase` values containing tab, space, or newline characters. IDs follow the pattern `case_NNN` (underscore-joined, no whitespace); phases are single lowercase words (`questions`, `research`, `design`, `structure`, `plan`, `worktree`, `implement`, `pr`). A `<case_id>\t<phase>` line format is unambiguous for the present suite. There is no schema-level constraint forbidding whitespace in future IDs/phases, so the risk is theoretical only.

**Evidence:** Programmatic check returned empty list:
```
[(c['id'], c['phase']) for c in cases if any(ch in id+phase for ch in ['\t',' ','\n'])]  ->  []
```
(all 15 cases scanned; IDs `case_001`..`case_015`, phases single words)
**Dependencies:** None.
**Implicit contracts:** IDs and phases are de facto whitespace-free tokens. Tab delimiter is safe given current data conventions.

## Q11: What test harness covers `run_eval.py` (under `evals/` or `scripts/`), and what is the existing pattern for asserting on CLI flag behavior and exit codes?

**Answer:** NOT FOUND — there is NO test harness for `run_eval.py` (or any script) in the repository. Searches:
- `find` for `test_*.py` / `*_test.py` -> no matches.
- `find` for `*test*` -> only one doc file (`docs/container-sandbox/research/q15-test-runner-sandboxing.md`), not a test.
- No `tests/` directory (`ls tests/` -> "No such file or directory").
- No `conftest.py`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, `requirements*.txt`, or `Makefile` found anywhere in the repo.

There is therefore NO existing pattern for asserting on CLI flags or exit codes in this codebase — a `--list-cases` test would establish the first one. Tooling availability: `python3` is version 3.14.2 and `pytest` 9.0.3 is importable in the environment (verified), but neither is wired into the repo via config. The nearest invocation-style reference is `scripts/check_scope.py:70`'s explicit `sys.exit` pattern, which a test could assert against via subprocess return code.

**Evidence:**
```
$ find . -name 'test_*.py' -o -name '*_test.py'   ->  (no output)
$ ls tests/                                         ->  No such file or directory
$ ls *.toml *.cfg requirements*.txt Makefile        ->  no matches
$ python3 -c "import pytest; print(pytest.__version__)"  ->  9.0.3
```
**Dependencies:** None present in-repo. pytest available only at environment level.
**Implicit contracts:** No test convention exists; new tests define the precedent. Scripts are executable (`-rwxr-xr-x`) with `if __name__ == "__main__"` guards, so subprocess-based CLI testing is feasible.

## Q12: Are there existing fixtures or sample suite files used in tests that a `--list-cases` test could reuse to assert the printed output?

**Answer:** No test fixtures exist (no tests exist — see Q11). However, reusable DATA fixtures are present:
- `evals/suite.json` — the real 15-case suite (24 KB).
- `evals/graphite-evals.json` — a second suite file (3.7 KB), separate eval set.
- `evals/fixtures/` — four ticket markdown files referenced by cases' `context.files`: `ticket_rest_endpoint.md`, `ticket_websocket.md`, `ticket_multi_tenancy.md`, `ticket_15_acceptance_criteria.md`.
- `evals/golden/` — contains only `.gitkeep` (empty, placeholder for golden outputs).

A `--list-cases` test could either point at `evals/suite.json` and assert against its 15 known `id`/`phase` pairs, or construct a small inline temp suite JSON (more hermetic). No pre-built minimal suite fixture exists for this purpose.

**Evidence:**
```
evals/suite.json            (15 cases, name "qrspi-agent-evals")
evals/graphite-evals.json   (second suite)
evals/fixtures/             ticket_rest_endpoint.md, ticket_websocket.md,
                            ticket_multi_tenancy.md, ticket_15_acceptance_criteria.md
evals/golden/.gitkeep       (empty)
```
**Dependencies:** Cases in `suite.json` reference `evals/fixtures/*.md` via `context.files`, but `--list-cases` does not load those files (only `load_suite` runs), so fixtures are irrelevant to listing.
**Implicit contracts:** `evals/suite.json` is the canonical sample. `graphite-evals.json` is an alternative suite — a `--list-cases` test could verify the listing varies by `--suite` argument.

## Q13: Which output stream (`stdout` vs `stderr`) does `run_eval.py` currently use for normal results versus diagnostic logging, so the `--list-cases` listing lands on the correct stream?

**Answer:** `run_eval.py` writes EVERYTHING to `stdout` via bare `print(...)` calls — progress lines, the run header, per-trial status, and the final "Results written to..." message (`scripts/run_eval.py:161-164, 187-189, 213`). There is NO use of `sys.stderr` anywhere in the file (grep for `sys.stderr`/`file=sys` returned no hits in `run_eval.py`). There is no `logging` module usage. Substantive output (results) goes to a FILE (`results.json`), not a stream. So there is no established stdout-vs-stderr split for "results vs diagnostics" — all console output is stdout. For `--list-cases`, the machine-readable listing conventionally belongs on `stdout` (consistent with every existing `print` in the file and with `check_scope.py` which `json.dump(..., sys.stdout, ...)` at line 69).

**Evidence:**

```python
    print(f"Running {total_runs} executions ({len(cases)} cases x {config.trials} trials)")
    print(f"Skill hash: {skill_hash}")
    ...
    print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ...")
    ...
    print(f"\nResults written to {output_path}")
```

— `scripts/run_eval.py:161-162, 187, 213`
**Dependencies:** stdlib `print` (stdout). No `logging`, no `sys.stderr`.
**Implicit contracts:** All human/console output is stdout; durable results are a JSON file. `--list-cases` output should go to stdout to match.

---

## Discovered Patterns

- **Uniform argparse + `main()` + `if __name__ == "__main__"` structure** across all six scripts in `scripts/` (`check_scope.py`, `diagnose.py`, `grade.py`, `report.py`, `revise.py`, `run_eval.py`). Any new flag/mode should follow this.
- **Dataclass config objects** for the eval pipeline: `EvalConfig` (`run_eval.py:32-39`) and `ExecutionResult` (`run_eval.py:19-29`) use `@dataclass` with `asdict` for serialization (`run_eval.py:185`).
- **`execute_single` is an unfinished stub** (`run_eval.py:93-143`) — the real agent invocation is a commented placeholder. The harness currently produces empty outputs. This means `run_eval.py` does no real model work yet, reinforcing that `--list-cases` adds a genuinely useful, side-effect-free inspection mode.
- **Boolean flags use `action="store_true"`** — the only existing example is `revise.py:192` (`--dry-run`). This is the precedent for a `--list-cases` boolean flag.
- **Explicit exit codes only appear in `check_scope.py`** (`sys.exit(0/1)`); the rest rely on implicit exit 0 and uncaught-exception exit 1.
- **`load_suite` returns the full suite dict** (not just cases), so the suite `name`, `version`, etc. are reachable — a listing could include a header if desired.
- **No project-level Python packaging or test config exists** (no `pyproject.toml`, `requirements.txt`, `tests/`, `conftest.py`, `Makefile`). The repo is primarily skill/agent prompts plus standalone stdlib-only scripts.

## Inconsistencies

- **Validation tolerates missing `phase` but every case has it.** `load_suite` requires only `{id, prompt, assertions}` (`run_eval.py:53`), yet all 15 cases carry `phase`. Code reading `case["phase"]` would crash on a (currently nonexistent) phase-less case; the loader's contract and the actual data disagree on whether `phase` is mandatory. Use `case.get("phase")` defensively.
- **`required=True` on `--skill`/`--suite`/`--output` conflicts with a listing-only mode.** A pure `--list-cases --suite X` invocation cannot satisfy the existing argparse `required` constraints on `--skill` and `--output`. This is a real design tension that the design phase must resolve (relax `required` and validate manually, or pre-scan argv).
- **No `import sys` in `run_eval.py`** despite the sibling pattern (`check_scope.py`) using `sys.exit`. If the design wants an explicit `sys.exit(0)` for `--list-cases`, the import must be added.
- **All output is stdout; the docstring says the harness "captures full transcripts, outputs, and metrics"** (`run_eval.py:2-5`), but `execute_single` is a stub returning empty values — the docstring describes intended, not actual, behavior.
- **Two suite files coexist** (`evals/suite.json` and `evals/graphite-evals.json`) with no documented relationship; `--list-cases` semantics apply to whichever `--suite` is passed, but the codebase does not document which is canonical.
