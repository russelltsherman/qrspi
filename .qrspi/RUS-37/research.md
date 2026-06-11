# Research — Codebase Map

**Questions source:** .qrspi/RUS-37/questions.md
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

> Scope: all citations are relative to `REPO_ROOT` = `/workspaces/qrspi/.worktrees/RUS-37`.
> The grading module is `scripts/grade.py` (387 lines); the eval suite is `evals/suite.json` (15 cases).

## Q1: How does `scripts/grade.py` load and parse `evals/suite.json`, and at what point are the per-case check names extracted and matched against the `CHECKS` registry?

**Answer:** `grade_results()` opens both `results.json` and the suite with `json.load`, indexes cases by `id` into `cases_by_id`, and groups results by `case_id`. For each trial it iterates `case["assertions"]` and dispatches by `assertion["type"]`. Only `type == "programmatic"` assertions reach the registry: `run_programmatic_check` calls `parse_check_call(assertion["check"])` to split the check string into a function name + arg list, then looks the name up in `CHECKS`. So check-name → registry matching happens per-assertion, per-trial, inside `run_programmatic_check`, at the moment the assertion is graded — not at load time. There is no upfront validation that every referenced check name exists.

**Evidence:**

```python
def grade_results(results_path, suite_path, output_dir=None):
    with open(results_path) as f: results_data = json.load(f)
    with open(suite_path) as f: suite = json.load(f)
    cases_by_id = {c["id"]: c for c in suite["cases"]}
    ...
    for assertion in assertions:
        atype = assertion.get("type", "")
        if atype == "programmatic":
            ar = run_programmatic_check(assertion, trial_result)
```

— `scripts/grade.py:282-311`

```python
def run_programmatic_check(assertion, result):
    check_str = assertion["check"]
    func_name, args = parse_check_call(check_str)
    if func_name in CHECKS:
        ...
    else:
        passed = None
        evidence = f"Unknown check function: {func_name}"
```

— `scripts/grade.py:177-197`

**Dependencies:** Upstream: `evals/suite.json` (case/assertion schema), `results.json` (produced by `scripts/run_eval.py`). Downstream: `CHECKS` registry, `parse_check_call`, `score_case`.
**Implicit contracts:** Every suite case must have an `id`; every result row must have a `case_id`; assertions must carry a `type`. A check name absent from `CHECKS` is silently downgraded to `passed: None` rather than erroring.

## Q2: What is the shape of the `results.json` input that check functions receive — what fields (artifact content, paths, metadata) does each check function read from a result entry?

**Answer:** `results.json` is `{ "skill_hash", "skill_path", "suite", "timestamp", "config", "results": [...] }`. Each element of `results` is the `asdict()` of `ExecutionResult` (defined in `run_eval.py`): `case_id`, `trial_id`, `output` (str — the agent's produced artifact text), `files` (list — output filenames), `duration_ms`, `tokens`, `tool_calls`, `transcript`, `error`. Check functions read almost exclusively two fields: `result.get("output", "")` (the artifact body, regex-scanned) and `result.get("files", [])` (used only by `output_file_exists`). The `filename` argument passed to checks is **not** used to select content — every check operates on the single `output` blob regardless of which artifact name the suite names. Trial identity comes from `result.get("trial_id", 0)`.

**Evidence:**

```python
@dataclass
class ExecutionResult:
    case_id: str
    trial_id: int
    output: str = ""
    files: list = field(default_factory=list)
    duration_ms: float = 0.0
    tokens: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
    error: Optional[str] = None
```

— `scripts/run_eval.py:19-29`

```python
def output_file_exists(filename, result):
    exists = filename in result.get("files", [])
    ...
def has_section(filename, heading, result):
    output = result.get("output", "")
```

— `scripts/grade.py:21-32`

**Dependencies:** Result shape is owned by `run_eval.py:ExecutionResult` + the `output` envelope at `run_eval.py:197-207`. Checks depend on `output`/`files` keys existing.
**Implicit contracts:** Every check signature ends with a trailing `result: dict` parameter. Content lives in `result["output"]`; the `filename` arg is decorative (no per-artifact file dispatch exists — see Q8). Missing `output`/`files` default to `""`/`[]`, so checks tolerate absent keys without KeyError.

## Q3: What is the exact structure of a case entry in `evals/suite.json` — how are check names declared per case, and do any checks take parameters or thresholds (e.g. minimum counts, file limits) alongside the name?

**Answer:** A case is an object with `id`, `name`, `phase`, `prompt`, `context` (`files`/`conversation_history`/`user_preferences`), `assertions`, `tags`, `difficulty`, `split`. Each assertion is `{ "type": "programmatic"|"llm_judge"|"script", "check"|"criteria": <str>, "weight": <float> }`. For programmatic assertions the `check` value is a **call-expression string**, e.g. `"has_section('design.md', 'Risk Register')"`. Thresholds appear in two forms: (a) as literal arguments inside the parens — `code_snippets_under_limit('research.md', 20)`, `risk_register_min_entries('design.md', 2)`, `no_slice_exceeds_file_limit('structure.md', 10)`, `pr_title_under_limit('pr-summary.md', 72)`, `pattern_decisions_have_options('design.md', 2)`, `section_question_count('questions.md', 'Edge Cases') >= 2`; and (b) as a trailing **comparison operator** appended OUTSIDE the parens — `question_count('questions.md') >= 8`, `question_count('questions.md') <= 15`, `section_count('questions.md', '## ') >= 5`, `line_count('design.md') <= 300`, `slice_count('structure.md') >= 2/>= 5`, `total_steps('plan.md') <= 100`. See Q6 for how (b) is (not) handled.

**Evidence:**

```json
{ "type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0 },
{ "type": "programmatic", "check": "section_count('questions.md', '## ') >= 5", "weight": 1.0 },
{ "type": "programmatic", "check": "section_question_count('questions.md', 'Edge Cases') >= 2", "weight": 0.5 }
```

— `evals/suite.json:37-41,33-36,62-66`

**Dependencies:** Schema enforced minimally by `run_eval.py:load_suite` (requires `name`,`cases` at top level; `id`,`prompt`,`assertions` per case — `scripts/run_eval.py:42-58`). Nothing validates `check` syntax or threshold semantics.
**Implicit contracts:** `weight` defaults to `1.0` when omitted (`assertion.get("weight", 1.0)`). LLM-judge assertions use key `criteria` not `check`. The comparison-operator form is a convention the parser does not actually understand.

## Q4: What is the common function signature contract for every entry in `CHECKS`, as shown by the 10 currently-registered functions at scripts/grade.py:146-157?

**Answer:** Two coexisting signature shapes:
1. **Boolean/evidence checks** (8 of 10): `def name(filename: str[, ...params], result: dict) -> tuple[bool, str]` — return `(passed, evidence_message)`. The `result` dict is always the LAST positional parameter; any check-specific params (`heading`, `max_lines`, `limit`) sit between `filename` and `result`.
2. **Count checks** (defined but NOT in `CHECKS`): `def name(filename: str, result: dict) -> int` — return a bare integer (`question_count`, `slice_count`, `total_steps`). The dispatcher special-cases non-tuple returns as `passed = True`, `evidence = f"Value: {outcome}"` — i.e. a count check unconditionally "passes" and the integer is never compared to any threshold.

**Evidence:**

```python
def has_section(filename, heading, result) -> tuple[bool, str]:
    ...
    return found, f"Section '{heading}' {'found' if found else 'not found'}"

def question_count(filename, result) -> int:
    questions = re.findall(r"^-\s+Q\d+:", output, re.MULTILINE)
    return len(questions)
```

— `scripts/grade.py:27-32,43-47`

```python
outcome = CHECKS[func_name](*args, result)
if isinstance(outcome, tuple):
    passed, evidence = outcome
else:
    passed = True            # numeric return → always passes
    evidence = f"Value: {outcome}"
```

— `scripts/grade.py:184-190`

**Dependencies:** Dispatcher `run_programmatic_check` is the sole caller; it splats `*args` then appends `result`, so arg ORDER and the trailing-`result` convention are load-bearing.
**Implicit contracts:** New functions MUST accept `result` as the final positional arg and (to be enforceable) return `tuple[bool, str]`. Returning a bare int makes the check a no-op pass. Exceptions raised inside a check are caught and become `passed: False` with `evidence = f"Check error: {e}"` (`scripts/grade.py:191-193`).

## Q5: How is the `CHECKS` mapping keyed and populated — literal dict, decorator-based registry, or another mechanism that each of the 27 new functions must conform to?

**Answer:** `CHECKS` is a plain module-level **literal dict** mapping the check-name string → the function object. No decorators, no auto-registration, no introspection. To register a new check a function must be defined AND manually added as a `"name": func` entry. The key string must exactly equal the function-name token the suite uses (i.e. the `\w+` captured by `parse_check_call`). There are exactly 10 entries today.

**Evidence:**

```python
CHECKS = {
    "output_file_exists": output_file_exists,
    "has_section": has_section,
    "line_count": line_count,
    "no_solution_language": no_solution_language,
    "all_questions_have_target": all_questions_have_target,
    "current_state_has_citations": current_state_has_citations,
    "no_code_blocks": no_code_blocks,
    "all_evidence_has_file_citations": all_evidence_has_file_citations,
    "all_slices_have_verification": all_slices_have_verification,
    "pr_title_under_limit": pr_title_under_limit,
}
```

— `scripts/grade.py:146-157`

**Verified gap (registered vs. referenced):** the suite references **36 distinct** programmatic check names; **10** are registered; **26 are missing** and currently resolve to `passed: None`:
`all_answers_have_evidence`, `all_files_marked_new_or_modify`, `all_modify_steps_have_current_after`, `all_questions_answered`, `all_slices_have_context_cost`, `all_slices_have_verify_checkpoint`, `all_steps_are_atomic`, `all_tasks_have_required_fields`, `code_snippets_under_limit`, `contains_new_pattern_flag`, `contains_not_found`, `has_critical_path`, `impl_log_has_deviations`, `impl_log_has_required_fields`, `no_large_slices_without_justification`, `no_slice_exceeds_file_limit`, `not_found_has_search_description`, `pattern_decisions_have_options`, `question_count`, `risk_register_min_entries`, `section_count`, `section_question_count`, `session_boundaries_have_reasons`, `sessions_have_load_manifests`, `slice_count`, `total_steps`.

Note: `question_count`, `slice_count`, `total_steps` are **defined in the module but absent from `CHECKS`** — so even though their bodies exist, they are unresolved at dispatch and return `passed: None`. The other 23 have no definition at all. (10 registered + 26 missing = 36; the "27 new functions" framing in the questions corresponds to 23 truly-new + 3 define-but-register + a `section_count`/`section_question_count` overlap — the exact count of new bodies depends on whether the 3 already-defined funcs are merely registered or rewritten.)

**Dependencies:** `parse_check_call` (name extraction) and `run_programmatic_check` (lookup). Adding entries is the only conformance step besides matching the Q4 signature.
**Implicit contracts:** Dict-key string is the single source of truth for the name; a typo silently yields `passed: None`.

## Q6: For parameterized checks, where do the limit/threshold values come from — encoded in the name, passed from the suite case, or hard-coded?

**Answer:** Three distinct mechanisms, two of which work and one of which is silently broken:
1. **In-paren literal args (works):** `parse_check_call` extracts single-quoted strings and bare `\d+` integers from inside the parens and splats them ahead of `result`. So `code_snippets_under_limit('research.md', 20)` → `code_snippets_under_limit('research.md', 20, result)` — the `20` reaches the function. Same for `risk_register_min_entries(...,2)`, `no_slice_exceeds_file_limit(...,10)`, `pr_title_under_limit(...,72)`, `pattern_decisions_have_options(...,2)`.
2. **Trailing comparison operator (BROKEN — dropped):** for `question_count('questions.md') >= 8`, `line_count('design.md') <= 300`, `section_count('questions.md','## ') >= 5`, `slice_count(...) >= 2`, `total_steps(...) <= 100`, the `>= 8` / `<= 300` lives OUTSIDE the parens. `parse_check_call`'s regex `(\w+)\((.+)\)` captures only up to the last `)`, so the operator + threshold are discarded. I verified this empirically: `parse_check_call("question_count('questions.md') >= 8")` → `('question_count', ['questions.md'])` — the `8` is gone. Combined with Q4, a count check then returns a bare int → `passed: True` unconditionally, so the `>= 8` threshold is NEVER enforced.
3. **Hard-coded:** none of the registered checks hard-code thresholds; `line_count`'s `max_lines` is a parameter (but, per #2, the suite passes it via the broken trailing form, so it too is unused — `line_count` is registered yet receives no `max_lines` and would raise → caught as `passed: False`).

**Evidence:**

```python
def parse_check_call(check_str):
    match = re.match(r"(\w+)\((.+)\)", check_str)   # nothing after ) is captured
    ...
    for arg in re.findall(r"'([^']*)'|(\d+)", args_str):
        if arg[0]: args.append(arg[0])
        elif arg[1]: args.append(int(arg[1]))
    return func_name, args
```

— `scripts/grade.py:160-174`

Empirical (run against the live function): `"line_count('design.md') <= 300"` → `('line_count', ['design.md'])` — `300` dropped; `line_count(filename, max_lines, result)` then called as `line_count('design.md', result)` → `TypeError` → caught → `passed: False`.

**Dependencies:** `parse_check_call` ↔ suite check-string convention. The two conventions (in-paren vs trailing-operator) are mutually inconsistent.
**Implicit contracts:** Only in-paren string/int literals survive parsing. Any threshold expressed as a trailing `>=`/`<=` is silently lost. New count-style checks must take their threshold as an IN-PAREN argument and compare internally (returning `tuple[bool,str]`) to be enforceable.

## Q7: How does the grader accumulate numerator/denominator for a case score, and how does a check returning `passed: None` feed into that aggregation?

**Answer:** `score_case(assertion_results)` sums `weight` into `max_score` (denominator) for EVERY assertion result, then adds `weight` to `actual_score` (numerator) only when `passed is True`, or `weight * (score-1)/4` for an LLM-judge with a numeric `score`. A result with `passed is None` (unknown check or un-integrated judge/script) still contributes its `weight` to `max_score` but **0** to `actual_score`. Net effect: an unresolved check **silently lowers the case score** exactly as a failing check would — it is indistinguishable from a real failure in the numerator/denominator, only in the per-assertion `evidence` string does it differ ("Unknown check function: X").

**Evidence:**

```python
def score_case(assertion_results):
    max_score = 0.0; actual_score = 0.0
    for ar in assertion_results:
        weight = ar.get("weight", 1.0)
        max_score += weight
        if ar.get("passed") is True:
            actual_score += weight
        elif ar.get("score") is not None:
            actual_score += weight * (ar["score"] - 1) / 4
    normalized = actual_score / max_score if max_score > 0 else 0.0
```

— `scripts/grade.py:246-259`

**Dependencies:** Upstream `run_programmatic_check`/`run_llm_judge`/`run_script_check` set `passed`/`score`. Downstream `grade_results` aggregates `score_case` outputs across trials via `statistics.mean`/`stdev` (`scripts/grade.py:321-336`) and across cases via `score_suite` (`scripts/grade.py:268-277`).
**Implicit contracts:** `passed is True` is the only positive path (strict `is True`, so a truthy-but-non-True value would NOT score). `None` counts against the denominator → registering the 26 missing checks will MOVE scores (mostly upward where artifacts comply), which is exactly what the acceptance criteria must assert. `max_score == 0` guards division-by-zero → score 0.0.

## Q8: Which artifact types do the check-name prefixes correspond to, and how does the grader determine which artifact a given check reads?

**Answer:** Prefixes map by CONVENTION to the seven QRSPI artifacts named in the suite's `filename` arg: `questions.md` (questions phase), `research.md` (research), `design.md` (design), `structure.md` (structure), `plan.md` (plan), `worktree.md` (worktree), `impl-log.md`/`pr-summary.md` (implement/pr). BUT the grader does **NOT** use the artifact name to select content. The `filename` argument is passed into every check yet only `output_file_exists` reads it (to test membership in `result["files"]`); all other checks regex-scan the single `result["output"]` blob. There is no map from artifact name → file content, and `results.json` carries one `output` string per trial, not per-artifact. So "which artifact a check reads" is effectively "always the trial's single `output`", and the prefix is purely documentary.

**Evidence:**

```python
def has_section(filename, heading, result):
    output = result.get("output", "")    # filename ignored for content
    pattern = rf"^#+\s+.*{re.escape(heading)}"
```

— `scripts/grade.py:27-31`

Suite cases are tagged with `"phase"` (e.g. `"phase": "research"`) — the closest thing to an artifact selector — but `grade.py` never reads `case["phase"]`; it only reads `assertions`, `split`, `tags`, `difficulty`, `id` (`scripts/grade.py:300-332`).

**Dependencies:** `evals/suite.json` `phase`/`filename` conventions; `run_eval.py` produces the single-`output` envelope.
**Implicit contracts:** New checks receive `filename` but should treat `result["output"]` as the content. If a future requirement is "read a SPECIFIC artifact", that capability does not exist today and would be a new contract.

## Q9: What does `grade.py` do when a check name has no matching function — where is `passed: None` produced, and is any warning/error surfaced?

**Answer:** Produced in the `else` branch of `run_programmatic_check`: when `func_name not in CHECKS`, it sets `passed = None`, `evidence = f"Unknown check function: {func_name}"`. The only "surfacing" is that string embedded in the per-assertion result inside `grades.json`. There is NO stdout warning, NO log, NO non-zero exit, NO aggregate "N checks unresolved" report. The CLI prints only train/test scores and the grades path (`scripts/grade.py:367-370`). An operator reading the summary cannot tell that 26 of 36 checks never ran — the score just looks low. (See Q14.)

**Evidence:**

```python
    else:
        # Unknown check — skip with warning
        passed = None
        evidence = f"Unknown check function: {func_name}"
    return {"check": check_str, "type": "programmatic",
            "passed": passed, "evidence": evidence,
            "weight": assertion.get("weight", 1.0)}
```

— `scripts/grade.py:194-205`

**Dependencies:** None beyond `CHECKS`. The comment says "skip with warning" but no warning is emitted (see Inconsistencies).
**Implicit contracts:** `passed: None` is the canonical "did not run" sentinel, shared with un-integrated `llm_judge`/`script` checks (`scripts/grade.py:222,238`). Score aggregation treats it as zero-credit (Q7).

## Q10: How is a missing/empty/malformed artifact handled by existing check functions — raise, return False, or None — and what must the 27 new checks match for absent content?

**Answer:** Existing checks NEVER raise on absent content; they degrade to `False` (a clean, scored fail). They read `result.get("output", "")` → `""` when the key is missing, then regex over the empty string. Patterns that require a positive match (`has_section`, `current_state_has_citations`, `all_evidence_has_file_citations`, `pr_title_under_limit`) return `False`/`(False, ...)`; absence-asserting checks (`no_solution_language`, `no_code_blocks`) return `True` on empty input (nothing banned found). `current_state_has_citations` and `all_evidence_has_file_citations` explicitly guard the no-match case and return `(False, "... not found")`. A genuine exception inside a check is the dispatcher's safety net: caught at `scripts/grade.py:191-193` → `passed: False`, `evidence: "Check error: {e}"`. So the contract the 26 new checks must match: **read `result.get("output","")`, never KeyError, return `(False, msg)` for absent/insufficient target content (or `(True, msg)` only if the check is a negative/absence assertion), and let unexpected errors propagate to the dispatcher's `try/except`.**

**Evidence:**

```python
def current_state_has_citations(filename, result):
    output = result.get("output", "")
    match = re.search(r"## Current State\s*\n(.*?)(?=\n## |\Z)", output, re.DOTALL)
    if not match:
        return False, "Current State section not found"
```

— `scripts/grade.py:75-84`

```python
except Exception as e:
    passed = False
    evidence = f"Check error: {e}"
```

— `scripts/grade.py:191-193`

**Dependencies:** `result["output"]` default-empty behavior. Dispatcher try/except.
**Implicit contracts:** No check distinguishes "artifact missing" from "artifact present but non-compliant" — both are `False`. New checks should preserve that (empty output → fail for positive checks, pass for negative checks).

## Q11: For count-based checks, how are items located and counted, and what happens for boundary inputs (zero items, duplicates)?

**Answer:** All count checks are `re.findall(pattern, output, re.MULTILINE)` followed by `len(...)`. The anchored patterns:
- `question_count`: `^-\s+Q\d+:` — counts top-level `- QN:` list items (matches the questions.md template's `- Q1: ...` form).
- `slice_count`: `^## Slice \d+` — counts `## Slice N` headings (matches structure.md `## Slice 1:`).
- `total_steps`: `^\d+\.\s+` — counts numbered-list lines `N. ` (matches plan.md ordered steps).

Boundary behavior: zero matches → `len == 0`, returned as the int → dispatcher makes it `passed: True` (the threshold from the suite is dropped, Q6), so **a count of 0 still "passes"** today. Duplicates: the regex counts raw line occurrences, so the plan.md template's literal duplicated step numbers (it repeats `2.` — see `plan.md` template lines `2. ⚠️ Modify`, `2. ⚠️ <action>`, `2. Run:`) are each counted independently; `re.findall` does not dedupe, and numbering correctness is not validated. `question_count` requires the EXACT `- Q\d+:` prefix — a `* Q1:` or indented variant would not match.

**Evidence:**

```python
def question_count(filename, result):
    return len(re.findall(r"^-\s+Q\d+:", result.get("output",""), re.MULTILINE))
def slice_count(filename, result):
    return len(re.findall(r"^## Slice \d+", result.get("output",""), re.MULTILINE))
def total_steps(filename, result):
    return len(re.findall(r"^\d+\.\s+", result.get("output",""), re.MULTILINE))
```

— `scripts/grade.py:43-47,110-114,126-130`

Template grounding: questions.md uses `- Q1: <question>` (`.qrspi/templates/questions.md:9`); structure.md uses `## Slice 1: <Name>` (`.qrspi/templates/structure.md:19,31`); plan.md uses ordered `1.`/`2.` lists with duplicated numbers (`.qrspi/templates/plan.md` Setup/Core Logic/Tests blocks).
**Dependencies:** Template markdown conventions in `.qrspi/templates/`. Suite thresholds (currently inert).
**Implicit contracts:** Counting is line-pattern based, MULTILINE-anchored, no dedupe, no threshold comparison. To make count checks enforce minimums/maximums the new design must move the threshold into an in-paren arg and return `tuple[bool,str]` (Q4/Q6).

## Q12: What testing conventions do existing `scripts/*_test.py` siblings follow that the new test for grade.py must adopt?

**Answer:** Conventions, from `qrspi_persist_test.py` and the 10 other `_test.py` siblings: (1) **stdlib-only** — `import unittest`, `tempfile`, `os`, `json`; no pytest, no third-party deps. (2) Shebang `#!/usr/bin/env python3` and a module docstring naming the run command, e.g. `"Run: python3 scripts/qrspi_persist_test.py"`. (3) The module under test is imported **by bare module name** (`import qrspi_persist as qp`) — the test relies on being run with `scripts/` on `sys.path` (i.e. invoked from inside `scripts/` or with that dir on the path), NOT `from scripts.x import`. (4) `unittest.TestCase` subclasses grouped by concern; `setUp`/`tearDown` use `tempfile.TemporaryDirectory()`. (5) Fixtures are constructed inline (write small files to the temp dir), no external fixture files. (6) `if __name__ == "__main__": unittest.main()` footer. NOTE the questions file names the target `scripts/test_grade.py`; the established repo convention is the `_test.py` SUFFIX (`grade_test.py`), not the `test_` prefix — every existing sibling uses the suffix. This is a naming discrepancy the design phase must resolve.

**Evidence:**

```python
#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_persist.py. Run: python3 scripts/qrspi_persist_test.py"""
import os, tempfile, unittest
import qrspi_persist as qp
...
if __name__ == "__main__":
    unittest.main()
```

— `scripts/qrspi_persist_test.py:1-8,89-90`

Sibling inventory (suffix convention, all stdlib): `qrspi_cleanup_test.py`, `qrspi_clear_stale_pr_test.py`, `qrspi_persist_test.py`, `qrspi_pr_body_test.py`, `qrspi_pr_state_test.py`, `qrspi_resolve_state_test.py`, `qrspi_resolve_test.py`, `qrspi_restack_test.py`, `qrspi_revise_amend_test.py`, `using_claude_cli_skill_test.py` (`scripts/` listing).
**Dependencies:** Tests import the SUT module by name → require `scripts/` on path at run time. `grade.py` exposes top-level functions (`parse_check_call`, `run_programmatic_check`, `score_case`, `grade_results`, `CHECKS`) that are directly unit-testable without the CLI.
**Implicit contracts:** No network, no fixtures-on-disk beyond temp dirs, `python3 scripts/<name>_test.py` is the runner. New tests should target check functions individually (pass a hand-built `result` dict) and the dispatcher path.

## Q13: What does a stub `results.json` with known outputs look like, and how must `grade.py` be invoked to assert expected scores?

**Answer:** No `results.json` fixture exists in the repo (searched `find . -name "results*.json"` → none; `evals/golden/` is empty; `evals/fixtures/` holds only 4 `ticket_*.md` files). The shape a stub must satisfy is the `run_eval.py` envelope (Q2): top-level `{ "skill_hash", "timestamp", "results": [ {case_id, trial_id, output, files, ...}, ... ] }`. `grade.py` consumes it via either (a) the CLI `python3 scripts/grade.py --results <results.json> --suite evals/suite.json [--output <dir>]`, which writes `grades.json` and prints train/test scores; or (b) for unit tests, by calling `grade_results(results_path, suite_path, output_dir)` directly, or testing individual checks with a synthetic `result = {"output": "...", "files": [...]}`. To assert a known score: build a `result["output"]` that deterministically passes/fails specific checks, run the assertion through `run_programmatic_check`/`score_case`, and assert `score_case(...)["score"]`. Because thresholds in the suite are currently dropped (Q6), end-to-end suite scoring is not a reliable oracle until the new design fixes parsing — unit-level assertions on individual checks are the dependable path.

**Evidence:**

```python
def grade_results(results_path, suite_path, output_dir=None):
    with open(results_path) as f: results_data = json.load(f)
    ...
    cases_by_id = {c["id"]: c for c in suite["cases"]}
    for r in results_data.get("results", []):
        cid = r["case_id"]
```

— `scripts/grade.py:282-296`

```python
parser.add_argument("--results", required=True)
parser.add_argument("--suite", required=True)
parser.add_argument("--output", help="Output directory (default: same as results)")
```

— `scripts/grade.py:377-379`

CLI default output dir = `os.path.dirname(results_path)`; writes `<dir>/grades.json` (`scripts/grade.py:362-365`).
**Dependencies:** `evals/suite.json` is the only on-disk suite. `evals/fixtures/` (4 ticket md files), `evals/golden/` (empty). No results fixture → the design phase must author one.
**Implicit contracts:** Each result row REQUIRES `case_id` (used as dict key at `scripts/grade.py:295` — `r["case_id"]` is a hard subscript, not `.get`, so a row missing it KeyErrors). `trial_id` defaults to 0. Cases with no matching results are simply absent from output.

## Q14: Does `grade.py` emit any log/warning/summary reporting which check names were unresolved or returned None, and where is that reporting (or its absence)?

**Answer:** No. The only stdout is four `print` lines in `grade_results` at the end: train score, test score, train-test gap, grades path. There is no aggregate count of unresolved checks, no warning per unknown check, no `logging` import, no stderr output. The per-assertion `evidence: "Unknown check function: X"` and `passed: None` are written into `grades.json` only; nothing summarizes them. So today, after registering or before registering checks, an operator cannot see from the console how many checks ran vs. were skipped — the absence is at the end of `grade_results` (`scripts/grade.py:367-370`) where a summary would naturally live.

**Evidence:**

```python
print(f"Train score: {train_scores['mean']:.4f} (+/- {train_scores['stddev']:.4f})")
print(f"Test score:  {test_scores['mean']:.4f} (+/- {test_scores['stddev']:.4f})")
print(f"Train-test gap: {output['train_test_gap']:.4f}")
print(f"Grades written to {grades_path}")
```

— `scripts/grade.py:367-370`

`grep` for `logging`/`warn`/`stderr` in `grade.py` → none. `import` block (`scripts/grade.py:9-16`) has no `logging` or `sys`.
**Dependencies:** None. Reporting would consume `assertion_results` entries where `passed is None`.
**Implicit contracts:** `grades.json` is the machine-readable record; console output is a 4-line human summary. Any new "unresolved checks" surfacing is a NEW behavior not present today.

---

## Discovered Patterns

- **Trailing-`result` signature convention:** every check function takes `result: dict` as its LAST positional parameter; the dispatcher splats parsed args then appends `result` (`scripts/grade.py:184`). This is the single most load-bearing contract for new checks.
- **`passed` tri-state:** `True` (scored), `False` (failed, scored zero), `None` (did not run — unknown check, un-integrated judge/script). Aggregation (`score_case`) credits only strict `passed is True`; `None` and `False` are numerically identical (zero credit) but semantically distinct in `evidence`.
- **Single-blob content model:** the whole grader operates on one `result["output"]` string per trial via regex. There is no per-artifact file loading; the `filename` arg is documentary except in `output_file_exists`.
- **Markdown-shape-coupled regexes:** checks are tightly coupled to the exact markdown produced by `.qrspi/templates/*` (e.g. `^- Q\d+:`, `^## Slice \d+`, `**Target:**`, `(ref: QN)`, `**Evidence:**`). New checks for `risk_register`, `pattern_decisions`, `impl_log`, `worktree` must mirror the corresponding template's literal markers (Risk Register table, Pattern Decisions `| Option |` table, impl-log `**Deviations from ...:**`, worktree `**Critical path:**`/`--- SESSION BOUNDARY ---`/`**Load:**`).
- **Stdlib-only, name-import, suffix-named tests:** all 11 `_test.py` siblings are dependency-free `unittest` modules imported by bare module name, run as `python3 scripts/<name>_test.py`.
- **Defensive `.get` with defaults everywhere** except `r["case_id"]` (`scripts/grade.py:295`) which is a hard subscript.

## Inconsistencies

- **"skip with warning" but no warning:** `scripts/grade.py:194` comment says "Unknown check — skip with warning" yet no warning is emitted anywhere (Q9/Q14). The behavior is silent.
- **Two contradictory threshold conventions in the suite:** in-paren literals (`code_snippets_under_limit('research.md', 20)`) DO reach functions, but trailing comparison operators (`question_count('questions.md') >= 8`, `line_count('design.md') <= 300`) are silently DROPPED by `parse_check_call`'s `(\w+)\((.+)\)` regex (verified empirically). Any threshold expressed as a trailing operator is currently dead.
- **Count checks are inert passes:** `question_count`/`slice_count`/`total_steps` return bare ints → dispatcher forces `passed: True` regardless of value, so `>= 8` / `>= 5` / `<= 100` minimums/maximums are never enforced — AND these three are not even in `CHECKS`, so they actually resolve to `passed: None` today (double broken: unregistered now, and would be a no-op pass if naively registered).
- **`line_count` is registered but its suite usage is broken:** `line_count(filename, max_lines, result)` requires `max_lines`, but the suite passes it via the trailing form `line_count('design.md') <= 300`, so `300` is dropped and the call becomes `line_count('design.md', result)` → `TypeError` → caught → `passed: False`. A registered check that always fails on its real suite invocation.
- **Test-file naming clash:** questions.md (Q12) names the new test `scripts/test_grade.py`, but every existing sibling uses the `_test.py` SUFFIX (`grade_test.py`). The repo convention and the questions disagree.
- **CLAUDE.md calls the eval harness a "non-functional placeholder"** ("The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder"), consistent with the missing 26 checks, dropped thresholds, and stubbed `run_llm_judge`/`run_script_check` (`scripts/grade.py:208-241`, both return `passed: None`).
- **No results fixture / empty golden dir:** `evals/golden/` is empty and no `results.json` exists, yet the acceptance criteria (per Q13) imply asserting expected scores against known outputs — the fixture must be authored.
