# Design — Implement script-based check execution in grade.py

**Ticket:** RUS-39
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** reviewed — all open questions resolved (see Resolved Questions)

## Current State

`scripts/grade.py:run_script_check(assertion, result)` is a 12-line stub: it returns the five-key result dict with `passed: None` and `evidence: "Script checks not yet integrated"`, never touching the filesystem or spawning a process (ref: Q1, Q8). A script-type assertion in `evals/suite.json` carries exactly three keys — `type` (`"script"`), `check` (a full inline shell-style command line string, not a structured object), and `weight` (a float); there is no separate script/args/expected-exit field (ref: Q1). For `case_011` the check string is `scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md` at weight 2.5 (ref: Q1, Q13).

The dispatch loop in `grade_results` (`grade.py:308-319`) branches on `atype` and calls `run_script_check` directly, then appends the returned dict verbatim to `assertion_results` for `score_case` (ref: Q2, Q9). `score_case` reads only `weight`, `passed` (checked strictly with `is True`), and optionally `score`; a `passed: None` result silently zeroes the assertion while still consuming its weight in `max_score` — so the current stub drags `case_011`'s score down by 2.5 (ref: Q2). All three `run_*_check` runners return the same key set `{check, type, passed, evidence, weight}` (llm_judge adds `score`); `evidence` is always a flat human-readable string, never parsed downstream (ref: Q4, Q7).

`grade.py` does not import `subprocess` and has no timeout concept; the only timeout precedent is `run_eval.py`'s `timeout_ms` dataclass default of 120000 ms, which is a separate pipeline stage not passed into the grader (ref: Q6). The repo-wide subprocess convention is `subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)` with `cwd` passed explicitly, reading `.returncode`/`.stdout`/`.stderr` off the `CompletedProcess` (ref: Q5, Q8). `check_scope.py` emits a `PASS:`/`FAIL:` prose line *then* a pretty-printed JSON object with keys `passed`, `allowed_files`, `touched_files`, `out_of_scope`, and exits 0/1 — so stdout is NOT clean JSON and a naive `json.loads(stdout)` would fail on the leading prose line (ref: Q3).

The dispatch loop has no try/except: only `run_programmatic_check` guards itself, folding exceptions into `passed=False, evidence="Check error: {e}"`; an exception raised inside `run_script_check` (a future `TimeoutExpired`/`FileNotFoundError`) would propagate uncaught and crash the whole grading run (ref: Q9, Q11). There is no script-path pre-validation, no tolerant JSON-parse helper, and no test file for `grade.py` at all (ref: Q10, Q11, Q12). The repo's testability convention isolates subprocess calls behind a thin `_run(cmd, cwd)` helper and unit-tests only the pure interpretation logic with stdlib `assert`/`check()`, no mocks (ref: Q12). Diagnostic detail reaches `grades.json` only through the per-assertion `evidence` string; there is no logging facility (ref: Q14).

## Desired End State

Each acceptance criterion maps to concrete behavior:

- **AC1 — `case_011` produces a real pass/fail from `check_scope.py` execution.** `run_script_check` tokenizes the `check` string into argv, runs `check_scope.py` via `subprocess.run` from repo root, and returns `passed: True` when exit code is 0, `passed: False` otherwise — so the 2.5-weight assertion contributes a real score instead of `None` (ref: Q2, Q3, Q5).
- **AC2 — Timeout is honored; script failures don't crash the grader.** The subprocess call passes a `timeout=` (seconds), and `run_script_check` catches `subprocess.TimeoutExpired`, `FileNotFoundError`/`PermissionError`, and any other exception, returning `passed: False` with explanatory `evidence` rather than propagating — matching the programmatic runner's self-guard pattern (ref: Q9, Q11).
- **AC3 — Stdout JSON is parsed and surfaced in `evidence`.** After running, the runner locates and parses the JSON region of stdout (stripping the leading `PASS:`/`FAIL:` line) and folds the parsed object (notably `out_of_scope`) into the `evidence` string (ref: Q3, Q7). Per RQ3 (reviewer: "evidence"), the `evidence` string — the only path into `grades.json` — is the **sole** diagnostic channel: the runner does **not** also emit a stderr warning on timeout/failure (the grader has no logging facility today, and adding one is out of scope) (ref: Q14).
- **AC4 — Non-zero exit without parseable JSON is reported as a failed assertion with raw stderr as evidence.** When exit is non-zero and stdout has no parseable JSON, the result is `passed: False` with `evidence` containing the raw stderr (and exit code), never a crash (ref: Q8, Q14).

The returned dict keeps the canonical five-key shape (`check`, `type: "script"`, `passed`, `evidence`, `weight`) so `score_case` and `grades.json` serialization are unaffected (ref: Q2, Q4).

## Delta

- **Modify `scripts/grade.py`:**
  - Add `import subprocess` to the import block (`grade.py:9-16`) (ref: Q6).
  - Add a module-level constant `SCRIPT_TIMEOUT_SEC = 120` (seconds — matching `run_eval.py`'s 120 s, but expressed in the unit `subprocess.run` expects; avoids the ms/sec mismatch) (ref: Q6).
  - Add a thin subprocess seam `_run_script(argv, cwd, timeout)` returning the `CompletedProcess` (or raising), kept in a clearly-marked subprocess-mechanics section per repo convention (ref: Q5, Q12).
  - Add a pure helper `interpret_script_result(check, weight, returncode, stdout, stderr) -> dict` that builds the five-key result: pass/fail from exit code, JSON parse of stdout, evidence assembly. This is the unit-tested half (ref: Q12).
  - Add a pure helper to extract the JSON object from mixed stdout (strip the prose prefix; e.g. locate the first `{`) with `try/except json.JSONDecodeError` (ref: Q3, Q10).
  - Rewrite `run_script_check` (`grade.py:230-241`) to tokenize `check` (`shlex.split`), call `_run_script` under a try/except covering `TimeoutExpired`/`OSError`/`Exception`, and delegate interpretation to `interpret_script_result` (ref: Q1, Q9).
  - **cwd contract (RQ2 — reviewer: "assume"):** `_run_script` is passed an explicit `cwd` equal to the **repo root**, which the grader assumes is the current implicit launch contract established by `run_eval.py` (ref: Q5). The grader does **not** self-locate the repo root from `grade.py`'s own path and does **not** add a CLI flag — the assumed-repo-root contract is documented in a comment at the call site, and a wrong cwd surfaces as a `FileNotFoundError` folded to `passed=False` evidence rather than a crash (ref: Q5, Q11).
- **New file `scripts/grade_test.py`:** stdlib-only `assert`/`check()` tests for `interpret_script_result` and the JSON-extraction helper across: exit 0 + valid JSON, exit 1 + valid JSON (`out_of_scope` populated), non-zero + unparseable stdout (stderr surfaced), empty stdout, malformed/truncated JSON. The subprocess seam itself is left untested per repo precedent (ref: Q12).
- **No changes to `evals/suite.json` or `check_scope.py`.** The cwd contract (repo root, where `scripts/` and `fixtures/` resolve) is assumed as established by `run_eval.py` (ref: Q5). Missing `case_011` fixtures are out of scope and deferred to a separate ticket (RQ1; ref: Q11, Q13). The separately-broken `impl_log_has_required_fields` check is also out of scope for RUS-39 (RQ4; ref: Q13).

## Pattern Decisions

### Decision 1: Tokenizing the `check` command string into argv

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `shlex.split(check)` then `subprocess.run(argv, ...)` (no shell) | Safe (no shell injection), handles quoted args, explicit argv matches repo `subprocess.run(cmd, cwd=...)` convention | Relies on `check` being a well-formed command line |
| B | `subprocess.run(check, shell=True, ...)` | One line, no tokenizing | Shell injection surface, diverges from every other repo subprocess call which passes a list + `cwd` |

**Recommendation:** Option A
**Rationale:** The repo convention is list-form `subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)` with no `shell=True` anywhere (ref: Q5). `shlex.split` is the stdlib-idiomatic, injection-safe way to turn the inline `check` string into that list (ref: Q1).
**NEW PATTERN?** No — extends the existing list-form subprocess convention.

### Decision 2: Determining pass/fail — exit code vs. stdout JSON

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Exit code is authoritative (0=pass, non-zero=fail); JSON parsed only for evidence | Matches ticket ("Interpret exit code"), matches `check_scope.py`'s `sys.exit(0/1)` contract, robust when JSON is absent/malformed | Trusts the script's exit discipline |
| B | Parse stdout JSON's `passed` field as authoritative | Uses the richer signal | Breaks AC4 (non-zero without JSON must still fail); JSON is mixed with prose and may be absent; couples grader to one script's schema |

**Recommendation:** Option A
**Rationale:** The ticket and `check_scope.py` both make exit code the primary signal (`sys.exit(0 if passed else 1)`); JSON is supplementary detail for evidence (ref: Q3, Q8). Option A also naturally satisfies AC4 — a non-zero exit fails regardless of JSON parseability (ref: Q8).
**NEW PATTERN?** No — adopts the repo's exit-code-as-signal pattern (ref: Discovered Patterns).

### Decision 3: Crash isolation — guard in the runner vs. the dispatch loop

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `run_script_check` catches its own exceptions, returns `passed=False` | Mirrors `run_programmatic_check`'s self-guard; localized; no change to the dispatch loop | Each future runner must repeat the guard |
| B | Wrap the dispatch loop in `grade_results` in try/except | Protects all runners at once | Larger blast radius edit; loses per-runner evidence specificity; not required by this ticket |

**Recommendation:** Option A
**Rationale:** `run_programmatic_check` already self-guards (`grade.py:183-193`); matching it keeps crash-safety consistent and scoped to this ticket without editing the shared dispatch loop (ref: Q9). Loop-level hardening (Option B) is a latent gap worth a separate ticket (ref: Inconsistencies).
**NEW PATTERN?** No — replicates the programmatic runner's existing self-guard.

### Decision 4: Extracting JSON from mixed stdout

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Locate first `{`, parse from there with `try/except json.JSONDecodeError` | Tolerant of the `PASS:`/`FAIL:` prose prefix; degrades to "no JSON" gracefully for AC4 | Heuristic; assumes JSON is the trailing region |
| B | Split off the first line, parse the remainder | Simple | Fragile if prose spans/omits a line; `check_scope.py` could change its prefix |

**Recommendation:** Option A
**Rationale:** `check_scope.py` prints prose then a pretty-printed JSON object, so the JSON is the trailing brace-delimited region; locating the first `{` is robust to prefix changes and wrapped in `try/except` it degrades cleanly to the "unparseable" path for AC4 (ref: Q3, Q10). No shared tolerant-parse helper exists to reuse, so this is local (ref: Q10).
**NEW PATTERN?** Yes — there is no existing JSON-from-subprocess-stdout parser in the grader (ref: Q10). Justified because `check_scope.py`'s mixed prose+JSON stdout has no precedent in `grade.py`, which only does `json.load(f)` on whole files (ref: Q10); kept as a small local pure helper, unit-tested.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `case_011` fixtures missing (`fixtures/worktree_session1.md` and context files absent — 4/21 fixtures present), so a real e2e run makes `check_scope.py` fail on `open()` (ref: Q5, Q11, Q13) | high | med | Per RQ1, fixture creation is **deferred to a separate ticket**; e2e green is out of scope here. Verify the runner via unit tests on `interpret_script_result` with synthetic stdout/exit, and a `check_scope.py` invocation against an existing fixture if one can be supplied |
| Timeout unit confusion: reusing `120000` directly would set a ~33 h timeout since `subprocess.run(timeout=)` is seconds, not ms (ref: Q6) | med | high | Define `SCRIPT_TIMEOUT_SEC = 120` in seconds; never pass `timeout_ms` straight through; assert the value in a test |
| cwd assumption wrong: relative paths (`scripts/...`, `fixtures/...`) only resolve from repo root, but the grader derives no repo root and assumes inherited cwd (ref: Q5, Q11) | med | med | Per RQ2, **assume** the grader is launched from repo root (the current implicit contract); pass that assumed repo root explicitly as `cwd` to `_run_script` and document the assumption at the call site (no self-location, no CLI flag); surface a wrong cwd as `FileNotFoundError` folded to `passed=False` evidence rather than crashing |
| `text=True` raises `UnicodeDecodeError` on non-UTF-8 script output (ref: Q10) | low | med | Set `errors="replace"` (or catch the decode error in the runner's guard) so binary/garbage output becomes failed-with-evidence, not a crash |
| Strict `is True` scoring: returning a truthy-but-not-`True` `passed` (e.g. `1`) would silently not score (ref: Q2) | low | med | Ensure `interpret_script_result` returns a real `bool`; cover both branches in tests |
| No existing `grade.py` test harness to extend — new test file may drift from repo conventions (ref: Q12) | low | low | Model `grade_test.py` on `scripts/qrspi_*_test.py` (stdlib-only, `assert`/`check()`, run with `python3`); test only the pure halves |

## Resolved Questions

All open questions were answered by the reviewer (PR #175 change request "incorporate answers") via four inline thread comments on this file — verbatim: "deferred", "assume", "evidence", "out of scope". Each is mapped to its question below and folded into the Desired End State, Delta, and Risk Register above:

- **RQ1 — Create the missing `case_011` fixtures in this ticket?** (reviewer: "deferred") → **Deferred.** Fixture creation (`fixtures/worktree_session1.md` plus context files) is split into a separate ticket; RUS-39 verifies the runner with unit tests on `interpret_script_result`, and a real e2e run against `check_scope.py` is out of scope here (ref: Q11, Q13).
- **RQ2 — How should the grader determine `cwd` for the subprocess?** (reviewer: "assume") → **Assume.** Assume the grader is launched from repo root (the current implicit `run_eval.py` contract); pass that assumed repo root explicitly as `cwd` to `_run_script`. Do **not** self-locate the repo root and do **not** add a CLI flag; a wrong cwd surfaces as a `FileNotFoundError` folded to `passed=False` evidence (ref: Q5, Discovered Patterns).
- **RQ3 — Warn to stderr on timeout/failure, or is `evidence` sufficient?** (reviewer: "evidence") → **Evidence.** Folding diagnostic detail into the per-assertion `evidence` string (the only path into `grades.json`) is sufficient; no stderr warning is emitted and no logging facility is added (ref: Q14).
- **RQ4 — Is the broken `impl_log_has_required_fields` check in scope?** (reviewer: "out of scope") → **Out of scope.** The separately-broken `impl_log_has_required_fields` check (referenced by `case_011` but absent from the `CHECKS` registry, scoring `None` at weight 1.5) is strictly out of scope for RUS-39 (ref: Q13).
