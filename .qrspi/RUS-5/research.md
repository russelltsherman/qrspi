# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: The skill follows the agentskills.io directory structure with SKILL.md plus optional references/, scripts/, assets/. Where in the `.qrspi/agents/` directory should the `writing-bash-scripts` skill be placed, and what is the exact invocation wrapper convention used to call this skill from other agents?
  **Target:** `.qrspi/agents/` directory and the skill-creator skill at `.qrspi/agents/skill-creator/`

**Answer:** The `.qrspi/agents/` directory does not exist in the codebase. Skills and agents are stored in two separate locations within the Claude Code harness directories:

- Skills live in `.claude/skills/<skill-name>/SKILL.md` (with optional subdirectories like `references/`).
- Agent prompt definitions live in `.claude/agents/<agent-name>.md`.

The `writing-bash-scripts` skill directory exists at `/workspaces/qrspi/.claude/skills/writing-bash-scripts/` but currently has NO `SKILL.md` file — only an empty `references/` subdirectory. There is no `skill-creator` skill or agent directory anywhere in the repository.

The invocation wrapper convention used by existing skills is:
1. A `SKILL.md` file contains YAML frontmatter with `name`, `description`, `command`, `argument-hint`, and `allowed-tools` keys.
2. The body describes steps, often spawning sub-agents via the `Agent` tool with `subagent_type`.
3. The `command` field (e.g., `/qrspi-design`) is how the skill is invoked by users.
4. Skills that wrap agents delegate to `.claude/agents/<agent-name>.md` — the SKILL.md reads as a "thin wrapper" that spawns the agent.

```
/workspaces/qrspi/.claude/
├── CLAUDE.md
├── agents/
│   ├── qrspi-design.md
│   ├── qrspi-implement.md
│   ├── qrspi-plan.md
│   ├── qrspi-pr.md
│   ├── qrspi-questions.md
│   ├── qrspi-research.md
│   ├── qrspi-structure.md
│   └── qrspi-worktree.md
├── skills/
│   ├── qrspi-design/SKILL.md
│   ├── qrspi-implement/SKILL.md
│   ├── qrspi-plan/SKILL.md
│   ├── qrspi-pr/SKILL.md
│   ├── qrspi-questions/SKILL.md
│   ├── qrspi-research/SKILL.md
│   ├── qrspi-structure/SKILL.md
│   ├── qrspi-ticket/SKILL.md
│   ├── qrspi-work/SKILL.md
│   ├── qrspi-worktree/SKILL.md
│   └── writing-bash-scripts/
│       └── references/    (empty directory)
└── settings.local.json
```

— `/workspaces/qrspi/.claude/` (full tree explored)
**Dependencies:** None — this is infrastructure layout
**Implicit contracts:** Skills at `.claude/skills/` are loaded by the Claude Code harness. Agent files at `.claude/agents/` are loaded as `subagent_type` definitions. The `Agent` tool resolves `subagent_type` against the agents directory.

## Q2: The ticket instructs to "use the Anthropic skill builder skill to generate the skill." How does the skill-creator skill produce SKILL.md content — does it scaffold files, invoke a model call, or generate a template? What is the exact input/output contract between the skill-creator and the generated skill directory?

**Answer:** The `skill-creator` skill does not exist in the codebase. There is no directory, file, or reference to a `skill-creator` skill anywhere under `/workspaces/qrspi/`. It was referenced in system-reminder available-skills lists but is not present in the project. Similarly, there is no `skill-creator` agent under `.claude/agents/`.

The eval system does have scripts related to skill iteration:
- `scripts/run_eval.py` — runs eval suites against a skill/agent prompt
- `scripts/grade.py` — grades results against the suite
- `scripts/diagnose.py` — analyzes failures and categorizes them
- `scripts/revise.py` — generates targeted skill revisions based on failure diagnosis

These scripts form a skill improvement loop but do not create SKILL.md files. They operate on existing skill/agent prompt files.

The closest thing to a "skill creator" pattern in the codebase is:
1. Manual creation of a SKILL.md with YAML frontmatter + body
2. Manual creation of an agent .md file with model/tool config

There is no automated scaffolding tool in the repo.

— `/workspaces/qrspi/scripts/` (all scripts examined)
— `/workspaces/qrspi/.claude/agents/` (all agents examined)
— `/workspaces/qrspi/.claude/skills/` (all skills examined)
**Dependencies:** N/A — skill-creator does not exist
**Implicit contracts:** The eval scripts (`run_eval.py`, `grade.py`, `diagnose.py`, `revise.py`) assume a skill is a single file (`.md` or `.txt`) that can be loaded via `load_skill()`. No multi-file SKILL.md parsing is implemented.

## Q3: Existing skills in the project (e.g., `writing-bash-scripts` in the available-skills list) — is this a pre-existing skill that should be updated, or is this ticket asking to create a new one that did not previously exist? How do existing skills reference the `agentskills.io` standard in their frontmatter?

**Answer:** The `writing-bash-scripts` skill directory EXISTS at `/workspaces/qrspi/.claude/skills/writing-bash-scripts/` but is incomplete — it has no `SKILL.md` file. It has only an empty `references/` subdirectory. It appears to have been scaffolded but never filled in.

There is no reference to `agentskills.io` in any SKILL.md file in the codebase. The existing SKILL.md files use a custom frontmatter format that does not match any documented `agentskills.io` spec:

```yaml
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

The frontmatter keys observed across all SKILL.md files are: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. These are project-specific conventions, not from `agentskills.io`.

Agent files (`.claude/agents/*.md`) use a separate frontmatter format:
```yaml
---
name: qrspi-research
description: Internal QRSPI workflow agent ...
model: opus
claude:
  tools: Read, Write, Glob, Grep
---
```

Agent frontmatter keys: `name`, `description`, `model`, `claude.tools`.

— `/workspaces/qrspi/.claude/skills/*/SKILL.md` (all 10 skills examined)
— `/workspaces/qrspi/.claude/agents/*.md` (all 8 agents examined)
**Dependencies:** Agent files depend on skill files for invocation; skills delegate to agents via `subagent_type`.
**Implicit contracts:** Skills are invoked via slash commands (`/command`). Agent files define the Claude model and available tools for sub-agents.

## Q4: The skill-creator skill must produce valid SKILL.md frontmatter following agentskills.io conventions. What are the required frontmatter keys (e.g., `name`, `description`, `version`), and how are optional directories (references/, scripts/, assets/) declared or implied?

**Answer:** There is no `agentskills.io` standard documented or referenced anywhere in the codebase. The project uses its own SKILL.md frontmatter convention with these observed keys:

Required keys (present in all 10 skills):
- `name` — skill identifier (string)
- `description` — human-readable description (string)

Common keys:
- `command` — slash command to invoke (string, e.g., `/qrspi-design`)
- `argument-hint` — positional argument format (string, e.g., `<ticket-id>`)
- `allowed-tools` — comma-separated list of tool names (string)

The `allowed-tools` field supports parameter constraints using `:` notation (e.g., `Bash(pwd:*)`).

Optional directories in skill directories:
- `references/` — used by `qrspi-work` skill (`references/review-cascade.md`)
- No `scripts/` or `assets/` directories exist in any skill

There is no `version` key in any existing SKILL.md. No `agentskills.io` references exist in any frontmatter or body text.

— `/workspaces/qrspi/.claude/skills/qrspi-work/SKILL.md` (lines 1-7)
— `/workspaces/qrspi/.claude/skills/qrspi-work/references/review-cascade.md` (line 1)
**Dependencies:** N/A — this defines the project's own convention
**Implicit contracts:** The `allowed-tools` list is enforced by the Claude Code harness at invocation time. The `references/` directory is implicitly declared by file existence, not frontmatter.

## Q5: The skill content describes shell conventions (shebang, set -euo pipefail, trap patterns, getopts, subcommand dispatcher). Should these conventions be encoded entirely in the SKILL.md body, or should reference scripts or example files live in a `references/` directory as supplementary material?

**Answer:** The project's existing convention shows both patterns in use:

1. **SKILL.md body** — All instructional content, rules, steps, and convention descriptions are written as Markdown in the SKILL.md body. This is the primary vehicle for skill guidance.

2. **references/ subdirectory** — Used as supplementary material. Example: `qrspi-work/SKILL.md` references `references/review-cascade.md` (line 272: "Read `references/review-cascade.md` for cascade logic."). This file contains detailed procedural rules that are too long for the main SKILL.md.

The `writing-bash-scripts` skill already has an empty `references/` directory created (`/workspaces/qrspi/.claude/skills/writing-bash-scripts/references/`), suggesting the intent was to use the references pattern.

The convention appears to be:
- SKILL.md body: ~50-730 lines, containing frontmatter + core instructions + step-by-step procedures
- references/: supplemental procedural documents, review cascades, or extended examples

No `scripts/` directory is used in any existing skill. The `scripts/` directory at the repo root (`/workspaces/qrspi/scripts/`) contains eval harness scripts, not skill content.

— `/workspaces/qrspi/.claude/skills/qrspi-work/SKILL.md` (line 272)
— `/workspaces/qrspi/.claude/skills/qrspi-work/references/review-cascade.md` (line 1)
— `/workspaces/qrspi/.claude/skills/writing-bash-scripts/` (directory structure)
**Dependencies:** SKILL.md body -> references/ files (read at invocation time)
**Implicit contracts:** References are resolved relative to the skill directory. A skill at `.claude/skills/X/SKILL.md` would read from `.claude/skills/X/references/`.

## Q6: Does the skill need any persistent state (e.g., a registry of validated shell conventions, a checklist of must-include patterns), or is it purely a static reference document? If state is needed, where is it stored relative to the skill directory?

**Answer:** The `writing-bash-scripts` skill is a **purely static reference document**. It requires no persistent state. The Claude Code skill/harness model operates statelessly — skills are loaded as text at session start and invoked on demand. They do not maintain runtime state between invocations.

The existing skills all follow this pattern:
- `qrspi-research/SKILL.md` — static instructions for the research phase
- `qrspi-work/SKILL.md` — static orchestrator instructions
- `writing-bash-scripts/SKILL.md` — would contain shell scripting conventions

No skill in the project uses any persistent state mechanism. There are no:
- State files alongside SKILL.md
- JSON/YAML config files within skill directories
- Registries or checklists stored in skill directories

State management exists only at the project level:
- Artifacts stored in `.qrspi/<ticket-id>/` directories
- Eval results stored in `evals/` output directories
- No per-skill state

— `/workspaces/qrspi/.claude/skills/*/SKILL.md` (all skills are static Markdown)
— `/workspaces/qrspi/.claude/skills/writing-bash-scripts/` (empty references/ only)
**Dependencies:** None — skills are stateless
**Implicit contracts:** Claude Code loads skill content once per session. Skills must be self-contained — no external state files expected.

## Q7: The ticket specifies conventions like "target bash 4+ (note macOS ships bash 3.2)" and "BSD vs GNU coreutils differences." Should the skill encode environment detection logic, or is it purely a static guidance document that agents read at invocation time?

**Answer:** Skills in this project are **purely static guidance documents**. They do not contain executable code or environment detection logic. The `writing-bash-scripts` skill should encode these conventions as **text instructions in the SKILL.md body**, not as executable detection scripts.

The agent (Claude) reads the SKILL.md at invocation time and follows the guidance when generating scripts. The skill's role is to inform the agent's behavior, not to execute environment checks.

However, there is a subtle distinction in the project:
- **Skills** (`.claude/skills/`) — static Markdown guidance for agents
- **Scripts** (`scripts/`) — executable Python scripts for the eval harness

If the ticket requires actual environment detection, that logic would belong in the generated scripts themselves (following the guidance in the SKILL.md), not in the SKILL.md.

Example of how this would work: The SKILL.md instructs: "When generating scripts, detect the OS with `uname -s` and branch on `Darwin` vs `Linux`." The agent follows this guidance when writing the script.

— `/workspaces/qrspi/.claude/skills/qrspi-work/SKILL.md` (contains bash code snippets as examples, not executable skill logic)
**Dependencies:** SKILL.md text -> agent behavior at generation time
**Implicit contracts:** Skills guide agents; they are not executed themselves.

## Q8: The skill's scope guidance says "never exceed ~200 lines without strong justification; at that point suggest a different language." Should the skill-enforcing agent validate line counts, or is this a soft heuristic? What happens if a bash script genuinely needs more than 200 lines — does the skill produce a warning, an error, or just a suggestion?

**Answer:** This guidance appears to be a **soft heuristic/suggestion**, not a hard constraint enforced by tooling. The project has no automated line-count validation for generated scripts.

The project's eval system (`grade.py`) does enforce line-count constraints on **agent output files** (e.g., design docs must be <= 300 lines), but not on the scripts themselves. The eval check:

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
```

This checks the SKILL.md or agent output, not generated bash scripts. There is no script-line-count checker in the eval harness.

The skill should therefore encode this as a **guideline for the agent** — "suggest a different language if the script would exceed 200 lines" — rather than as an enforcement mechanism. The agent (Claude) should follow this heuristic when generating scripts.

For the SKILL.md itself: the design phase enforces a hard limit of 300 lines on design docs (eval case_005), but no comparable hard limit exists for SKILL.md files. The ticket mentions "SKILL.md body must be under 500 lines / 5000 tokens" (Q14), which suggests a soft target for SKILL.md content.

— `/workspaces/qrspi/scripts/grade.py` (lines 35-41, line_count check)
— `/workspaces/qrspi/evals/suite.json` (case_005, line_count assertion on design.md)
**Dependencies:** N/A — no automated enforcement exists
**Implicit contracts:** Line-count limits are agent-guidance heuristics, not tool-enforced constraints, unless specified in eval assertions.

## Q9: The ticket mentions "include a gotchas section covering common pitfalls (unquoted variables, missing -- in commands, cd without error check)." How should the gotchas section be structured relative to the main conventions — as a separate subsection, as inline notes, or in a dedicated references/ file?

**Answer:** Based on the project's established conventions, the gotchas section should be a **separate subsection within the SKILL.md body**, not a references/ file. The `review-cascade.md` pattern shows that references/ is reserved for procedural documents that are too long to embed inline.

A gotchas section is procedural guidance that agents need to read at invocation time, so it belongs in the SKILL.md body. It should use a clear subsection heading and bullet-point format for scannability.

The existing pattern from `qrspi-work/SKILL.md` supports this:
- Main body contains critical rules in clearly labeled sections (e.g., "### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve")
- Referenced documents contain multi-step procedures (e.g., `references/review-cascade.md`)

A gotchas section would fit the style of inline rules, not referenced procedures.

Example structure:
```markdown
## Gotchas

- Unquoted variables: Always use double quotes around variable expansions
- Missing -- in commands: Use -- before file arguments to prevent option parsing
- cd without error check: Always check cd exit status before proceeding
```

— `/workspaces/qrspi/.claude/skills/qrspi-work/SKILL.md` (hard-stop section as inline pattern)
— `/workspaces/qrspi/.claude/skills/qrspi-work/references/review-cascade.md` (referenced procedural document pattern)
**Dependencies:** N/A — this is a content structure convention
**Implicit contracts:** Inline sections are for quick-reference rules; references/ is for multi-step procedures or extended content.

## Q10: The skill should handle the case where `command -v` checks find missing dependencies. Should the skill specify exit codes and error message formats for each possible missing dependency, or just a generic pattern?

**Answer:** The project's existing scripts use generic error handling patterns rather than per-dependency exit codes. Examining the eval scripts:

```python
# scripts/run_eval.py — generic exception handling
except Exception as e:
    result.error = str(e)

# scripts/check_scope.py — generic exit
sys.exit(0 if result["passed"] else 1)
```

There is no pattern of per-dependency exit codes in the project. The convention is:
1. Use a generic exit code (0 for success, 1 for failure)
2. Print a descriptive error message to stderr

The skill should specify a **generic pattern** that the agent follows when generating scripts:
- Detect missing dependencies via `command -v`
- Exit with code 1
- Print a clear error message naming the missing dependency
- No need for per-dependency exit code mapping

This aligns with the project's simple error-handling philosophy seen across all scripts.

— `/workspaces/qrspi/scripts/check_scope.py` (lines 55-71, error handling)
— `/workspaces/qrspi/scripts/run_eval.py` (lines 139-140, error handling)
**Dependencies:** N/A — this is an error-handling convention
**Implicit contracts:** Simple exit codes; descriptive error messages; no per-dependency error taxonomy.

## Q11: The ticket states "produces ShellCheck-clean output when an agent follows the guidance." How should testability of the skill be measured — by generating example scripts and running them through ShellCheck, or by having the skill-creator's eval harness validate the SKILL.md against an agentskills.io schema?

**Answer:** The project's eval system (`evals/suite.json`) validates **agent output artifacts**, not generated scripts. There is no ShellCheck integration and no agentskills.io schema validation.

The eval harness evaluates whether agents produce correct output files:
- `output_file_exists` — artifact was created
- `has_section` — required sections present
- `no_solution_language` — no solution-oriented language
- `all_evidence_has_file_citations` — proper citations
- `current_state_has_citations` — design docs cite research

To measure skill testability, the eval system would need:
1. Generated example scripts (not currently in `evals/fixtures/`)
2. A ShellCheck invocation step in the eval pipeline
3. An assertion check for ShellCheck exit code and warnings

Currently none of this exists. The `evals/fixtures/` directory contains only ticket/question/research template files — no generated scripts. The `evals/golden/` directory is empty (just `.gitkeep`).

The skill-creator does not exist, so there is no SKILL.md schema validator.

— `/workspaces/qrspi/evals/fixtures/` (only template files, no scripts)
— `/workspaces/qrspi/evals/golden/` (empty, .gitkeep only)
— `/workspaces/qrspi/evals/suite.json` (cases validate agent outputs, not scripts)
**Dependencies:** N/A — ShellCheck and agentskills.io schema validation are not implemented
**Implicit contracts:** The eval system validates agent output structure, not generated code quality.

## Q12: The skill mentions recommending BATS-core for testable scripts. Should the skill include a BATS test template in a scripts/ or references/ directory, or just mention BATS-core by name in the SKILL.md body?

**Answer:** Based on the project's conventions, the skill should **mention BATS-core by name in the SKILL.md body** and optionally provide an example in the body text. No existing skill includes test templates or template files in a `scripts/` or `references/` directory.

The existing `references/` usage (`qrspi-work/references/review-cascade.md`) is for procedural documents, not templates. There is no `scripts/` directory in any skill.

If a BATS template is useful, the most appropriate placement would be:
1. **SKILL.md body** — inline code example of a BATS test
2. **references/** — only if the template is extensive enough to merit a separate file

The simpler approach (inline example) is more consistent with the existing patterns. The `qrspi-work/SKILL.md` includes bash code snippets directly in its body (e.g., worktree setup, error handling patterns).

The eval system does not currently validate test coverage of generated scripts, so including BATS guidance is advisory, not enforceable.

— `/workspaces/qrspi/.claude/skills/qrspi-work/SKILL.md` (bash snippets inline, not in references/)
— `/workspaces/qrspi/evals/suite.json` (no test-coverage assertions exist)
**Dependencies:** N/A — advisory guidance only
**Implicit contracts:** Inline examples in SKILL.md body; no test template files in skill directories.

## Q13: When other agents invoke the `writing-bash-scripts` skill, how is skill usage tracked or logged in the qrspi project? Is there there a mechanism to measure how often each skill is triggered, or whether agents follow the skill's guidance (e.g., by scanning generated scripts for ShellCheck violations)?

**Answer:** There is **no skill usage tracking or logging mechanism** in the project. The Claude Code harness loads skills on demand and has no built-in invocation counter or audit log that the project uses.

The eval system provides a form of measurement, but it is retrospective and manual:
1. Run `scripts/run_eval.py` with a skill file and test suite
2. Grade results with `scripts/grade.py`
3. Diagnose failures with `scripts/diagnose.py`
4. Propose revisions with `scripts/revise.py`

This is a skill improvement loop, not real-time usage tracking. It requires manually running the eval suite and reviewing results.

There is no:
- Invocation counter
- Agent activity log
- Skill trigger histogram
- Usage dashboard
- Automatic ShellCheck scanning of generated scripts

— `/workspaces/qrspi/scripts/run_eval.py` (eval runner, not usage tracker)
— `/workspaces/qrspi/evals/` (no log or tracking infrastructure)
**Dependencies:** N/A — no tracking exists
**Implicit contracts:** Skills are invoked on-demand; usage tracking is manual via eval runs.

## Q14: The ticket says the SKILL.md body must be under 500 lines / 5000 tokens. Should the skill-creator enforce this limit during generation, or should a post-generation validation step check it? What is the consequence if the generated SKILL.md exceeds this limit?

**Answer:** Since the skill-creator does not exist, there is no enforcement or validation step. The limit is a **soft target**, not an enforced constraint.

The project's eval system does enforce line-count limits on certain artifacts:
- Design docs: `line_count('design.md', 300)` — hard check in eval (case_005)
- Questions: `question_count('questions.md') <= 15` — soft upper bound (case_001, case_015)
- Structure slices: `no_slice_exceeds_file_limit('structure.md', 10)` — max 10 files per slice (case_007)
- Plan steps: `total_steps('plan.md') <= 100` — hard limit (case_009)

These are eval assertions, not pre-generation checks. They verify the output after generation. If an assertion fails, the case gets a lower score but the artifact is not rejected.

For the 500-line SKILL.md target: there is no eval assertion checking SKILL.md line count. The limit should be enforced as:
1. **Soft guidance** in the skill-creator's instructions (if it existed)
2. **Post-generation check** via a new eval assertion: `line_count('SKILL.md', 500)`

The consequence of exceeding the limit would be:
- Higher token usage in subsequent agent invocations
- Risk of context window overflow (agent context cap is 40% — see worktree agent rules)
- Lower eval score if an assertion is added

— `/workspaces/qrspi/evals/suite.json` (case_005, line_count assertion for design.md)
— `/workspaces/qrspi/.claude/agents/qrspi-structure.md` (lines 33-41, slice/file limits)
— `/workspaces/qrspi/.claude/agents/qrspi-plan.md` (line 23, 100-step limit)
**Dependencies:** N/A — eval assertions are post-generation checks
**Implicit contracts:** Limits are checked after generation via eval assertions; exceeding a limit reduces score but does not block artifact creation.

## Q15: Should the skill include a self-documenting mechanism where it lists its own conventions in a machine-readable format (e.g., a JSON schema or YAML checklist) so that downstream tools can verify a generated script complies with the skill's rules?

**Answer:** The project **does not use machine-readable skill definitions**. All skills are pure Markdown documents read by the Claude agent at invocation time. There is no JSON schema, YAML checklist, or machine-readable format associated with any skill.

The only machine-readable artifacts in the project are:
- `evals/suite.json` — eval test case definitions
- `evals/graphite-evals.json` — graphite skill eval cases

These are for the eval harness, not for skill definitions. The skills themselves have no machine-readable companion files.

Adding a machine-readable format would be a **new pattern** not present in the existing codebase. The existing pattern is purely human-readable Markdown + agent inference.

If a machine-readable checklist were desired, the most natural placement would be:
- In the eval suite (`evals/suite.json`) as new assertions
- In a separate file alongside the SKILL.md (not inside it)

But this is not required by the current project conventions.

— `/workspaces/qrspi/.claude/skills/*/SKILL.md` (all pure Markdown, no machine-readable sidecar files)
— `/workspaces/qrspi/evals/suite.json` (machine-readable but for evals, not skills)
**Dependencies:** N/A — no machine-readable skill format exists
**Implicit contracts:** Skills are purely human-readable Markdown; machine-readable checks live only in the eval system.

---

## Discovered Patterns

1. **Two-tier skill/agent architecture**: Skills (`.claude/skills/`) are thin invocation wrappers with YAML frontmatter + step instructions. They spawn agents (`.claude/agents/`) via the `Agent` tool. The skill handles input parsing and post-verification; the agent handles the actual work.

2. **QRSPI workflow agent model**: All workflow agents (qrspi-questions, qrspi-research, qrspi-design, qrspi-structure, qrspi-plan, qrspi-worktree, qrspi-implement, qrspi-pr) are `opus`-model agents with restricted tool sets. They only read their input artifacts and write to a single output path.

3. **Stateless skills**: All skills are static Markdown documents. No per-skill state, registries, or persistent files exist. The Claude Code harness loads them at session start.

4. **Eval system as post-hoc validation**: The eval harness (`evals/`, `scripts/`) validates agent outputs after generation. It does not prevent violations; it scores them. This is a feedback loop for improving agent prompts, not a gate.

5. **`qrspi-work` orchestrator as single source of truth**: The `qrspi-work/SKILL.md` (731 lines) is the largest and most complex skill. It coordinates all other phases, manages worktrees, handles git/graphite operations, and contains its own error handling and firewall logic.

6. **Reference files for procedural depth**: When a skill's procedural content becomes too long for the SKILL.md body, it goes in a `references/` subdirectory (only `qrspi-work/references/review-cascade.md` uses this pattern).

7. **Eval fixture format**: Test cases use fixture files in `evals/fixtures/` that contain ticket/question/research/pr templates. The `build_messages()` function concatenates fixture files into the user message context.

8. **No agentskills.io compliance**: Despite the ticket's references to `agentskills.io`, the project uses its own SKILL.md frontmatter convention (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) with no documented standard.

## Inconsistencies

1. **CLAUDE.md agent path vs actual location**: The project CLAUDE.md states "Agent prompt definitions live in `.qrspi/agents/`" but the actual agent files are in `.claude/agents/`. There is no `.qrspi/agents/` directory.

2. **CLAUDE.md skills location vs actual location**: The project CLAUDE.md does not explicitly state where skills live, but the skills are in `.claude/skills/`, not `.qrspi/skills/`. The worktree convention places ticket artifacts in `.worktrees/<ticket-id>/` but the canonical skills are in the main repo's `.claude/skills/`.

3. **writing-bash-scripts directory created without SKILL.md**: The `writing-bash-scripts` directory exists with an empty `references/` subdirectory but no `SKILL.md` file. This suggests the directory was scaffolded but the skill content was never written.

4. **Ticket references non-existent skill-creator**: The ticket asks to "use the Anthropic skill builder skill" but no `skill-creator` skill or agent exists anywhere in the project. This is an unimplemented dependency.

5. **Eval harness scripts are Python but eval cases reference `.md` fixtures**: `run_eval.py` loads fixture files generically (no format validation), but `check_scope.py` uses regex to extract backtick-wrapped file paths from markdown content. The grade.py assertions are hardcoded strings, not configurable per-case.

6. **Line-count enforcement inconsistency**: Some artifacts have eval assertions enforcing line limits (design.md: 300 lines), while others have no such check. The 500-line SKILL.md target from the ticket has no corresponding eval assertion.

7. **Template directory is dead code**: `.qrspi/templates/` contains template files for artifacts but the workflow agents read templates from `.qrspi/templates/` relative to the worktree, not the main repo. Worktrees get synced copies of these templates, but the main repo templates are the source of truth — creating a potential drift if they diverge.

8. **Graphite-evals.json is unused**: `evals/graphite-evals.json` contains eval cases for a "graphite" skill but is not referenced by `suite.json` or any eval script. It appears to be a separate, standalone eval definition.

9. **LLM judge and script checks are stubbed**: In `grade.py`, both `run_llm_judge()` and `run_script_check()` return stubs with `passed: null`. The eval harness can only run programmatic assertions; subjective evaluation and external tool invocations are not implemented.

10. **Revision pipeline is incomplete**: `revise.py` references a "meta-agent" for proposing edits but has no integration. The `propose_revisions()` function returns `pending_meta_agent` edits that cannot be applied without LLM integration.
