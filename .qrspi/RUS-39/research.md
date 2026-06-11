# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Q1: What is the input contract passed into `run_script_check` — what fields does an assertion of script type carry (script path, args, expected exit code, weight)?

**Answer:** `run_script_check(assertion, result)` receives the `assertion` dict (one entry from a case's `assertions` list) plus the `trial_result` dict. A script-type assertion in `evals/suite.json` carries exactly three keys: `type` (`"script"`), `check` (a full shell-style command line string, NOT a structured object), and `weight` (a float). There is **no** separate `script`/`args`/`expected_exit_code` field — the entire invocation lives inline in the `check` string. For `case_011` the check is `"scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md"`. The current `run_script_check` reads only `assertion["check"]` (required, no `.get`) and `assertion.get("weight", 1.0)`. It does not read the `result` argument at all today (stub).

**Evidence:**

```python
def run_script_check(assertion: dict, result: dict) -> dict:
    """Run a script-based assertion.

    Executes the script and interprets its exit code and stdout.
    """
    return {
        "check": assertion["check"],
        "type": "script",
        "passed": None,
        "evidence": "Script checks not yet integrated",
        "weight": assertion.get("weight", 1.0),
    }
```

— `scripts/grade.py:230-241`

```json
{
  "type": "script",
  "check": "scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md",
  "weight": 2.5
}
```

— `evals/suite.json:587-591`

**Dependencies:** Upstream caller is the assertion-dispatch loop in `grade_results` (`scripts/grade.py:308-319`). The `check` string format mirrors `run_programmatic_check`'s `assertion["check"]` (also a string), but programmatic checks parse it via `parse_check_call` into `func_name(args)`; script checks treat it as a literal command line.

**Implicit contracts:** `assertion["check"]` is mandatory (direct subscript, raises `KeyError` if absent); `weight` defaults to `1.0`. The script-type `check` string is whitespace-tokenizable into argv (script path then flags). Programmatic and llm_judge assertions use different key conventions (`check` vs `criteria`) — script uses `check`.

## Q2: How does the caller of `run_script_check` consume its return value, and what shape (keys, types) must that return value have to be folded into the overall assertion result?

**Answer:** The caller is the per-trial loop inside `grade_results`. It appends the returned dict verbatim to `assertion_results`, which is then passed to `score_case`. `score_case` reads only two keys off each assertion result: `weight` (via `.get("weight", 1.0)`) and `passed` (must be exactly `True` to add weight), and optionally `score` (for llm_judge normalization). The full dict is also stored under `trial_score["assertions"]` and serialized into `grades.json`. So the required shape is the same dict all `run_*_check` functions return: keys `check`, `type`, `passed`, `evidence`, `weight` (script/programmatic) — `passed` must be a real bool `True`/`False` (not `None`) to affect the score; `None` counts as not-passed but still consumes `weight` in `max_score`.

**Evidence:**

```python
elif atype == "script":
    ar = run_script_check(assertion, trial_result)
...
assertion_results.append(ar)
...
trial_score = score_case(assertion_results)
trial_score["assertions"] = assertion_results
```

— `scripts/grade.py:314-323`

```python
for ar in assertion_results:
    weight = ar.get("weight", 1.0)
    max_score += weight
    if ar.get("passed") is True:
        actual_score += weight
    elif ar.get("score") is not None:
        actual_score += weight * (ar["score"] - 1) / 4
```

— `scripts/grade.py:250-257`

**Dependencies:** Downstream consumers: `score_case` (`grade.py:246-265`), then `grades.json` serialization (`grade.py:364-365`). No other module reads the per-assertion dict.

**Implicit contracts:** `passed` must be the literal `True` (the check is `is True`, so truthy-but-not-True values like `1` would NOT score). A `passed: None` (current stub) silently zeroes the assertion while still counting its `weight` into `max_score` — i.e. the unimplemented script check currently drags `case_011`'s score down by its 2.5 weight. Returning the same five-key dict as siblings is required for consistent `grades.json` shape.

## Q3: What output format does `scripts/check_scope.py` emit on stdout, and what JSON keys does it produce that the grader is expected to surface as evidence?

**Answer:** `check_scope.py` prints a human-readable status line (`PASS: ...` or `FAIL: Out-of-scope files: [...]`) then dumps a JSON object to stdout via `json.dump(result, sys.stdout, indent=2)` followed by a newline. The JSON object has four keys: `passed` (bool), `allowed_files` (sorted list), `touched_files` (sorted list), `out_of_scope` (sorted list). It exits `0` when `passed` is true, `1` otherwise. So stdout is a mixed payload: one prose line + a pretty-printed JSON blob (NOT pure JSON — a naive `json.loads(stdout)` would fail because of the leading `PASS:`/`FAIL:` line).

**Evidence:**

```python
result = {
    "passed": len(out_of_scope) == 0,
    "allowed_files": sorted(allowed),
    "touched_files": sorted(touched),
    "out_of_scope": sorted(out_of_scope),
}
```

— `scripts/check_scope.py:45-50`

```python
if result["passed"]:
    print("PASS: All files within scope")
else:
    print(f"FAIL: Out-of-scope files: {result['out_of_scope']}")

json.dump(result, sys.stdout, indent=2)
print()
sys.exit(0 if result["passed"] else 1)
```

— `scripts/check_scope.py:63-70`

**Dependencies:** `check_scope.py` is standalone (stdlib `argparse`, `json`, `re`, `sys`). It is invoked as an external process by the script-check command string in `case_011`. The grader does not import it.

**Implicit contracts:** Exit code is the primary pass/fail signal (0/1). Stdout is NOT clean JSON — the `PASS:`/`FAIL:` prefix line precedes the JSON, so any JSON-parsing in the grader must strip or locate the JSON region. The `out_of_scope` list is the diagnostic payload most useful as evidence.

## Q4: What is the exact signature and return type of `run_script_check` today, and what do the sibling check-runner functions return so the script runner stays consistent?

**Answer:** Signature: `run_script_check(assertion: dict, result: dict) -> dict`. All three runners return a dict; the canonical key set is `{check, type, passed, evidence, weight}`. `run_programmatic_check(assertion, result) -> dict` returns those five keys with `passed` a bool/None and `evidence` a string. `run_llm_judge(assertion, result, case) -> dict` returns the same five PLUS a `score` key (currently `None`), and uses `assertion["criteria"]` (not `check`) as the `check` value. `run_script_check` matches the five-key shape but always returns `passed: None`, `evidence: "Script checks not yet integrated"`.

**Evidence:**

```python
def run_programmatic_check(assertion: dict, result: dict) -> dict:
    ...
    return {
        "check": check_str,
        "type": "programmatic",
        "passed": passed,
        "evidence": evidence,
        "weight": assertion.get("weight", 1.0),
    }
```

— `scripts/grade.py:177-205`

```python
def run_llm_judge(assertion: dict, result: dict, case: dict) -> dict:
    ...
    return {
        "check": assertion["criteria"],
        "type": "llm_judge",
        "passed": None,
        "score": None,
        "evidence": "LLM judge not yet integrated — requires model API",
        "weight": assertion.get("weight", 1.0),
    }
```

— `scripts/grade.py:208-227`

**Dependencies:** All three are called from `grade_results` (`grade.py:310-315`); `run_llm_judge` uniquely also receives `case`. None call each other.

**Implicit contracts:** Consistency requires `run_script_check` to keep `type: "script"` and the five-key shape; adding a `score` key (as llm_judge does) is allowed but unused for script type. `evidence` is always a human-readable string. Note `run_programmatic_check` wraps its check body in try/except (`grade.py:183-193`) returning `passed=False, evidence=f"Check error: {e}"` — the script runner has no such guard yet.

## Q5: How are script paths in `case_011`'s assertion expressed (absolute, relative to repo root, relative to cwd), and what working directory is `subprocess.run` expected to execute under?

**Answer:** Paths are **relative**: `scripts/check_scope.py`, `--log impl-log.md`, `--allowed fixtures/worktree_session1.md`. `scripts/check_scope.py` is relative to the repo root; `impl-log.md` and `fixtures/worktree_session1.md` are relative to where the grader runs (the agent-output/cwd and the eval fixtures dir respectively). There is **no `subprocess.run` in `grade.py` today** — `run_script_check` is a pure stub. The repo's convention for subprocess-backed scripts (e.g. `qrspi_resolve.py`, `qrspi_pr_state.py`) is `subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)`, explicitly passing `cwd`. `run_eval.py` resolves fixture paths via `os.path.exists(file_path)` relative to the process cwd (`run_eval.py:79`), implying eval execution is expected to run from the repo root. So the intended cwd is the repo root (where `scripts/` and `fixtures/`/`evals/fixtures/` resolve). NOTE: `case_011` references `fixtures/worktree_session1.md` but per `docs/eval-system.md:87` that fixture does NOT yet exist (4/21 fixtures present).

**Evidence:**

```json
"check": "scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md",
"weight": 2.5
```

— `evals/suite.json:588-590`

```python
res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
```

— `scripts/qrspi_resolve.py:210` (repo convention for subprocess calls; same pattern at `qrspi_pr_state.py`, `qrspi_restack.py:132`, `qrspi_pr_body.py:150`)

**Dependencies:** Path resolution couples `grade.py` (future subprocess) to the cwd contract established by `run_eval.py`'s fixture loading.

**Implicit contracts:** Scripts are run as relative paths from repo root; the executor must set/assume cwd = repo root. `check_scope.py` has a `#!/usr/bin/env python3` shebang and is `chmod +x` (`-rwxr-xr-x`), so it can be invoked directly OR via `python3 <path>`. Other repo scripts always pass `cwd=` explicitly to `subprocess.run` rather than relying on inherited cwd.

## Q6: Is there an existing timeout value or configuration constant used elsewhere in `grade.py` (for other check types or global config) that script execution must reuse?

**Answer:** There is **no timeout constant in `grade.py`** — it imports `argparse, json, os, re, statistics, dataclasses, pathlib, typing` only (no `subprocess`, no time/timeout config). The timeout convention lives in `scripts/run_eval.py`: `EvalConfig.timeout_ms: int = 120000` (a dataclass default), threaded through `execute_single(..., timeout_ms)` and exposed as CLI `--timeout` (default 120000 ms). `docs/eval-system.md:28` documents "120s timeout" as the suite default. There is no shared constants module — each script defines its own. So script execution in `grade.py` has no existing timeout to reuse from within `grade.py`; the only precedent (120000 ms / 120 s) is in `run_eval.py`, but that is per-agent-execution, not per-grading-script, and is not currently passed into the grader.

**Evidence:**

```python
@dataclass
class EvalConfig:
    skill_path: str
    suite_path: str
    output_dir: str
    trials: int = 3
    max_workers: int = 4
    timeout_ms: int = 120000
```

— `scripts/run_eval.py:32-39`

```python
parser.add_argument("--timeout", type=int, default=120000, help="Timeout per execution in ms")
```

— `scripts/run_eval.py:224`

**Dependencies:** `grade.py` imports (`grade.py:9-16`) include no `subprocess`/`time`. `run_eval.py` and `grade.py` are separate pipeline stages with separate CLIs; the grader does not receive `run_eval`'s timeout.

**Implicit contracts:** Repo convention for "per execution timeout" is milliseconds (`timeout_ms`), but Python `subprocess.run(timeout=...)` expects seconds — a future implementation reusing `120000` must divide by 1000. No global config object exists; constants are per-module.

## Q7: How is the `evidence` field on an assertion result currently structured and populated by the existing (non-script) check runners?

**Answer:** `evidence` is always a single human-readable string. Programmatic checks: the registered check functions return `(bool, str)` tuples where the second element is the evidence (e.g. `f"File '{filename}' {'found' if exists else 'not found'} in outputs"`), and `run_programmatic_check` surfaces that string directly; for numeric-returning checks it synthesizes `f"Value: {outcome}"`; on exception, `f"Check error: {e}"`; on unknown function, `f"Unknown check function: {func_name}"`. The llm_judge stub hardcodes `"LLM judge not yet integrated — requires model API"`. There is no structured/dict evidence — it is flat text.

**Evidence:**

```python
if isinstance(outcome, tuple):
    passed, evidence = outcome
else:
    passed = True
    evidence = f"Value: {outcome}"
except Exception as e:
    passed = False
    evidence = f"Check error: {e}"
else:
    passed = None
    evidence = f"Unknown check function: {func_name}"
```

— `scripts/grade.py:185-197`

```python
return exists, f"File '{filename}' {'found' if exists else 'not found'} in outputs"
```

— `scripts/grade.py:24` (representative check returning `(bool, str)`)

**Dependencies:** `evidence` is produced by registry functions in `CHECKS` (`grade.py:146-157`), assembled in `run_programmatic_check`, and consumed only as a display/diagnostic string in `grades.json`. `score_case` ignores `evidence` entirely.

**Implicit contracts:** `evidence` is free-form text, never parsed downstream — safe to put multi-line subprocess stderr / exit codes there. The `(passed, evidence)` tuple convention is how all programmatic checks report; a script runner producing similar `(passed, evidence)` would be idiomatic.

## Q8: How is a non-zero exit code with no parseable JSON on stdout currently distinguished from a non-zero exit with valid JSON, and where would stderr be captured to surface as evidence?

**Answer:** **NOT FOUND** as implemented — there is no exit-code or JSON handling in `run_script_check` today; it is a stub returning `passed: None` regardless of any script. No `subprocess`, no stdout parsing, no stderr capture exists anywhere in `grade.py`. The closest precedent for the *intended* pattern is `check_scope.py` itself, which encodes pass/fail in its exit code (`sys.exit(0 if result["passed"] else 1)`, `check_scope.py:70`) AND emits JSON on stdout, and the repo-wide subprocess convention (`capture_output=True, text=True`, e.g. `qrspi_resolve.py:210`) which captures both stdout and stderr separately on the `CompletedProcess` (`.stdout`, `.stderr`, `.returncode`). So today no distinction is made; a future implementation would use `subprocess.run(..., capture_output=True, text=True)` and read `.returncode`, `.stdout`, `.stderr`.

**Evidence:** Searched `scripts/grade.py` for `subprocess`, `returncode`, `stderr`, `stdout`, `json.loads` — none present. The runner body is the 12-line stub at `grade.py:230-241` (see Q1).

```python
sys.exit(0 if result["passed"] else 1)
```

— `scripts/check_scope.py:70` (exit-code-as-signal precedent)

**Dependencies:** None in current code. Future: would depend on `subprocess` (not imported) and possibly `json` (already imported, `grade.py:10`).

**Implicit contracts:** `check_scope.py` mixes a prose prefix line with JSON on stdout (Q3), so "valid JSON on stdout" requires stripping the leading `PASS:`/`FAIL:` line before `json.loads`. Exit code is the authoritative pass/fail; JSON is supplementary detail.

## Q9: What happens in the existing grader flow when a check runner raises an exception or a subprocess times out — is there a try/except boundary that prevents one failing assertion from crashing the whole grading run?

**Answer:** Partial protection. `run_programmatic_check` has its OWN try/except around the check invocation (`grade.py:183-193`) — a raising registry function is caught and turned into `passed=False, evidence="Check error: {e}"`. However, the **assertion-dispatch loop in `grade_results` has NO try/except** — it calls `run_programmatic_check` / `run_llm_judge` / `run_script_check` directly (`grade.py:310-315`). So if `run_script_check` itself raises (e.g. a future `subprocess.TimeoutExpired` or `FileNotFoundError`), it would propagate up through `grade_results` and crash the entire grading run; one assertion failure is NOT currently isolated at the loop level. The stubs never raise today, so this gap is latent.

**Evidence:**

```python
for assertion in assertions:
    atype = assertion.get("type", "")
    if atype == "programmatic":
        ar = run_programmatic_check(assertion, trial_result)
    elif atype == "llm_judge":
        ar = run_llm_judge(assertion, trial_result, case)
    elif atype == "script":
        ar = run_script_check(assertion, trial_result)
    else:
        ar = {"check": "unknown", "type": atype, "passed": None,
              "evidence": f"Unknown assertion type: {atype}", "weight": 0}
    assertion_results.append(ar)
```

— `scripts/grade.py:308-319` (no try/except wrapping the dispatch)

```python
try:
    outcome = CHECKS[func_name](*args, result)
    ...
except Exception as e:
    passed = False
    evidence = f"Check error: {e}"
```

— `scripts/grade.py:183-193` (per-check guard, programmatic only)

**Dependencies:** Loop in `grade_results` → the three runner functions. The guard exists inside `run_programmatic_check` only.

**Implicit contracts:** The established pattern for "isolate one failing assertion" is the try/except-returning-`passed=False` used by programmatic checks. To stay consistent and crash-safe, `run_script_check` should catch its own exceptions (including `subprocess.TimeoutExpired`) and return `passed=False` rather than relying on the loop. The unknown-type branch sets `weight: 0` (so unknown types don't penalize), unlike known-but-failed assertions.

## Q10: How are partial or malformed stdout payloads (empty stdout, truncated JSON, non-UTF-8 bytes) handled by any existing JSON-parsing helpers in the grader?

**Answer:** **NOT FOUND** — there is no shared JSON-parsing helper for subprocess stdout in the grader. `grade.py` uses `json` only twice: `json.load(f)` to read `results.json` and the suite (`grade.py:284-287`) and `json.dump` to write `grades.json` (`grade.py:365`). Neither parses subprocess output, and there is no try/except around them (a malformed `results.json`/suite would raise and crash). No `json.loads` call exists anywhere in `grade.py`. `check_scope.py` produces JSON but the grader never parses it today. There is no utility module shared across scripts for tolerant JSON parsing (each script imports stdlib `json` directly). Searched: `json.loads`, `JSONDecodeError`, `errors=`, `decode(` across `scripts/grade.py` and `scripts/*.py` — no tolerant-parse helper.

**Evidence:**

```python
with open(results_path) as f:
    results_data = json.load(f)
with open(suite_path) as f:
    suite = json.load(f)
```

— `scripts/grade.py:284-287` (the only JSON reads; no error handling)

**Dependencies:** `grade.py` imports `json` (`grade.py:10`). No shared parse utility imported.

**Implicit contracts:** Input files are assumed well-formed JSON (no defensive parsing). A future script-check JSON parse would need its own `try/except json.JSONDecodeError` and a `text=True`/encoding decision — `subprocess.run(text=True)` decodes as UTF-8 and would raise `UnicodeDecodeError` on non-UTF-8 bytes unless `errors=` is set; no such handling exists today.

## Q11: What is the behavior when `check_scope.py` itself is missing or not executable — does the dispatch layer pre-validate script existence before invoking `subprocess.run`?

**Answer:** **NOT FOUND** / no pre-validation. The dispatch layer (`grade_results` loop, `grade.py:308-319`) does no existence or executability check; `run_script_check` (`grade.py:230-241`) never touches the filesystem and never invokes a process. There is no `os.path.exists` / `os.access` / `shutil.which` guard for the script path. The only existence check in the pipeline is in `run_eval.py` for *fixture context files* (`if os.path.exists(file_path)`, `run_eval.py:79`), which silently skips missing files — not applicable to the grader's script dispatch. So if/when subprocess execution is added, a missing/non-executable `check_scope.py` would raise `FileNotFoundError`/`PermissionError` from `subprocess.run`, and per Q9 that would propagate uncaught and crash the run.

**Evidence:**

```python
elif atype == "script":
    ar = run_script_check(assertion, trial_result)
```

— `scripts/grade.py:314-315` (no pre-validation around the script runner)

```python
if os.path.exists(file_path):
    with open(file_path) as f:
        content = f.read()
```

— `scripts/run_eval.py:79-81` (the only existence check in the pipeline — for fixtures, silently skips if absent)

**Dependencies:** Dispatch loop → `run_script_check`. No filesystem-validation dependency exists.

**Implicit contracts:** No guarantee the script path resolves; the executor currently assumes scripts exist. Per `docs/eval-system.md:87`, even `case_011`'s `fixtures/worktree_session1.md` argument is itself a missing fixture (4/21 exist), so a real run would hit a missing-file condition on the `--allowed` argument inside `check_scope.py` (`open(...)` at `check_scope.py:16`) even if `check_scope.py` exists.

## Q12: What test files cover `grade.py` today, and is there an existing fixture or pattern for stubbing/mocking `subprocess.run` so script-check tests run deterministically?

**Answer:** **NOT FOUND** — there is **no test file for `grade.py`**. `grep` for `import grade`, `from grade`, `run_script_check`, `grade_results` across the repo returns only `scripts/grade.py` itself. The unit-tested scripts are the `qrspi_*` family (`scripts/qrspi_*_test.py`); those deliberately do NOT mock `subprocess` — they test only the pure functions and leave subprocess-backed mechanics untested (e.g. `qrspi_pr_body_test.py:7`: "The subprocess-backed parts ... are intentionally NOT tested"; `qrspi_cleanup_test.py:3`: "NO subprocess mocks — only the pure"). So the established repo pattern is: split pure logic from subprocess mechanics and unit-test only the pure half with stdlib `assert`/`check()` style, no mocking framework, run with `python3`. There is no existing precedent for mocking `subprocess.run`; the convention is to factor subprocess out and not test it.

**Evidence:** `ls scripts/*grade*` → `scripts/grade.py` only (no `grade_test.py`). `grep -rln "import grade\|run_script_check\|grade_results"` → `scripts/grade.py` only.

```python
# The subprocess-backed parts (gt checkout/modify, git log) are intentionally NOT tested
```

— `scripts/qrspi_pr_body_test.py:7`

```
decision). Stdlib-only, assert/check() style, NO subprocess mocks — only the pure
```

— `scripts/qrspi_cleanup_test.py:3`

**Dependencies:** Test convention modeled on `scripts/qrspi_*_test.py` siblings; CLAUDE.md states "stdlib-only unit tests as `_test.py` siblings ... run with `python3`".

**Implicit contracts:** New tests for `grade.py` should be `scripts/grade_test.py`, stdlib-only, `assert`-based, no external deps. Per repo precedent, the subprocess call should be isolated into a thin helper (like `_run(cmd, cwd)` in `qrspi_resolve.py:206-210`) and the *interpretation* logic (exit code + stdout → result dict) tested as a pure function without spawning a process.

## Q13: How is `case_011` defined and weighted (the 2.5 weight), and is there a fixture that exercises it end-to-end to assert a real pass/fail result?

**Answer:** `case_011` (`id: "case_011"`, `name: "implement_scope_enforcement"`, `phase: "implement"`, `split: "train"`, `difficulty: "medium"`) lives in `evals/suite.json:562-606`. It has four assertions: programmatic `output_file_exists('impl-log.md')` weight 1.0; programmatic `impl_log_has_required_fields('impl-log.md')` weight 1.5; **script** `scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md` weight **2.5**; llm_judge weight 3.0 (total max 8.0). There is **NO end-to-end fixture** that exercises it: its `context.files` reference `fixtures/worktree_session1.md`, `fixtures/structure_rest_endpoint.md`, `fixtures/plan_rest_endpoint_slice1.md` — all listed as MISSING in `docs/eval-system.md:85-87` (only 4/21 fixtures exist, the ticket files). Also note `impl_log_has_required_fields` is referenced but is **not** in the `CHECKS` registry (`grade.py:146-157`), so today it resolves to `passed: None` ("Unknown check function") — corroborated by `docs/eval-system.md:96` ("14 of ~37 referenced checks implemented").

**Evidence:**

```json
{
  "id": "case_011",
  "name": "implement_scope_enforcement",
  "phase": "implement",
  ...
  "assertions": [
    { "type": "programmatic", "check": "output_file_exists('impl-log.md')", "weight": 1.0 },
    { "type": "programmatic", "check": "impl_log_has_required_fields('impl-log.md')", "weight": 1.5 },
    { "type": "script", "check": "scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md", "weight": 2.5 },
    { "type": "llm_judge", "criteria": "Agent only modified files listed in the session task list ...", "weight": 3.0 }
  ],
  "tags": ["implement", "happy-path", "scope"],
  "difficulty": "medium",
  "split": "train"
}
```

— `evals/suite.json:562-606`

**Dependencies:** `case_011` → `check_scope.py` (script), → `CHECKS` registry (programmatic), → missing fixtures under `evals/fixtures/`. Graded via `grade_results`.

**Implicit contracts:** A case's `context.files` are loaded relative to cwd by `run_eval.py` and silently skipped if absent — a real e2e run currently produces empty agent output, so all programmatic checks fail/zero. The script check's `--allowed fixtures/worktree_session1.md` argument points at a non-existent file, so `check_scope.py` would raise on `open()` unless the fixture is created first.

## Q14: How does the grader currently log or report per-assertion failures, and what mechanism exists to record subprocess stderr / timeout details for diagnosis without crashing the run?

**Answer:** Per-assertion results are **not logged** — they are captured in the returned dict's `evidence` string and persisted into `grades.json` (under `cases[].trials[].assertions[]`), never printed. `grade.py` uses `print` only four times in `grade_results` for suite-level summary lines (train score, test score, gap, output path) — `grade.py:367-370`. There is **no `logging` module usage, no stderr writes, no warning emission** (the "skip with warning" at `grade.py:195` is just a comment; it sets `passed=None`/evidence text, it does not actually warn). The mechanism to record diagnostic detail without crashing is the per-result `evidence` string: programmatic checks fold exceptions into `evidence="Check error: {e}"` (`grade.py:191-193`). So for subprocess stderr/timeout, the idiomatic place is the script runner's `evidence` field — but that requires the runner to catch the error itself (per Q9, the dispatch loop won't).

**Evidence:**

```python
print(f"Train score: {train_scores['mean']:.4f} (+/- {train_scores['stddev']:.4f})")
print(f"Test score:  {test_scores['mean']:.4f} (+/- {test_scores['stddev']:.4f})")
print(f"Train-test gap: {output['train_test_gap']:.4f}")
print(f"Grades written to {grades_path}")
```

— `scripts/grade.py:367-370` (the only output; suite-level only)

```python
# Unknown check — skip with warning
passed = None
evidence = f"Unknown check function: {func_name}"
```

— `scripts/grade.py:195-197` (comment says "warning" but no warning is emitted)

**Dependencies:** `evidence` strings → `grades.json` (the diagnostic record). `diagnose.py` (`docs/eval-system.md:57-71`) is the downstream consumer that categorizes failures, but it reads `grades.json`, not live logs.

**Implicit contracts:** Diagnostic detail must live in the per-assertion `evidence` string to reach `grades.json` (the only persisted record); stdout/stderr printing is reserved for suite-level summaries. No structured logging facility exists; the convention is "fold the error text into `evidence`, return `passed=False`, never raise."

---

## Discovered Patterns

- **Stub-and-document pattern:** Three pipeline capabilities are explicit stubs returning `passed: None` with an explanatory `evidence` string — `run_llm_judge` (`grade.py:208-227`), `run_script_check` (`grade.py:230-241`), and the agent runtime in `run_eval.py:117-137`. `docs/eval-system.md:97-101` tracks each as "Stub" with exact line ranges. The intended-implementation guidance is written into docstrings (e.g. `run_llm_judge` shows the real `judge_model.complete(...)` shape).
- **Uniform assertion-result dict:** Every `run_*_check` returns the same five-key dict (`check`, `type`, `passed`, `evidence`, `weight`), optionally `+score`. `score_case` reads only `weight`/`passed`/`score`. `passed` is checked with `is True` (strict).
- **Pure/impure split for testability (repo-wide):** `qrspi_*` scripts isolate subprocess calls behind a thin `_run(cmd, cwd, ...)` helper in a clearly-marked "subprocess-backed mechanics (not unit-tested)" section, and unit-test only the pure logic with stdlib `assert`/`check()` (no mocks). `grade.py` does NOT yet follow this split — it has no test file and no subprocess seam.
- **Exit-code-as-signal:** `check_scope.py` and the repo's other CLIs use `sys.exit(0/1)` for pass/fail and emit JSON to stdout for detail.
- **Timeouts are milliseconds in config but absent from the grader:** `run_eval.py` uses `timeout_ms` (default 120000); `grade.py` has no timeout concept.
- **Self-locating scripts:** Several scripts (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`) self-locate the repo root from their own path; `grade.py` instead derives output dir from `os.path.dirname(results_path)` and assumes cwd for relative paths.

## Inconsistencies

- **Comment vs. code — "skip with warning":** `grade.py:195` comment says "Unknown check — skip with warning" but no warning is emitted (no `logging`, no stderr write); it only sets `passed=None`. Misleading.
- **Per-check guard exists for programmatic but not for the dispatch loop:** `run_programmatic_check` catches exceptions (`grade.py:183-193`), but the `grade_results` dispatch loop (`grade.py:308-319`) has no try/except, so an exception from `run_script_check` (future subprocess errors/timeouts) or `run_llm_judge` would crash the whole run — inconsistent crash-safety across the two layers.
- **`case_011` references an unimplemented check:** its assertion `impl_log_has_required_fields('impl-log.md')` is not in the `CHECKS` registry (`grade.py:146-157`), so it currently scores as `passed: None` ("Unknown check function") while still consuming weight 1.5. `docs/eval-system.md:96` confirms only "14 of ~37 referenced checks" are implemented.
- **`case_011` fixtures missing:** all three `context.files` and the script check's `--allowed fixtures/worktree_session1.md` point at files that do not exist (`docs/eval-system.md:80-89`, 4/21 fixtures present) — no end-to-end exercise is currently possible.
- **`check_scope.py` stdout is not pure JSON:** it prefixes a `PASS:`/`FAIL:` prose line before the JSON dump (`check_scope.py:63-69`), so a naive `json.loads(stdout)` in a future grader would fail — the prose prefix must be stripped or the exit code used instead.
- **Timeout unit mismatch risk:** repo convention stores timeout as `timeout_ms` (ms), but Python `subprocess.run(timeout=...)` takes seconds — reusing `120000` directly would be a 120000-second (~33h) timeout.
- **No test coverage for `grade.py`:** despite CLAUDE.md's TDD directive and the `_test.py`-sibling convention, `grade.py` (the second pipeline stage, with scoring logic) has no test file at all.
