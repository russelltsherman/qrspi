# Research — Create a new agent skill called writing bash scripts

**Questions source:** `.qrspi/RUS-5/questions.md`
**Generated:** 2026-05-27
**Status:** complete

---

## Q1: What is the directory structure, file naming conventions, and frontmatter schema that the existing skill definitions follow in this project?

**Answer:** Skills follow the `skill-creator` standard structure defined in `/home/vscode/.claude/skills/skill-creator/SKILL.md` lines 75-83. Each skill is a directory containing a `SKILL.md` file with YAML frontmatter followed by Markdown body.

**Evidence:**

Directory structure (from skill-creator SKILL.md line 75-83):
```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

Frontmatter schema (from `qrspi-questions/SKILL.md` lines 1-5):
```yaml
---
name: qrspi-questions
description: "Generate technical questions from a Linear ticket. Use to produce structured questions for any ticket, covering data flow, API surface, state management, edge cases, testing, and observability."
command: /qrspi-questions
argument-hint: "<ticket-id>"
---
```

Frontmatter fields observed across all project skills (`.claude/skills/`):
- `name` (required): Skill identifier, matches directory name
- `description` (required): When to trigger and what it does, ~100 words
- `command` (required): Slash command prefix (e.g., `/qrspi-questions`)
- `argument-hint` (optional): Expected argument format (e.g., `<ticket-id>`)

Skills are located in `.claude/skills/<skill-name>/` relative to the worktree root. The project has 10 skills:
- `qrspi-work/` (638 lines, orchestrator), `qrspi-worktree/` (24 lines), `qrspi-research/` (48 lines), `qrspi-ticket/` (76 lines), `qrspi-design/` (34 lines), `qrspi-implement/` (43 lines), `qrspi-plan/` (27 lines), `qrspi-structure/` (32 lines), `qrspi-questions/` (37 lines), `qrspi-pr/` (34 lines)

**Dependencies:** None. This is a structural fact about the project.

**Implicit contracts:**
- The `command` field value becomes the slash command (`/qrspi-questions` invokes the skill named `qrspi-questions`).
- The `argument-hint` value is passed as `$ARGUMENTS` to the skill (used in `qrspi-worktree/SKILL.md` line 13: `.qrspi/$ARGUMENTS/worktree.md`).
- `SKILL.md` bodies should ideally stay under 500 lines (skill-creator SKILL.md line 90).

---

## Q2: What content and structure do the existing skill `SKILL.md` files contain, and what tokens/lines do they typically use?

**Answer:** SKILL.md files contain YAML frontmatter (3-5 fields) followed by Markdown body with structured sections: purpose, when to trigger, step-by-step instructions, code templates, and conventions. Line counts vary from 24 to 638.

**Evidence:**

Line counts for all project skills:
- `qrspi-work/SKILL.md`: 638 lines (largest, orchestrator with full ticket lifecycle, worktree setup, Linear states, sub-agent dispatch, cleanup)
- `qrspi-ticket/SKILL.md`: 76 lines (guided ticket authoring via Linear API)
- `qrspi-research/SKILL.md`: 48 lines (maps codebase facts)
- `qrspi-implement/SKILL.md`: 43 lines (vertical slice implementation)
- `qrspi-questions/SKILL.md`: 37 lines (question generation with category requirements)
- `qrspi-structure/SKILL.md`: 32 lines (vertical slices with types and contracts)
- `qrspi-design/SKILL.md`: 34 lines (design document generation)
- `qrspi-pr/SKILL.md`: 34 lines (PR summary generation)
- `qrspi-plan/SKILL.md`: 27 lines (atomic implementation steps)
- `qrspi-worktree/SKILL.md`: 24 lines (session-aware task DAG)

Common content patterns across all skills:
- `---` frontmatter delimiter
- `description` field contains trigger phrases (what user would say)
- Section headers: `## Purpose`, `## When to use`, `## Steps`, `## Output`
- Code blocks for file paths, commands, and templates
- References to other skills (e.g., `qrspi-work` references `qrspi-worktree/SKILL.md`)
- Output path conventions: artifacts written to `.qrspi/<ticket-id>/<artifact>.md`

The `qrspi-work/SKILL.md` is the only skill exceeding 500 lines (the skill-creator ideal). It contains embedded Bash code for worktree setup (lines 29-78), sub-agent prompts with workspace scoping (lines 514-527), and Linear state machine logic.

**Dependencies:**
- `qrspi-work` references: `qrspi-worktree/SKILL.md`, `qrspi-research/SKILL.md`, `qrspi-design/SKILL.md`, `qrspi-structure/SKILL.md`, `qrspi-plan/SKILL.md`, `qrspi-pr/SKILL.md`

**Implicit contracts:**
- Skills reference each other by relative path from worktree root (`.claude/skills/<name>/SKILL.md`).
- Artifact output paths follow `.qrspi/<ticket-id>/<phase>.md` convention.
- The description field is Claude's primary trigger mechanism — it must contain both what the skill does AND specific trigger phrases (skill-creator SKILL.md line 67).

---

## Q3: What does the `skill-creator` skill produce when invoked, and how does its output differ from a hand-written skill?

**Answer:** skill-creator produces: (1) SKILL.md with frontmatter, (2) eval harness directory with test cases, (3) iterative benchmark workspace, (4) optionally optimized description. Its outputs include structural artifacts (evals/, timing.json, grading.json, benchmark.json) that hand-written skills would not include.

**Evidence:**

skill-creator SKILL.md output structure (lines 167-252):

Workspace layout:
```
<skill-name>-workspace/
├── iteration-1/
│   ├── eval-0/
│   │   ├── with_skill/outputs/
│   │   ├── without_skill/outputs/ (baseline for new skill)
│   │   ├── eval_metadata.json
│   │   └── timing.json
│   ├── eval-1/
│   └── ...
├── skill-snapshot/  (for improving existing skills)
├── benchmark.json   (aggregated pass rates, timing, tokens)
├── benchmark.md
└── feedback.json    (human review from viewer)
```

Eval file format (`evals.json`, lines 147-159):
```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

Eval metadata per run (`eval_metadata.json`, lines 190-197):
```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

Timing data captured on run completion (`timing.json`, lines 208-217):
```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

Grading results (`grading.json`, lines 225):
- Each assertion has `text`, `passed`, and `evidence` fields.

Benchmark aggregation (lines 227-232):
- `benchmark.json` with pass_rate, time, tokens per configuration, mean +/- stddev, and delta.
- Produced by: `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>`

Description optimization output (lines 380-394):
- `run_loop.py` produces JSON with `best_description` selected by test score.
- Eval queries: 20-25 queries mix of should-trigger and should-not-trigger.

**Differences from hand-written skills:**
- Hand-written skills produce only SKILL.md + optional references/ and scripts/.
- skill-creator adds: eval harness (evals.json), timing/grading/benchmark tracking, iterative benchmark workspace with iteration directories, baseline comparison runs, and description optimization via `run_loop.py`.
- The eval infrastructure saves `timing.json`, `grading.json`, `benchmark.json`, `benchmark.md`, and `feedback.json` — none of which are part of the skill itself.

**Dependencies:**
- Depends on `/home/vscode/.claude/skills/skill-creator/` (486 lines + `references/schemas.md` 431 lines + `eval-viewer/generate_review.py` + `scripts/aggregate_benchmark.py` + `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md`)
- Depends on `claude` CLI tool for `run_loop.py` description optimization (line 380)

**Implicit contracts:**
- `timing.json` is only captured at run completion notification — not persisted elsewhere (line 219).
- The `eval_metadata.json` directory name should match the descriptive eval name (line 188).
- For existing skill improvements, baseline is the `skill-snapshot/` of the old version.
- Grading output must use exact field names `text`, `passed`, `evidence` — the viewer depends on this (line 225).

---

## Q4: What is the `agentskills.io` standard pattern for agent skill directory structure, and what fields are required in SKILL.md frontmatter?

**Answer:** NOT FOUND. No references to `agentskills.io` exist anywhere in the project codebase, eval harness, or global skills directory. The only mention is in `questions.md` itself.

**Evidence:** Searched all files:
- `grep -ri "agentskills" /workspaces/qrspi/ --include="*.md" --include="*.json" --include="*.py" --include="*.sh"` — returns only `questions.md`
- `grep -ri "agentskills" /home/vscode/.claude/skills/ --include="*.md" --include="*.json" --include="*.py" --include="*.sh"` — returns nothing
- `grep -rn "agentskills.io\|agentskills_io" /home/vscode/.claude/skills/writing-bash-scripts/` — returns nothing

The `skill-creator` skill (line 73-83) defines the standard pattern independently, and there is no reference to an external `agentskills.io` specification anywhere.

**Dependencies:** Cannot determine — source not found in codebase.

**Implicit contracts:** None discoverable. The skill format observed in this project appears to be a project-local standard, not one sourced from an external spec.

---

## Q5: What parameters, invocation syntax, and output format does the `skill-creator` skill accept?

**Answer:** skill-creator is a Claude Code skill invoked implicitly by matching its description. It accepts no command-line parameters — it operates through conversation with the user, producing files on the filesystem.

**Evidence:**

skill-creator SKILL.md (lines 1-4):
```yaml
---
name: skill-creator
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
---
```

There is no `command` field — skill-creator is invoked by description matching, not a slash command.

skill-creator invokes these subprocess tools:
- `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>` (line 229)
- `python <skill-creator-path>/eval-viewer/generate_review.py <workspace>/iteration-N --skill-name <name> --benchmark <benchmark.json> [--previous-workspace <workspace>/iteration-N-1] [--static <output_path>]` (lines 238-244)
- `python -m scripts.run_loop --eval-set <path> --skill-path <path> --model <model> --max-iterations 5 --verbose` (lines 382-388)
- `python -m scripts.package_skill <path/to/skill-folder>` (line 413)

**Output format:**
1. `SKILL.md` — YAML frontmatter + Markdown body
2. `evals/evals.json` — test cases with prompts and assertions
3. `<skill-name>-workspace/iteration-N/` — benchmark runs with timing/grading
4. `benchmark.json` — aggregated pass rates, timing, tokens
5. `benchmark.md` — human-readable benchmark summary
6. `feedback.json` — human review from viewer
7. Optimized description JSON from `run_loop.py`

**Dependencies:**
- `claude` CLI tool (for `run_loop.py` description optimization)
- Python 3 with scripts in `skill-creator/scripts/`
- Browser or static HTML fallback for `generate_review.py` viewer

**Implicit contracts:**
- `--static` mode writes standalone HTML; user clicks "Submit All Reviews" which downloads `feedback.json` as a file (line 247).
- `timing.json` must be captured immediately at run completion — not persisted elsewhere (line 219).
- Grading assertions use exact field names: `text`, `passed`, `evidence` (line 225).

---

## Q6: Where are generated skill artifacts stored and how are they discovered or loaded by the agent harness at runtime?

**Answer:** Skills are stored in `.claude/skills/<name>/` within each worktree. The agent harness (Claude Code) discovers them automatically from this directory. Generated eval artifacts go to `results/<version>/` (run_loop) or `<skill-name>-workspace/iteration-N/` (skill-creator).

**Evidence:**

Skill storage locations (from worktree):
- Project-local: `/workspaces/qrspi/.worktrees/RUS-5/.claude/skills/` — contains 10 qrspi-* skills
- Global: `/home/vscode/.claude/skills/` — contains 6 skills (graphite-workspace, mcp-builder, skill-creator, using-graphite-cli, workflow-creator, writing-bash-scripts)

The `qrspi-work/SKILL.md` worktree setup (lines 27-31) establishes:
- `REPO_ROOT` = absolute path to main repo (where `.git/` lives)
- `WORKTREE_PATH` = `<REPO_ROOT>/.worktrees/<ticket-id>`

Sub-agent scoping (lines 525-527):
> "All sub-agents are scoped to the ticket's worktree directory (`WORKTREE_PATH`). Include this absolute path in every sub-agent prompt. Sub-agents must not read, explore, or reference files outside the worktree."

The project `CLAUDE.md` (line 39):
> "Agent prompt definitions live in `.qrspi/agents/`"

However, this path does not exist in any worktree. The actual skill storage is `.claude/skills/` not `.qrspi/agents/`. The `CLAUDE.md` documentation may be stale or refer to a different convention.

Eval artifact storage:
- `run_loop.sh` (line 34): `OUTPUT_DIR="results/${VERSION}"` — results written to `results/v1/`, `results/v2/`, etc.
- `run_eval.py` (line 152): `os.makedirs(config.output_dir, exist_ok=True)` — results directory created per run
- `scripts/run_eval.py` (line 209): `output_path = os.path.join(config.output_dir, "results.json")` — results written as JSON

**Dependencies:**
- Claude Code runtime handles skill discovery from `.claude/skills/` — this is implicit, not documented in codebase files.
- Sub-agents inherit worktree scoping from parent skill prompts.

**Implicit contracts:**
- Skills in `.claude/skills/` are discovered by Claude Code automatically — no manifest or configuration file is used.
- The absence of `.qrspi/agents/` directory suggests either the convention changed or the documentation is out of sync.
- `.worktrees/` is gitignored (line 35 of CLAUDE.md), so worktree artifacts are local-only.

---

## Q7: Are skills scoped per-worktree, per-user, or workspace-wide, and does this affect where the new skill file is placed?

**Answer:** Skills exist at two levels: global (per-user, in `/home/vscode/.claude/skills/`) and local (per-worktree, in `.claude/skills/`). Both levels are active simultaneously. The new skill should be placed in the global directory since it is a general-purpose skill, not ticket-specific.

**Evidence:**

Two skill directories observed:
- Global: `/home/vscode/.claude/skills/` — 6 skills shared across all worktrees
  - `graphite-workspace`, `mcp-builder`, `skill-creator`, `using-graphite-cli`, `workflow-creator`, `writing-bash-scripts`
- Worktree-local: `/workspaces/qrspi/.worktrees/RUS-5/.claude/skills/` — 10 qrspi-* skills
  - `qrspi-design`, `qrspi-implement`, `qrspi-plan`, `qrspi-pr`, `qrspi-questions`, `qrspi-research`, `qrspi-structure`, `qrspi-ticket`, `qrspi-work`, `qrspi-worktree`

The `qrspi-work/SKILL.md` worktree setup code (lines 36-41) shows worktree-local operations:
```bash
if [ -d "<WORKTREE_PATH>" ]; then
  cd "<WORKTREE_PATH>"
  ...
  Print: "Using existing worktree at `.worktrees/<ticket-id>/`"
```

Worktree isolation (CLAUDE.md lines 31-35):
> "Each ticket gets an isolated git worktree at `.worktrees/<ticket-id>/`. This allows multiple agents to work on different tickets concurrently. The main repo checkout stays on `main`; all ticket work happens in worktrees. `.worktrees/` is gitignored."

No `settings.json` exists in the worktree to configure skill loading paths. The `.gitignore` only contains `.worktrees/`.

**Dependencies:**
- Claude Code's skill loading mechanism (not documented in codebase)
- Global vs local skill scoping is an implicit runtime behavior of Claude Code

**Implicit contracts:**
- Global skills (`/home/vscode/.claude/skills/`) apply to all worktrees and the main repo.
- Worktree-local skills (`.claude/skills/`) override or supplement global skills within that specific worktree.
- `qrspi-*` skills are worktree-local because they are ticket-specific workflow orchestrators.
- `writing-bash-scripts` is a global skill because it is general-purpose, not ticket-specific.

---

## Q8: When a skill's guidance conflicts with an existing project convention (e.g., the project may have its own bash style), which takes precedence — the skill or the project convention?

**Answer:** NOT explicitly documented. No override mechanism exists in the codebase for skill-vs-convention conflicts. The implicit precedence appears to be: project convention within a worktree > global skill, because sub-agents are scoped to the worktree directory and cannot access files outside it.

**Evidence:**

No conflict resolution mechanism found anywhere in:
- `skill-creator/SKILL.md` — no mention of convention override
- `qrspi-work/SKILL.md` — no override mechanism for skill-vs-project conflicts
- `.claude/settings.json` — file does not exist
- `.gitignore` — only contains `.worktrees/`
- `CLAUDE.md` — no override mechanism documented

The writing-bash-scripts skill (SKILL.md) and project-local skills (e.g., `qrspi-*`) could potentially conflict on conventions. However:
- The `qrspi-*` skills do not contain bash scripting conventions — they are workflow orchestrators
- The `writing-bash-scripts` skill is the only bash-specific skill, and it provides conventions that apply when writing `.sh` files

The `qrspi-work/SKILL.md` sub-agent scoping (lines 525-527) restricts sub-agents to the worktree directory, which implicitly limits their access to project-local conventions but does not address skill-vs-convention conflicts.

**Dependencies:** None — this is a gap in the documented conventions.

**Implicit contracts:**
- Since no override mechanism exists, the pragmatic approach is: worktree-local conventions take precedence for worktree-local work, global skills apply to global/general work.
- The `writing-bash-scripts` skill conventions (strict mode, quoting, ShellCheck) are likely the de facto project standard for any bash scripts, since it is the only bash-specific skill and the conventions align with standard shell best practices.

---

## Q9: How should the skill handle bash 3.2 (macOS default) versus bash 4+ feature requests — does it produce conditional code, or does it document the incompatibility and refuse to generate it?

**Answer:** The `writing-bash-scripts` skill handles this through documentation and fallback patterns rather than conditional code generation. It documents which features are unavailable in bash 3.2 and provides POSIX-compatible or cross-version alternatives. It also provides an explicit version check pattern for scripts that require bash 4+.

**Evidence:**

writing-bash-scripts `references/gotchas.md` (lines 91-125):

> "macOS ships bash 3.2 (2007) due to GPLv3 licensing. Many modern features require bash 4+."

Feature availability table (lines 96-105):
| Feature | Requires | Alternative |
|---|---|---|
| Associative arrays (`declare -A`) | bash 4.0 | Use parallel indexed arrays or `case` |
| `mapfile` / `readarray` | bash 4.0 | Use `while IFS= read -r` loop |
| `${var,,}` lowercase | bash 4.0 | `tr '[:upper:]' '[:lower:]'` |
| `${var^^}` uppercase | bash 4.0 | `tr '[:lower:]' '[:upper:]'` |
| `&>>` append redirect stderr+stdout | bash 4.0 | `>> file 2>&1` |
| `|&` pipe stderr | bash 4.0 | `2>&1 |` |
| Negative array indexing `${arr[-1]}` | bash 4.3 | `${arr[${#arr[@]}-1]}` |
| `declare -n` namerefs | bash 4.3 | Pass variable name and use `eval` |

Bash version check pattern (lines 109-114):
```bash
if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
  echo "This script requires bash 4+. Found: ${BASH_VERSION}" >&2
  exit 1
fi
```

bash 3.2 empty array gotcha (lines 118-125):
```bash
# Fails in bash 3.2 with set -u if arr is empty
# Safest pattern:
for item in "${arr[@]+"${arr[@]}"}"; do
  echo "$item"
done
```

The skill does NOT produce conditional code (e.g., `if bash_version_ge 4; then ...`). Instead:
1. The SKILL.md body documents the default conventions (strict mode, quoting, etc.)
2. The `references/gotchas.md` file documents bash 3.2 vs 4+ incompatibilities with alternatives
3. The pattern provided for scripts that specifically need 4+ is an explicit version check that exits with an error — not conditional code generation

**Dependencies:**
- Depends on `BASH_VERSINFO` array (available in all bash versions)
- Cross-version alternatives use POSIX-compatible tools (`tr`, `while read`)

**Implicit contracts:**
- The skill treats bash 3.2 as the minimum target. If a feature requires 4+, it provides the alternative pattern rather than generating version-conditional code.
- The `references/gotchas.md` is loaded only when portability is relevant (SKILL.md line 20-21: "If dealing with portability... read `references/gotchas.md`").
- Scripts that are known to require bash 4+ can use the explicit version check and exit pattern.

---

## Q10: What happens when the generated script exceeds the ~200 line threshold the skill mentions — does the skill truncate, warn, or suggest switching languages mid-output?

**Answer:** NOT FOUND. The `writing-bash-scripts` skill does NOT mention a 200-line threshold anywhere. The skill-creator skill mentions a 500-line threshold for SKILL.md files (not scripts), advising to add additional hierarchy if approaching the limit. No line-count enforcement or truncation logic exists in any skill.

**Evidence:**

Searched `writing-bash-scripts/`:
- `grep -n "200 line\|200-line\|line count" SKILL.md references/` — no matches
- `grep -n "500 line\|500-line\|line count" SKILL.md references/` — no matches (writing-bash-scripts does not mention line limits)

Searched skill-creator:
- Line 90: "SKILL.md body - In context whenever skill triggers (<500 lines ideal)"
- Line 96: "Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up."
- Line 98: "For large reference files (>300 lines), include a table of contents"

These 500-line and 300-line thresholds apply to SKILL.md files and reference files respectively, not to generated bash scripts. No threshold exists for generated scripts.

The writing-bash-scripts skill provides a `template.sh` (105 lines) as a structural example, and recommends keeping functions under ~40 lines (SKILL.md line 205), but there is no overall script line-count limit.

**Dependencies:** None — the 200-line threshold referenced in questions.md does not exist in any skill definition found.

**Implicit contracts:** None. The question may reference a threshold from an external spec (agentskills.io, which is NOT FOUND in this codebase) or from a different version of the skill.

---

## Q11: How are existing skills tested in this project — are there eval harnesses, regression tests, or human-review checklists for skill quality?

**Answer:** Skills are tested via a Python-based eval harness (`run_eval.py`) with a JSON test suite (`evals/suite.json`), executed through a bash optimization loop (`run_loop.sh`). The harness runs each test case multiple trials in parallel, captures outputs and metrics, then grades results using `grade.py`. The skill-creator adds a second, more sophisticated eval layer with baseline comparisons, benchmark viewer, and human feedback loops.

**Evidence:**

Project eval harness (`evals/suite.json`): 781 lines, 15 eval cases across all QRSPI phases (questions, research, design, structure, plan, worktree, implement, pr). Each case has:
- `id`: unique identifier
- `prompt`: task description
- `context`: conversation history and fixture files
- `assertions`: programmatic and LLM-judge assertions

Eval runner (`scripts/run_eval.py`): 241 lines
- Loads suite and skill
- Builds message sequences for each test case
- Runs each case x trials in parallel via `ThreadPoolExecutor`
- Captures: output, files, duration_ms, tokens, tool_calls, transcript, error
- Writes results as JSON to output directory

Optimization loop (`run_loop.sh`): 122 lines
```bash
./run_loop.sh <skill_path> <eval_suite> [max_iterations] [target_score]
# Example: ./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85
```
Steps per iteration: (1) run evals, (2) grade, (3) check target score, (4) diagnose failures, (5) propose revisions

Grading (`scripts/grade.py`): 141 lines
- Reads results.json and suite.json
- Evaluates assertions
- Produces `grades.json` with test_score

skill-creator eval loop (`skill-creator/SKILL.md` lines 163-289):
- Spawns with-skill AND baseline subagents in parallel
- Captures timing.json on run completion
- Grades assertions via grader subagent
- Aggregates benchmark.json with pass_rate, time, tokens
- Opens browser viewer (`generate_review.py`) for human review
- Collects `feedback.json` from user reviews
- Iterates until satisfied

Additional scripts:
- `scripts/diagnose.py` — analyzes grading results to find failure patterns
- `scripts/revise.py` — proposes skill revisions based on diagnosis
- `scripts/check_scope.py` — validates implementation scope
- `scripts/report.py` — generates final report from results directory

Fixture files (`evals/fixtures/`): 4 ticket fixtures
- `ticket_rest_endpoint.md`, `ticket_multi_tenancy.md`, `ticket_websocket.md`, `ticket_15_acceptance_criteria.md`

**Dependencies:**
- Python 3 (all harness scripts)
- `evals/suite.json` (15 cases)
- `evals/fixtures/` (4 ticket files)
- skill-creator requires `claude` CLI tool for description optimization
- skill-creator viewer requires browser or `--static` fallback

**Implicit contracts:**
- `scripts/run_eval.py` is a stub — the agent execution block is a placeholder with TODO comments (lines 117-131). The actual agent invocation is not wired up.
- Grading assertions use `text`, `passed`, `evidence` fields — viewer depends on exact schema.
- The optimize loop targets a score threshold (default 0.85) and stops when reached or after max iterations.
- Regression detection triggers a rollback (5% threshold: `prev - curr > 0.05`).

---

## Q12: What ShellCheck versions and rule sets are configured in this project, and are there any intentional exceptions?

**Answer:** No project-wide ShellCheck configuration (e.g., `.shellcheckrc`) exists in the codebase. The `writing-bash-scripts` skill documents ShellCheck compliance as a delivery requirement and provides inline suppression directives for known false positives. The only flag used is `-x` (follow source directives).

**Evidence:**

ShellCheck invocation in `writing-bash-scripts/SKILL.md` (lines 258-273):
```bash
shellcheck -x my_script.sh
```

Inline suppression pattern (lines 264-271):
```bash
# shellcheck disable=SC2206
local -a lines=($output)
```

Rules documented in `references/gotchas.md`:
- SC2086 — Double-quote to prevent globbing and word splitting
- SC2046 — Quote command substitution to prevent word splitting
- SC2155 — Declare and assign separately
- SC2164 — Use `cd ... || exit` in case cd fails
- SC2034 — Variable appears unused (shown with disable example)
- SC2029 — Variable in single-quoted ssh command

Rules documented in `references/conventions.md`:
- SC2155 — do not combine `local`/`export` with command substitution

No `.shellcheckrc` or project-level ShellCheck config found:
- `find /workspaces/qrspi/.worktrees/RUS-5 -name ".shellcheckrc"` — no results
- `grep -rn "shellcheck" /workspaces/qrspi/.worktrees/RUS-5/scripts/*.py` — no matches in eval scripts

The skill-creator documentation mentions ShellCheck compliance (line 258: "Target zero warnings") but no exceptions list or rule configuration.

**Dependencies:**
- Depends on ShellCheck being installed on the system (not enforced by code)
- Inline suppressions use `shellcheck disable=SCnnnn` syntax (standard ShellCheck directive format)

**Implicit contracts:**
- The `-x` flag means `source` directives are followed, so ShellCheck analyzes sourced files too.
- Suppressions are per-line, not global. Every suppression requires a comment explaining why.
- The convention of "target zero warnings" is documented in the skill but not enforced by automation in the project codebase.
- No version pinning for ShellCheck — no `.shellcheckrc` or CI configuration found.

---

## Q13: How is skill usage tracked or measured in this project — is there telemetry, usage logging, or a way to determine which skills are invoked most frequently?

**Answer:** NOT FOUND. No telemetry, usage logging, or skill invocation tracking mechanism exists in the project codebase, eval harness, or global skills.

**Evidence:**

Searched for telemetry/tracking in:
- `scripts/run_eval.py` — captures `tokens`, `duration_ms`, `tool_calls` per eval trial, but this is eval-specific, not general skill usage tracking
- `scripts/grade.py` — no tracking
- `scripts/diagnose.py` — no tracking
- `scripts/revise.py` — no tracking
- `scripts/report.py` — generates report from results directory, not general usage
- `run_loop.sh` — no tracking
- `evals/suite.json` — no tracking
- `skill-creator/SKILL.md` — captures `total_tokens` and `duration_ms` for individual eval runs via `timing.json`, but this is bounded to the eval loop, not general skill usage

The `timing.json` format (skill-creator line 208-217):
```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

This is captured per-eval-run in the skill-creator eval loop. It measures tokens and duration for individual test cases, not overall skill usage frequency.

No configuration files, logs, or API endpoints for skill invocation tracking were found anywhere in the project or global skills directory.

**Dependencies:** None — this is an absence of capability.

**Implicit contracts:**
- The project has no observable mechanism for tracking which skills are used, how often, or in what contexts.
- Token/duration tracking exists only within the bounded scope of the eval harness, not for general Claude Code skill invocations.
- If skill usage tracking is needed, it would require adding a new mechanism (e.g., Claude Code's built-in usage logs, a custom MCP server, or an external telemetry service).

---

## Discovered Patterns

1. **Two-tier skill scoping:** Global skills (`/home/vscode/.claude/skills/`) provide general-purpose guidance applicable across all worktrees. Worktree-local skills (`.claude/skills/`) are ticket-specific workflow orchestrators. New general-purpose skills belong in the global directory.

2. **Progressive disclosure architecture:** Skills use a three-level loading system: frontmatter metadata (~100 words, always in context) → SKILL.md body (<500 lines) → bundled resources (scripts/, references/, assets/, loaded only when needed).

3. **YAML frontmatter is the trigger mechanism:** The `description` field in SKILL.md frontmatter is Claude's primary discovery mechanism. It must include both what the skill does AND specific trigger phrases. No other discovery mechanism (manifest files, settings.json, etc.) exists.

4. **Artifact path convention:** All QRSPI phase artifacts follow `.qrspi/<ticket-id>/<artifact>.md` convention. Skills reference output paths explicitly (e.g., `Produce .qrspi/$ARGUMENTS/worktree.md`).

5. **Eval harness is worktree-local:** Eval suites and fixtures live in `evals/suite.json` and `evals/fixtures/` within each worktree. The harness is invoked via `run_loop.sh` from the worktree root.

6. **Sub-agent scoping via directory restriction:** Parent skills (e.g., `qrspi-work`) pass `WORKTREE_PATH` to sub-agents and instruct them to operate only within that directory. This is the project's isolation mechanism.

7. **Inline script conventions:** All bash scripts in the project follow `set -euo pipefail`, `#!/usr/bin/env bash`, and use functions with `local` declarations. No project-level linter config exists.

## Inconsistencies

1. **Stale documentation path:** `CLAUDE.md` states "Agent prompt definitions live in `.qrspi/agents/`" (line 39), but this directory does not exist. Skills are actually in `.claude/skills/`. The `.qrspi/agents/` path is never created or referenced by any skill code.

2. **No shellcheckrc or version pinning:** The writing-bash-scripts skill says "Target zero warnings" for ShellCheck, but there is no project configuration (.shellcheckrc) to enforce this, no CI linting step, and no version pinning. Compliance is enforced only by convention, not automation.

3. **Eval harness is stubbed:** `scripts/run_eval.py` lines 117-131 contain a placeholder implementation with TODO comments. The `agent.run()` call is not wired up — actual execution falls through to `result.transcript = messages` (line 137). The harness defines the structure but does not execute real agent runs.

4. **200-line threshold question references non-existent constraint:** Question Q10 references a "~200 line threshold" in the writing-bash-scripts skill, but no such threshold exists in the skill or anywhere else in the codebase. The 500-line limit in skill-creator applies to SKILL.md files, not scripts.

5. **agentskills.io is not in the codebase:** Question Q4 references "agentskills.io" as the standard for skill directory structure and frontmatter. This domain does not appear anywhere in the project codebase, global skills, or eval harness. The skill format used here appears to be a project-local convention derived from skill-creator, not an external spec.

6. **No settings.json for skill configuration:** Worktrees do not contain `.claude/settings.json` (verified absent). Skill loading is handled by Claude Code's default mechanism, not by project configuration. This means skill scoping behavior depends on Claude Code's implicit behavior rather than explicit configuration.
