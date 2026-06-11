# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Q1: What inputs does `run_loop.sh` accept (agent name, flags, environment variables) and how does it pass them to the underlying eval invocation that the wrapper must iterate over?

**Answer:** `run_loop.sh` is a single-agent optimization loop, not a multi-agent driver. It accepts four **positional** args and two **environment variables**; there are NO flags (no `--phase`, `--all`, `--regression-only` exist today). Positional: `$1 SKILL_PATH` (path to one agent/skill prompt file, required), `$2 EVAL_SUITE` (path to suite JSON, required), `$3 MAX_ITER` (default 5), `$4 TARGET_SCORE` (default 0.85). Env vars: `TRIALS` (default 3), `WORKERS` (default 4). It loops `MAX_ITER` times, and per iteration calls `python3 scripts/run_eval.py --skill "$SKILL_PATH" --suite "$EVAL_SUITE" --output "$OUTPUT_DIR" --trials "$TRIALS" --workers "$WORKERS"`, where `OUTPUT_DIR=results/v${i}`. So the single agent is identified solely by `SKILL_PATH`, passed straight through as `run_eval.py --skill`.

**Evidence:**

```bash
SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
EVAL_SUITE=${2:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
MAX_ITER=${3:-5}
TARGET_SCORE=${4:-0.85}
TRIALS=${TRIALS:-3}
WORKERS=${WORKERS:-4}
...
    python3 scripts/run_eval.py \
        --skill "$SKILL_PATH" --suite "$EVAL_SUITE" \
        --output "$OUTPUT_DIR" --trials "$TRIALS" --workers "$WORKERS"
```

— `run_loop.sh:12-17`, `run_loop.sh:43-48`
**Dependencies:** Calls (downstream) `scripts/run_eval.py`, `scripts/grade.py`, `scripts/diagnose.py`, `scripts/revise.py`, `scripts/report.py`, plus inline `python3 -c` snippets. No upstream caller in-repo (invoked manually; `set -euo pipefail` at `run_loop.sh:2`).
**Implicit contracts:** Exactly one skill per invocation; output dirs are named `results/v${i}` (`run_loop.sh:34`); the suite path is shared across all iterations. There is no notion of "agent" identity beyond the raw file path — a multi-agent wrapper would have to map a phase name to its skill file itself.

## Q2: How does the existing single-agent eval path locate and load fixtures, and what is the file/path contract the per-agent runs depend on?

**Answer:** Fixtures are loaded by `run_eval.py` per test case, not per agent. `build_messages(case)` reads `case["context"]["files"]` (a list of relative paths) and `case["context"]["conversation_history"]`. Each file path is checked with `os.path.exists(file_path)` and, if present, read and appended to the user message as `--- {file_path} ---\n{content}`. Paths in the suite are written relative to the `evals/` dir (e.g. `"fixtures/ticket_rest_endpoint.md"`), so the contract is that the runner's working directory is `evals/`-relative — but `run_loop.sh` invokes `python3 scripts/run_eval.py` from the repo root, so `fixtures/...` would NOT resolve from repo root. Fixtures on disk live at `evals/fixtures/` (4 files: `ticket_rest_endpoint.md`, `ticket_websocket.md`, `ticket_multi_tenancy.md`, `ticket_15_acceptance_criteria.md`). `evals/golden/` contains only `.gitkeep` (no golden outputs).

**Evidence:**

```python
context_files = case.get("context", {}).get("files", [])
file_context_parts = []
for file_path in context_files:
    if os.path.exists(file_path):
        with open(file_path) as f:
            content = f.read()
        file_context_parts.append(f"--- {file_path} ---\n{content}")
```

— `scripts/run_eval.py:76-82`; suite path form at `evals/suite.json` (`"files": ["fixtures/ticket_rest_endpoint.md"]`)
**Dependencies:** `build_messages` is called only inside `execute_single` (`scripts/run_eval.py:132`). Fixtures live under `evals/fixtures/`.
**Implicit contracts:** Fixture paths are relative and silently skipped if not found (no error) — see Q10. The CWD-vs-path mismatch (suite uses `fixtures/...` but runner runs from repo root) means fixtures are currently silently NOT loaded when driven via `run_loop.sh`. This is a latent path contract bug a multi-agent wrapper would inherit.

## Q3: What is the structure and on-disk format of the per-agent result output that the consolidated `results/all/` report must aggregate from?

**Answer:** `results/all/` does not exist anywhere in the repo today (no reference in any script, doc, or README). The existing per-run output is a single `results.json` written by `run_eval.py` into the `--output` dir. Its top-level keys: `skill_hash` (sha256[:12] of skill text), `skill_path`, `suite` (suite name), `timestamp` (`%Y-%m-%dT%H:%M:%SZ`), `config` (`trials`, `timeout_ms`), and `results` (list of `ExecutionResult` dicts via `dataclasses.asdict`). Each `ExecutionResult` has: `case_id`, `trial_id`, `output`, `files`, `duration_ms`, `tokens`, `tool_calls`, `transcript`, `error`. `grade.py` then writes `grades.json` (keys: `train_score`, `test_score`, `train_test_gap`, `train_details`, `test_details`, `cases[]`). `report.py` aggregates across `results/v*/grades.json` into `results/report.json` + `results/ledger.json`.

**Evidence:**

```python
output = {
    "skill_hash": skill_hash, "skill_path": config.skill_path,
    "suite": suite["name"],
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "config": {"trials": config.trials, "timeout_ms": config.timeout_ms},
    "results": all_results,
}
output_path = os.path.join(config.output_dir, "results.json")
```

— `scripts/run_eval.py:197-211`; `ExecutionResult` fields at `scripts/run_eval.py:19-29`
**Dependencies:** `report.py:load_version_results` scans `results/` for subdirs containing `grades.json` (`scripts/report.py:14-32`). It treats every immediate subdirectory as a "version" — so a new `results/all/` subdir would be picked up by `report.py` as if it were a version directory unless excluded.
**Implicit contracts:** Output dir is per-version (`results/v${i}`); aggregation keys off `grades.json` presence per subdir; case identity is `case_id`. NOT FOUND on disk: any `results/all/` format — it must be designed, not discovered. `results/` currently holds only `.gitkeep`.

## Q4: What command-line interface does `run_loop.sh` currently expose, and which flags or positional arguments identify the target agent that `--phase <name>` must map onto?

**Answer:** `run_loop.sh` exposes ONLY positional args (see Q1): `<skill_path> <eval_suite> [max_iter] [target_score]`, plus `TRIALS`/`WORKERS` env vars. There are no flags at all — `--phase`, `--all`, `--regression-only` are all new surface to add. The "target agent" is identified by `$1 SKILL_PATH` (a raw file path). A `--phase <name>` would need a name→path mapping; the natural mapping is `<name>` → `.claude/agents/qrspi-<name>.md` (see Q5). The doc-comment example `./run_loop.sh .qrspi/agents/01-questions.md ...` (`run_loop.sh:10`) references a path scheme (`.qrspi/agents/01-questions.md`) that does NOT exist on disk — the real agents are at `.claude/agents/qrspi-*.md` (inconsistency, see Inconsistencies).

**Evidence:**

```bash
# Usage:
#   ./run_loop.sh <skill_path> <eval_suite> [max_iterations] [target_score]
# Example:
#   ./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85
```

— `run_loop.sh:6-10`
**Dependencies:** None new; the agent path is consumed only by `run_eval.py --skill`.
**Implicit contracts:** `${1:?...}` and `${2:?...}` make the first two positionals mandatory and abort with the Usage string if absent — any new flag parsing must preserve or replace this guard. The suite (`evals/suite.json`) is one file shared across all phases, with per-case `phase` tags being the only per-agent discriminator inside it (see Q5/Q7).

## Q5: How are the 8 phase agents discovered on disk, and what is the exact glob pattern and naming convention for `.claude/agents/qrspi-*.md` that `--all` must enumerate?

**Answer:** There is NO existing discovery code — `run_loop.sh` never enumerates agents; it takes one explicit path. The 8 agent files exist on disk at `.claude/agents/` and match the glob `.claude/agents/qrspi-*.md` exactly: `qrspi-design.md`, `qrspi-implement.md`, `qrspi-plan.md`, `qrspi-pr.md`, `qrspi-questions.md`, `qrspi-research.md`, `qrspi-structure.md`, `qrspi-worktree.md` (8 files, confirmed). The phase name is the filename stem after `qrspi-`. The eval suite's `phase` tags use the same 8 names: `questions`, `research`, `design`, `structure`, `plan`, `worktree`, `implement`, `pr`. So `--all` should glob `.claude/agents/qrspi-*.md` and derive phase = basename minus `qrspi-` prefix and `.md` suffix.

**Evidence:**

```
.claude/agents/qrspi-design.md     .claude/agents/qrspi-pr.md
.claude/agents/qrspi-implement.md  .claude/agents/qrspi-questions.md
.claude/agents/qrspi-plan.md       .claude/agents/qrspi-research.md
.claude/agents/qrspi-structure.md  .claude/agents/qrspi-worktree.md
```

— directory listing of `.claude/agents/`; suite phase tags at `evals/suite.json` (Counter: questions 3, design 3, research 2, structure 2, implement 2, plan 1, worktree 1, pr 1)
**Dependencies:** None today (greenfield). README documents these as "Phase agent definitions" at `README.md:77`.
**Implicit contracts:** Phase names are 1:1 between `.claude/agents/qrspi-<phase>.md` and suite `case["phase"]`. Note `evals/suite.json` is NOT split per-phase — all 15 cases live in one file, so a `--phase`/`--all` driver must FILTER the suite by `case["phase"]` to evaluate one agent against only its cases (no per-phase suite files exist).

## Q6: What exit-code conventions does the existing eval runner use to signal pass versus regression, which `--regression-only` CI mode must propagate non-zero on?

**Answer:** NOT FOUND — no explicit exit-code convention exists. `run_eval.py`, `grade.py`, `diagnose.py`, `revise.py`, `report.py` all end `main()` without `sys.exit(code)`, so they exit 0 on success and only non-zero on an uncaught Python exception. `run_loop.sh` runs `set -euo pipefail` (`run_loop.sh:2`) so any failing command aborts the loop with that command's status, but the loop itself never `exit`s with a pass/fail code — on a met target it `break`s and proceeds to the final report; on regression it `continue`s. Pass/fail is encoded only as data inside `grades.json` (`test_score`) and surfaced by the shell via `python3 -c` reads (`run_loop.sh:59-69`), not as a process exit code. A `--regression-only` CI mode that must propagate non-zero has NO existing mechanism to build on — it would be new behavior.

**Evidence:**

```bash
TARGET_MET=$(python3 -c "print(1 if float('${SCORE}') >= float('${TARGET_SCORE}') else 0)")
if [ "$TARGET_MET" = "1" ]; then
    echo "  ✓ Target score reached!"
    break
fi
```

— `run_loop.sh:69-74` (decision is a `break`, not an `exit`); no `sys.exit` in any `scripts/*.py main()` (searched).
**Dependencies:** Shell relies on `pipefail` to catch subprocess failures.
**Implicit contracts:** Today success/failure is value-based (score in JSON), not exit-code-based. Regression is detected (`run_loop.sh:77-91`) but only logged + `continue`d; it never fails the process. CI propagation must be added.

## Q7: How does the current eval flow distinguish a regression iteration from a revision iteration, given that `--regression-only` must skip the revision step?

**Answer:** The distinction is positional within the loop body, gated on score comparison. Per iteration `run_loop.sh` computes `SCORE` from `grades.json`, then: (1) if `SCORE >= TARGET_SCORE` → `break` (done); (2) else compute `REGRESSED = (prev > 0 and prev - curr > 0.05)` and if regressed → print rollback message + `continue` (SKIPS diagnose+revise); (3) otherwise fall through to Step 3 `diagnose.py` and Step 4 `revise.py`, then set `PREVIOUS_SCORE=$SCORE`. So a "regression iteration" is the `continue` branch (no revision), and a "revision iteration" is the fall-through (runs diagnose+revise). The revision step is literally Steps 3–4 (`run_loop.sh:93-107`). A `--regression-only` mode would skip those two steps unconditionally — equivalent to always taking a no-revise path while still running eval+grade+regression-detection.

**Evidence:**

```bash
REGRESSED=$(python3 -c "
prev = float('${PREVIOUS_SCORE}'); curr = float('${SCORE}')
threshold = 0.05
print(1 if prev > 0 and (prev - curr) > threshold else 0)")
if [ "$REGRESSED" = "1" ]; then
    echo "  ⚠ Regression detected (${PREVIOUS_SCORE} → ${SCORE})"
    continue   # skips diagnose + revise
fi
# ...falls through to Step 3 diagnose + Step 4 revise
```

— `run_loop.sh:77-107`
**Dependencies:** Regression detection inline (shell + `python3 -c`); revision delegates to `diagnose.py` then `revise.py`. `report.py:detect_regressions` (`scripts/report.py:35-54`) is a SEPARATE, post-hoc per-case regression detector (drop > 0.2) used only in the final report, distinct from the loop's 0.05 suite-level threshold.
**Implicit contracts:** Two different regression thresholds coexist: 0.05 suite-level in the loop (`run_loop.sh:80`), 0.2 per-case in the report (`scripts/report.py:46`). Revision = the diagnose→revise pair. `--regression-only` must short-circuit before Step 3.

## Q8: Where are per-phase scores recorded and how would the wrapper accumulate them into a top-level summary without overwriting individual phase results under `results/all/`?

**Answer:** Per-run scores are recorded in `grades.json` (written by `grade.py:grade_results`, `scripts/grade.py:362-365`) in the run's `--output` dir. There is no per-PHASE recording today — `run_loop.sh` runs one phase and names dirs by iteration (`results/v${i}`), NOT by phase. `report.py` accumulates across `results/v*/` by treating each subdir with a `grades.json` as a version (`scripts/report.py:14-32`). To accumulate per-phase without overwriting, a wrapper would give each phase its own subdir (e.g. `results/all/<phase>/grades.json`) and write a top-level summary file alongside; the existing aggregation pattern to mirror is `report.py`'s scan-subdirs-for-grades.json. Note `grade.py` already separates `train_score`/`test_score` per run but has no phase dimension.

**Evidence:**

```python
out_dir = output_dir or os.path.dirname(results_path)
grades_path = os.path.join(out_dir, "grades.json")
with open(grades_path, "w") as f:
    json.dump(output, f, indent=2)
```

— `scripts/grade.py:362-365`; version-dir scan at `scripts/report.py:19-31`
**Dependencies:** `report.py` consumes `grades.json` files; `run_loop.sh` Step 3 reads `grades.json` `test_score` (`run_loop.sh:59-63`).
**Implicit contracts:** A `grades.json` per subdir is the unit of aggregation. Output dirs are caller-named via `--output`; `os.makedirs(..., exist_ok=True)` (`run_eval.py:152`) means re-running into the same dir merges/overwrites that dir's `results.json` (see Q11). To avoid overwriting phase results, each phase needs a DISTINCT subdir; the top-level summary must be a separate file (not another phase's `grades.json`).

## Q9: What happens in the current single-agent path when an agent run fails, produces no score, or times out — and how is that failure surfaced versus a legitimate low score?

**Answer:** Three distinct failure surfaces. (1) Execution error: `execute_single` wraps the (stubbed) agent call in try/except and sets `result.error = str(e)` (`run_eval.py:139-140`); the result is still recorded with status printed as `ERROR` (`run_eval.py:186-187`). (2) Future-level exception: caught in `run_suite`, prints `EXCEPTION` and appends a minimal `{case_id, trial_id, error}` dict (`run_eval.py:188-194`). (3) Timeout: `timeout_ms` (default 120000) is stored in config and passed to `execute_single` but is NEVER enforced — the stub ignores it; there is no actual timeout mechanism, so a real hang would not be surfaced. Critically, `grade.py` does NOT check `result.error` — an errored result with empty `output`/`files` simply fails its assertions and scores ~0, so an EXECUTION FAILURE is INDISTINGUISHABLE from a legitimate low score at grading time. The only failure signal is the printed `ERROR`/`EXCEPTION` line on stdout and the presence of an `error` key in `results.json`.

**Evidence:**

```python
try:
    ... result.output = "" ...
except Exception as e:
    result.error = str(e)
result.duration_ms = (time.time() - start) * 1000
```

— `scripts/run_eval.py:116-143`; `grade.py` never reads `result.get("error")` (searched `scripts/grade.py`).
**Dependencies:** `grade.py:grade_results` consumes `results.json` results blindly via `result.get("output","")` / `result.get("files",[])`.
**Implicit contracts:** `error` field is advisory only; graders treat missing output as score 0. No timeout enforcement exists despite `timeout_ms` plumbing. A multi-agent wrapper iterating 8 agents would silently score a crashed agent as 0 unless it inspects `results[].error`.

## Q10: How does the existing runner behave when a fixture is missing or malformed for a given phase agent, which the iterating wrapper would encounter across all 8 agents?

**Answer:** Missing fixture: SILENTLY SKIPPED. `build_messages` guards each fixture with `if os.path.exists(file_path)` and simply omits any path that does not resolve — no warning, no error, no record (`run_eval.py:78-82`). The case still runs with reduced/empty context and is scored normally. Malformed fixture: not validated at all — the file is read as raw text (`f.read()`) and concatenated verbatim; there is no parsing of fixture content, so "malformed" never raises. The ONLY hard validation is on the SUITE itself: `load_suite` raises `ValueError` if top-level `name`/`cases` are missing, or if any case lacks `id`/`prompt`/`assertions` (`run_eval.py:42-58`) — that `ValueError` would abort the whole run (and, under `pipefail`, the whole loop). So across 8 agents, a missing fixture degrades silently to a low score; only a structurally broken suite hard-fails.

**Evidence:**

```python
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
    case_missing = case_required - set(case.keys())
    if case_missing:
        raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
```

— `scripts/run_eval.py:47-56`; silent fixture skip at `scripts/run_eval.py:78-82`
**Dependencies:** `load_suite` is called once at the top of `run_suite` (`run_eval.py:148`); a raised `ValueError` propagates out of `main()` → non-zero exit → `pipefail` aborts `run_loop.sh`.
**Implicit contracts:** Suite structural integrity is a hard gate; fixture presence is best-effort/silent. Combined with the CWD path mismatch from Q2 (suite uses `fixtures/...` paths, runner runs from repo root), ALL fixtures may currently be silently skipped under `run_loop.sh`.

## Q11: What is the current behavior when `results/` (or a target output subdirectory) already exists or is partially written from a prior run, which `--all` would re-enter for `results/all/`?

**Answer:** Idempotent-by-overwrite, no cleanup. `run_eval.py` calls `os.makedirs(config.output_dir, exist_ok=True)` (`run_eval.py:152`) — re-entering an existing dir does NOT error and does NOT clear it. `results.json` is opened with `"w"` (`run_eval.py:210`), so it is fully overwritten; same for `grades.json` (`grade.py:364`). Stale sibling files from a prior run (e.g. `diagnosis.json`, `revision-log.json`) are left in place. `report.py` scans EVERY subdir of `results/` containing a `grades.json` and treats it as a version (`scripts/report.py:19-31`) sorted by name — so a leftover/partial subdir with a valid `grades.json` would be silently included in the report ledger. `revise.py` APPENDS to `revision-log.json` rather than overwriting (`scripts/revise.py:175-181`), so partial prior state accumulates there.

**Evidence:**

```python
os.makedirs(config.output_dir, exist_ok=True)
...
output_path = os.path.join(config.output_dir, "results.json")
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
```

— `scripts/run_eval.py:152, 209-211`; `report.py` subdir scan at `scripts/report.py:19-31`
**Dependencies:** `report.py:load_version_results` enumerates `results/` subdirs; `update_ledger` writes `results/ledger.json`.
**Implicit contracts:** Output dirs are reused, not reset — partial writes from a crashed run can persist and (if they contain `grades.json`) be picked up by `report.py` as a version. A `results/all/` subdir would itself be enumerated by `report.py` as a version unless explicitly excluded — a real collision risk for `--all`.

## Q12: What testing convention do the existing `scripts/qrspi_*_test.py` siblings follow (stdlib-only, `python3`-run) that a new `eval_all` implementation would need matching unit tests under?

**Answer:** Convention: a `_test.py` sibling next to the module, named `<module>_test.py`, importing the module under test by bare name (e.g. `import qrspi_persist as qp`) — which requires the test to be run from within `scripts/` (CWD on `sys.path`). Tests use only the stdlib `unittest` framework (plus `os`, `tempfile`, `json`), no pytest, no third-party deps. Each file ends with `if __name__ == "__main__": unittest.main()` and is run with `python3 scripts/<module>_test.py`. Tests favor pure-function checks (path construction, persist semantics) and use `tempfile.TemporaryDirectory()` for filesystem isolation. There are 10 such test files today (e.g. `qrspi_persist_test.py`, `qrspi_resolve_state_test.py`, `qrspi_pr_state_test.py`). NOTE: `run_eval.py`, `grade.py`, `report.py`, `diagnose.py`, `revise.py` currently have NO `_test.py` siblings — the eval scripts are untested.

**Evidence:**

```python
"""Stdlib-only unit tests for qrspi_persist.py. Run: python3 scripts/qrspi_persist_test.py"""
import os, tempfile, unittest
import qrspi_persist as qp
class StagingPathTest(unittest.TestCase):
    def test_token_free_construction(self):
        p = qp.staging_path("/tmp/phase-stage", "RUS-21", "plan")
        self.assertEqual(p, "/tmp/phase-stage/RUS-21/plan.md")
...
if __name__ == "__main__":
    unittest.main()
```

— `scripts/qrspi_persist_test.py:1-17, 89-90`
**Dependencies:** Bare-name import means tests depend on CWD=`scripts/`. No conftest/pytest config in repo.
**Implicit contracts:** A new `eval_all` impl should ship a `scripts/eval_all_test.py` (or `_test.py` sibling) that is stdlib-only `unittest`, imports the module by bare name, uses `tempfile` for fs, and is runnable via `python3 scripts/eval_all_test.py`. Per CLAUDE.md: "stdlib-only unit tests ... run with python3."

## Q13: Is there an existing end-to-end or smoke test that exercises `run_loop.sh` against a single agent that the multi-agent wrapper could be validated against?

**Answer:** NOT FOUND. No test exercises `run_loop.sh`. Searched `scripts/` and `evals/` — the only `_test.py` files are the 10 `scripts/qrspi_*_test.py` siblings plus `scripts/using_claude_cli_skill_test.py`; none invoke `run_loop.sh`, `run_eval.py`, `grade.py`, or the bash loop. There is no shell test harness, no `bats`, no CI workflow under the worktree that runs the loop. CLAUDE.md and README explicitly state the eval harness is a "non-functional placeholder" verified by "manual end-to-end runs," confirming no automated e2e exists. So a multi-agent wrapper has no existing smoke test to validate against — it would be the first.

**Evidence:**

```
# searched: grep -rn "run_loop\|run_eval" scripts/ evals/ → no test references
# CLAUDE.md: "The evals/ + scripts/run_eval.py harness is a non-functional
#  placeholder — verify pure logic with the unit tests and orchestration
#  changes with manual end-to-end runs"
```

— `.claude/CLAUDE.md` (Codebase conventions, final bullet); directory scan of `scripts/`, `evals/`
**Dependencies:** None.
**Implicit contracts:** Validation today is manual. The stub `execute_single` returns empty output (`run_eval.py:132-137`), so even a full `run_loop.sh` run produces all-zero scores — any e2e "smoke" test can only assert plumbing (files written, exit code), not real scores, until the agent runtime is wired in.

## Q14: How does the current eval runner emit progress and score output (stdout format, log lines, summary block) that the consolidated report must reproduce per-phase and at suite level?

**Answer:** Three emitters. (1) `run_eval.py` prints a header (`Running N executions...`, `Skill hash: ...`, `Max workers: ...`) then one line per completed run: `  [{completed}/{total}] {case_id} trial={trial} {OK|ERROR} ({duration}ms)`, then `Results written to {path}` (`run_eval.py:161-213`). (2) `grade.py` prints a summary block: `Train score: X (+/- s)`, `Test score:  X (+/- s)`, `Train-test gap: X`, `Grades written to {path}` (`grade.py:367-370`). (3) `run_loop.sh` wraps everything in box-drawing banners (`╔═...═╗`) and numbered `[1/4]`..`[4/4]` step labels, prints `  Score: ${SCORE} (target: ${TARGET_SCORE})`, and `✓`/`⚠` markers for target-met/regression (`run_loop.sh:19-66`). (4) `report.py` prints `=== Eval Report (N versions) ===` with Latest/Train/Test/Gap/Best-test plus `ALERT:` lines for plateau/overfitting (`scripts/report.py:159-169`). A consolidated per-phase report must reproduce the `grade.py` train/test summary block per phase and the `report.py` aggregate block at suite level.

**Evidence:**

```python
print(f"Train score: {train_scores['mean']:.4f} (+/- {train_scores['stddev']:.4f})")
print(f"Test score:  {test_scores['mean']:.4f} (+/- {test_scores['stddev']:.4f})")
print(f"Train-test gap: {output['train_test_gap']:.4f}")
```

— `scripts/grade.py:367-369`; per-run lines at `scripts/run_eval.py:187`; report block at `scripts/report.py:159-169`
**Dependencies:** `run_loop.sh` parses `grades.json` (not stdout) for the actual score it prints (`run_loop.sh:59-63`) — stdout is human-facing only; machine state flows via JSON files.
**Implicit contracts:** Score floats are formatted `:.4f`; per-run status is `OK`/`ERROR`; alerts use the literal `ALERT:` prefix. A consolidated report should keep the JSON-as-source-of-truth + stdout-as-human-log split.

## Q15: What mechanism, if any, currently distinguishes a phase-level signal from a suite-level signal in the runner's output, which the report must use to separate phase-level from suite-level regressions?

**Answer:** There is NO phase dimension in any output today — the only structural split is train vs test (per `case["split"]`), NOT per phase. `grade.py` partitions cases by `split` into `train_grades`/`test_grades` and emits `train_score`/`test_score`/`train_test_gap` (`grade.py:340-358`); it never groups by `case["phase"]` even though every case carries a `phase` field. `report.py` aggregates across VERSIONS (iteration dirs `v1..vN`), not phases. So the existing "levels" are: per-case (`cases[].mean_score`), per-split (train/test), per-version (report ledger). A per-phase vs suite-level distinction does NOT exist and must be built — the raw material is the `phase` field present on every case in `evals/suite.json` (Q5), which `grade.py` currently ignores.

**Evidence:**

```python
train_grades = [cg for cg in case_grades if cg["split"] == "train"]
test_grades = [cg for cg in case_grades if cg["split"] == "test"]
train_scores = score_suite([{"score": cg["mean_score"]} for cg in train_grades])
test_scores  = score_suite([{"score": cg["mean_score"]} for cg in test_grades])
```

— `scripts/grade.py:340-348`; `case["phase"]` is read nowhere in `grade.py` (searched, only `split` is used)
**Dependencies:** `grade.py` reads `case["split"]` (`grade.py:302`) and `case["tags"]`/`case["difficulty"]`; `report.py:detect_regressions` keys on `case_id` only (`scripts/report.py:35-54`).
**Implicit contracts:** Aggregation today is split-based and version-based. The `phase` tag on each suite case is the latent key for any phase-level signal — a per-phase report must group `case_grades` by `phase` (a field `grade.py` currently drops from its output entirely: `case_grade` at `grade.py:328-336` omits `phase`).

---

## Discovered Patterns

- **Stub/placeholder architecture.** Every "intelligent" step is a documented stub awaiting real integration: `execute_single` returns empty output (`run_eval.py:117-137`), `run_llm_judge`/`run_script_check` return `passed: None` (`grade.py:208-241`), `categorize_failure` is heuristic (`diagnose.py:58-103`), `propose_revisions` emits `pending_meta_agent` edits (`revise.py:26-72`). Consequence: a full pipeline run today yields all-zero scores. CLAUDE.md confirms the harness is a "non-functional placeholder."
- **JSON files as the state bus; stdout as human log.** Every stage reads/writes JSON (`results.json` → `grades.json` → `diagnosis.json` → `revision-log.json` → `report.json` + `ledger.json`) and `run_loop.sh` extracts decisions via `python3 -c` JSON reads, never by parsing stdout (`run_loop.sh:59-63`).
- **Per-subdir aggregation.** `report.py` treats each `results/` subdir containing a `grades.json` as a unit. Any new output layout (`results/all/<phase>/`) must account for this enumerator (`scripts/report.py:19-31`).
- **`phase` is a first-class suite field but a second-class runtime field.** All 15 cases in `evals/suite.json` carry a `phase` (8 distinct values matching the 8 agent files), yet no script groups or filters by it — `grade.py` even drops `phase` from its emitted `case_grade`. This is the single biggest gap a multi-agent driver must close: filter the shared suite by `phase`, and aggregate scores by `phase`.
- **Stdlib-only `unittest` testing.** 10 `qrspi_*_test.py` siblings, bare-name imports (CWD=`scripts/`), `tempfile` isolation, `python3 scripts/X_test.py`. The five eval scripts (`run_eval/grade/report/diagnose/revise`) have NO tests.
- **Two regression thresholds.** 0.05 suite-level in the loop (`run_loop.sh:80`) vs 0.2 per-case in the report (`scripts/report.py:46`).

## Inconsistencies

- **Doc-comment agent path scheme does not exist.** `run_loop.sh:10` example uses `.qrspi/agents/01-questions.md`, but the real agents live at `.claude/agents/qrspi-*.md` (8 files). No `.qrspi/agents/` numbered-prefix scheme exists in the worktree. Any `--phase`/`--all` mapping must target `.claude/agents/qrspi-<phase>.md`, not the doc-comment path.
- **Fixture path / CWD mismatch.** Suite fixtures are referenced relative to `evals/` (e.g. `"fixtures/ticket_rest_endpoint.md"`), but `run_loop.sh` runs `python3 scripts/run_eval.py` from the repo root, where `fixtures/...` does NOT resolve. Because `build_messages` silently skips missing files (`run_eval.py:78-82`), fixtures are currently loaded as empty — a silent, unsurfaced failure.
- **Suite references an undefined check.** `evals/suite.json` case_001 uses `check: "section_count('questions.md', '## ') >= 5"`, but `section_count` is NOT in `grade.py`'s `CHECKS` registry (`grade.py:146-157`) — it would resolve to `passed: None` ("Unknown check function"). Similarly the suite uses comparison-operator check strings (`... >= 5`) that `parse_check_call` (`grade.py:160-174`) does not parse into a comparison — it extracts only the literal args. These checks silently no-op today.
- **`timeout_ms` is plumbed but never enforced.** Threaded through `EvalConfig`/`execute_single` (`run_eval.py:39, 97`) but no timeout is applied; a real hung agent would not be killed or surfaced.
- **Error results are recorded but never graded.** `run_eval.py` writes `result.error`, but `grade.py` never inspects it — an execution failure scores identically to a legitimate 0 (Q9).
- **`grade.py` drops `phase` from output** despite it being present on every input case, blocking any downstream per-phase aggregation without re-reading the suite (`grade.py:328-336`).
