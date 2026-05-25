# Design — Create a skill for writing bash scripts
**Ticket:** RUS-5
**Generated:** 2026-05-25
**Status:** draft

## Current State

The project has 10 skills under `.claude/skills/`, all following a `SKILL.md`-only structure except `qrspi-work` which adds a `references/` subdirectory (ref: Q1). Skills are discovered by directory convention with no manifest or registration step required (ref: Q4). The canonical skill anatomy is defined by the user-level skill-creator at `~/.claude/skills/skill-creator/SKILL.md` (ref: Q1).

The project's 8 existing bash scripts are all single-purpose with no subcommand dispatch, no argument parsing, and no `usage()` functions (ref: Q11). Seven of eight use `#!/usr/bin/env bash`; all but `show-motd` include `set -euo pipefail` (ref: Q9, Q11). No script uses bash 4+ exclusive features (ref: Q9).

ShellCheck is not installed in the devcontainer and no `.shellcheckrc` exists. One inline ShellCheck directive (`SC2053`) exists in `protect-paths` with a justification comment (ref: Q10). BATS-core is not installed, though the user's global settings include `Bash(bats:*)` permissions (ref: Q12).

The skill-creator is an interactive conversational skill that writes `SKILL.md` directly and optionally runs an eval loop with subagent-based test execution (ref: Q2, Q5). A user-level memory directive requires invoking the skill-creator when creating or substantially modifying a skill (ref: Q5). The eval loop is recommended but not mandatory — the user can opt out (ref: Q5).

SKILL.md has a soft budget of 500 lines; overflow goes to `references/` with prose-based "when to read" instructions in the main file (ref: Q6, Q7, Q8). Frontmatter requires `name` and `description`; the project convention adds `command`, `argument-hint`, and `allowed-tools` (ref: Q3).

No CI, pre-commit hooks, or automated validation exists in the project (ref: Q6, Q10, Q14).

## Desired End State

Each acceptance criterion mapped to system behavior:

**AC1: Skill follows agentskills.io directory structure with valid SKILL.md frontmatter** — A directory `.claude/skills/bash-scripts/` exists containing `SKILL.md` with valid YAML frontmatter (minimally `name` and `description`; following project convention also `command`, `argument-hint`, `allowed-tools`) and optionally a `references/` subdirectory.

**AC2: Built using the Anthropic skill builder skill** — The skill-creator skill is invoked to produce the SKILL.md. The conversation follows the skill-creator's multi-phase process (capture intent, interview, write, optionally eval).

**AC3: SKILL.md body under 500 lines / 5000 tokens** — The main SKILL.md file stays within the soft budget. Detailed reference material (examples, gotchas catalog, portability notes) lives in `references/` if needed to stay under budget.

**AC4: Detailed reference material in references/ directory if needed** — If the ticket's conventions cannot fit within 500 lines of SKILL.md, a `references/` directory is created containing supplementary files (e.g., `references/conventions.md`, `references/gotchas.md`) with clear "when to read" instructions in the main SKILL.md body.

**AC5: Produces ShellCheck-clean output when an agent follows the guidance** — The skill's instructions, when followed by an agent, result in bash scripts that pass `shellcheck` with zero warnings. The skill encodes quoting rules, proper variable expansion, and the justification-comment convention for any disable directives.

## Delta

### New Files

| Path | Purpose |
|------|---------|
| `.claude/skills/bash-scripts/SKILL.md` | Main skill definition with frontmatter and body |
| `.claude/skills/bash-scripts/references/conventions.md` | Full convention catalog (header, error handling, argument parsing, logging, quoting, deps, organization) |
| `.claude/skills/bash-scripts/references/gotchas.md` | Common pitfalls section with explanations |

### Modified Files

None. This is a purely additive change. No existing files require modification.

### Content Allocation

SKILL.md (~200-300 lines) contains:
- Frontmatter with triggering description
- When-to-use decision logic (new script vs. existing script vs. "too large, use another language")
- Template skeleton (prose description, not code block — per design rules)
- Pointers to reference files with "when to read" guidance
- ShellCheck compliance rules
- Testing guidance (BATS mention, source guard pattern)

`references/conventions.md` (~150-250 lines) contains:
- Header and strict mode rules
- Error handling patterns (trap, exit codes, stderr)
- Argument parsing (getopts vs while/case/shift)
- Subcommand dispatcher pattern
- Logging helpers
- Quoting and variable rules
- Dependency checking
- Usage/help patterns
- Temp file handling
- Code organization order
- Portability notes (bash 3.2 vs 4+ vs 5+)

`references/gotchas.md` (~50-100 lines) contains:
- Unquoted variables
- Missing `--` in commands accepting options
- `cd` without error check
- Word splitting in `for` loops
- Process substitution portability
- Array gotchas

## Pattern Decisions

### Decision 1: Skill location (project-level vs user-level)

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Project-level (`.claude/skills/bash-scripts/`) | Consistent with all 10 existing project skills; versioned with the repo | Only useful in this project unless copied | |
| B. User-level (`~/.claude/skills/bash-scripts/`) | Available across all projects; bash guidance is general-purpose | Not versioned with this project; invisible to collaborators | RECOMMENDED |

This is a general-purpose skill not specific to the QRSPI project. However, the ticket says "build an agent skill" in the context of this project, and all 10 existing skills live at project level. **Flag: this requires human decision.** Placed in Open Questions.

### Decision 2: Content split strategy

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Single SKILL.md, no references | Simplest; all content in one file; matches 9 of 10 project skills | Likely exceeds 500-line budget given ticket scope | |
| B. SKILL.md + references/ split | Follows progressive disclosure; keeps triggering fast; matches qrspi-work and skill-creator patterns | Two-file coordination; reference must be explicitly loaded | RECOMMENDED |
| C. SKILL.md + multiple reference files | Fine-grained lazy loading (conventions, gotchas, portability each separate) | More files to maintain; may be overkill for this scope | |

Recommendation: Option B with two reference files (conventions + gotchas). The ticket's content naturally splits into "decision logic" (SKILL.md) and "lookup tables" (references). This follows the established pattern from qrspi-work (ref: Q8). **NEW PATTERN: This would be the first project-level skill with multiple reference files.** The skill-creator has multiple references, but it is user-level.

### Decision 3: Frontmatter field set

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Minimal (`name`, `description` only) | Matches skill-creator's own frontmatter; agentskills.io minimum | Breaks project convention; no explicit slash command | |
| B. Full project convention (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Consistent with all 10 project skills; explicit invocation path | Adds fields not strictly required by the standard | RECOMMENDED |

Recommendation: Option B. Consistency with the existing 10 skills matters more than minimalism. The `command` field enables explicit `/bash-scripts` invocation. `allowed-tools` should be `Read, Write, Bash` since the skill may need to read reference files and write/execute scripts.

### Decision 4: Portability stance

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Target bash 3.2+ (macOS stock) | Maximum portability; works on macOS without Homebrew bash | Loses associative arrays, namerefs, mapfile | |
| B. Target bash 4+ (ticket default) | Richer features; most Linux systems covered | macOS users need Homebrew bash; must document this | RECOMMENDED |
| C. Target bash 5+ (modern) | Latest features | Excludes older Linux distros | |

Recommendation: Option B per the ticket's explicit guidance. The skill should call out bash 4+ features when used and note the macOS 3.2 limitation. This aligns with existing project practice where no script currently uses bash 4+ features but the ticket explicitly states this target (ref: Q9).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md exceeds 500-line budget during skill-creator conversation | Medium | Low | Pre-allocate content to references/ before starting skill-creator; provide the split plan as input to the capture-intent phase |
| Skill-creator eval loop produces inconclusive results for a guidance-only skill (no code output to assert against) | High | Medium | Design eval cases that provide a bash scripting prompt, then assert structural properties of the generated script (shebang present, set -euo pipefail present, shellcheck-clean). May need to skip full eval and use qualitative review |
| Skill triggers too broadly (any mention of "bash" or "script") causing false activations | Medium | Medium | Craft description carefully to trigger on "writing bash scripts" not "running bash commands". Run the skill-creator's description optimization loop to tune triggering accuracy |
| Reference files not loaded when needed because Claude does not recognize the trigger condition | Low | High | Use explicit, unambiguous "when to read" language in SKILL.md (e.g., "Before generating any bash script, read references/conventions.md") rather than conditional loading |
| Conflict with user's existing bash conventions in other projects if skill is installed at user level | Low | Medium | Keep the skill opinionated but document override points; install at project level if human decides project-level placement |

## Open Questions

1. **Installation location**: Should the bash-scripts skill live at project level (`.claude/skills/bash-scripts/`) or user level (`~/.claude/skills/bash-scripts/`)? The skill is general-purpose (not QRSPI-specific), but the ticket context is this project. If user-level, the implementation slice must write to `~/.claude/skills/` instead.

2. **Eval loop depth**: The ticket says "Built using the Anthropic skill builder skill" and the memory directive says to always run the eval loop. However, a guidance-only skill (no deterministic output format) is hard to eval quantitatively. Should we run a lightweight eval (2-3 test cases, qualitative grading only) or the full benchmark cycle?

3. **Slash command name**: Should the command be `/bash-scripts`, `/write-bash`, or something else? The name affects both the directory and the triggering behavior.
