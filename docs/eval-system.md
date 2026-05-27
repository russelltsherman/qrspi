# Eval System

## Architecture

The eval harness is a 5-stage pipeline for iterating on QRSPI skill/agent prompts:

1. **`scripts/run_eval.py`** — Execute test cases against a skill prompt (multi-trial, parallel)
2. **`scripts/grade.py`** — Score results using programmatic checks + LLM judges
3. **`scripts/report.py`** — Compare versions, detect regressions/plateaus/overfitting
4. **`scripts/diagnose.py`** — Categorize failures into root causes (8 categories)
5. **`scripts/revise.py`** — Propose and apply targeted prompt edits

## Suite Definition

`evals/suite.json` defines 15 eval cases spanning all QRSPI phases:

| Phase | Cases | Coverage |
|---|---|---|
| questions | case_001, case_002, case_015 | happy path, complex ticket, instruction-budget stress |
| research | case_003, case_004 | factual accuracy, NOT FOUND handling |
| design | case_005, case_006, case_014 | citation compliance, new-pattern flagging, fabrication detection |
| structure | case_007, case_008 | vertical slices, large-feature splitting |
| plan | case_009 | atomicity |
| worktree | case_010 | session boundaries |
| implement | case_011, case_012 | scope enforcement, deviation reporting |
| pr | case_013 | acceptance criteria mapping |

Cases use a 65/35 train/test split (seed 42). Defaults: 3 trials per case, 120s timeout, 128k max tokens.

`evals/graphite-evals.json` is a separate eval for the Graphite CLI skill (5 cases covering commit, submit, log, move, sync).

## Assertion Types

Each case has weighted assertions of three types:

- **programmatic** — Deterministic checks (file exists, section present, line count, regex patterns). Implemented in `grade.py` check registry.
- **llm_judge** — Subjective quality criteria evaluated by a grading model. Each has a natural-language criteria string.
- **script** — External script execution (e.g., `scripts/check_scope.py`). Interprets exit code and stdout.

## Scoring

- Per-case: weighted sum of passed assertions / max possible score, normalized to 0-1.
- LLM judge scores use a 1-5 scale normalized to 0-1.
- Per-suite: mean across cases, with stddev, min, max.
- Train and test scores are computed separately; the train-test gap flags overfitting.

## Reporting

`report.py` builds a version ledger and checks promotion criteria:

- Test score must not regress vs. previous version
- No per-case drops > 0.2
- Train-test gap must be <= 0.1

Alerts: plateau detection (last 3 versions within 0.01), overfitting detection (growing train-test gap).

## Diagnosis

`diagnose.py` categorizes failures into 8 root causes:

| Category | Description |
|---|---|
| MISSING_INSTRUCTION | Skill doesn't tell agent to do X |
| CONFLICTING_INSTRUCTION | Skill says A but case needs B |
| OVER_CONSTRAINED | Skill is too rigid for this edge case |
| UNDER_SPECIFIED | Skill is too vague, agent guesses wrong |
| TOOL_MISUSE | Agent uses wrong tool or wrong sequence |
| CONTEXT_LOSS | Agent loses track over long workflows |
| MODEL_LIMITATION | Not addressable via prompt changes |
| EVAL_ISSUE | The eval case or assertion is flawed |

## Revision

`revise.py` proposes minimal, surgical edits to agent prompts. Each edit is traceable to specific failure cases and assessed for regression risk (low/medium/high). Supports dry-run mode.

## Fixtures

Test fixtures live in `evals/fixtures/`. Golden outputs (expected references) go in `evals/golden/`.

4 of 21 referenced fixtures exist (the ticket files). Missing fixtures:

- questions phase: `questions_rest_endpoint.md`, `questions_websocket.md`, `questions_multi_tenancy.md`
- research phase: `research_rest_endpoint.md`, `research_websocket.md`, `research_multi_tenancy_sparse.md`
- design phase: `design_rest_endpoint.md`, `design_billing_migration.md`
- structure phase: `structure_rest_endpoint.md`, `structure_broken_contract.md`
- plan phase: `plan_rest_endpoint.md`, `plan_rest_endpoint_slice1.md`, `plan_broken_contract_slice1.md`
- worktree phase: `worktree_session1.md`, `worktree_session_broken_contract.md`
- implement phase: `impl_log_complete.md`
- pr phase: `git_diff_rest_endpoint.txt`

## Completeness

| Component | Status | Notes |
|---|---|---|
| Suite definition (15 cases) | Done | Well-designed with train/test split |
| Programmatic check registry | Partial | 14 of ~37 referenced checks implemented in `grade.py` |
| Agent execution runtime | Stub | `run_eval.py:117-137` — no actual agent invocation |
| LLM judge integration | Stub | `grade.py:208-227` — returns None |
| Script check execution | Stub | `grade.py:230-241` — returns None |
| Meta-agent diagnosis | Stub | `diagnose.py:58-73` — heuristics only |
| Meta-agent revision | Stub | `revise.py:26-44` — placeholder edits |
| Fixture files | 4/21 | Only ticket fixtures exist |
| Golden outputs | Empty | `.gitkeep` only |
| Scoring & aggregation | Done | Weighted scoring, variance, normalization |
| Reporting & regression guard | Done | Ledger, promotion criteria, alerts |
| `check_scope.py` | Done | Implementation scope enforcement |

The pipeline runs end-to-end but produces zeros — the three critical gaps are agent execution, LLM judge integration, and the 17 missing fixture files.
