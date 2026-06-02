# Research — Codebase Map

**Questions source:** /workspaces/qrspi/.worktrees/INFRA-2059/.qrspi/INFRA-2059/questions.md @ 2026-06-02T14:30:00Z
**Generated:** 2026-06-02T14:35:00Z
**Status:** draft

## Q1: What data sources feed the existing auto-triager script, and what is the structure of alert payloads received from the #alerts-daytime channel?

**Answer:** NOT FOUND. There is no auto-triager script in this codebase. The entire repository under `/workspaces/qrspi/.worktrees/INFRA-2059/` is the QRSPI framework — a structured workflow system for AI-agent-driven software feature development. No Slack integration, no `#alerts-daytime` channel reference, and no alert ingestion pipeline exist anywhere in the repo. The only mentions of "alert" or "triage" are in docs/eval-system.md (describing score plateau/overfitting alerts) and scripts/report.py (generating alerts about test score regressions), which are internal to the eval system, not an external alert channel.

**Evidence:**

```
# Full directory tree of the repo:
scripts/          — Python scripts: run_eval.py, grade.py, diagnose.py, report.py, check_scope.py, qrspi_resolve.py, qrspi_persist.py, qrspi_pr_state.py, revise.py
evals/            — Test fixtures and suite JSON for the QRSPI eval harness
docs/             — Documentation for QRSPI workflows
.claude/          — Phase agent definitions and slash-command skills
.devcontainer/    — Dev container configuration (Dockerfile, squid proxy, seccomp)
.qrspi/           — Artifact templates per phase
results/          — Empty placeholder directory
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/` (entire repo structure)

**Dependencies:** None — this is the root of the project.

**Implicit contracts:** This codebase is designed to be self-contained and tool-focused; it does not integrate with external notification systems or Slack APIs.

---

## Q2: How does the auto-triager currently decide which alerts warrant a response versus being silently dropped or logged only?

**Answer:** NOT FOUND — there is no existing auto-triager decision logic in this codebase. The closest analogy for triage/filtering exists within the eval system's regression guard in `scripts/report.py`, which evaluates version scores against promotion criteria (test_score_no_regression, no_large_case_drops, acceptable_gap), but this operates on internal eval results rather than incoming alert payloads.

**Evidence:**

```python
# scripts/report.py:77-90 — the only "triage-like" filtering in the repo
def check_promotion_criteria(entry: dict, previous_entry: dict) -> dict:
    criteria = {
        "test_score_no_regression": (
            entry["test_score"] >= previous_entry.get("test_score", 0)
        ),
        "no_large_case_drops": entry["regression_count"] == 0,
        "acceptable_gap": entry["train_test_gap"] <= 0.1,
    }
    promoted = all(criteria.values())
    return {"promoted": promoted, "criteria": criteria}
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/report.py:77-90`

**Dependencies:** `report.py` reads from version result directories; it does not accept external inputs.

**Implicit contracts:** The promotion criteria are hard-coded constants, not configurable rules. There is no concept of "silently dropping" — only promoting or flagging regressions.

---

## Q3: What outputs does the current auto-triager produce, and how are those outputs delivered back to #alerts-daytime or other downstream consumers?

**Answer:** NOT FOUND. The codebase produces no outputs intended for `#alerts-daytime` or any external channel. The closest output-producing script is `scripts/report.py`, which writes a JSON report file (with optional console summary) comparing eval versions — the output is written to a local filesystem path, not an external channel.

**Evidence:**

```python
# scripts/report.py:93-102 — output is a local JSON file, not a channel message
def generate_report(results_dir: str, output_path: str) -> dict:
    ...
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report written to {output_path}")
    return report
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/report.py:93-102`

**Dependencies:** None — the report writes to a filesystem path provided as an argument.

**Implicit contracts:** Output delivery is always to local files; there is no channel-messaging library or outbound network transport in this codebase.

---

## Q4: What external APIs or services (e.g., monitoring systems, ticketing platforms, notification services) does the existing auto-triager call to gather context for triage decisions?

**Answer:** NOT FOUND — there is no existing auto-triager and therefore no external API calls from it. More broadly, **none of the scripts in this codebase make any external HTTP/API calls**. All scripts are self-contained CLI tools that read/write local files. The only references to external services are in `scripts/qrspi_pr_state.py` (which uses the `gh` CLI to query GitHub GraphQL) and `.claude/workflows/qrspi-batch.js` (which uses Linear MCP for ticket data), but these operate through CLI wrappers / MCP tool calls, not direct HTTP calls from Python code.

**Evidence:**

```bash
# grep confirms NO HTTP calls anywhere in the Python scripts:
grep -r "requests\|urllib\|http.client\|aiohttp" scripts/
# Returns nothing — no external API library imports exist.
```

— Search across `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/`

**Dependencies:** N/A — no external service integration exists.

**Implicit contracts:** All Python scripts are offline, file-based CLIs with no network dependencies. The only external communication path is through `gh` CLI (GitHub) and Linear MCP (for ticket orchestration).

---

## Q5: How is the current auto-triager script invoked — via CLI arguments, stdin/stdout, cron/schedule, or event hooks — and what are its accepted input parameters?

**Answer:** NOT FOUND. There is no auto-triager script in this codebase. For the **closest analog**, `scripts/qrspi_resolve.py` (the single-source-of-truth resolver) and `.claude/workflows/qrspi-batch.js` (the batch orchestrator) are invoked via CLI arguments with specific flags:

```
python3 scripts/qrspi_resolve.py --ticket <ID> --linear-status "<STATUS>" [--assigned]
```

And `qrspi-batch.js` receives configuration through its `args` JSON object (`{ statuses?: string[], project?: string }`). These are not an auto-triager; they drive the QRSPI PR-gated workflow.

**Evidence:**

```python
# scripts/qrspi_resolve.py (the tested resolver) — CLI invocation pattern:
parser = argparse.ArgumentParser(description="QRSPI state resolver")
parser.add_argument("--ticket", required=True, help="Ticket identifier")
parser.add_argument("--linear-status", required=True, help="Linear ticket status name")
parser.add_argument("--assigned", action="store_true", help="Ticket is assigned")
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/qrspi_resolve.py` (pattern observed from resolver scripts)

**Dependencies:** `qrspi_resolve.py` calls `qrspi_pr_state.py` internally; both use Python stdlib only.

**Implicit contracts:** CLI invocation with required arguments — no stdin, no cron, no event hooks. No scheduled or automated invocations exist outside of batch runs.

---

## Q6: Does the current auto-triager persist any state between runs (e.g., deduplication keys, last-seen alerts, throttle windows), and if so, where is that state stored?

**Answer:** NOT FOUND. No auto-triager exists. For **state persistence in this codebase generally**: The eval system (`run_eval.py`) stores results as JSON files under `results/<version>/` directories (see `scripts/report.py:176-190`). The QRSPI framework persists artifacts per-ticket under `.worktrees/<ticket-id>/.qrspi/<ticket-id>/` (staged first at `/tmp/phase-stage/<id>/<name>.md`, then moved by `qrspi_persist.py`). There is no shared cache, Redis, queue, or persistent database — all state is filesystem-local JSON files.

**Evidence:**

```python
# scripts/report.py:175-190 — state persisted as local JSON file
def update_ledger(results_dir: str):
    ledger_path = os.path.join(results_dir, "ledger.json")
    # ... writes version ledger to local filesystem
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/report.py:175-190`

**Dependencies:** Filesystem-local; no external storage backends.

**Implicit contracts:** State is file-based and non-distributed. No deduplication, throttle windows, or dedup keys exist. The `qrspi_persist.py` script self-locates paths from its own location to avoid path mangling (see Fix A pattern).

---

## Q7: How does the existing auto-triager handle malformed, duplicate, or already-resolved alerts, and what failure modes have been observed in production?

**Answer:** NOT FOUND — there is no existing auto-triager. For **error handling patterns in this codebase**, scripts use `try/except` blocks and argument validation:

1. `run_eval.py:32-57` — validates required fields on suite JSON, raises `ValueError` for missing fields (no retry logic).
2. `grade.py:191-198` — catch-all `try/except` around check execution returns `passed=False` with error evidence (no retry or fallback).
3. `diagnose.py:58-73` — stub LLM-based categorization returns placeholder categories; no production failure modes documented.
4. No existing production logs, crash reports, or observed failure mode documentation exists in the repo.

**Evidence:**

```python
# scripts/run_eval.py:42-57 — validation with ValueError for malformed input
def load_suite(suite_path: str) -> dict:
    with open(suite_path) as f:
        suite = json.load(f)
    required = {"name", "cases"}
    missing = required - set(suite.keys())
    if missing:
        raise ValueError(f"Suite missing required fields: {missing}")
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/run_eval.py:42-57`

**Dependencies:** N/A — these are self-contained validation patterns.

**Implicit contracts:** No retry logic, no dead-letter queues, no deduplication, no "already-resolved" tracking. Malformed input causes `ValueError` which terminates the script.

---

## Q8: What happens when the auto-triager's response to #alerts-daytime is delivered but the receiving service (e.g., Slack) returns an error or timeout — is there dead-letter handling or retry?

**Answer:** NOT FOUND. There is no existing Slack integration or message delivery in this codebase, so there is no error handling for Slack failures, no dead-letter queue, and no retry logic. The closest analog is `report.py` which writes to a local filesystem path — if the directory doesn't exist, `os.makedirs(..., exist_ok=True)` creates it; errors are not caught beyond that.

**Evidence:**

```python
# scripts/report.py:154-156 — no error handling on write; just os.makedirs
os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
with open(output_path, "w") as f:
    json.dump(report, f, indent=2)
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/report.py:154-156`

**Dependencies:** N/A — no network communication exists.

**Implicit contracts:** Best-effort local file writes only. No retry, no dead-letter queue, no alert escalation mechanism. The `qrspi-batch.js` workflow uses "BEST-EFFORT" for Linear status updates (a failed write is a WARN, not a failure).

---

## Q9: What existing test coverage exists for the auto-triager script, and what mocking or fixture infrastructure is available for testing channel interactions?

**Answer:** NOT FOUND. There is no auto-triager script. For **test coverage in this codebase**: Unit tests exist for the PR-state resolver logic (`scripts/qrspi_resolve_state_test.py`, `scripts/qrspi_pr_state_test.py`, `scripts/qrspi_resolve_test.py`). The eval harness itself (`evals/suite.json`) defines 15 test cases spanning all QRSPI phases, but these are **eval assertions** (programmatic checks, LLM judges, script checks), not traditional unit tests of auto-triager behavior. The eval fixtures directory has only 4 of 21 needed ticket files; golden outputs are empty. No mocking infrastructure for channel interactions exists because no channel interaction code exists.

**Evidence:**

```json
// evals/suite.json — 15 eval cases, but the harness is a placeholder:
// "Agent execution runtime": Stub — no actual agent invocation
// "LLM judge integration": Stub — returns None
// "Script check execution": Stub — returns None
// Only 4/21 fixtures exist; golden outputs are .gitkeep only
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/evals/suite.json` (referenced in docs/eval-system.md:15-108)

**Dependencies:** `grade.py` is the scoring engine, but LLM judge and script checks are stubs returning `None`.

**Implicit contracts:** Test infrastructure exists only for eval suite scoring; no mock channel interactions are available because no channels exist. The fixture system supports file-based context loading (`run_eval.py:76-82`) which could serve as a basis for mocking, but the agents themselves are not invoked.

---

## Q10: Which components of the auto-triager are pure functions (testable without external dependencies) versus which require live service connections, and how should that distinction guide test strategy for the new skill?

**Answer:** NOT FOUND — there is no existing auto-triager. For **the current codebase's component analysis**: The entire Python script ecosystem under `scripts/` consists of pure-file I/O functions (JSON read/write, string parsing, regex-based assertions). These are fully testable without external services:

| Component | External Dependency? | Testable Standalone? |
|---|---|---|
| `grade.py` scoring logic (lines 246-278) | No | Yes — pure math on dicts |
| `grade.py` check registry (lines 21-157) | No | Yes — regex + I/O |
| `report.py` regression detection (lines 35-54) | No | Yes — dict comparison |
| `report.py` plateau/overfitting detection (lines 121-136) | No | Yes — list analysis |
| `diagnose.py` failure categorization stub (lines 58-103) | No | Yes — heuristics only |
| `run_eval.py:execute_single()` (lines 93-143) | **No** (stub returns empty result) | Yes — but not meaningful |
| All scripts | No | Yes |

The entire Python codebase is self-contained and fully testable without any live service connections. There are zero HTTP calls, zero database operations, zero file system watcher operations.

**Evidence:**

```python
# scripts/grade.py:246-265 — pure function: scoring based only on input dict
def score_case(assertion_results: list) -> dict:
    max_score = 0.0
    actual_score = 0.0
    for ar in assertion_results:
        weight = ar.get("weight", 1.0)
        max_score += weight
        if ar.get("passed") is True:
            actual_score += weight
    normalized = actual_score / max_score if max_score > 0 else 0.0
    return {"score": round(normalized, 4), ...}
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/grade.py:246-265`

**Dependencies:** All scripts depend only on Python stdlib (`json`, `argparse`, `re`, `statistics`, `pathlib`). No external packages.

**Implicit contracts:** The codebase is designed to be fully testable in isolation. This should guide the new auto-triager skill's test strategy: core logic should be pure functions, with any external integrations (Slack API, monitoring systems) as injectable dependencies.

---

## Q11: What logging, metrics, or tracing does the current auto-triager emit today, and are there any dashboards or alerting rules tied to its behavior that need to be preserved or updated when the skill is extended?

**Answer:** NOT FOUND. There is no existing auto-triager. For **logging/metrics/tracing in this codebase**: No scripts emit structured logs, metrics, or traces. The closest observability pattern is `print()` statements used as console output:

1. `report.py:159-168` — prints a summary block (`"=== Eval Report (N versions) ==="` with scores and plateau/overfitting alerts).
2. `run_eval.py:161-163, 187` — prints per-trial progress (`"[completed/total] case_id trial=N STATUS (durationms)")`.
3. No structured logging module (e.g., `logging`, `structlog`) is imported anywhere.
4. No metrics exporter, no dashboard configuration, no alerting rules.

**Evidence:**

```bash
# grep confirms: NO logging module imports in any script:
grep -r "import logging\|from logging\|import structlog\|from structlog" scripts/
# Returns nothing — zero structured log usage across the entire repo.
```

— Search across `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/`

**Dependencies:** N/A — all output is console `print()` statements to stdout.

**Implicit contracts:** Scripts are CLI tools that print to stdout; no log files, no metrics endpoints, no dashboards. This means there are zero existing alerting rules or dashboard configurations to preserve when building the new skill.

---

## Q12: How can we ensure the new extended skill produces distinguishable log entries from the current version so that a rollback or A/B comparison is feasible after deployment?

**Answer:** NOT FOUND — this question pertains to the **new skill being designed**, not the existing codebase. Based on the current state of the codebase: **There are currently NO log entries at all** (only console `print()` statements). To make new log entries distinguishable from existing ones, there is nothing to distinguish FROM — the baseline is a non-existent logging system. The recommendation is straightforward: implement structured logging from scratch for the new skill, using a log format that includes a version/timestamp/agent-identity field so rollback comparison can match logs by agent identity (e.g., `auto_triager_v1` vs. `auto_triager_v2`).

**Evidence:**

```python
# scripts/report.py:159-168 — the most verbose console output in the codebase:
print(f"=== Eval Report ({len(versions)} versions) ===")
print(f"Latest: {latest['version']}")
print(f"  Train: {latest['train_score']:.4f}")
print(f"  Test:   {latest['test_score']:.4f}")
# ... all stdout, no structured log.
```

— `/workspaces/qrspi/.worktrees/INFRA-2059/scripts/report.py:159-168`

**Dependencies:** N/A — this is a design recommendation based on zero existing logging infrastructure.

**Implicit contracts:** The codebase has no logging baseline, so any structured logging added to the new skill will be trivially distinguishable from nothing. A/B comparison is feasible by default since all production logs would come from the new implementation.

---

---

## Discovered Patterns

1. **Stdlib-only Python scripts** — All Python code in `scripts/` uses only the Python standard library (`json`, `argparse`, `re`, `statistics`, `pathlib`, `os`, `hashlib`, `time`, `dataclasses`, `typing`). No third-party dependencies are vendored or declared. This means the entire codebase runs in any Python 3 environment without `pip install`.

2. **CLI-first, no daemon** — Every script is a CLI tool invoked with `--required` arguments. There are no long-running daemons, no event loops, no background workers, and no scheduled cron entries.

3. **Fix A — staging + deterministic move** — Phase artifacts are written to a short, token-free staging path (`/tmp/phase-stage/<id>/<name>.md`) by the phase agent, then moved to the canonical worktree path by `scripts/qrspi_persist.py`. This avoids the "path mangling" bug where a weak local worker model corrupts the `qrspi` token (e.g., `qrspi` → `qrpii`).

4. **PR-gated advancement** — The single source of truth for phase progression is PR review state (`reviewDecision == APPROVED` + zero unresolved threads), not Linear status. Linear status is only an entry gate (`Selected`) and best-effort reporting projection.

5. **Self-locating scripts** — `qrspi_resolve.py` and `qrspi_persist.py` self-locate their repo root from their own file path, reducing the number of hardcoded path parameters that a weak worker model must get right.

6. **All output is local filesystem** — Every script reads or writes JSON files under `results/`, `.worktrees/`, or explicit output paths. No network I/O, no database, no message queue exists in this codebase.

7. **Eval harness is a non-functional placeholder** — The eval system (`evals/suite.json`) defines 15 test cases, but the three critical execution paths are stubs: agent execution runtime (no actual agent invocation), LLM judge integration (returns `None`), script check execution (returns `None`). Only 4 of 21 needed fixtures exist; golden outputs are empty.

8. **Batch orchestrator delegates to typed agents** — `.claude/workflows/qrspi-batch.js` resolves PR state via the tested Python resolver, then spawns typed phase agents (`qrspi-questions`, `qrspi-research`, etc.) through the agent-spawning API. The JS script itself has no LLM capability; it orchestrates by routing decisions to the right agent type.

9. **No external integrations** — No HTTP client libraries, no message queue connectors, no webhook handlers exist in this codebase. External communication (GitHub via `gh` CLI, Linear via MCP) is mediated through CLI wrappers or MCP tools, not direct Python code.

10. **Documentation as a separate artifact** — All workflow documentation lives in `docs/` and is never embedded in scripts. The doc files (`qrspi-orientation.md`, `qrspi_complete_guide.md`, etc.) are reference documents for humans, not machine-readable specs.

## Inconsistencies

1. **Eval system docs claim "pipeline runs end-to-end but produces zeros"** (docs/eval-system.md:108) — The evaluation harness is documented as a non-functional placeholder that produces all-zero scores because all three critical execution paths (agent execution, LLM judge, script check) are stubs returning `None`. This should be flagged for any downstream consumers assuming eval results represent real test data.

2. **`run_eval.py:117-138` says "In a real implementation..." but IS the only implementation** — The docstring on `execute_single()` describes what a real agent invocation would look like, then immediately below it provides a stub that just builds messages and returns an empty result. The function exists but does nothing meaningful. This is inconsistent with the claim in `eval-system.md` that "Agent execution runtime" is a stub.

3. **`grade.py:208-227` LLM judge stub returns `"passed": None`** — The comment says "In a real implementation, this calls a grading model," but the code returns `{"passed": None}` for every assertion. This means all programmatic tests pass/fail based solely on the 14 implemented check functions in `CHECKS`, while all LLM-judge assertions are skipped (scored as `None` which is neither `True` nor `False`).

4. **`diagnose.py:58-73` says it uses a meta-agent but has hardcoded heuristics** — The docstring describes an LLM-based meta-agent diagnostic, but the actual implementation (`categorize_failure`) uses string-matching heuristics (`"not found"` → `MISSING_INSTRUCTION`, `"llm_judge"` type → `UNDER_SPECIFIED`). The comment "This stub uses heuristics for common patterns" contradicts the more sophisticated docstring description.

5. **`scripts/report.py` plateau detection threshold is hardcoded** — Line 129 uses `< 0.01` as the plateau threshold (last 3 versions within 0.01 of each other), but this is not configurable or documented. A user observing false-positive plateaus has no way to adjust this without modifying source code.

6. **Missing fixture files undermine eval validity** — docs/eval-system.md:80-89 documents 17 missing fixture files (including `research_rest_endpoint.md`, `research_websocket.md`, etc.). Without these fixtures, even if the agent execution runtime were functional, most test cases would fail due to missing context data.

7. **No version pinning for eval harness** — `run_eval.py` computes a `skill_hash` (sha256 of skill text) but does not store the skill version or hash anywhere persistent besides the results JSON. There is no way to reproduce which skill version produced which result without reading both files together.

8. **Eval suite has 15 cases but only 4 fixtures** — This means 11 of 15 test cases have no fixture data to operate on, making any future agent execution meaningless for those cases. The eval system as documented cannot produce meaningful results until all 21 fixtures are populated.

9. **`check_scope.py` extracts file paths from backtick-wrapped markdown** — This assumes all impl-logs use backtick-delimited file paths, which is a fragile convention. If an impl-log uses a different path format (e.g., code blocks, plain text), the scope check silently passes without detecting out-of-scope changes.

10. **The `qrspi-batch.js` workflow has no error handling for agent spawn failures** — When an `agent()` call returns `null` (line 210), the ticket is marked as failed but nothing else happens. There is no retry, no alert, and no way to distinguish between a transient failure and a systematic issue.
