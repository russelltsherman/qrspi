# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Q1: What inputs does `run_llm_judge` currently receive (signature, parameter types) and what does each caller pass into it?

**Answer:** `run_llm_judge(assertion: dict, result: dict, case: dict) -> dict`. It has exactly one caller, the grading pipeline in `grade_results`, which dispatches by `assertion["type"] == "llm_judge"`. The function currently ignores all three params except `assertion["criteria"]` (the only key it reads) and `assertion.get("weight", 1.0)`. It is a stub: it never inspects `result` (agent output) or `case`.

`assertion` is one entry from a case's `assertions` list (keys observed in the suite: `type`, `criteria`, `weight`). `result` is one `ExecutionResult` rendered to dict via `asdict` in run_eval.py (keys: `case_id`, `trial_id`, `output`, `files`, `duration_ms`, `tokens`, `tool_calls`, `transcript`, `error`). `case` is the suite case dict (`id`, `prompt`, `assertions`, plus optional `split`, `tags`, `difficulty`, `context`).

**Evidence:**

```python
def run_llm_judge(assertion: dict, result: dict, case: dict) -> dict:
    return {
        "check": assertion["criteria"],
        "type": "llm_judge",
        "passed": None,  # null until real judge is integrated
        "score": None,    # 1-5 scale from judge
        "evidence": "LLM judge not yet integrated — requires model API",
        "weight": assertion.get("weight", 1.0),
    }
```

— `scripts/grade.py:208-227`

```python
elif atype == "llm_judge":
    ar = run_llm_judge(assertion, trial_result, case)
```

— `scripts/grade.py:312-313`

**Dependencies:** Caller is `grade_results` (`scripts/grade.py:282-372`). Upstream `assertion`/`case` originate from `evals/suite.json`; `result` originates from `scripts/run_eval.py` (`ExecutionResult`, line 19-29).
**Implicit contracts:** Return dict MUST carry `check`, `type`, `passed`, `weight`; LLM-judge results additionally carry `score`. `score_case` (line 246) reads `passed` and `score`; `extract_failures`/`categorize_failure` in diagnose.py read `passed`, `type`, `check`, `evidence`, `weight`. `assertion["criteria"]` is a hard `KeyError` if absent (no `.get`).

## Q2: How is the rubric, criteria, and agent output represented and passed through the grading pipeline before reaching `run_llm_judge`?

**Answer:** There is no separate "rubric" object — the grading unit is an *assertion*. For an llm_judge assertion the rubric is a single free-text string `criteria` plus a numeric `weight`. The agent output to be judged lives in `result["output"]` (a string; programmatic checks read it via `result.get("output", "")`). The pipeline in `grade_results` loads `results.json` and `suite.json`, indexes cases by id, groups results by `case_id`, and for each trial iterates the case's `assertions`, dispatching each to the type-specific runner. `case` and `trial_result` are passed positionally; the assertion's `criteria`/`weight` and the result's `output` are the only relevant fields for a real judge.

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
```

— `scripts/grade.py:308-315`

Sample llm_judge assertion shape in the suite:

```json
{ "type": "llm_judge",
  "criteria": "Questions are specific and answerable by reading code, not speculative or opinion-seeking",
  "weight": 2.0 }
```

— `evals/suite.json` (case `case_001`)

**Dependencies:** `grade_results` reads files written by run_eval.py (results.json) and the static `evals/suite.json`. Agent output text comes from `ExecutionResult.output` (`scripts/run_eval.py:23,133`), which is currently `""` because execution is itself a stub (`execute_single`, lines 93-143).
**Implicit contracts:** Cases carry `assertions: list`; each assertion has a `type`; missing/unknown type yields a `passed: None` placeholder (line 316-318). `result["output"]` is a single string blob, not per-file structured content.

## Q3: How is a results directory located and structured at runtime, so a cache keyed within it can persist across `run_loop.sh` iterations?

**Answer:** `run_loop.sh` derives a per-iteration directory `OUTPUT_DIR="results/${VERSION}"` where `VERSION="v${i}"` for `i` in `1..MAX_ITER`. run_eval.py writes `<OUTPUT_DIR>/results.json` (creating the dir with `os.makedirs(..., exist_ok=True)`). grade.py is invoked WITHOUT `--output`, so its grades default to `os.path.dirname(results_path)` = the same `results/vN/`. **Critically, the cache would NOT naturally persist across iterations if keyed inside `results/vN/`**: each iteration gets a fresh `vN` directory. A cache that must survive across iterations would need a fixed location (e.g., `results/` root or a sibling like `results/.cache/`), not the per-version subdir. No cache exists today.

**Evidence:**

```bash
VERSION="v${i}"
OUTPUT_DIR="results/${VERSION}"
...
python3 scripts/grade.py \
    --results "${OUTPUT_DIR}/results.json" \
    --suite "$EVAL_SUITE"
```

— `run_loop.sh:33-34, 53-55`

```python
out_dir = output_dir or os.path.dirname(results_path)
grades_path = os.path.join(out_dir, "grades.json")
```

— `scripts/grade.py:362-363`

**Dependencies:** `run_loop.sh` → run_eval.py (creates `results/vN/`) → grade.py (writes into the same dir). report.py later globs `results/*/grades.json` (`load_version_results`, `scripts/report.py:14-32`), so any new top-level file/dir under `results/` must be a directory-with-grades or it is skipped (`if not version_dir.is_dir(): continue`, line 20-21) — a `results/.cache/` dir without a `grades.json` is safely ignored by report.py.
**Implicit contracts:** `results/` is the stable root (`.gitkeep` present, dir tracked). Per-version dirs are `vN`. report.py assumes every direct child dir of `results/` is a version; a cache sibling must avoid carrying a `grades.json`.

## Q4: What return shape do callers of `run_llm_judge` expect today (which keys beyond `passed` are read, and how is `passed: None` currently handled downstream)?

**Answer:** Two downstream consumers. (1) `score_case` reads `passed` and `score`: a judge result contributes only via its `score` branch — `passed is True` adds full weight; otherwise if `score is not None`, it adds `weight * (score-1)/4` (1-5 → 0-1). With the current stub both `passed` and `score` are `None`, so the assertion contributes **0 actual** but still adds its `weight` to `max_score` — i.e. every llm_judge assertion is scored as a guaranteed zero today, dragging scores down. (2) diagnose.py's `extract_failures`/`categorize_failure` only collect assertions where `passed is False` (line 38); `passed: None` is NOT counted as a failure there, and an llm_judge type routes to the `UNDER_SPECIFIED` category (line 84-85).

**Evidence:**

```python
weight = ar.get("weight", 1.0)
max_score += weight
if ar.get("passed") is True:
    actual_score += weight
elif ar.get("score") is not None:
    # LLM judge: normalize 1-5 to 0-1
    actual_score += weight * (ar["score"] - 1) / 4
```

— `scripts/grade.py:251-257`

```python
if assertion.get("passed") is False:
    failed_assertions.append({...})
```

— `scripts/diagnose.py:38-44`

**Dependencies:** `score_case` (grade.py:246-265) → `score_suite` (268-277) → final train/test means. diagnose.py reads the persisted `grades.json`.
**Implicit contracts:** A real judge should set EITHER `passed: True/False` OR `score: 1..5`. `passed: None` + `score: None` is treated as "present but worth zero" by score_case yet "not a failure" by diagnose — an inconsistency (see Inconsistencies). Keys read downstream: `passed`, `score`, `weight`, `type`, `check`, `evidence`.

## Q5: Is the Anthropic SDK already a declared dependency, and what model/client configuration patterns already exist in the codebase?

**Answer:** NOT FOUND as a declared dependency. There is **no dependency manifest at all** — no `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, or `*.cfg` anywhere in the repo (searched). All scripts are stdlib-only (`argparse`, `json`, `os`, `re`, `statistics`, `hashlib`, `time`, `pathlib`, `dataclasses`, `typing`, `concurrent.futures`). No `import anthropic` exists. The only "client" patterns are illustrative pseudocode in docstrings: `judge_model.complete(...)` in grade.py (line 213-216) and `meta_agent.complete(...)` in diagnose.py (line 64-70) and revise.py (line 34-40) — none reference a real SDK, model id, or client constructor.

**Evidence:**

```python
"""
    In a real implementation, this calls a grading model:

        response = judge_model.complete(
            system="You are grading an AI agent's output...",
            messages=[{"role": "user", "content": grading_prompt}],
        )
"""
```

— `scripts/grade.py:209-218` (docstring, not executable)

Search results: `find ... -name requirements*.txt -o -name pyproject.toml ...` → no matches; `grep -ri anthropic scripts/` → no matches.

**Dependencies:** None declared. CLAUDE.md states the `evals/` + `scripts/run_eval.py` harness is a "non-functional placeholder."
**Implicit contracts:** Repo convention is stdlib-only and "no pytest dependency" (`scripts/using_claude_cli_skill_test.py:3-7`). Introducing the Anthropic SDK would be the first third-party runtime dependency and would also be the first thing requiring a manifest.

## Q6: How are API credentials (e.g., `ANTHROPIC_API_KEY`) currently sourced and referenced elsewhere in the suite?

**Answer:** NOT FOUND — no credential sourcing exists anywhere. Grepping `os.environ`, `getenv`, `ANTHROPIC_API_KEY`, `load_dotenv`, `.env` across `scripts/` and `run_loop.sh` returns zero hits. `import os` is used only for path operations (`os.path.*`, `os.makedirs`). A `.env` file exists at the repo root but is **empty** (0 meaningful content) and, notably, is NOT listed in `.gitignore` (`.gitignore` ignores `__pycache__`, `.worktrees/`, a lock file, and `.qrspi/config.json`). There is no config-loading module; per-user config elsewhere lives in `.qrspi/config.json` (gitignored, JSON), read by the qrspi_*.py orchestration scripts — but that is for reviewers/team, not API keys.

**Evidence:**

```
# .gitignore
__pycache__
.worktrees/
.claude/scheduled_tasks.lock
# Local config override (per-user); see .qrspi/config.example.json
.qrspi/config.json
```

— `.gitignore:1-5` (note: `.env` absent)

`grep -rniE "os.environ|getenv|ANTHROPIC_API_KEY|load_dotenv|\.env" scripts/ run_loop.sh` → no output.

**Dependencies:** None.
**Implicit contracts:** No established env-var or secret pattern to follow. A new judge integration must define its own credential sourcing convention (and likely add `.env` to `.gitignore`).

## Q7: Where do other parts of the suite persist intermediate state to disk, and what serialization format and file-locking conventions do they use?

**Answer:** All persistence is **JSON via `json.dump(..., indent=2)`**, written with a plain `open(path, "w")` — **no file locking anywhere** (no `flock`, `fcntl`, `filelock`, or atomic temp-then-rename). Artifacts: run_eval.py writes `results/vN/results.json`; grade.py writes `grades.json`; diagnose.py writes `diagnosis.json`; revise.py writes the revised skill file plus an *append-style* `revision-log.json` (reads existing JSON list, appends, rewrites whole file — read-modify-write, race-prone but single-threaded in run_loop.sh); report.py writes `report.json` and `ledger.json`. run_eval.py runs trials concurrently (`ThreadPoolExecutor`) but each writes only its own in-memory result; the single `results.json` is written once after all futures complete.

**Evidence:**

```python
log = []
if os.path.exists(log_path):
    with open(log_path) as f:
        log = json.load(f)
log.append(log_entry)
with open(log_path, "w") as f:
    json.dump(log, f, indent=2)
```

— `scripts/revise.py:175-181` (read-modify-write, no lock)

```python
with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
```

— `scripts/run_eval.py:166`

**Dependencies:** Separate qrspi orchestration scripts (`qrspi_persist.py`) use a staging+move convention for phase artifacts, but the eval scripts do not.
**Implicit contracts:** JSON, 2-space indent, full-file overwrite. A cache file should follow JSON+`indent=2` to match. Concurrency note: run_eval.py is multi-threaded — if a cache is read/written during `execute_single` it would need locking, but grading (grade.py) is single-threaded.

## Q8: How is the total suite weight computed and where is the ~30% LLM-judge contribution aggregated into the final score?

**Answer:** Weighting is per-assertion, summed in `score_case`: `max_score = sum(weight)` over all assertions in a trial; `actual_score` accrues `weight` (programmatic pass) or `weight*(score-1)/4` (judge). `normalized = actual/max`. There is no global "30%" constant — the llm_judge share is *emergent* from the assertion weights in `evals/suite.json`. Measured: 76 programmatic (total weight 92.0), 22 llm_judge (49.5), 1 script (2.5); llm_judge is **34.4%** of total weight (close to the "~30%" framing in the question). Per-case → `mean_score` across trials → `score_suite` mean across cases, split into `train_score`/`test_score`. Because judge results currently return `score: None`, that 34.4% of weight contributes 0 to `actual` but full to `max`, capping achievable normalized scores at ~0.66 on judge-heavy cases.

**Evidence:**

```python
normalized = actual_score / max_score if max_score > 0 else 0.0
return {"score": round(normalized, 4), "actual": ..., "max": ..., ...}
```

— `scripts/grade.py:259-265`

```python
"train_score": train_scores["mean"],
"test_score": test_scores["mean"],
"train_test_gap": round(abs(train_scores["mean"] - test_scores["mean"]), 4),
```

— `scripts/grade.py:353-355`

**Dependencies:** `score_case` → case `mean_score` (grade.py:333) → `score_suite` (268-277) → top-level scores → consumed by run_loop.sh target check (`g.get('test_score', 0)`, run_loop.sh:59-64) and report.py.
**Implicit contracts:** `weight` defaults to `1.0` (`assertion.get("weight", 1.0)`). Cases are split by `case["split"]` (default `"train"`, grade.py:302); only `split in {train,test}` cases are aggregated (others dropped, lines 340-348). Judge weight is data-driven, not a code constant.

## Q9: How does `run_llm_judge` and its callers currently behave when an assertion returns `passed: None` versus `True`/`False`?

**Answer:** `run_llm_judge` ALWAYS returns `passed: None, score: None` today (it is a stub). In `score_case`: `passed is True` → full weight; `passed is False` → no weight from the `passed` branch, then falls to the `elif score is not None` branch; with `passed: None` and `score: None`, neither branch fires → contributes 0 to actual but its weight still counts toward `max` (line 251-257). So `passed: None` is scored as a hard zero. In diagnose.py, only `passed is False` is collected as a failure (line 38); `passed: None` assertions are silently excluded from the failure list and from categorization — meaning judge stubs depress the score but never surface as diagnosable failures.

**Evidence:**

```python
if ar.get("passed") is True:
    actual_score += weight
elif ar.get("score") is not None:
    actual_score += weight * (ar["score"] - 1) / 4
# passed is None AND score is None -> 0 contribution, weight still in max
```

— `scripts/grade.py:253-257`

Also note `run_programmatic_check` returns `passed: None` for unknown check functions (line 196-197), so `None` is an existing sentinel for "not evaluated."

**Dependencies:** `score_case` (grade.py:246), `extract_failures` (diagnose.py:27-55).
**Implicit contracts:** `passed: None` = "not evaluated / skip" by intent, but score_case penalizes it as zero. A real judge should set `passed` or `score` so the assertion is not silently zero-weighted.

## Q10: What existing handling exists for Anthropic API errors, rate limits, timeouts, or malformed model responses in the codebase?

**Answer:** NOT FOUND — none. There are no external API calls in the codebase, hence no retry/backoff, no rate-limit handling, no timeout-on-API, no response-shape validation. The only error handling present is generic: `run_programmatic_check` wraps the check call in `try/except Exception` and sets `passed: False, evidence: f"Check error: {e}"` (grade.py:191-193); run_eval.py's `execute_single` catches `Exception` into `result.error` (lines 139-140); `as_completed` loop catches per-future exceptions (lines 188-194). `EvalConfig.timeout_ms`/`--timeout` (run_eval.py:39, 224) is plumbed but never enforced (the stub `execute_single` ignores it). No `requests`/`httpx`/`anthropic` import exists.

**Evidence:**

```python
try:
    outcome = CHECKS[func_name](*args, result)
    ...
except Exception as e:
    passed = False
    evidence = f"Check error: {e}"
```

— `scripts/grade.py:183-193`

**Dependencies:** None external.
**Implicit contracts:** Established failure convention is `passed: False` + human-readable `evidence` string. A judge integration should map API/parse errors into that same `{passed: False/None, evidence: "..."}` shape to stay consistent with score_case and diagnose.

## Q11: How are non-deterministic or out-of-range judge outputs (e.g., a score outside 1-5, or missing rationale) expected to be validated, given the cache key `(sha256(output) + criteria)`?

**Answer:** NOT FOUND — no validation exists today, and no cache exists today. `run_llm_judge` performs no range-checking; `score_case` blindly computes `weight*(score-1)/4` with no clamp, so a score of 0 yields a negative contribution and a score of 6 yields >weight — there is no guard (grade.py:256-257). There is no rationale field validated anywhere (the stub's `evidence` is a fixed string). No `sha256`/`hashlib` usage exists in grade.py (only run_eval.py uses `hashlib.sha256` to hash the *skill text* into a 12-char `skill_hash`, line 155 — unrelated to any judge cache). The `(sha256(output) + criteria)` cache key described in the question is a *proposed* design, not present in code.

**Evidence:**

```python
elif ar.get("score") is not None:
    actual_score += weight * (ar["score"] - 1) / 4   # no clamp to [1,5]
```

— `scripts/grade.py:255-257`

```python
skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]
```

— `scripts/run_eval.py:155` (hashes skill text, not judge output)

**Dependencies:** score_case math (grade.py:246-265).
**Implicit contracts:** None for ranges. Existing `skill_hash` precedent: `hashlib.sha256(text.encode()).hexdigest()[:12]` — a real judge cache could reuse this hashing convention.

## Q12: What happens to the `(sha256(output) + criteria)` cache when two different rubrics share the same output and criteria, or when criteria text varies only by whitespace?

**Answer:** NOT FOUND in current code — no cache and no key-construction logic exist to inspect. Reasoning from the only existing hash precedent (`hashlib.sha256(skill_text.encode())`, run_eval.py:155): SHA-256 is byte-exact, so two rubrics that share identical `output` AND identical `criteria` bytes would collide to the same key (correctly cache-share, since the judge inputs are identical — the rubric-vs-assertion distinction does not exist; the "rubric" IS the `criteria` string, see Q2). Criteria differing only by whitespace (`"a b"` vs `"a  b"`) produce different SHA-256 digests → distinct cache entries (no normalization). Since `criteria` strings in the suite are author-written free text with no canonicalization step anywhere, whitespace variance would silently fragment the cache. There is no existing trimming/normalization helper in the codebase to reuse.

**Evidence:**

```python
skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]
```

— `scripts/run_eval.py:155` (only hashing precedent; byte-exact, no normalization)

No cache-key construction code exists in grade.py (grep `cache`/`sha256` in grade.py → none).

**Dependencies:** None present.
**Implicit contracts:** The judge input is `(result["output"], assertion["criteria"])`. There is no rubric object distinct from criteria, so "two different rubrics, same criteria+output" reduces to identical judge inputs and SHOULD share a cache entry by design.

## Q13: How are existing assertion types in `grade.py` unit-tested, and is the Anthropic client mocked or stubbed in current tests?

**Answer:** NOT FOUND — `grade.py` has **no unit tests at all**. There is no `scripts/grade_test.py`. The 10 existing `*_test.py` files all cover the qrspi orchestration scripts (`qrspi_cleanup`, `qrspi_clear_stale_pr`, `qrspi_persist`, `qrspi_pr_body`, `qrspi_pr_state`, `qrspi_resolve_state`, `qrspi_resolve`, `qrspi_restack`, `qrspi_revise_amend`) plus `using_claude_cli_skill_test.py`. None import `grade`, `run_eval`, `diagnose`, `revise`, or `report` (verified by grep). Consequently there is no existing mock/stub of any model client. The test convention, per `using_claude_cli_skill_test.py:3-7`, is "Stdlib-only, assert-based (no pytest dependency)... Run with python3 ... Exits 0 if all checks pass, 1 on the first failure" — `assert`-driven, self-locating the repo root from `__file__`.

**Evidence:**

```
scripts/qrspi_cleanup_test.py        scripts/qrspi_pr_state_test.py
scripts/qrspi_clear_stale_pr_test.py scripts/qrspi_resolve_state_test.py
scripts/qrspi_persist_test.py        scripts/qrspi_resolve_test.py
scripts/qrspi_pr_body_test.py        scripts/qrspi_restack_test.py
scripts/qrspi_revise_amend_test.py   scripts/using_claude_cli_skill_test.py
```

— `ls scripts/*_test.py` (no `grade_test.py`)

**Dependencies:** None test the eval pipeline.
**Implicit contracts:** New tests should be `scripts/grade_test.py`, stdlib-only, `assert`-based, runnable via `python3 scripts/grade_test.py`, exit 0/1. CLAUDE.md: "stdlib-only unit tests as `_test.py` siblings." Any judge client must be injectable/stubbable to test without network (no DI seam exists today — `run_llm_judge` would need one).

## Q14: What harness or fixture exists for "running the same suite twice" to verify the cache is hit on the second run?

**Answer:** NOT FOUND as a cache-verification harness. The closest existing mechanism is `run_loop.sh`, which runs the suite up to `MAX_ITER` times — but each iteration writes to a fresh `results/vN/` dir and **revises the skill between runs** (steps 3-4: diagnose.py + revise.py mutate `SKILL_PATH`), so consecutive runs are NOT identical inputs and the loop is not a same-suite-twice fixture. `run_eval.py` runs `trials` (default 3) of each case within one invocation, but those are independent executions, not cache re-hits. No fixture, golden file, or test asserts "second run reuses cached result." Fixtures that DO exist (`evals/fixtures/*.md`, `evals/golden/`) are input ticket files / golden outputs for cases, unrelated to caching. (`evals/golden/` exists but is effectively empty.)

**Evidence:**

```bash
for i in $(seq 1 "$MAX_ITER"); do
    VERSION="v${i}"
    OUTPUT_DIR="results/${VERSION}"
    ... run_eval ... grade ... diagnose ... revise (mutates SKILL_PATH) ...
done
```

— `run_loop.sh:32-112` (skill changes each iteration → not a stable re-run)

**Dependencies:** `run_loop.sh` → run_eval.py → grade.py → diagnose.py → revise.py.
**Implicit contracts:** To test a cache hit deterministically, a new harness must hold inputs (output text + criteria) constant across two grade.py invocations sharing a persistent cache location (see Q3 — must be outside the per-`vN` dir).

## Q15: How are costs, token counts, and per-call metrics currently logged in the suite, so that "cost per full suite run" can be emitted in the same channel?

**Answer:** NOT FOUND — no cost or token logging is emitted. `ExecutionResult` has a `tokens: dict` field, but `execute_single` hard-codes `result.tokens = {"input": 0, "output": 0}` (a stub placeholder; the real `response.usage` is commented out, run_eval.py:128). Nothing reads or aggregates `tokens` afterward; grade.py/report.py never touch token or cost data. The only output "channel" is **`print()` to stdout** — run_eval.py prints per-execution `[n/total] case trial STATUS (durationms)` (line 187) and a results-path line; grade.py prints train/test scores (lines 367-370); report.py prints a summary block. There is no logging module, no structured metrics file for cost, and no `$`/price computation anywhere.

**Evidence:**

```python
result.tokens = {"input": 0, "output": 0}   # stub; real: response.usage
```

— `scripts/run_eval.py:135` (and commented `result.tokens = response.usage`, line 128)

```python
print(f"Train score: {train_scores['mean']:.4f} (+/- {train_scores['stddev']:.4f})")
```

— `scripts/grade.py:367` (stdout is the sole reporting channel)

**Dependencies:** run_eval.py captures `tokens` per result; grade.py/report.py ignore them.
**Implicit contracts:** Reporting convention is plain `print()` to stdout (no `logging` module configured anywhere in scripts). "Cost per full suite run" would have to be summed from per-call token counts and printed in the same stdout style (e.g., alongside grade.py's score lines), since that is the only existing channel.

---

## Discovered Patterns

- **The entire eval pipeline is intentionally stubbed.** `run_eval.execute_single`, `grade.run_llm_judge`, `grade.run_script_check`, `diagnose.categorize_failure`, and `revise.propose_revisions` all return placeholders with docstrings describing the "real implementation." CLAUDE.md confirms: "evals/ + scripts/run_eval.py harness is a non-functional placeholder." `run_llm_judge` is one of several parallel stubs, not an isolated gap.
- **`passed: None` is the codebase's "not evaluated" sentinel** — used by unknown programmatic checks (grade.py:196), the script stub (239), and the judge stub (223). score_case treats it as a zero, diagnose treats it as a non-failure.
- **JSON + `indent=2` + full-file overwrite** is the universal serialization convention; no locking, no atomic writes (in the eval scripts). The qrspi_*.py orchestration scripts separately use a staging+move pattern (`qrspi_persist.py`) but the eval scripts do not.
- **Hashing precedent:** `hashlib.sha256(text.encode()).hexdigest()[:12]` (run_eval.py:155) for the skill version — the only existing hash idiom, reusable for a judge cache key.
- **Test convention:** stdlib-only, `assert`-based, no pytest, self-locating repo root from `__file__`, runnable via `python3 scripts/<name>_test.py`, exit 0/1. CLAUDE.md mandates `_test.py` siblings.
- **Reporting channel is stdout `print()` only** — no `logging`, no metrics sink, no cost accounting.
- **Stub model-call pseudocode uses a `.complete(system=..., messages=[...])` shape** in 3 files (grade.py:213, diagnose.py:64, revise.py:34) — a hypothetical client interface, NOT the actual Anthropic SDK (`messages.create`) signature.

## Inconsistencies

- **`passed: None` is scored two contradictory ways.** `score_case` (grade.py:251-257) counts a `None`/`None` judge result as a guaranteed **zero** against full weight, but `extract_failures` (diagnose.py:38) excludes `passed is None` from failures entirely. Net effect: every llm_judge assertion (34.4% of suite weight) silently caps achievable scores at ~0.66 yet never appears as a diagnosable failure — the score depression has no diagnostic trail.
- **`score` is never range-validated, and the normalization math is unguarded.** `weight*(score-1)/4` (grade.py:257) assumes `score ∈ [1,5]`; an out-of-range judge score produces negative or >weight contributions with no clamp — a real judge must validate before returning.
- **Docstring model-call signature vs. real SDK.** The illustrative `judge_model.complete(system=, messages=)` (grade.py:213-216) does not match the Anthropic Python SDK (`client.messages.create(model=, max_tokens=, system=, messages=)`). The docstring is aspirational and should not be copied verbatim.
- **`--timeout`/`timeout_ms` is plumbed but unenforced** (run_eval.py:39,224 vs. the stub `execute_single` which ignores it) — a latent contract that callers may assume holds but does not.
- **`.env` exists at repo root but is empty AND not gitignored** (`.gitignore:1-5` lists `.qrspi/config.json` but not `.env`). If a judge integration sources `ANTHROPIC_API_KEY` from `.env`, the file must be added to `.gitignore` to avoid committing a secret.
- **No dependency manifest** despite multiple scripts being slated to call external services (per their docstrings). Adding the Anthropic SDK would be the first runtime third-party dependency and require creating a manifest, breaking the current stdlib-only invariant.
