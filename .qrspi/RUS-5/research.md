# Research - Codebase Map

**Questions source:** questions.md @ 2026-05-30
**Generated:** 2026-05-30
**Status:** draft

## Q1: How does the skill-creator skill (available as the `skill-creator` skill) structure its output? The ticket says to use it but the `writing-bash-scripts` skill already exists in the available skills list -- was it already created, or does the ticket describe work that remains?
  **Target:** `.qrspi/agents/skill-creator` skill definition, or the `writing-bash-scripts` skill already present in the system prompt

**Answer:** The `skill-creator` skill already exists as a global skill at `~/.claude/skills/skill-creator/SKILL.md` (486 lines). It is a structured workflow for creating and improving skills. It does NOT produce a ready-to-save SKILL.md file directly. Instead, it guides the agent through a process (capture intent, interview, write the SKILL.md draft, create test cases, run evaluations, iterate based on feedback). The actual SKILL.md file must be written by the agent to a directory under `~/.claude/skills/<name>/` or `.claude/skills/<name>/` -- the skill-creator outputs structured guidance, directory layout, and instructions for what to put in each file, but the agent (or user) must create the files.

The `writing-bash-scripts` skill already exists as a global skill at `~/.claude/skills/writing-bash-scripts/SKILL.md` (273 lines). This means the work described by the ticket has already been completed by a prior agent session (likely RUS-1 through RUS-4). The ticket RUS-5 asks to "create a new agent skill called writing bash scripts" but this skill already exists. The remaining work is likely a refinement or restructuring rather than initial creation.

**Evidence:**

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:62-69
### Write the SKILL.md
Based on the user interview, fill in these components:
- **name**: Skill identifier
- **description**: When to trigger, what it does. ...
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:62-69`

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:73-84
#### Anatomy of a Skill
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
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:73-84`

```
/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:1-5
---
name: writing-bash-scripts
description: "Guide for writing robust, ShellCheck-clean bash scripts. ..."
---

# Writing Bash Scripts
```

— `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:1-5`

**Dependencies:** The skill-creator skill depends on `~/.claude/skills/skill-creator/scripts/` (Python scripts for eval/grading/benchmarking), `~/.claude/skills/skill-creator/agents/` (subagent prompts for grading and analysis), and `~/.claude/skills/skill-creator/eval-viewer/` (HTML viewer).

**Implicit contracts:** The skill-creator skill assumes the environment has `claude` CLI access, Python 3, and a web browser (or `--static` mode for headless). It expects the agent to have filesystem write access to `~/.claude/skills/<name>/`.

## Q2: The ticket references the "agentskills.io standard pattern" -- what is the exact directory schema expected (frontmatter fields, file conventions)? Is there a canonical reference for agentskills.io that the SKILL.md frontmatter must match?
  **Target:** External agentskills.io specification or any existing SKILL.md files in the repo that already follow this pattern

**Answer:** There is no external `agentskills.io` website or canonical specification referenced anywhere in the codebase. A grep for "agentskills" finds only the questions.md file itself. The pattern described by the ticket refers to the Claude Code skills convention defined within the `skill-creator` skill itself. All existing SKILL.md files in the codebase follow a consistent frontmatter convention using `name` and `description` fields. Some also include `command`, `argument-hint`, `allowed-tools`, and `license` fields. The canonical reference is the `skill-creator` skill at `~/.claude/skills/skill-creator/SKILL.md` section "Anatomy of a Skill" (line 73).

**Evidence:**

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:62-69
### Write the SKILL.md
Based on the user interview, fill in these components:
- **name**: Skill identifier
- **description**: When to trigger, what it does. ...
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:62-69`

```
/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:1-5
---
name: writing-bash-scripts
description: "Guide for writing robust, ShellCheck-clean bash scripts. ..."
command: writing-bash-scripts
---
```

— `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:1-5`

```
/home/vscode/.claude/skills/qrspi-questions/SKILL.md:1-7
---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `/home/vscode/.claude/skills/qrspi-questions/SKILL.md:1-7`

```
/home/vscode/.claude/skills/mcp-builder/SKILL.md:1-5
---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers...
license: Complete terms in LICENSE.txt
---
```

— `/home/vscode/.claude/skills/mcp-builder/SKILL.md:1-5`

**Dependencies:** N/A -- this is a convention observation question.

**Implicit contracts:** Claude Code uses the `name` + `description` frontmatter fields as the primary skill matching mechanism. The `command` field maps to a slash command. The `allowed-tools` field is a Claude Code permission configuration. `argument-hint` documents expected CLI arguments.

## Q3: Where in the project directory tree should this new skill's SKILL.md and any `references/`, `scripts/`, or `assets/` subdirectories be placed? The CLAUDE.md notes that agent prompt definitions live in `.qrspi/agents/` and skills are invoked via `/` slash commands -- does this new skill need a corresponding slash command wrapper or does it register purely via its skill invocation mechanism?
  **Target:** `.qrspi/agents/` directory structure, existing skill SKILL.md files for structural reference

**Answer:** There are two skill locations in this codebase:

1. **Global skills** (`~/.claude/skills/<name>/`) -- These are installed at the user level and apply to all projects. Examples: `skill-creator`, `writing-bash-scripts`, `using-graphite-cli`, `mcp-builder`, `workflow-creator`. These do NOT have a `/` slash command wrapper. They register purely via their `name` + `description` frontmatter in Claude Code's available skills list. The agent loads them based on description matching.

2. **Project-level skills** (`<repo>/.claude/skills/<name>/`) -- These are installed at the project level. Examples: `qrspi-questions`, `qrspi-research`, `qrspi-design`, etc. These DO have a corresponding slash command wrapper (e.g., `/qrspi-questions`) defined in the frontmatter `command` field. They additionally may reference `.claude/agents/<name>.md` files for the actual prompt content, but the `.qrspi/agents/` directory does not exist in this project.

The `writing-bash-scripts` skill is a **global skill** -- it lives at `~/.claude/skills/writing-bash-scripts/` and registers purely via its frontmatter description. It does NOT have a `/writing-bash-scripts` slash command. A `command: writing-bash-scripts` frontmatter field exists but maps to a different invocation mechanism.

The `.qrspi/agents/` directory does NOT exist in this repository. The CLAUDE.md references it as a convention, but the actual agent prompt definitions for QRSPI skills live in `.claude/agents/` (a sibling directory) and are referenced by the `.claude/skills/` wrappers.

**Evidence:**

```
/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:1-5
---
name: writing-bash-scripts
description: "Guide for writing robust, ShellCheck-clean bash scripts. ..."
command: writing-bash-scripts
---
```

— `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:1-5`

```
$ ls -la /workspaces/qrspi/.qrspi/agents/
No .qrspi/agents directory
```

— Bash output from `ls -la /workspaces/qrspi/.qrspi/agents/`

```
/home/vscode/.claude/CLAUDE.md:4-7
- `/qrspi-ticket <initial description>` -- Create a Linear issue through guided conversation
- `/qrspi-questions <ticket-id>` -- Generate technical questions from a ticket (fetched from Linear)
- `/qrspi-research <ticket-id>` -- Map the codebase (ticket is hidden during this phase)
...
```

— `/home/vscode/.claude/CLAUDE.md:4-7`

**Dependencies:** Project skills in `.claude/skills/` depend on `.claude/agents/` for prompt content. Global skills in `~/.claude/skills/` are standalone.

**Implicit contracts:** Global skills (like `writing-bash-scripts`) are shared across all projects and registered automatically by Claude Code. Project skills (like `qrspi-questions`) have slash command wrappers for explicit invocation. The `.qrspi/agents/` path in CLAUDE.md appears to be a stale convention reference.

## Q4: The `writing-bash-scripts` skill already appears in the available skills list. Is this ticket about refining an existing skill, or about creating a separate new skill with a different name/trigger that supersedes it?
  **Target:** Existing `writing-bash-scripts` skill definition in the skill registry or available skills list

**Answer:** The `writing-bash-scripts` skill already exists at `~/.claude/skills/writing-bash-scripts/SKILL.md` (273 lines) and has a complete directory structure:

- `SKILL.md` (273 lines) -- Main skill body
- `references/conventions.md` (236 lines) -- Detailed conventions
- `references/gotchas.md` (198 lines) -- Portability pitfalls and ShellCheck warnings
- `references/patterns.md` (172 lines) -- Code patterns
- `references/template.sh` (105 lines) -- Structural example

The ticket RUS-5 says "Create a new agent skill called writing bash scripts" but the skill already exists. The ticket also mentions "target bash 4+" and "ShellCheck-clean output" -- both of which the existing skill already addresses (the `references/conventions.md` at line 127-132 includes a `check_bash_version()` function that enforces bash 4+).

This appears to be a case where a prior agent (likely RUS-1 through RUS-4) already created the skill. The ticket RUS-5 may be a duplicate request or may describe refinements needed on the existing skill. The existing skill is a well-structured implementation that follows the skill-creator's recommended directory schema.

**Evidence:**

```
/home/vscode/.claude/skills/writing-bash-scripts/references/conventions.md:127-132
check_bash_version() {
  if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
    log_error "Bash 4+ required, found ${BASH_VERSION}"
    exit 1
  fi
}
```

— `/home/vscode/.claude/skills/writing-bash-scripts/references/conventions.md:127-132`

```
$ wc -l /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
273 /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
```

— Bash output from `wc -l`

**Dependencies:** The skill depends on Claude Code's skill loading mechanism for invocation.

**Implicit contracts:** The skill follows the same pattern as other global skills (`using-graphite-cli`, `mcp-builder`) -- it registers via frontmatter description matching and provides bundled reference files for contextually loaded detail.

## Q5: The skill-creator skill is available in the available skills list. What input contract (description, conventions, scope) does it expect, and does it produce output in a format that can be directly saved as a SKILL.md? Or does it produce structured guidance that still needs manual assembly?
  **Target:** `skill-creator` skill definition file

**Answer:** The skill-creator skill expects the following inputs from the user:

1. **What the skill should do** (its purpose and behavior)
2. **When it should trigger** (user phrases/contexts that invoke it)
3. **Expected output format**
4. **Whether test cases are needed**

It produces **structured guidance**, not a ready-to-save SKILL.md file. The skill-creator guides the agent through:
- Writing a draft SKILL.md based on user interview
- Creating a directory structure (`skill-name/` with `SKILL.md` + optional `scripts/`, `references/`, `assets/`)
- Running evaluation test cases via subagents
- Iterating based on feedback

The agent must manually write the SKILL.md file and directory structure. The skill-creator includes a `package_skill.py` script that can package a skill into a `.skill` file, but the SKILL.md content itself is authored by the agent during the interview/writing phase.

**Evidence:**

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:47-54
### Capture Intent
Start by understanding the user's intent. ...
1. What should this skill enable Claude to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works? ...
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:47-54`

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:62-69
### Write the SKILL.md
Based on the user interview, fill in these components:
- **name**: Skill identifier
- **description**: When to trigger, what it does. ...
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:62-69`

**Dependencies:** The skill-creator depends on `claude` CLI (for eval runs), Python 3 (for scripts), web browser (for reviewer), and subagent infrastructure.

**Implicit contracts:** The skill-creator assumes Claude Code or Cowork environment with filesystem write access. It expects subagents for parallel eval runs (or manual execution in Claude.ai).

## Q6: The ticket says to target bash 4+ but calls out macOS ships bash 3.2. Does the skill need to encode fallback patterns for bash 3.2 features (e.g., no associative arrays, no `mapfile`), or is the decision to exclude macOS support acceptable? This is a judgment call outside the ticket's stated conventions.
  **Target:** The `writing-bash-scripts` SKILL.md body and any bash portability reference material

**Answer:** The existing `writing-bash-scripts` skill makes a clear decision: it targets bash 4+ and explicitly enforces this with a `check_bash_version()` function in `references/conventions.md` (line 127). There are NO fallback patterns for bash 3.2. The skill treats bash 4+ as a hard requirement, not a soft guideline.

The decision is encoded in the conventions reference, not the SKILL.md body. The SKILL.md body focuses on general scripting conventions (strict mode, quoting, error handling, ShellCheck). The bash version check is in `references/conventions.md` under "Dependency Checking" as an example pattern.

There is no explicit discussion of macOS portability trade-offs in the skill. The conventions.md includes a `check_bash_version()` function as a copy-paste pattern, suggesting that any script using these conventions should fail fast with a clear error message if bash < 4 is detected.

**Evidence:**

```
/home/vscode/.claude/skills/writing-bash-scripts/references/conventions.md:127-132
check_bash_version() {
  if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
    log_error "Bash 4+ required, found ${BASH_VERSION}"
    exit 1
  fi
}
```

— `/home/vscode/.claude/skills/writing-bash-scripts/references/conventions.md:127-132`

```
/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:20-22
- **If dealing with portability** (macOS + Linux, bash 3.2 vs 4+), debugging
  ShellCheck warnings, or tracking down a subtle bug: read `references/gotchas.md`
```

— `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:20-22`

**Dependencies:** The bash version check function is a copy-paste pattern in `references/conventions.md` used by scripts that follow these conventions.

**Implicit contracts:** Scripts following these conventions are expected to require bash 4+. There is no grace period or auto-detection with fallbacks.

## Q7: The ticket says "never exceed ~200 lines without strong justification" and "at that point suggest a different language." Who makes this judgment -- the skill, or the agent using the skill? Does the skill need to encode a checklist for when to exit bash and switch to Python/Go, or is this advisory only?
  **Target:** The `writing-bash-scripts` SKILL.md body, specifically the scope guidance section

**Answer:** The existing `writing-bash-scripts` SKILL.md does NOT contain any guidance about when to switch from bash to Python/Go, nor does it have a scope checklist. The ~200-line threshold is mentioned in the ticket but is not encoded in the current skill.

However, the `skill-creator` skill (which guides skill creation) does have a 500-line threshold for SKILL.md bodies (line 96). The current `writing-bash-scripts` SKILL.md is 273 lines, well under both thresholds.

The scope judgment for bash scripts (when to exit bash for Python/Go) is currently advisory only -- there is no encoded checklist or decision tree in the skill. The ticket's guidance ("never exceed ~200 lines without strong justification") is not reflected in the existing skill body or reference files.

**Evidence:**

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:90-96
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
...
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:90-96`

```
$ wc -l /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
273 /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
```

— Bash output from `wc -l`

```
$ grep -n "python\|go\|switch\|language" /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
```

— Bash output (no matches -- no Python/Go switching guidance exists in the SKILL.md)

**Dependencies:** N/A -- this is an advisory gap observation.

**Implicit contracts:** The current skill does not address scope limits for generated scripts. The agent following the skill is expected to use judgment.

## Q8: The acceptance criteria mention "ShellCheck-clean output when an agent follows the guidance." How is this evaluated -- is there an automated check (a script in `references/` or `scripts/` that runs ShellCheck on generated output), or is this a manual review gate?
  **Target:** Any existing eval or test harness in `evals/` or `scripts/` directories

**Answer:** ShellCheck evaluation is a **manual review gate**, not automated. The `writing-bash-scripts` SKILL.md states (line 258): "Run `shellcheck` on every script before delivery. Target zero warnings." This is an instruction to the agent, not an automated check.

There is no ShellCheck binary installed in the environment (`which shellcheck` returns not found). The existing eval infrastructure in `evals/` and `scripts/` has no ShellCheck evaluation. The `evals/suite.json` contains programmatic assertions for QRSPI workflow agents (file existence, section counts, etc.) but nothing for script quality validation. The `evals/graphite-evals.json` contains assertions for the graphite CLI skill, not for bash scripts.

The `scripts/` directory contains Python scripts for eval grading, scope checking, and diagnosis -- none of which run ShellCheck on generated bash scripts.

**Evidence:**

```
/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:256-273
## ShellCheck
Run `shellcheck` on every script before delivery. Target zero warnings.
shellcheck -x my_script.sh
...
Never disable ShellCheck globally. Suppress per-line with justification only.
```

— `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:256-273`

```
$ which shellcheck
shellcheck not found
```

— Bash output (ShellCheck is not installed)

```
$ grep -rn "shellcheck" evals/ scripts/ 2>/dev/null
```

— Bash output (no ShellCheck references in evals or scripts)

**Dependencies:** N/A -- no automated ShellCheck integration exists.

**Implicit contracts:** The ShellCheck quality gate relies on the agent following the skill guidance and running ShellCheck manually. There is no CI/CD hook, eval assertion, or pre-commit check.

## Q9: The ticket recommends BATS-core for testable scripts. Should the `writing-bash-scripts` skill include a BATS template or scaffolding script as part of its `scripts/` or `references/` directory, or does it only reference BATS as a recommendation?
  **Target:** The `writing-bash-scripts` skill's `scripts/` or `references/` directory (if they exist)

**Answer:** The `writing-bash-scripts` skill **only references BATS as a recommendation**. There is no BATS template, scaffolding script, or test directory in the skill. The SKILL.md section on Testing (line 234-253) provides a BATS example inline but does not bundle any files.

The skill's directory structure is:
- `SKILL.md` (273 lines) -- includes an inline BATS example
- `references/conventions.md` -- no BATS
- `references/gotchas.md` -- no BATS
- `references/patterns.md` -- no BATS
- `references/template.sh` -- no BATS

There is no `scripts/` directory (only `references/`). The `bats` binary is not installed in the environment.

The inline BATS example (lines 237-253 in SKILL.md) shows the basic test structure but does not include a complete scaffolding setup (no `Makefile`, no `install-bats.sh`, no project template).

**Evidence:**

```
/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:234-253
## Testing
Use [bats-core](https://github.com/bats-core/bats-core) for testing bash scripts.
```bash
# test/my_script.bats
@test "greet prints hello" {
  run ./my_script.sh greet
  [ "$status" -eq 0 ]
  [[ "$output" == *"Hello"* ]]
}

@test "unknown command exits 1" {
  run ./my_script.sh bogus
  [ "$status" -eq 1 ]
}
```
Structure tests beside the script in a `test/` directory. Each `.bats` file tests one script or module.
```

— `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md:234-253`

```
$ ls -la ~/.claude/skills/writing-bash-scripts/references/
conventions.md  gotchas.md  patterns.md  template.sh
```

— Bash output (no scripts/ directory, no BATS files in references/)

**Dependencies:** The BATS recommendation is informational only. Agents following the skill must install BATS themselves.

**Implicit contracts:** The skill treats BATS as an optional testing tool that agents should adopt but not as a required dependency.

## Q10: The ticket says the skill body must be under 500 lines / 5000 tokens. Is there an existing mechanism to enforce or verify this constraint, or is it a manual review criterion?
  **Target:** The skill-creator skill's output validation logic or manual review process

**Answer:** The 500-line / 5000-token constraint is a **manual review criterion** with no automated enforcement. The `skill-creator` skill mentions the 500-line ideal at line 96 ("Keep SKILL.md under 500 lines") and suggests adding additional layers of hierarchy when approaching the limit. There is no script or eval assertion that validates skill body line counts.

The existing `writing-bash-scripts` SKILL.md is 273 lines, well under the 500-line threshold. No automation exists to measure or enforce this constraint -- the skill-creator's `quick_validate.py` script exists but its actual validation logic is not visible in the codebase (it may rely on the skill-creator's internal instructions rather than standalone scripts).

The eval infrastructure (`evals/suite.json`, `scripts/grade.py`) has programmatic checks for QRSPI workflow artifacts but no skill body size validation.

**Evidence:**

```
/home/vscode/.claude/skills/skill-creator/SKILL.md:96
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
```

— `/home/vscode/.claude/skills/skill-creator/SKILL.md:96`

```
$ wc -l /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
273 /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
```

— Bash output from `wc -l`

```
$ grep -rn "line_count\|line_count\|500\|5000\|token_count" scripts/*.py evals/*.json 2>/dev/null | head -10
```

— Bash output (no line count validation in eval infrastructure)

**Dependencies:** N/A -- no automated enforcement exists.

**Implicit contracts:** The 500-line limit is enforced by agent discipline and manual review. The skill-creator guides agents toward it but does not automate it.

## Q11: The skill includes conventions for `log()`, `info()`, `warn()`, `die()` helpers inside generated scripts. Does the qrspi system itself need to intercept or log when this skill is used (e.g., to measure how often agents invoke it, or to track whether scripts it generates produce expected output), or is observability scoped only to the scripts the skill helps create?
  **Target:** The qrspi skill invocation system or any eval/monitoring infrastructure

**Answer:** The qrspi system does NOT track skill invocation or measure how often agents invoke individual skills. There is no telemetry, logging, or monitoring infrastructure for skill usage.

The existing `writing-bash-scripts` skill uses `log_info`, `log_warn`, `log_error` helper functions (in its template and conventions), not `log()`, `info()`, `warn()`, `die()`. The naming convention is `log_<level>()` (info/warn/error), not the shorter names mentioned in the question.

Observability in the qrspi system is limited to:
- **Linear status tracking**: Phase transitions are tracked via Linear issue status (e.g., `mcp__linear-russelltsherman__save_issue`)
- **Eval harness**: `evals/suite.json` defines test cases and `scripts/grade.py` runs programmatic/LLM assertions, but this evaluates QRSPI workflow agents (questions, research, design), not skill usage

There is no mechanism to measure how often agents invoke `writing-bash-scripts`, how many scripts it generates, or the quality of generated scripts.

**Evidence:**

```
/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh:18-20
log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
```

— `/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh:18-20`

```
/home/vscode/.claude/CLAUDE.md:1-10
# Project: qrspi
...
Linear is used for status tracking and phase-transition comments only -- artifacts are not uploaded as attachments.
```

— `/home/vscode/.claude/CLAUDE.md`

```
/home/vscode/.claude/skills/qrspi-work/SKILL.md:11-14
You are a state machine. Read the ticket's Linear status and execute the matching action. Run autonomously -- no approval gates between phases. Print verbose progress so the operator can observe.
```

— `/home/vscode/.claude/skills/qrspi-work/SKILL.md:11-14`

**Dependencies:** The qrspi system depends on Linear for phase tracking but has no skill invocation observability.

**Implicit contracts:** Observability is scoped only to the scripts the skill helps create (via ShellCheck and manual review), not to the skill's own usage patterns.

---

## Discovered Patterns

1. **Two-tier skill architecture**: Global skills (`~/.claude/skills/`) register via frontmatter description matching without slash commands. Project skills (`<repo>/.claude/skills/`) have slash command wrappers (`/qrspi-*`) and reference `.claude/agents/` for prompt content.

2. **Frontmatter field consistency**: All SKILL.md files use `name` and `description` as required fields. Project skills add `command`, `argument-hint`, and `allowed-tools`. Global skills may add `command` but it maps differently (slash command vs. tool invocation).

3. **No `.qrspi/agents/` directory exists**: Despite CLAUDE.md documenting it as the convention, the actual agent definitions live in `.claude/agents/` (created during worktree setup). The `.qrspi/agents/` path is a stale convention reference.

4. **ShellCheck is manual-only**: No automated ShellCheck infrastructure exists. The tool is not even installed in the environment. The quality gate relies entirely on agent compliance with skill guidance.

5. **Evals are agent-focused, not skill-focused**: The `evals/` directory contains test cases for QRSPI workflow agents (questions, research, implement, etc.) and the graphite CLI skill, but no eval infrastructure for generic skills like `writing-bash-scripts`.

6. **Worktree skills diverge from repo skills**: Each worktree (RUS-5, RUS-6, RUS-7, RUS-8) has its own copy of `.claude/skills/qrspi-*` SKILL.md files with worktree-specific content (inlining the full prompt instead of referencing `.claude/agents/`). The main repo SKILL.md files are thin wrappers.

7. **Skill-creator produces guidance, not files**: The skill-creator skill guides the agent through a skill creation workflow but expects the agent to manually create and write the SKILL.md and supporting files. The `package_skill.py` script packages a completed skill into a `.skill` file but does not create the SKILL.md content.

## Inconsistencies

1. **CLAUDE.md references `.qrspi/agents/` but it does not exist**: The project CLAUDE.md states "Agent prompt definitions live in `.qrspi/agents/`" but the directory has never been created. The actual agent files live in `.claude/agents/` within each worktree.

2. **Bash version check location**: The bash 4+ requirement is documented in `references/conventions.md` (a detailed reference file) rather than in the SKILL.md body (the primary skill entry point). An agent reading only SKILL.md would not know about the bash version requirement.

3. **BATS recommendation vs. no infrastructure**: The SKILL.md recommends BATS for testing but provides no BATS scaffolding files, no install script, and the `bats` binary is not installed. This creates a gap between recommendation and practical usability.

4. **Logging convention naming mismatch**: The skill-creator's question Q11 mentions `log()`, `info()`, `warn()`, `die()` helpers, but the actual writing-bash-scripts skill uses `log_info()`, `log_warn()`, `log_error()` -- a different naming convention.

5. **Ticket may be a duplicate**: The writing-bash-scripts skill already exists with complete structure (SKILL.md + 4 reference files). The ticket RUS-5 ("Create a new agent skill called writing bash scripts") appears to have already been completed by a prior agent. This is either a duplicate ticket or a request for refinement that is not reflected in the current skill.

6. **No ShellCheck in environment**: The skill's acceptance criteria call for "ShellCheck-clean output" but ShellCheck is not installed in the environment. The guidance assumes the agent can run `shellcheck -x` but the tool is unavailable.
