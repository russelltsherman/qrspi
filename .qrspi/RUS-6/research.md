# Research -- Codebase Map

**Questions source:** questions.md @ 2026-05-26T01:16:20Z
**Generated:** 2026-05-26T01:18:54Z
**Status:** draft

## Q1: How does the existing skill-creator skill discover and validate `SKILL.md` frontmatter fields, and what schema does it enforce for the agentskills.io standard pattern?

**Answer:** The skill-creator skill is not part of this project's codebase. No file matching `skill-creator` exists anywhere under `/workspaces/qrspi/.worktrees/RUS-6/`. The skill-creator is listed as an available skill in the Claude Code system-level configuration (visible in the system-reminder block), which means it is provided by the Claude Code harness itself, not by this repository.

Because skill-creator is external, its SKILL.md definition, frontmatter validation logic, and schema enforcement are not inspectable from within this codebase. The project's own skills do follow a consistent frontmatter pattern (documented below in Q4), but there is no local code that parses or validates these frontmatter fields.

**Evidence:** Search commands attempted:
- `find /workspaces/qrspi/.worktrees/RUS-6 -path '*skill-creator*' -type f` -- returned no results
- `find /workspaces/qrspi/.worktrees/RUS-6/.claude -type f -not -path '*/skills/*'` -- returned only `CLAUDE.md`
- No `settings.json`, `settings.local.json`, or `.claude.json` files exist in the project

**Dependencies:** The skill-creator is an upstream dependency provided by the Claude Code runtime environment, not by this project.
**Implicit contracts:** This project's skills implicitly conform to whatever schema skill-creator enforces, but that schema is not codified locally.

## Q2: What directory structure does the project currently use for skills, and where are existing `SKILL.md` files located relative to the project root?

**Answer:** Skills live under `.claude/skills/<skill-name>/SKILL.md`. Each skill gets its own directory named after the skill. There are 10 skills in the project, all following the QRSPI workflow naming convention. Only one skill (`qrspi-work`) has a `references/` subdirectory.

**Evidence:**

```
.claude/skills/
  qrspi-design/SKILL.md
  qrspi-implement/SKILL.md
  qrspi-plan/SKILL.md
  qrspi-pr/SKILL.md
  qrspi-questions/SKILL.md
  qrspi-research/SKILL.md
  qrspi-structure/SKILL.md
  qrspi-ticket/SKILL.md
  qrspi-work/SKILL.md
  qrspi-work/references/review-cascade.md
  qrspi-worktree/SKILL.md
```

-- directory listing via `find /workspaces/qrspi/.worktrees/RUS-6/.claude/skills -type f | sort`

**Dependencies:** Skills are discovered by the Claude Code harness from the `.claude/skills/` directory tree. The harness populates them in the system-reminder `available-skills` list.
**Implicit contracts:** One skill per directory. The directory name matches the `name` field in the SKILL.md frontmatter. The directory name also matches the `command` field (prefixed with `/`).

## Q3: How does the skill-creator skill's eval loop feed back into `SKILL.md` content -- what inputs does it consume and what outputs does it produce during each iteration?

**Answer:** The skill-creator skill is not present in this codebase (see Q1). However, this project does contain a complete eval loop infrastructure in `scripts/` and `evals/` that operates on skills. The pipeline is:

1. `run_eval.py` -- executes eval cases against a skill, producing `results.json`
2. `grade.py` -- grades results using programmatic checks and LLM judges, producing `grades.json`
3. `diagnose.py` -- analyzes failures and categorizes them, producing `diagnosis.json`
4. `revise.py` -- proposes targeted edits to the skill text based on diagnosis, producing a modified skill file and `revision-log.json`

The orchestrator `run_loop.sh` chains these four steps iteratively until a target test score is reached or max iterations are exhausted.

**Evidence:**

```bash
# From run_loop.sh:30-48
python3 scripts/run_eval.py \
    --skill "$SKILL_PATH" \
    --suite "$EVAL_SUITE" \
    --output "$OUTPUT_DIR" \
    --trials "$TRIALS" \
    --workers "$WORKERS"
```

-- `run_loop.sh:42-48`

The eval runner accepts a `--skill` path (the SKILL.md file) and a `--suite` path (the eval suite JSON). The current `execute_single` function is a stub that returns empty results; the actual agent invocation is marked as a placeholder.

```python
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
#   response = agent.run(
#       system_prompt=skill_text,
#       messages=build_messages(case),
#       tools=<tool_set>,
#       sandbox=IsolatedContainer(),
#   )
```

-- `scripts/run_eval.py:117-125`

**Dependencies:** `run_loop.sh` -> `run_eval.py` -> `grade.py` -> `diagnose.py` -> `revise.py` -> `report.py`. Each step reads the previous step's output from disk.
**Implicit contracts:** The eval loop expects results in the `results/<version>/` directory structure. Grade, diagnosis, and revision files co-locate with results. The revision step writes back to the original skill path in-place.

## Q4: What fields and format does the `SKILL.md` frontmatter require (e.g., `name`, `description`, `triggers`, `version`) and are any fields optional versus mandatory?

**Answer:** All 10 SKILL.md files in the project use YAML frontmatter delimited by `---`. The fields observed across all skills are:

| Field | Present in all 10? | Example value |
|---|---|---|
| `name` | Yes | `qrspi-work` |
| `description` | Yes | A quoted string describing when to invoke the skill |
| `command` | Yes | `/qrspi-work` |
| `argument-hint` | Yes | `<ticket-id>` or `<ticket-id> <slice-number>` |
| `allowed-tools` | Yes | Comma-separated list of tool names |

No skill uses `triggers`, `version`, or any other frontmatter field. The `description` field doubles as the trigger description -- it contains natural language describing when the skill should be invoked.

**Evidence:**

```yaml
---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development..."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, ...
---
```

-- `.claude/skills/qrspi-work/SKILL.md:1-7`

```yaml
---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket...
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(wc:*), Bash(curl:*), ...
---
```

-- `.claude/skills/qrspi-questions/SKILL.md:1-7`

**Dependencies:** The Claude Code harness reads these frontmatter fields to populate the available-skills list, register the `/command`, and gate tool access.
**Implicit contracts:** `name` matches the directory name. `command` is `/<name>`. `allowed-tools` restricts which tools the skill can use -- some skills use wildcard patterns like `Bash(wc:*)` to allow only specific bash subcommands. The `description` field serves as both documentation and trigger-matching text for the Claude Code skill dispatcher.

## Q5: What is the expected interface between a skill's `references/` directory and the skill runner -- are reference files loaded automatically, on-demand, or explicitly referenced from within `SKILL.md`?

**Answer:** Only one skill in the project uses a `references/` directory: `qrspi-work`. That skill explicitly references its reference file by path within the SKILL.md body. There is no evidence of automatic loading.

The `qrspi-work` skill instructs: "Read `references/review-cascade.md` for cascade logic" at line 175 in its SKILL.md. The reference file `review-cascade.md` contains cascade rules for re-running downstream artifacts when planning feedback requires changes.

**Evidence:**

```
c. Read `references/review-cascade.md` for cascade logic.
d. Address feedback starting from the earliest affected artifact
   -- read the cascade reference for the re-run rules.
```

-- `.claude/skills/qrspi-work/SKILL.md:175-176`

The reference file is a 64-line markdown document with rules and a worked example:

```
# Review Cascade Logic
When planning review feedback requires changes to an artifact, downstream artifacts
may be invalidated. The planning artifacts form a dependency chain:
Questions -> Research -> Design -> Structure -> Plan -> Work Tree
```

-- `.claude/skills/qrspi-work/references/review-cascade.md:1-5`

**Dependencies:** `qrspi-work/SKILL.md` -> `qrspi-work/references/review-cascade.md` (explicit read at invocation time).
**Implicit contracts:** Reference files are loaded via the `Read` tool when the skill body instructs it. There is no auto-loading mechanism visible in the codebase. The path used is relative to the skill directory (`references/review-cascade.md`), not the project root.

## Q6: Does the project define any token-budget or line-count enforcement mechanism that validates the "under 500 lines / 5000 tokens" constraint on `SKILL.md` bodies?

**Answer:** NOT FOUND. No file in the project enforces a 500-line or 5000-token constraint on SKILL.md files. The constraint is not mentioned in any code, script, eval case, or configuration file within this project.

Search queries attempted:
- `find /workspaces/qrspi/.worktrees/RUS-6 -type f -name '*.py' -o -name '*.sh' -o -name '*.json'` followed by searching content for "500", "5000", "token", "line_count" in eval and script files
- Reading all files in `scripts/` -- none contain skill body size validation
- Reading `evals/suite.json` -- the only `line_count` check is on `design.md` output (300-line limit), not on SKILL.md input
- Reading `evals/graphite-evals.json` -- no size constraints

The `grade.py` script has a `line_count` function, but it is used to validate agent output files, not SKILL.md source files.

**Evidence:**

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

-- `scripts/grade.py:35-40`

This is applied only to eval outputs, not to skill definitions.

**Dependencies:** None -- no such mechanism exists.
**Implicit contracts:** The "under 500 lines / 5000 tokens" constraint may be enforced by the external skill-creator skill or by Claude Code itself, but it is not codified in this project.

## Q7: How does the skill-creator skill manage intermediate state between iterations of its eval loop -- does it persist drafts to disk, hold them in memory, or rely on conversation context?

**Answer:** The skill-creator skill is external to this project (see Q1). However, the project's own eval loop (`run_loop.sh` + scripts) manages state entirely through disk persistence. Each iteration writes to `results/<version>/` directories. The revision step writes modified skill text directly back to the original skill file path.

**Evidence:**

```bash
# From run_loop.sh:33-35
VERSION="v${i}"
OUTPUT_DIR="results/${VERSION}"
```

-- `run_loop.sh:33-35`

The `revise.py` script appends to a persistent `revision-log.json`:

```python
log_path = os.path.join(os.path.dirname(output_path) or ".", "revision-log.json")
log_entry = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "skill_path": skill_path,
    "diagnosis_path": diagnosis_path,
    **result,
}
# Append to log
log = []
if os.path.exists(log_path):
    with open(log_path) as f:
        log = json.load(f)
log.append(log_entry)
```

-- `scripts/revise.py:166-179`

The regression guard in `run_loop.sh` compares the current score to `$PREVIOUS_SCORE` (a shell variable) and can roll back:

```bash
REGRESSED=$(python3 -c "
prev = float('${PREVIOUS_SCORE}')
curr = float('${SCORE}')
threshold = 0.05
print(1 if prev > 0 and (prev - curr) > threshold else 0)
")
```

-- `run_loop.sh:77-82`

**Dependencies:** `run_loop.sh` -> `results/v<N>/results.json` -> `grades.json` -> `diagnosis.json` -> skill file (modified in place).
**Implicit contracts:** State persists between iterations via the filesystem. No database or in-memory state store is used. The `PREVIOUS_SCORE` variable resets if the script is restarted.

## Q8: When a skill includes a `references/` directory with multiple files, what naming or indexing convention determines load order or lookup keys?

**Answer:** Only one skill has a `references/` directory (`qrspi-work`), and it contains only one file (`review-cascade.md`). There is no multi-file load order convention observable in the codebase.

The reference file is loaded explicitly by name from within the SKILL.md body (see Q5). There is no indexing mechanism, no manifest file, and no alphabetical or numeric ordering convention evident from the single example.

**Evidence:**

```
$ ls -la .claude/skills/qrspi-work/references/
total 4
drwxr-xr-x 3 vscode vscode   96 May 26 01:14 .
drwxr-xr-x 4 vscode vscode  128 May 26 01:14 ..
-rw-r--r-- 1 vscode vscode 2554 May 26 01:14 review-cascade.md
```

-- directory listing of the only `references/` directory in the project

**Dependencies:** N/A -- only one reference file exists.
**Implicit contracts:** Reference files appear to be loaded by explicit instruction within the skill body, not by convention. This means adding a second reference file would require adding a corresponding `Read` instruction in the SKILL.md.

## Q9: What happens when a skill's trigger description overlaps with an existing skill's triggers -- does the system detect or warn about ambiguity, or does invocation order depend on something else?

**Answer:** NOT FOUND. The skill matching and dispatch logic is part of the Claude Code harness, which is external to this project. No code within this repository handles skill trigger matching, ambiguity detection, or dispatch ordering.

The system-reminder block in the conversation shows all skills listed with their descriptions. The harness documentation (embedded in tool descriptions) states: "Available skills are listed in system-reminder messages in the conversation" and "Only invoke a skill that appears in that list."

Search queries attempted:
- `find /workspaces/qrspi/.worktrees/RUS-6 -type f -name '*.py' -o -name '*.js' -o -name '*.ts'` -- found only Python scripts in `scripts/`, none related to skill dispatch
- No settings files exist in `.claude/` that configure dispatch behavior
- The Skill tool description states: "When users reference a 'slash command' or '/<something>', they are referring to a skill" -- but provides no details about ambiguity resolution

**Dependencies:** Skill dispatch is entirely owned by the Claude Code harness.
**Implicit contracts:** The project's skills avoid trigger overlap by using a consistent `qrspi-` prefix. Each skill targets a distinct phase of the QRSPI workflow. The `qrspi-work` skill is the broadest trigger (matches "work on", "continue", "pick up") and acts as a meta-dispatcher to the other phase skills.

## Q10: If a `SKILL.md` body exceeds the 500-line or 5000-token limit, does the skill-creator's eval loop catch this violation, or is it only enforced manually during review?

**Answer:** NOT FOUND in this project. No enforcement of a 500-line or 5000-token limit on SKILL.md files exists in any script, eval case, or configuration file in this repository (see Q6).

For reference, the longest SKILL.md in the project is `qrspi-work/SKILL.md` at 501 lines. Other skills range from approximately 37 to 58 lines.

Search queries attempted:
- Read all files in `scripts/` -- no SKILL.md size validation
- Read `evals/suite.json` and `evals/graphite-evals.json` -- no assertions on skill file size
- Read `run_loop.sh` -- no pre-flight size check before eval execution

**Evidence:**

```bash
$ wc -l .claude/skills/*/SKILL.md
  44 qrspi-design/SKILL.md
  53 qrspi-implement/SKILL.md
  37 qrspi-plan/SKILL.md
  43 qrspi-pr/SKILL.md
  47 qrspi-questions/SKILL.md
  58 qrspi-research/SKILL.md
  42 qrspi-structure/SKILL.md
  76 qrspi-ticket/SKILL.md
 501 qrspi-work/SKILL.md
  37 qrspi-worktree/SKILL.md
```

(Line counts approximate, derived from reading the files.)

**Dependencies:** None in this project.
**Implicit contracts:** The 500-line constraint, if enforced, would be enforced by the external skill-creator skill or by Claude Code itself. The `qrspi-work` skill at ~501 lines either slightly exceeds or is right at the boundary.

## Q11: How does the system behave when a skill references commands (e.g., `gt`) that are not installed on the current machine -- does skill loading fail, or is the failure deferred to invocation time?

**Answer:** Skill loading does not check for command availability. Skills are loaded as prompt text by the Claude Code harness. The `allowed-tools` frontmatter gates which tools the skill can call, but it does not verify that external CLIs invoked via `Bash` are installed.

Failure is deferred to invocation time. When a skill instructs the agent to run a command like `gt`, the agent would execute it via the Bash tool. If `gt` is not installed, the Bash tool would return a "command not found" error at runtime.

The `qrspi-work` skill explicitly addresses this scenario via its error handling rules:

**Evidence:**

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve
When ANY operation fails due to permissions, authentication,
configuration, or tooling errors (e.g., EACCES, permission denied,
auth token expired, config file inaccessible, tool not found):
1. STOP. Do not execute another command.
2. Print the exact error verbatim
3. Exit the skill.
```

-- `.claude/skills/qrspi-work/SKILL.md:479-483`

The `qrspi-implement` skill has a similar constraint:

```
8. HARD STOP on infrastructure errors. If ANY command fails with
   permissions, auth, config, or tooling errors (EACCES, permission
   denied, token expired, command not found, config inaccessible):
   print the exact failing command and exact error output, then STOP.
```

-- `.claude/skills/qrspi-implement/SKILL.md:29`

**Dependencies:** Skills depend on the runtime environment having necessary CLIs installed. The `qrspi-work` skill references both `gt` (Graphite CLI) and `gh` (GitHub CLI). The `allowed-tools` field includes `Bash` (unrestricted) for `qrspi-work` and `qrspi-implement`.
**Implicit contracts:** "command not found" is treated as an infrastructure error that triggers a hard stop. The agent is forbidden from attempting workarounds such as using raw `git` instead of `gt`.

## Q12: What eval harness infrastructure exists for testing skills, and what does a passing eval look like for a skill that wraps an external CLI tool?

**Answer:** The eval harness consists of six Python scripts and two JSON suite definitions:

**Scripts (`scripts/`):**
1. `run_eval.py` -- Executes eval cases in parallel (ThreadPoolExecutor), captures output, tokens, tool calls, transcripts. Currently a stub for agent execution.
2. `grade.py` -- Runs programmatic assertions (regex-based checks) and LLM judge assertions (stub). Computes weighted scores per case and suite.
3. `diagnose.py` -- Categorizes failures into 8 categories (MISSING_INSTRUCTION, CONFLICTING_INSTRUCTION, OVER_CONSTRAINED, UNDER_SPECIFIED, TOOL_MISUSE, CONTEXT_LOSS, MODEL_LIMITATION, EVAL_ISSUE).
4. `revise.py` -- Proposes targeted edits based on diagnosis. Applies edits as find-and-replace on skill text.
5. `report.py` -- Generates iteration reports with score trajectories, regression detection, plateau detection, overfitting alerts.
6. `check_scope.py` -- Validates implementation agent stayed within allowed file scope.

**Suites (`evals/`):**
1. `suite.json` -- 15 eval cases covering questions, research, design, structure, plan, worktree, implement, and PR phases. Uses 65/35 train/test split.
2. `graphite-evals.json` -- 5 eval cases specifically for a "graphite" skill. Tests commit, push, log, move, and sync operations.

**Evidence:**

For a CLI-wrapping skill, `graphite-evals.json` provides the only existing pattern. A passing eval checks:

```json
{
  "id": 1,
  "prompt": "I just made some changes to the auth module. commit my changes...",
  "assertions": [
    {"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
    {"text": "Includes --no-interactive flag", "type": "flag_check"},
    {"text": "Includes -m flag with a commit message", "type": "flag_check"},
    {"text": "Includes Co-Authored-By trailer", "type": "content_check"},
    {"text": "Checks git status or git diff before committing", "type": "workflow_check"}
  ]
}
```

-- `evals/graphite-evals.json:6-17`

The assertion types in `graphite-evals.json` (`command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`) differ from those in `suite.json` (`programmatic`, `llm_judge`, `script`). The `grade.py` script only handles the `suite.json` assertion types; there is no grading script for the `graphite-evals.json` assertion types.

**Dependencies:** `run_loop.sh` orchestrates the full pipeline. `scripts/` modules are independent and communicate via JSON on disk.
**Implicit contracts:** Eval cases in `suite.json` use `programmatic` assertions backed by regex functions in `grade.py`, plus `llm_judge` assertions that are currently stubs. The `graphite-evals.json` uses a different assertion schema with no corresponding grading implementation.

## Q13: Are there existing eval cases for other CLI-wrapping skills that can serve as a pattern for testing the Graphite CLI skill?

**Answer:** Yes. `evals/graphite-evals.json` contains 5 eval cases for a "graphite" skill. This is the only eval suite for a CLI-wrapping skill in the project.

The 5 cases test:
1. Committing changes (id: 1) -- verifies `gt create`/`gt modify` usage, flags, co-authorship trailer
2. Pushing PRs (id: 2) -- verifies `gt submit` usage, `--no-edit`, `--no-interactive`, confirmation before submit
3. Viewing stack (id: 3) -- verifies `gt log short`, read-only behavior
4. Moving branches (id: 4) -- verifies `gt move --onto`, post-operation verification
5. Syncing with main (id: 5) -- verifies `gt sync`, pre-flight `git status` check, `--delete-all` flag

**Evidence:**

```json
{
  "skill_name": "graphite",
  "evals": [
    {"id": 1, "prompt": "commit my changes with a message about adding JWT validation"},
    {"id": 2, "prompt": "push my PR so the team can review it"},
    {"id": 3, "prompt": "show me the current stack and what branch I'm on"},
    {"id": 4, "prompt": "move this branch so it stacks on top of feature-auth"},
    {"id": 5, "prompt": "sync with main and clean up any merged branches"}
  ]
}
```

-- `evals/graphite-evals.json:1-68` (summarized)

The assertion types used (`command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`) are descriptive labels without corresponding implementation in `grade.py`.

**Dependencies:** `graphite-evals.json` is standalone -- not referenced by `suite.json` or `run_loop.sh`.
**Implicit contracts:** The graphite evals use a simpler assertion format than `suite.json`. Each assertion has `text` (human-readable description) and `type` (category label), but no `check` function reference or `weight`. This suggests the graphite evals are designed for manual or LLM-judge-only grading, not the automated pipeline.

## Q14: Does the project emit any structured logs or telemetry when a skill is invoked, and if so, what fields identify the skill, the triggering input, and the outcome?

**Answer:** NOT FOUND within the project's own code. No file in this repository emits structured logs or telemetry upon skill invocation.

The eval harness captures execution metadata (`duration_ms`, `tokens`, `tool_calls`, `transcript`) per trial in `run_eval.py`, but this is eval infrastructure, not production skill invocation telemetry.

The `revise.py` script writes a `revision-log.json` that tracks revision history, and `report.py` generates a `ledger.json` with score progressions. These are eval iteration tracking, not invocation telemetry.

Search queries attempted:
- Read all Python scripts in `scripts/` -- no logging/telemetry modules
- Read all SKILL.md files -- no instrumentation instructions
- No `logging`, `structlog`, `opentelemetry`, or similar imports in any script

**Evidence:**

The closest thing to invocation telemetry is the `ExecutionResult` dataclass in `run_eval.py`:

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

-- `scripts/run_eval.py:19-29`

This captures eval-time execution data but is not emitted during normal skill invocation.

**Dependencies:** Any invocation telemetry would be provided by the Claude Code harness, which is external.
**Implicit contracts:** The project does not depend on or consume invocation telemetry from the harness. Skills are fire-and-forget from a telemetry perspective.

## Discovered Patterns

1. **Consistent frontmatter schema across all skills.** Every SKILL.md uses exactly 5 frontmatter fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. No skill deviates from this pattern or adds extra fields.

2. **Tool restriction as a security boundary.** The `allowed-tools` field varies significantly per skill. Research-phase skills get read-only tools (`Read, Glob, Grep, Bash(find:*), Bash(wc:*)`), while implementation skills get full `Bash` and `Write`/`Edit` access. This creates a least-privilege model where each phase can only access tools appropriate to its role.

3. **Artifact chain with explicit handoff.** Each SKILL.md ends with an "After writing" message telling the user what to do next. The chain is: ticket -> questions -> research -> design -> structure -> plan -> worktree -> implement -> PR. Each skill reads only its required upstream artifacts and writes exactly one output artifact.

4. **Upload-to-Linear as a common postscript.** 8 of 10 skills include an identical "Upload artifact" section at the end. The upload pattern is: get file size -> prepare attachment -> curl PUT -> create attachment from upload. The upload is documented as non-blocking (failure does not fail the phase).

5. **Two eval suite formats coexist.** `suite.json` uses `{type, check, weight}` assertions with function references parseable by `grade.py`. `graphite-evals.json` uses `{text, type}` assertions with descriptive labels. These are incompatible formats with no shared grading infrastructure.

6. **Stub architecture in eval scripts.** Both `run_eval.py` (agent execution) and `grade.py` (LLM judge) contain placeholder implementations marked with comments. The `revise.py` revision proposals also require a "meta-agent" that is not yet integrated. The pipeline structure is complete but the execution layer is not.

7. **Error handling is prompt-based, not code-based.** The hard-stop error handling rules in `qrspi-work` and `qrspi-implement` are instructions in the prompt text, not enforced by code. There is no wrapper or harness code that catches errors and enforces the stop behavior.

8. **Graphite CLI (`gt`) as the exclusive git interface.** The `qrspi-work` skill mandates `gt` commands with `--no-interactive` flags for all git operations. Raw `git` is permitted only for `git add` and `git status --short`. Using raw `git` when a `gt` equivalent exists is explicitly forbidden.

## Inconsistencies

1. **`graphite-evals.json` assertion format vs `suite.json` assertion format.** The two eval suites use incompatible assertion schemas. `suite.json` uses `{type: "programmatic", check: "function_call()", weight: N}` while `graphite-evals.json` uses `{text: "description", type: "command_check"}`. The `grade.py` grading script can only process `suite.json` format assertions. There is no grading implementation for `graphite-evals.json`.

2. **`graphite-evals.json` references a skill that does not exist.** The eval file specifies `"skill_name": "graphite"` but no skill directory `.claude/skills/graphite/` exists. The file appears to be a forward-looking eval definition for a skill not yet created.

3. **`qrspi-work` SKILL.md may exceed the 500-line convention.** The `qrspi-work/SKILL.md` file is approximately 501 lines, which is at or above the 500-line limit referenced in the questions. No other skill exceeds 80 lines.

4. **`allowed-tools` in `graphite-evals.json` assertion says `-a` or `-u` flag expected, but `qrspi-work/SKILL.md` explicitly forbids the `-a` flag.** Eval case 1 in `graphite-evals.json` asserts: "Includes -a or -u flag to stage changes." However, `qrspi-work/SKILL.md` lines 444-457 contain a section titled "Staging -- NEVER use `-a` flag" that explicitly forbids this. These two files contradict each other on whether `-a` is acceptable behavior.

5. **`run_loop.sh` references `$SKILL_PATH` as a generic path, but the project only has skills at `.claude/skills/<name>/SKILL.md`.** The script documentation example uses `.qrspi/agents/01-questions.md`, which is a path convention that does not exist in the current project. The `.qrspi/agents/` directory does not exist.
