# Design — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Generated:** 2026-05-25
**Status:** draft

---

## Current State

Skills in this project are stored in `.claude/skills/<skill-name>/` using kebab-case directory names, each containing a required `SKILL.md` with YAML frontmatter (ref: Q3). The skill-creator operates as a conversational agent that guides the user through intent capture, drafts the SKILL.md, and optionally produces reference files, scripts, and assets (ref: Q5). Validation is handled by `quick_validate.py`, which checks for required `name` and `description` frontmatter fields and rejects unexpected keys from a hardcoded allow-list of six properties (ref: Q1).

The canonical directory layout is `skill-name/SKILL.md` plus optional `references/`, `scripts/`, and `assets/` subdirectories, enforced only by convention — no module validates the structure beyond requiring SKILL.md to exist (ref: Q2). Reference files are never auto-loaded into agent context; the SKILL.md body must contain explicit pointers telling the consuming agent when to read them (ref: Q6). Activation requires no registry — placing a valid SKILL.md in the correct filesystem location is sufficient for Claude Code to discover it (ref: Q7).

There is no automated enforcement of the 500-line / 5000-token guidance for SKILL.md files; it is an advisory convention only (ref: Q9). No CI pipeline, ShellCheck integration, or pre-commit hooks exist in this repository (ref: Q13). The project eval harness has orchestration infrastructure but agent execution is stubbed (ref: Q12). No runtime telemetry captures skill invocation or adherence (ref: Q14). The skill-creator's `quick_validate.py` allow-list does not include `command` or `argument-hint` fields used by this project's own skills (ref: Q4). No deduplication mechanism exists between SKILL.md body and reference files (ref: Q10).

---

## Desired End State

Each acceptance criterion from the ticket mapped to observable system behavior:

**AC: Skill follows agentskills.io directory structure with valid SKILL.md frontmatter** — A new directory `writing-bash-scripts/` exists at the target skill location containing a `SKILL.md` with valid `name` and `description` frontmatter, plus a `references/` subdirectory for detailed convention material that exceeds what fits in the main body.

**AC: Built using the Anthropic skill builder skill** — The skill-creator skill is invoked during authoring. The resulting artifact reflects the skill-creator's output conventions (progressive disclosure structure, clear trigger conditions, bundled resources pattern).

**AC: SKILL.md body under 500 lines / 5000 tokens** — The main SKILL.md body contains a concise summary of bash scripting conventions (header/strict mode, error handling, argument parsing, code organization, testing) with explicit pointers to reference files for detailed rules. Line count stays well under 500.

**AC: Detailed reference material in references/ directory if needed** — A `references/` directory contains one or more files providing expanded guidance on topics too detailed for the main body: the full subcommand dispatcher pattern, the complete logging helper library, portability gotchas, and a ShellCheck-clean template script.

**AC: Produces ShellCheck-clean output when an agent follows the guidance** — Every code pattern described in the skill and its references passes ShellCheck with zero warnings. The guidance itself is structured to produce compliant output (strict mode, proper quoting, no unquoted variables).

---

## Delta

### New files

| Path | Purpose |
|------|---------|
| `writing-bash-scripts/SKILL.md` | Main skill definition with frontmatter and concise body |
| `writing-bash-scripts/references/conventions.md` | Full bash conventions (quoting, variables, dependencies, temp files) |
| `writing-bash-scripts/references/patterns.md` | Subcommand dispatcher, argument parsing templates, logging helpers |
| `writing-bash-scripts/references/gotchas.md` | Common pitfalls and portability notes (BSD vs GNU, bash 3.2 vs 4+) |

### Modified files

None. This is a net-new skill with no modifications to existing project files.

### New queries / integrations

None. The skill is passive guidance — it is loaded into context when triggered and requires no external API calls, database queries, or service integrations.

### Placement decision

The skill will be authored in a temporary working location and then placed in the appropriate skills directory. Final placement depends on whether this is a project-scoped or user-scoped skill (see Open Questions).

---

## Pattern Decisions

### PD-1: Skill body structure (concise summary vs. full inline)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Full inline | All conventions in SKILL.md body, no references | Single file, no Read calls needed | Will exceed 500-line limit given ticket scope |
| **B: Summary + references (recommended)** | SKILL.md has triggers, structure overview, and pointers; references hold details | Stays under 500 lines, progressive disclosure matches existing pattern | Agent must make Read calls for full detail |
| C: Minimal stub + heavy references | SKILL.md is just frontmatter and a "read references/" instruction | Maximum brevity | Loses the benefit of immediate in-context guidance |

Recommendation: Option B. This matches the progressive disclosure pattern documented in the skill-creator (ref: Q6) and used by the skill-creator's own SKILL.md (486 lines with references for schemas and eval configs).

**Pattern status:** EXISTING PATTERN — mirrors skill-creator's own structure.

### PD-2: Reference file granularity

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Single reference file | One `references/bash-conventions.md` with all detail | Simple, one Read call | Large file, agent loads everything even if only one topic is relevant |
| **B: Topic-split references (recommended)** | Separate files for conventions, patterns, and gotchas | Agent reads only what is needed for current task | More files to maintain, more pointers in SKILL.md |
| C: Per-section files | One file per ticket section (header, error handling, args, logging, etc.) | Maximum granularity | Too many files (10+), excessive fragmentation |

Recommendation: Option B. Three reference files provide meaningful topic boundaries without over-fragmentation. The agent writing a simple script reads `conventions.md`; one writing a multi-command CLI also reads `patterns.md`; one debugging portability issues reads `gotchas.md`.

**Pattern status:** EXISTING PATTERN — skill-creator uses topic-split references (schemas.md, eval-config.md).

### PD-3: Frontmatter field set

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Strict skill-creator schema | Only `name`, `description`, optional `allowed-tools` | Passes `quick_validate.py` | No `command` field, cannot be invoked via `/writing-bash-scripts` |
| **B: Extended fields matching project convention (recommended)** | Include `name`, `description`, and `command` | Matches how all QRSPI skills are defined; invocable via slash command | Would fail `quick_validate.py` if run against it |
| C: Full QRSPI set | Include `command`, `argument-hint`, `allowed-tools` | Most feature-complete | `argument-hint` is unnecessary (skill takes no arguments) |

Recommendation: Option B. The project already uses `command` in all 10 local skills (ref: Q4). The `quick_validate.py` mismatch is a known inconsistency in the ecosystem, not something this skill should try to fix.

**Pattern status:** EXISTING PATTERN — all QRSPI skills use this field set.

### PD-4: Skill placement scope

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Project-local (`.claude/skills/`) | Scoped to this repository | Only available in this project | Bash scripting is a general skill |
| **B: User-global (`~/.agents/skills/`) (recommended)** | Available across all projects | Matches the general-purpose nature of bash guidance | Not version-controlled with any single project |

Recommendation: Option B. Bash scripting guidance is project-agnostic. Placing it alongside `skill-creator` and `using-graphite-cli` in the user-global location is appropriate.

**Pattern status:** EXISTING PATTERN — general-purpose skills live in `~/.agents/skills/` (ref: Q3).

### PD-5: Template script inclusion

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: No template | Conventions described in prose only | Agent synthesizes from rules each time | Higher variance in output |
| **B: Template in references (recommended)** | A `references/template.sh` showing canonical structure | Agent can copy and adapt; demonstrates all conventions together | One more file; must be kept in sync with prose |
| C: Template in assets | A `assets/template.sh` for direct file copy | Usable as a scaffold | assets/ semantics imply inclusion in output, not context |

Recommendation: Option B. A reference template gives the agent a concrete starting point that demonstrates the code organization section of the ticket (shebang, set options, constants, helpers, commands, main). Placing it in `references/` means it is read into context rather than blindly copied.

**Pattern status:** NEW PATTERN — no existing skill includes a `.sh` file in references. However, the skill-creator documentation explicitly supports scripts and references containing any file type. Low risk.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md exceeds 500-line limit due to ticket's extensive convention list | High | Medium — violates acceptance criteria | Use progressive disclosure: keep body to structure/triggers/overview (~150-200 lines), move detailed rules to references |
| Agent ignores reference file pointers and produces incomplete bash scripts | Medium | Medium — output missing conventions for portability, gotchas | Include conditional triggers in SKILL.md: "If the script has 2+ commands, read `references/patterns.md`". Make pointers actionable, not optional-sounding |
| Template script in references becomes stale relative to prose conventions | Low | Low — minor inconsistency | Template is small (~40 lines), demonstrating structure only. Detailed rules live in prose. Cross-reference with a note in the template header |
| Frontmatter using `command` field fails if skill-creator validation is run against it | Medium | Low — validation is optional, not in CI | Document the known schema mismatch. Do not add `command` to `quick_validate.py` (out of scope) |
| ShellCheck compliance claim is unverifiable without CI integration | Medium | Medium — acceptance criterion cannot be mechanically confirmed | Include ShellCheck directives guidance in the skill. Recommend running `shellcheck` locally. Note that CI enforcement is out of scope for this ticket |

---

## Open Questions

1. **Placement confirmation:** Should this skill live in `~/.agents/skills/writing-bash-scripts/` (user-global, available in all projects) or `.claude/skills/writing-bash-scripts/` (project-local to qrspi)? The design recommends user-global based on the general-purpose nature of bash guidance, but this is a human decision about scope.

2. **Trigger conditions:** What phrases or contexts should cause Claude to auto-invoke this skill? Candidates include: any request to write a bash/shell script, any `.sh` file creation, any modification to an existing bash script. Should it also trigger when reviewing bash scripts (code review mode)?

3. **Interaction with existing scripts in the project:** The project contains `run_loop.sh` and `.devcontainer/config/post-start.sh`. Should this skill retroactively apply to those files, or is it forward-looking only?

4. **ShellCheck version targeting:** The ticket says "ShellCheck-clean output" but does not specify a ShellCheck version. Should the skill target the latest stable ShellCheck rules, or pin to a specific version for reproducibility?
