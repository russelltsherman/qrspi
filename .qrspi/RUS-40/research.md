# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Q1: What inputs does `categorize_failure` currently receive, and in what shape are the failure transcripts passed in (file paths, in-memory objects, or raw strings)?

**Answer:** `categorize_failure(failure, skill_text)` takes two in-memory arguments: `failure` is a `dict` and `skill_text` is a `str`. There are no transcripts of any kind passed in. The `failure` dict is built by `extract_failures` from a loaded `grades.json` and contains `case_id`, `score` (= `mean_score`), `variance`, `tags`, `difficulty`, and `failed_assertions` (a list of `{check, type, evidence, weight}`). It never receives the raw agent output/transcript — only the per-assertion `evidence` string lifted from the first trial. `skill_text` is the full skill prompt file read via `open(skill_path).read()` in `produce_diagnosis`.

**Evidence:**

```python
def extract_failures(grades: dict) -> list:
    failures = []
    for case in grades.get("cases", []):
        if case["mean_score"] >= 0.9:
            continue
        failed_assertions = []
        if case.get("trials"):
            for assertion in case["trials"][0].get("assertions", []):
                if assertion.get("passed") is False:
                    failed_assertions.append({
                        "check": assertion["check"], "type": assertion["type"],
                        "evidence": assertion.get("evidence", ""),
                        "weight": assertion.get("weight", 1.0)})
        failures.append({"case_id": case["case_id"], "score": case["mean_score"],
            "variance": case.get("stddev", 0), "tags": case.get("tags", []),
            "difficulty": case.get("difficulty", "unknown"),
            "failed_assertions": failed_assertions})
    return sorted(failures, key=lambda f: f["score"])
```

— `scripts/diagnose.py:27-55`
**Dependencies:** Upstream: `scripts/grade.py` writes `grades.json` (the `cases[].trials[].assertions[]` shape). `produce_diagnosis` (diagnose.py:106-167) reads `grades.json` + skill file and calls `extract_failures` then `categorize_failure` per failure.
**Implicit contracts:** Each grade case MUST have `case_id`, `mean_score`; assertions are read only from `trials[0]`. Failure threshold is hard-coded `mean_score >= 0.9` (diagnose.py:31) — a case above 0.9 is never categorized regardless of the loop's `TARGET_SCORE`.

## Q2: How does `propose_revisions` obtain the skill/prompt text and the diagnosis it operates on — are they passed as arguments, read from disk, or pulled from a shared state object?

**Answer:** Both are passed as in-memory arguments: `propose_revisions(skill_text: str, diagnosis: dict) -> list`. The caller `revise_skill` (revise.py:125-184) is responsible for the disk reads: `load_skill(skill_path)` (`open().read()`, returns str) and `load_diagnosis(diagnosis_path)` (`json.load`, returns dict). `propose_revisions` itself touches no disk and no shared/global state — it only iterates `diagnosis["recommendations"]`. Notably `skill_text` is passed in but used **only** for risk assessment (`_assess_risk`), never to locate edit anchors.

**Evidence:**

```python
def propose_revisions(skill_text: str, diagnosis: dict) -> list:
    revisions = []
    for rec in diagnosis.get("recommendations", []):
        category = rec["category"]
        if category in ("MODEL_LIMITATION", "EVAL_ISSUE"):
            continue
        revision = {"id": f"rev_{len(revisions) + 1}", "category": category,
            "affected_cases": rec["affected_cases"], "action": rec["suggested_action"],
            "edit": {"type": "pending_meta_agent",
                "description": (f"Meta-agent should propose a specific edit to address "
                    f"{category} affecting cases: {', '.join(rec['affected_cases'])}"),
                "old_text": None, "new_text": None},
            "regression_risk": _assess_risk(category, len(rec["affected_cases"]), skill_text)}
        revisions.append(revision)
    return revisions
```

— `scripts/revise.py:26-72`
**Dependencies:** Consumes the `recommendations` list produced by `produce_diagnosis` (diagnose.py:134-141), each rec = `{category, description, affected_cases, suggested_action}`.
**Implicit contracts:** Every recommendation MUST carry `category`, `affected_cases`, `suggested_action`. Categories `MODEL_LIMITATION`/`EVAL_ISSUE` are silently dropped (revise.py:51-52). No edit is ever produced — `old_text`/`new_text` are hard-coded `None`.

## Q3: How does `run_loop.sh` chain the score → diagnose → revise → re-score steps, and where in that pipeline are diagnosis output and revision output handed between stages?

**Answer:** `run_loop.sh` runs a `for i in seq 1..MAX_ITER` loop. Per iteration `VERSION=v{i}`, `OUTPUT_DIR=results/v{i}`. Steps: [1] `run_eval.py` → `OUTPUT_DIR/results.json`; [2] `grade.py --results ...results.json` → `grades.json`; [3] read `test_score` from `grades.json` via inline python — if `>= TARGET_SCORE` break; else compute regression vs `PREVIOUS_SCORE`; [4] `diagnose.py --grades grades.json --skill SKILL_PATH --output OUTPUT_DIR/diagnosis.json`, then `revise.py --skill SKILL_PATH --diagnosis OUTPUT_DIR/diagnosis.json --output SKILL_PATH`. The hand-offs are **files on disk**: diagnose reads `grades.json` + writes `diagnosis.json`; revise reads that `diagnosis.json` and writes back **in place to `SKILL_PATH`** (output == input path). After the loop, `report.py --results-dir results/ --output results/report.json`.

**Evidence:**

```bash
echo "[3/4] Diagnosing failures..."
python3 scripts/diagnose.py --grades "${OUTPUT_DIR}/grades.json" \
    --skill "$SKILL_PATH" --output "${OUTPUT_DIR}/diagnosis.json"
echo "[4/4] Proposing revisions..."
python3 scripts/revise.py --skill "$SKILL_PATH" \
    --diagnosis "${OUTPUT_DIR}/diagnosis.json" --output "$SKILL_PATH"
PREVIOUS_SCORE=$SCORE
```

— `run_loop.sh:95-109`
**Dependencies:** Orchestrates `run_eval.py`, `grade.py`, `diagnose.py`, `revise.py`, `report.py`. `set -euo pipefail` (line 2) means any non-zero exit aborts the whole loop.
**Implicit contracts:** Scoring uses `test_score` (run_loop.sh:59-64), but the regression-guard in step 3 and report use the same; CLI flag names (`--grades/--skill/--output/--diagnosis`) must match each script's argparse. `revise.py` writing to `SKILL_PATH` is how a revision feeds the next iteration.

## Q4: What is the exact signature and return contract of `categorize_failure` and `propose_revisions` today, and what fields does each return value contain?

**Answer:**
- `categorize_failure(failure: dict, skill_text: str) -> dict` returns `{case_id, score, categories (list[str], deduped, order-preserved), failed_assertions, regression_risk}`. `regression_risk` is `"low"` if `difficulty == "hard"` else `"medium"` (note: inverted-looking — see Inconsistencies).
- `propose_revisions(skill_text: str, diagnosis: dict) -> list` returns a list of revision dicts, each `{id ("rev_N"), category, affected_cases, action, edit: {type:"pending_meta_agent", description, old_text:None, new_text:None}, regression_risk}`.

**Evidence:**

```python
    return {"case_id": failure["case_id"], "score": failure["score"],
        "categories": unique, "failed_assertions": failure["failed_assertions"],
        "regression_risk": "low" if failure["difficulty"] == "hard" else "medium"}
```

— `scripts/diagnose.py:97-103`
**Dependencies:** `produce_diagnosis` consumes `categorize_failure`'s return to build `recommendations` and `non_prompt_issues`. `revise_skill`/`apply_revisions` consume `propose_revisions`' return.
**Implicit contracts:** `categorize_failure` always returns ≥0 categories; with no `failed_assertions` it returns an empty `categories` list. `propose_revisions` never emits a concrete edit (`old_text`/`new_text` always None), so downstream `apply_revisions` can never apply anything today.

## Q5: What does the pseudocode in the docstrings of `diagnose.py` and `revise.py` specify about the intended meta-agent invocation — what arguments, model, and output format are described?

**Answer:** Both docstrings sketch the same `meta_agent.complete(system=..., messages=[{"role":"user","content":...}])` shape. `diagnose.py` describes `system=DIAGNOSIS_PROMPT` with user content `f"Skill: {skill_text}\nFailure: {json.dumps(failure)}"`. `revise.py` describes `system=REVISION_PROMPT` with user content `f"Skill:\n{skill_text}\n\nDiagnosis:\n{json.dumps(diagnosis)}"`, and states "The meta-agent returns structured edits that are applied as diffs." Neither docstring names a model id, an SDK, or a concrete output schema — `DIAGNOSIS_PROMPT`/`REVISION_PROMPT` and `meta_agent` are referenced but defined nowhere in the repo. No "Opus" string appears in code (only inferred from the ticket-domain term "meta-agent").

**Evidence:**

```python
    In a real implementation, this would use a meta-agent (LLM) to
    analyze the failure transcript against the skill text:
        response = meta_agent.complete(
            system=DIAGNOSIS_PROMPT,
            messages=[{"role": "user",
                "content": f"Skill: {skill_text}\nFailure: {json.dumps(failure)}"}])
    This stub uses heuristics for common patterns.
```

— `scripts/diagnose.py:60-72` (mirror in `scripts/revise.py:32-44`)
**Dependencies:** None wired — purely descriptive docstrings.
**Implicit contracts:** Intended output of revision meta-agent = "structured edits applied as diffs", aligning with `apply_revisions`' `old_text`/`new_text` replace mechanism.

## Q6: How is the meta-agent (Opus) invoked elsewhere in the codebase — is there an existing client, wrapper, or CLI call pattern these two scripts can use?

**Answer:** NOT FOUND — there is no LLM client/wrapper anywhere in the repo. Searched `scripts/` and `run_loop.sh` for `ANTHROPIC_API_KEY`, `import anthropic`, `messages.create`, `class .*Agent`, `def complete`, `claude -p`, `using-claude-cli` — all empty. The only `.complete(` references are the same illustrative docstrings in `diagnose.py`, `revise.py`, and `grade.py:run_llm_judge` (grade.py:213, also a stub returning `passed: None`). The actual agent runtime in `run_eval.py:execute_single` (run_eval.py:93-141) is likewise a stub that sets `output=""`, `tokens={"input":0,"output":0}`. There is a `using-claude-cli` skill available in the environment (a documented way to invoke Claude via CLI) but no code in this repo uses it. Subprocess-based external calls exist only for git/gh/gt in the unrelated `qrspi_*` orchestration scripts.

**Evidence:**

```python
    response = judge_model.complete(
        system="You are grading an AI agent's output...",
        messages=[{"role": "user", "content": grading_prompt}])
    This stub returns a placeholder for integration.
    return {..., "passed": None, "score": None,
        "evidence": "LLM judge not yet integrated — requires model API", ...}
```

— `scripts/grade.py:208-227`
**Dependencies:** None.
**Implicit contracts:** The whole eval pipeline assumes a future `*.complete(system, messages)` style client; no concrete pattern to reuse exists today.

## Q7: What `old_text`/`new_text` edit structure does `apply_revisions` expect, and how does it locate and mechanically apply each edit to the skill text?

**Answer:** `apply_revisions(skill_text: str, revisions: list) -> tuple[str, list]` lives in `scripts/revise.py:75-109`. For each revision it reads `rev["edit"]["old_text"]` and `["new_text"]`. Location is by literal substring match (`old_text in modified`); application is a single non-regex replace: `modified.replace(old_text, new_text, 1)` (first occurrence only). It returns the modified text plus an `applied` log of `{id, status, ...}` entries.

**Evidence:**

```python
def apply_revisions(skill_text: str, revisions: list) -> tuple[str, list]:
    modified = skill_text
    applied = []
    for rev in revisions:
        edit = rev.get("edit", {})
        old_text = edit.get("old_text"); new_text = edit.get("new_text")
        if old_text and new_text and old_text in modified:
            modified = modified.replace(old_text, new_text, 1)
            applied.append({"id": rev["id"], "status": "applied",
                "description": edit.get("description", "")})
        elif old_text and old_text not in modified:
            applied.append({"id": rev["id"], "status": "skipped",
                "reason": "old_text not found in skill"})
        else:
            applied.append({"id": rev["id"], "status": "pending",
                "reason": "No concrete edit — requires meta-agent"})
    return modified, applied
```

— `scripts/revise.py:75-109`
**Dependencies:** Consumes `propose_revisions` output; called by `revise_skill` (revise.py:148).
**Implicit contracts:** Edit anchors are plain strings, not regex/line-numbers. `count=1` replace assumes anchors are intended unique. Since `propose_revisions` always emits `old_text=None`, every revision today falls to the `else` (`status: "pending"`) branch.

## Q8: Where and how is the prompt/skill text persisted between loop iterations so that an applied revision feeds the next scoring run?

**Answer:** The skill is a single file at `SKILL_PATH` (e.g. `.qrspi/agents/01-questions.md`, run_loop.sh:10). `revise.py` is invoked with `--output "$SKILL_PATH"` — i.e. it overwrites the skill file in place. `revise_skill` only writes when `modified_text != skill_text` (revise.py:151-154); otherwise it prints "No concrete edits to apply" and the file is untouched. The next iteration's `run_eval.py` re-reads the same `SKILL_PATH`, so any in-place edit feeds forward. There is also a side-channel `revision-log.json` written next to the output (revise.py:166-181) appending a per-call entry, but that log is not consumed by scoring. No git/version snapshot of the skill is taken — rollback in run_loop.sh is only a commented placeholder.

**Evidence:**

```python
        if modified_text != skill_text:
            with open(output_path, "w") as f:
                f.write(modified_text)
            print(f"Skill updated: {output_path}")
        else:
            print("No concrete edits to apply — revisions require meta-agent integration.")
```

— `scripts/revise.py:151-156`
**Dependencies:** `run_eval.py:load_skill` re-reads `SKILL_PATH` each iteration; `run_eval.py` also hashes the skill (`skill_hash`, run_eval.py:151) so changed text yields a new hash recorded in results/grades.
**Implicit contracts:** In-place overwrite of the live skill file is the persistence mechanism — no backup. `results/v{i}/` directories accumulate per-version grades for `report.py`.

## Q9: How is dry-run mode currently represented or wired in `diagnose.py` and `revise.py`, and what does each script do differently when dry-run is active versus applying changes?

**Answer:** Dry-run exists **only in `revise.py`**. `revise_skill(..., dry_run: bool = False)` and `--dry-run` (store_true) at revise.py:129/192. When `dry_run` is True: it calls `propose_revisions` and returns `{status:"dry_run", revisions, skill_path}` **without** calling `apply_revisions` and **without writing the skill file** (revise.py:141-146); it still writes the `revision-log.json` entry. When False: it calls `apply_revisions`, conditionally writes the skill, and returns `status` `"revised"` or `"pending_meta_agent"`. `diagnose.py` has **no** dry-run concept — it always writes `diagnosis.json` (diagnose.py:156-158). `run_loop.sh` never passes `--dry-run` (run_loop.sh:102-106), so the loop always runs in apply mode.

**Evidence:**

```python
    if dry_run:
        result = {"status": "dry_run", "revisions": revisions, "skill_path": skill_path}
    else:
        modified_text, applied_log = apply_revisions(skill_text, revisions)
        if modified_text != skill_text:
            with open(output_path, "w") as f: f.write(modified_text)
```

— `scripts/revise.py:141-153`
**Dependencies:** CLI `--dry-run` flag (revise.py:192); not invoked by run_loop.sh.
**Implicit contracts:** dry-run still mutates `revision-log.json` (side effect even in "dry" mode — see Inconsistencies).

## Q10: What does `apply_revisions` do when an `old_text` value is not found in the skill text, appears more than once, or overlaps another edit?

**Answer:**
- **Not found:** if `old_text` is truthy but not a substring → appends `{status:"skipped", reason:"old_text not found in skill"}`; text unchanged (revise.py:96-101).
- **Appears more than once:** `replace(old_text, new_text, 1)` replaces only the **first** occurrence; remaining occurrences are silently left. No ambiguity detection or error — it does not check uniqueness (revise.py:90).
- **Overlapping edits:** No handling. Edits are applied sequentially over the accumulating `modified` string; an earlier edit can delete/alter the anchor a later edit expects, which then falls to the "skipped" branch. There is no conflict detection, ordering guarantee, or rollback.

**Evidence:**

```python
        if old_text and new_text and old_text in modified:
            modified = modified.replace(old_text, new_text, 1)
            applied.append({"id": rev["id"], "status": "applied", ...})
        elif old_text and old_text not in modified:
            applied.append({"id": rev["id"], "status": "skipped",
                "reason": "old_text not found in skill"})
```

— `scripts/revise.py:89-101`
**Dependencies:** None beyond the revisions list.
**Implicit contracts:** Caller must supply unique, non-overlapping anchors; the function trusts but does not verify this. `None`/empty `new_text` with a present `old_text` falls to the `else` "pending" branch (no deletion supported).

## Q11: How does `categorize_failure` behave when there are zero failed cases or when a transcript is empty or truncated?

**Answer:**
- **Zero failed cases:** `categorize_failure` is never called — `produce_diagnosis` short-circuits when `extract_failures` returns empty, emitting `{status:"ALL_PASSING", message:"No failures detected — all cases above 0.9 threshold", failures:[], recommendations:[]}` (diagnose.py:118-124).
- **A case with no failed assertions:** `extract_failures` only appends cases with `mean_score < 0.9`, but `failed_assertions` can still be empty if no assertion has `passed is False` (e.g. all assertions are `passed: None`, the LLM-judge stub default). Then `categorize_failure`'s loop body runs zero times and returns `categories: []`.
- **Empty/truncated transcript:** No transcript is consumed at all (see Q1). `extract_failures` reads only `trials[0]["assertions"]`; if `trials` is empty/missing, `failed_assertions` stays `[]` (guarded by `if case.get("trials")`, diagnose.py:36). If a case dict lacks `case_id` or `mean_score`, `extract_failures` raises `KeyError` (direct `case["case_id"]`/`case["mean_score"]`).

**Evidence:**

```python
    failures = extract_failures(grades)
    if not failures:
        diagnosis = {"status": "ALL_PASSING",
            "message": "No failures detected — all cases above 0.9 threshold",
            "failures": [], "recommendations": []}
```

— `scripts/diagnose.py:117-124`
**Dependencies:** Behavior gated on `extract_failures` output and `grades.json` shape.
**Implicit contracts:** "All passing" is defined as every case `>= 0.9` (diagnose.py:31), independent of the loop's `TARGET_SCORE`. Empty `failed_assertions` yields an empty-categories diagnosis (a failure with no categorized cause is possible).

## Q12: What is the current meaning of the `pending_meta_agent` status returned by `propose_revisions`, and which downstream consumers branch on it?

**Answer:** Two distinct uses of the token, neither is a return value of `propose_revisions` itself:
1. `propose_revisions` stamps every edit object with `edit["type"] = "pending_meta_agent"` (revise.py:60) — a marker that the concrete edit has not been generated.
2. `revise_skill` returns top-level `status = "pending_meta_agent"` when `modified_text == skill_text` after `apply_revisions` (revise.py:159), i.e. nothing was applied.

Downstream branching: **`run_loop.sh` does NOT branch on it** — the loop ignores `revise.py`'s exit/status entirely and proceeds to the next iteration regardless (run_loop.sh:102-110). The only consumer is `revise_skill` itself (deciding the `result` dict) and the appended `revision-log.json` record. `apply_revisions` independently emits per-revision `status:"pending"` (not the same string) for the same condition (revise.py:104-107).

**Evidence:**

```python
        result = {"status": "revised" if modified_text != skill_text else "pending_meta_agent",
            "revisions": revisions, "applied": applied_log, "output_path": output_path}
```

— `scripts/revise.py:158-163`
**Dependencies:** No automated consumer branches on it; it is a reporting/log value for humans.
**Implicit contracts:** Today the loop always lands in `pending_meta_agent` (no concrete edits exist), so iterations make no skill changes — convergence is impossible without the meta-agent wiring.

## Q13: What existing tests cover `diagnose.py`, `revise.py`, and `apply_revisions`, and do they stub or mock the meta-agent call versus exercising the string heuristics directly?

**Answer:** NOT FOUND — there are **no** tests for `diagnose.py`, `revise.py`, or `apply_revisions`. Searched `scripts/` for any module importing or referencing `diagnose`/`revise`/`apply_revisions`/`categorize_failure`/`propose_revisions`: the only hits are `scripts/qrspi_resolve_state.py` (uses the word "revise" for the unrelated QRSPI PR-revise action) and `scripts/qrspi_revise_amend_test.py` (tests `qrspi_revise_amend.py`, the Graphite amend helper — unrelated to skill revision). The `_test.py` siblings present are all `qrspi_*_test.py` orchestration tests; none import `diagnose`/`revise`/`grade`/`run_eval`/`report`. So there is nothing exercising the string heuristics and nothing mocking a meta-agent.

**Evidence:**

```
$ grep -rln "import diagnose|import revise|from diagnose|from revise" scripts/
(no matches)
$ ls scripts/*_test.py
qrspi_cleanup_test.py  qrspi_clear_stale_pr_test.py  qrspi_persist_test.py
qrspi_pr_body_test.py  qrspi_pr_state_test.py  qrspi_resolve_state_test.py
qrspi_resolve_test.py  qrspi_restack_test.py  qrspi_revise_amend_test.py
using_claude_cli_skill_test.py
```

— `scripts/` directory listing + grep
**Dependencies:** The eval-system scripts (diagnose/revise/grade/run_eval/report) are entirely untested.
**Implicit contracts:** Project convention (per CLAUDE.md) is stdlib-only `_test.py` siblings run with `python3`; the eval-loop modules currently violate the "task is never complete without tests" directive.

## Q14: How does `run_loop.sh` produce and store per-iteration scores, and what fixtures / under-specified prompt are available to validate monotonic convergence?

**Answer:** Per-iteration: `run_eval.py` writes `results/v{i}/results.json`; `grade.py` writes `results/v{i}/grades.json` (containing `train_score`, `test_score`, `train_test_gap`, per-case `cases[]`). `run_loop.sh` extracts the scalar `test_score` from `grades.json` via inline python (run_loop.sh:59-64) into shell var `SCORE`, carries `PREVIOUS_SCORE` across iterations (run_loop.sh:30,109). Persistent history is the set of `results/v{i}/` dirs, which `report.py` later folds into `results/report.json` and `results/ledger.json`.

Fixtures: `evals/fixtures/` holds only 4 ticket files (`ticket_rest_endpoint.md`, `ticket_websocket.md`, `ticket_multi_tenancy.md`, `ticket_15_acceptance_criteria.md`). `evals/golden/` is empty (`.gitkeep`). Per `docs/eval-system.md:80-89`, 17 of 21 referenced fixtures are missing (incl. a `research_multi_tenancy_sparse.md` "sparse"/under-specified research fixture). The eval suite `evals/suite.json` has 15 cases with a `split` (train_ratio 0.65 / test_ratio 0.35, seed 42) across 8 phases. There is **no** dedicated "under-specified prompt" skill fixture in the repo for convergence testing — and since `run_eval.py`/`grade.py` are stubs producing zeros, convergence cannot currently be observed.

**Evidence:**

```bash
SCORE=$(python3 -c "
import json
with open('${OUTPUT_DIR}/grades.json') as f:
    g = json.load(f)
print(g.get('test_score', 0))
")
```

— `run_loop.sh:59-64`
**Dependencies:** `results/v{i}/grades.json` produced by grade.py; `report.py` reads all `results/v*/grades.json`.
**Implicit contracts:** Scoring key is `test_score`. The pipeline "runs end-to-end but produces zeros" (docs/eval-system.md:108) — the three gaps are agent execution, LLM judge, and 17 missing fixtures.

## Q15: How does `report.py` currently read per-iteration scores, and where would the > 0.05 score-drop regression guard hook into its existing output or logging?

**Answer:** `report.py:load_version_results` (report.py:14-32) globs sorted subdirs of `results/`, loads each `grades.json`, and builds a per-version ledger. It already has regression machinery but at **different thresholds** than 0.05:
- per-case `detect_regressions` flags a drop `> 0.2` (report.py:46);
- `check_promotion_criteria` requires `test_score >= previous test_score` (no tolerance) and `train_test_gap <= 0.1` (report.py:80-85);
- plateau detection uses `< 0.01` over last 3 (report.py:127-129).

The only existing `> 0.05` guard is in **`run_loop.sh:77-91`** (`threshold = 0.05`; `prev - curr > 0.05` ⇒ "Regression detected", `continue` — rollback is a commented placeholder, `git checkout HEAD~1`). A version-level >0.05 score-drop guard in `report.py` would most naturally hook into `build_ledger_entry` (report.py:57-74, add a `score_drop`/`regressed` field comparing `entry["test_score"]` to `previous_entry["test_score"]`) and surface in the `report["alerts"]` block (report.py:145-149) and the printed summary (report.py:159-169). The persistent `ledger.json` written by `update_ledger` (report.py:175-190) is the natural durable home for the guard signal.

**Evidence:**

```python
def detect_regressions(current: dict, previous: dict) -> list:
    ...
        drop = prev["mean_score"] - curr["mean_score"]
        if drop > 0.2:  # More than 1 point on 5-point scale
            regressions.append({"case_id": case_id,
                "previous_score": prev["mean_score"],
                "current_score": curr["mean_score"], "drop": round(drop, 4)})
```

— `scripts/report.py:35-52`
**Dependencies:** Reads `results/v*/grades.json`; writes `results/report.json` + `results/ledger.json`.
**Implicit contracts:** Regression is currently per-**case** at 0.2; there is no version-level test_score-drop alert. The 0.05 threshold lives only in shell. Note `report.py` uses `test_score`/`train_score` keys; `build_ledger_entry` reads them with `.get(..., 0)`.

## Q16: What logging or transcript-trace does `diagnose.py`/`revise.py` emit today that records the meta-agent's rationale or proposed edits for human review?

**Answer:**
- `diagnose.py`: writes the full `diagnosis.json` (status, total_failures, worst_score, per-case `failures` with `categories`/`failed_assertions`/`regression_risk`, `recommendations` with `suggested_action`, `non_prompt_issues`) (diagnose.py:143-158); prints a human summary to stdout (diagnose.py:160-165). No meta-agent rationale field exists (no meta-agent runs).
- `revise.py`: writes/append `revision-log.json` next to the output (revise.py:166-181) with `{timestamp, skill_path, diagnosis_path, **result}` where result carries `revisions` (each with `action`, `edit.description`, `regression_risk`) and `applied` log; prints "Skill updated"/"No concrete edits..." to stdout (revise.py:154-156,183). The closest thing to a recorded "rationale" is each revision's `action` (from `_suggest_action`) and `edit.description` ("Meta-agent should propose a specific edit to address {category} affecting cases: ...").

No transcript trace, no LLM prompt/response capture, no proposed-diff record (since `old_text`/`new_text` are None). `evals/golden/` (intended for reference outputs) is empty.

**Evidence:**

```python
    log_path = os.path.join(os.path.dirname(output_path) or ".", "revision-log.json")
    log_entry = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "skill_path": skill_path, "diagnosis_path": diagnosis_path, **result}
    log = []
    if os.path.exists(log_path):
        with open(log_path) as f: log = json.load(f)
    log.append(log_entry)
    with open(log_path, "w") as f: json.dump(log, f, indent=2)
```

— `scripts/revise.py:166-181`
**Dependencies:** Outputs colocated with the diagnosis/revision output dir.
**Implicit contracts:** `revision-log.json` is JSON-array-append (read-modify-write); concurrent runs would race. Human-review artifacts are `diagnosis.json` + `revision-log.json` + stdout — no meta-agent reasoning is captured because none is invoked.

---

## Discovered Patterns

- **Stub-with-pseudocode-docstring convention.** Every integration boundary in the eval system is an explicit stub whose docstring shows the intended real implementation as `*.complete(system=..., messages=[...])`: `run_eval.py:execute_single` (107-137), `grade.py:run_llm_judge` (208-227) and `run_script_check` (230-241), `diagnose.py:categorize_failure` (60-73), `revise.py:propose_revisions` (32-44). All return `None`/`""`/`0`/placeholder. A new meta-agent integration should follow this same boundary shape and the `using-claude-cli` skill is the available invocation path (no in-repo client exists).
- **File-on-disk hand-off between pipeline stages.** No shared state object; every stage reads/writes JSON (`results.json` → `grades.json` → `diagnosis.json` → skill file + `revision-log.json` → `report.json`/`ledger.json`). Output paths are always explicit CLI flags.
- **`mean_score >= 0.9` per-case pass bar** (diagnose.py:31) is a separate, hard-coded constant from the loop-level `TARGET_SCORE` (run_loop.sh default 0.85) and from report's promotion gap `0.1` — three independent thresholds.
- **Score scale ambiguity.** grade.py aggregates `mean_score` and computes `test_score` as a mean of those; report.py comment treats 0.2 as "1 point on a 5-point scale" (report.py:46), implying a 1–5 judge scale, while diagnose's 0.9 and the loop's 0.85 imply a 0–1 scale. The two coexist without normalization being visible at these call sites.
- **Stdlib-only, argparse CLI + `main()` + `if __name__=="__main__"`** across all five eval scripts — consistent and test-friendly (pure functions separable from `main`).
- **In-place skill mutation as the convergence mechanism** (revise output path == input `SKILL_PATH`), with no version snapshot/rollback (run_loop.sh rollback is a commented `git checkout` placeholder, line 88).

## Inconsistencies

- **`regression_risk` looks inverted in diagnose.py:102:** `"low" if difficulty == "hard" else "medium"` — a *hard* case is labeled *low* regression risk while easy/medium cases get *medium*. The comment/intent is unstated; this reads backwards and is unguarded by any test.
- **The loop can never converge today.** `propose_revisions` always emits `old_text=None`/`new_text=None` (revise.py:64-66), so `apply_revisions` always returns the unchanged text, `revise_skill` always returns `pending_meta_agent`, and the skill file is never rewritten — every iteration re-scores the identical skill. The "diagnosis + revision loop" is structurally a no-op until the meta-agent is wired.
- **Two different regression thresholds, two locations.** The >0.05 score-drop guard exists only in `run_loop.sh:80`; `report.py` uses 0.2 per-case and 0.0 version-level (`>=` previous). Q15's requested >0.05 version guard is absent from report.py.
- **dry-run still has a side effect.** `revise_skill(dry_run=True)` skips applying/writing the skill but still appends to `revision-log.json` (revise.py:165-181 runs unconditionally) — a "dry" run mutates a file.
- **`run_loop.sh` ignores revise/diagnose exit status.** With `set -euo pipefail`, a non-zero exit would abort, but on success the loop never branches on `pending_meta_agent` vs `revised` (Q12); it cannot detect that no progress was made and will burn all `MAX_ITER` iterations.
- **Docs vs code on stub line ranges:** `docs/eval-system.md:100-101` cites `diagnose.py:58-73` and `revise.py:26-44` as the stub regions — these match the current docstrings, but the docs also claim "8 categories" while `CATEGORIES` defines exactly 8 (consistent) and "14 of ~37 referenced checks" implemented (grade.py) — the eval suite references more checks than grade.py implements.
- **No tests for any eval-system module** (Q13) despite the project-wide "task is never complete without tests" directive and the `_test.py`-sibling convention used by every `qrspi_*` script.
