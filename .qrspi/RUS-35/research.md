# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Q1: How does `run_loop.sh` consume its first positional argument (the agent file path) — is the value passed through to another command, read as a file, or only echoed in a usage/header comment?

**Answer:** The first positional arg is captured as `SKILL_PATH` (a guarded required arg). It is (a) echoed in the banner, and (b) passed through as `--skill "$SKILL_PATH"` to `python3 scripts/run_eval.py`, and to `diagnose.py` and `revise.py` (the latter also as `--output "$SKILL_PATH"`, i.e. revisions are written back to the same path). It is NOT itself opened/read by the shell script — the file read happens inside `run_eval.py:load_skill()` (`open(skill_path)`). So the value flows: shell arg → `--skill` flag → `run_eval.load_skill()` opens it.
**Evidence:**

```bash
SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
...
    python3 scripts/run_eval.py \
        --skill "$SKILL_PATH" \
        --suite "$EVAL_SUITE" \
        --output "$OUTPUT_DIR" \
```

— `run_loop.sh:12`, `run_loop.sh:43-48`, `run_loop.sh:96-106`

```python
def load_skill(skill_path: str) -> str:
    """Load the agent prompt / skill text."""
    with open(skill_path) as f:
        return f.read()
```

— `scripts/run_eval.py:61-64`
**Dependencies:** `run_loop.sh` → `scripts/run_eval.py` (`--skill`), `scripts/diagnose.py` (`--skill`), `scripts/revise.py` (`--skill`/`--output`).
**Implicit contracts:** `SKILL_PATH` must be an existing readable file at invocation CWD-relative path; `run_eval.load_skill()` does a bare `open()` with no existence guard, so a bad path raises `FileNotFoundError` inside Python, not in the shell. `revise.py --output "$SKILL_PATH"` implies the path is also writable (the loop mutates the skill file in place).

## Q2: What does `run_loop.sh` do with its second argument (the suite path, e.g. `evals/suite.json`) — how does the value flow from invocation into the eval runtime?

**Answer:** The second arg is captured as `EVAL_SUITE` (guarded required arg), echoed in the banner, and passed as `--suite "$EVAL_SUITE"` to both `run_eval.py` and `grade.py` on every iteration. Inside `run_eval.py` it becomes `config.suite_path`, consumed by `load_suite()` which `open()`s and `json.load()`s it, then validates required top-level keys (`name`, `cases`) and per-case keys (`id`, `prompt`, `assertions`).
**Evidence:**

```bash
EVAL_SUITE=${2:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
...
    python3 scripts/grade.py \
        --results "${OUTPUT_DIR}/results.json" \
        --suite "$EVAL_SUITE"
```

— `run_loop.sh:13`, `run_loop.sh:43-55`

```python
def load_suite(suite_path: str) -> dict:
    suite = json.load(f)
    required = {"name", "cases"}
    missing = required - set(suite.keys())
    if missing:
        raise ValueError(f"Suite missing required fields: {missing}")
```

— `scripts/run_eval.py:42-58`
**Dependencies:** `run_loop.sh` → `run_eval.py` + `grade.py`, both `--suite`.
**Implicit contracts:** Suite JSON must contain `name` + `cases[]`, each case with `id`/`prompt`/`assertions`, or `load_suite` raises `ValueError`. `evals/suite.json` (name `qrspi-agent-evals`, 15 cases) satisfies this contract.

## Q3: What is the exact invocation contract (usage string, argument order, defaults) that `run_loop.sh` documents in its header comment, and which argument occupies line 9?

**Answer:** The documented usage is `./run_loop.sh <skill_path> <eval_suite> [max_iterations] [target_score]` (header line 7), with a worked example on **line 10**: `./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85`. Argument order: `$1`=skill_path (required), `$2`=eval_suite (required), `$3`=max_iter (default 5), `$4`=target_score (default 0.85). Two env-var knobs: `TRIALS` (default 3), `WORKERS` (default 4).

**IMPORTANT DISCREPANCY (flagged in Inconsistencies):** Q3 and Q8 both state the agent/`.qrspi/agents/` path is on **line 9**. It is actually on **line 10**. Line 9 is the bare comment `#   Example:`. The only `.qrspi/agents/` occurrence in the file is the example on line 10.
**Evidence:**

```bash
# Usage:
#   ./run_loop.sh <skill_path> <eval_suite> [max_iterations] [target_score]
#
# Example:
#   ./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85

SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
EVAL_SUITE=${2:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
MAX_ITER=${3:-5}
TARGET_SCORE=${4:-0.85}
```

— `run_loop.sh:6-15` (example on line 10; line 9 is `#   Example:`)
**Dependencies:** None — pure documentation/parameter-binding.
**Implicit contracts:** Required args use `${N:?msg}` so omitting them aborts immediately with the usage message on stderr.

## Q4: Does any other script, workflow, or documentation invoke `run_loop.sh` or pass it an agent path, such that a changed expected path format would affect callers?

**Answer:** No active caller. A repo-wide grep for `run_loop` (excluding `.git`) found only: (1) `run_loop.sh` itself; (2) prose mentions inside `.qrspi/<ticket>/` artifact files from prior tickets (research/impl-log/pr-summary). No script, workflow (`.claude/workflows/qrspi-batch.js`), Makefile, CI config (none exists), or live doc executes `run_loop.sh` or constructs an agent path to feed it. There is no `.github/` directory. The example path is referenced only inside the script's own comment. Therefore changing the example path format has no downstream caller impact.
**Evidence:**

```
run_loop.sh:7, 10, 12, 13          (self)
.qrspi/RUS-16/research.md:239      (prose: "the top-level shell driver")
.qrspi/RUS-30/research.md:207-210  (prose: quotes the SKILL_PATH line)
.qrspi/RUS-7/research.md:205-221   (prose: describes the harness)
```

— grep `run_loop` across repo (excluding `.git`)
**Dependencies:** None invoke it; it is a leaf top-level driver.
**Implicit contracts:** None — the example is illustrative, not a parsed contract.

## Q5: Does `run_loop.sh` resolve the agent path relative to a fixed base directory, an environment variable, or the current working directory before using it?

**Answer:** It does NOT resolve or normalize the path at all. `SKILL_PATH` is used verbatim as given. There is no `cd`, no base-dir prefix, no env-var resolution, no `realpath`/`readlink`. The script also assumes its sibling scripts at the relative path `scripts/*.py` and writes results to `results/${VERSION}` — all CWD-relative — so the effective contract is "run from the repo root". Whatever the caller passes for `SKILL_PATH` is resolved by Python's `open()` relative to that same CWD.
**Evidence:**

```bash
#!/bin/bash
set -euo pipefail
...
SKILL_PATH=${1:?Usage: ...}
...
    python3 scripts/run_eval.py \
        --skill "$SKILL_PATH" \
```

— `run_loop.sh:1-2,12,43-44` (no path resolution between capture and use; no `cd` anywhere in the file)
**Dependencies:** Implicit dependency on CWD == repo root (for `scripts/`, `results/`).
**Implicit contracts:** Caller must invoke from repo root and pass a path valid relative to that CWD.

## Q6: What is the current on-disk layout of agent files referenced by the ticket — do files exist at `.claude/agents/qrspi-<phase>.md`, and is there any remaining `.qrspi/agents/` directory?

**Answer:** Agent files live at `.claude/agents/qrspi-<phase>.md`. There is **no** `.qrspi/agents/` directory anywhere in the repo (confirmed: that path resolves to "NO .qrspi/agents dir"). The legacy `01-questions.md`-style naming in the run_loop.sh example does not exist on disk; the actual files use `qrspi-<phase>.md`. Present files in `.claude/agents/`: `qrspi-design.md`, `qrspi-implement.md`, `qrspi-plan.md`, `qrspi-pr.md`, `qrspi-questions.md`, `qrspi-research.md`, `qrspi-structure.md`, `qrspi-worktree.md`.
**Evidence:**

```
.claude/agents/qrspi-design.md
.claude/agents/qrspi-implement.md
.claude/agents/qrspi-plan.md
.claude/agents/qrspi-pr.md
.claude/agents/qrspi-questions.md
.claude/agents/qrspi-research.md
.claude/agents/qrspi-structure.md
.claude/agents/qrspi-worktree.md
```

— `ls .claude/agents/`; `ls .qrspi/agents/` → directory does not exist
**Dependencies:** `.claude/CLAUDE.md` documents this layout ("Phase agent definitions live in `.claude/agents/`"); confirmed by 9 SKILL.md files plus docs referencing `.claude/agents/`.
**Implicit contracts:** The canonical, on-disk agent path for the questions phase is `.claude/agents/qrspi-questions.md`. The run_loop.sh example path `.qrspi/agents/01-questions.md` matches neither the directory nor the filename convention.

## Q7: What happens in `run_loop.sh` when the agent path argument points to a nonexistent file — is there a guard/validation, or does it fail later inside the runtime?

**Answer:** No guard in the shell script. There is no `[ -f "$SKILL_PATH" ]` / `-e` check anywhere. With `set -euo pipefail`, the first time the path is dereferenced is inside `run_eval.py:load_skill()` via a bare `open(skill_path)`, which raises `FileNotFoundError` (uncaught — `load_skill` is called at `run_suite` top level, outside the per-trial try/except). Python exits non-zero, the `python3 scripts/run_eval.py` step fails, and `set -e` aborts the whole loop. So the failure surfaces late, from the Python runtime, with a traceback rather than a friendly shell message.
**Evidence:**

```python
skill_text = load_skill(config.skill_path)   # run_suite() top-level, no try/except
...
def load_skill(skill_path: str) -> str:
    with open(skill_path) as f:   # FileNotFoundError if missing
        return f.read()
```

— `scripts/run_eval.py:149`, `scripts/run_eval.py:61-64` (no existence guard in `run_loop.sh`)
**Dependencies:** Error path runs through `run_eval.py` → `set -e` in `run_loop.sh`.
**Implicit contracts:** Validity of `SKILL_PATH` is the caller's responsibility; the harness fails fast but only at Python load time, not at arg-parse time.

## Q8: Are there occurrences of the literal string `.qrspi/agents/` anywhere in `run_loop.sh` besides line 9 (in comments, variable defaults, or fallback paths) that must also be updated?

**Answer:** There is exactly **one** occurrence of `.qrspi/agents/` in `run_loop.sh`, and it is on **line 10** (the `Example:` comment), not line 9. No other occurrence exists — not in variable defaults (`MAX_ITER`/`TARGET_SCORE`/`TRIALS`/`WORKERS` have numeric/empty defaults), not in fallbacks, not elsewhere in comments. The required-arg guards reference `<skill_path>` as a placeholder, not the literal `.qrspi/agents/` path.
**Evidence:**

```bash
#   ./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85
```

— `run_loop.sh:10` (sole `.qrspi/agents/` occurrence; `grep -n ".qrspi/agents/" run_loop.sh` returns only line 10)
**Dependencies:** None.
**Implicit contracts:** Updating the single line-10 example fully removes the stale path from the file.

## Q9: Does `run_loop.sh` depend on the "runtime ticket" referenced in the acceptance criteria — what runtime component must exist for `./run_loop.sh .claude/agents/qrspi-questions.md evals/suite.json` to run without errors?

**Answer:** For that invocation to even begin and not crash on missing inputs, the following must exist (all do): `.claude/agents/qrspi-questions.md` (exists), `evals/suite.json` (exists, valid 15-case `qrspi-agent-evals` suite), and the five Python scripts the loop shells out to: `scripts/run_eval.py`, `scripts/grade.py`, `scripts/diagnose.py`, `scripts/revise.py`, `scripts/report.py` (all present in `scripts/`). HOWEVER, the eval runtime itself is a **non-functional placeholder**: `run_eval.py:execute_single()` does NOT invoke any agent — it returns empty output and zeroed metrics with a comment describing what a real implementation would do. So `run_loop.sh` will *run* (no crash on the path/suite/scripts) but produces stub results; downstream grading/diagnosis operates on empty transcripts. `.claude/CLAUDE.md` and project memory both state the harness is a placeholder verified instead via unit tests + manual e2e.
**Evidence:**

```python
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    ...
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:117-135`

```
The evals/ + scripts/run_eval.py harness is a non-functional placeholder
```

— `.claude/CLAUDE.md` (Codebase conventions)
**Dependencies:** `run_loop.sh` → `run_eval.py`, `grade.py`, `diagnose.py`, `revise.py`, `report.py`; suite + skill files.
**Implicit contracts:** "Runs without errors" means the shell driver completes; it does NOT mean real evaluation occurred. The executor is intentionally stubbed.

## Q10: Is there any existing test, smoke check, or ShellCheck configuration covering `run_loop.sh`, and does any test assert on the agent path string or header comment content?

**Answer:** NOT FOUND. There is no test, smoke check, or ShellCheck config covering `run_loop.sh`. No `.github/` directory (no CI workflows). No `.shellcheckrc`. No test file references `run_loop`, `SKILL_PATH`, the example path, `01-questions`, or `qrspi-questions.md`. The repo's tests are stdlib Python `scripts/qrspi_*_test.py` siblings covering the resolver/persist/PR-state logic — none touch `run_loop.sh` or its header comment. (A grep hit for `scripts/using_claude_cli_skill_test.py` was a false positive on a generic substring; it has zero `run_loop`/`skill_path`/`01-questions`/`qrspi-questions` references.) Search queries attempted: `grep -rln "run_loop"` in `.github/ scripts/ .devcontainer/`; `ls .shellcheckrc`; `ls .github/`; `grep -n "run_loop|skill_path|01-questions|qrspi-questions" scripts/*_test.py`.
**Evidence:**

```
no .github
no .shellcheckrc
(no test asserts on run_loop.sh agent path or header)
```

— `ls .github/` → absent; `ls .shellcheckrc` → absent; test-file grep → no real match
**Dependencies:** None — `run_loop.sh` is untested by automation.
**Implicit contracts:** Changes to `run_loop.sh` will not be caught by any automated gate; verification is manual per project convention.

## Q11: Does `evals/suite.json` exist and does its content reference agent paths in either the old `.qrspi/agents/` or new `.claude/agents/` form?

**Answer:** Yes, `evals/suite.json` exists (24 KB, top-level keys `name`/`version`/`description`/`split`/`defaults`/`cases`; name `qrspi-agent-evals`; 15 cases). It contains **zero** agent-path references in either form — `grep -c "agents/"` returns 0. Cases reference only fixture files under `fixtures/` via `context.files` (e.g. `fixtures/ticket_rest_endpoint.md`, `fixtures/questions_rest_endpoint.md`). The skill/agent path is supplied at runtime via the `--skill` CLI flag from `run_loop.sh`, never embedded in the suite. So suite.json needs no change for an agent-path fix.
**Evidence:**

```
case_001 -> ['fixtures/ticket_rest_endpoint.md']
case_003 -> ['fixtures/questions_rest_endpoint.md']
case_005 -> ['fixtures/ticket_rest_endpoint.md', 'fixtures/questions_rest_endpoint.md', ...]
```

— `evals/suite.json` (`grep -c "agents/" evals/suite.json` → `0`)
**Dependencies:** `suite.json` `context.files` → `evals/fixtures/*.md` (resolved CWD-relative by `run_eval.build_messages`).
**Implicit contracts:** Suite is agent-agnostic; the agent under test is injected externally via `--skill`.

## Q12: What does `run_loop.sh` emit to stdout/stderr (usage message, progress logs, errors) and would those messages echo the agent path that the ticket says is wrong?

**Answer:** stdout: a boxed banner that echoes `Skill: ${SKILL_PATH}` and `Suite: ${EVAL_SUITE}` plus max-iter/target/trials; per-iteration section headers; numbered step logs (`[1/4] Running eval suite...`, `[2/4] Grading...`, `[3/4] Diagnosing...`, `[4/4] Proposing revisions...`); the score line `Score: ${SCORE} (target: ${TARGET_SCORE})`; target-met / regression / rollback notices; and a final report section. stderr: only the `${N:?Usage: ...}` guard messages when a required arg is omitted (these print the usage string `run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]`, which uses the `<skill_path>` placeholder, NOT the literal stale path). The banner DOES echo the actual `SKILL_PATH` *value* the caller passed at runtime — but the only place the wrong literal `.qrspi/agents/01-questions.md` string lives is the line-10 example comment, which is never emitted (it is a comment, not an `echo`).
**Evidence:**

```bash
echo "║ Skill:    ${SKILL_PATH}"
echo "║ Suite:    ${EVAL_SUITE}"
...
echo "  Score: ${SCORE} (target: ${TARGET_SCORE})"
```

— `run_loop.sh:22-23`, `run_loop.sh:66`; usage guards at `run_loop.sh:12-13`
**Dependencies:** None beyond `echo`/`python3` stdout.
**Implicit contracts:** Runtime banner reflects whatever path the caller supplies; the stale path is confined to a non-emitted comment.

---

## Discovered Patterns

- **Stub eval harness.** `run_loop.sh` → `run_eval.py`/`grade.py`/`diagnose.py`/`revise.py`/`report.py` is wired end-to-end but the executor (`run_eval.execute_single`) is an intentional placeholder returning empty output (`run_eval.py:117-135`). `.claude/CLAUDE.md` and project memory both label it non-functional; real verification is via stdlib `scripts/qrspi_*_test.py` + manual e2e.
- **Shell arg-guard convention.** Required positional args use `${N:?Usage: ...}` (fail-fast to stderr); shebang `#!/bin/bash` + `set -euo pipefail` (matches `.qrspi/RUS-30/research.md:187` characterization). `run_loop.sh` uses `#!/bin/bash` while `.devcontainer` scripts use `#!/usr/bin/env bash`.
- **CWD == repo-root assumption.** All paths in `run_loop.sh` (`scripts/`, `results/`, the skill/suite args) are CWD-relative with no resolution; the driver assumes invocation from repo root.
- **Agent-path injected at runtime, never embedded in data.** The suite is agent-agnostic; the agent under test arrives via the `--skill` flag, so only the run_loop.sh example comment carries an agent path.
- **Canonical agent layout is `.claude/agents/qrspi-<phase>.md`** (8 files), documented in `.claude/CLAUDE.md` and referenced by 9 SKILL.md wrappers + docs. The `.qrspi/agents/` directory does not exist.

## Inconsistencies

- **Line-number mismatch (Q3, Q8 vs. actual file).** The questions assert the agent path / `.qrspi/agents/` reference is on **line 9** of `run_loop.sh`. It is actually on **line 10**; line 9 is the bare `#   Example:` comment. Any edit must target line 10.
- **Stale example path vs. on-disk reality.** `run_loop.sh:10` shows `.qrspi/agents/01-questions.md`. Neither the directory (`.qrspi/agents/` — absent) nor the filename (`01-questions.md` — uses old numeric naming) exists. The current equivalent is `.claude/agents/qrspi-questions.md`. The header example references a layout that has since been migrated.
- **"Runs without errors" ambiguity (Q9).** The harness will run to completion with the corrected path, but the executor is a stub — "no errors" does not imply meaningful evaluation. Any acceptance criterion expecting real scoring would not be satisfied by the placeholder runtime.
- **No automated guardrail.** Despite the project's TDD posture, `run_loop.sh` has no test, ShellCheck config, or CI (no `.github/`). A path fix here cannot be regression-protected by existing automation; only manual verification applies.
