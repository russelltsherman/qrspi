# Design — writing-bash-scripts agent skill

**Ticket:** RUS-5
**Research basis:** research.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

The `writing-bash-scripts` skill directory exists at `/workspaces/qrspi/.claude/skills/writing-bash-scripts/` but is incomplete — it contains only an empty `references/` subdirectory and no `SKILL.md` file (ref: Q3). This suggests the directory was scaffolded but the content was never written.

The project's skills live in `.claude/skills/<name>/` and use a custom YAML frontmatter convention with keys: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q4). There is no reference to `agentskills.io` anywhere in the codebase (ref: Q8).

There is no `skill-creator` skill, agent, or automation tool in the project (ref: Q2). The eval harness (`scripts/run_eval.py`, `scripts/grade.py`, etc.) exists but only validates agent output artifacts after generation — it has no ShellCheck integration and no schema validation for SKILL.md files (ref: Q11).

All skills in the project are purely static Markdown documents with no persistent state (ref: Q6). The `qrspi-work` skill (731 lines) is the largest, using a two-tier pattern: thin SKILL.md wrappers that spawn agents from `.claude/agents/` (ref: Q5). But not all skills follow this — some embed all guidance directly in the SKILL.md body.

## Desired End State

A complete `writing-bash-scripts` skill at `.claude/skills/writing-bash-scripts/SKILL.md` that:

- **AC1:** Follows the agentskills.io directory structure — SKILL.md at the root, with optional `references/`, `scripts/`, `assets/` subdirectories. The directory already exists with `references/`; we confirm this layout matches the standard.
- **AC2:** Built following the skill-creator pattern (adapted — since skill-creator does not exist, we create the SKILL.md directly, as manual creation is the project's established pattern per research).
- **AC3:** SKILL.md body under 500 lines / 5000 tokens, using the project's custom frontmatter format (`name`, `description`, `command`, `argument-hint`, `allowed-tools`).
- **AC4:** Contains all specified conventions: strict mode, error handling, argument parsing, subcommand dispatcher, logging, quoting, dependency checking, help, temp files, code organization, testing/linting, portability notes.
- **AC5:** Includes a gotchas section covering common pitfalls (unquoted variables, missing `--` in commands, `cd` without error check) as a separate subsection in the SKILL.md body.
- **AC6:** Mentions BATS-core by name with an inline example in the SKILL.md body (consistent with the pattern of embedding bash snippets directly rather than placing them in references/).
- **AC7:** Encodes the ~200-line heuristic as soft guidance for the agent, not as enforced tooling.
- **AC8:** Specifies a generic pattern for dependency checking (exit code 1, descriptive error message to stderr) — no per-dependency exit code mapping.

## Delta

### Files to create/modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `.claude/skills/writing-bash-scripts/SKILL.md` | The complete skill document (~180-250 lines) |
| Create (optional) | `.claude/skills/writing-bash-scripts/references/bash-template.sh` | A minimal bash script template showing all conventions in a single working example |

### Content structure of SKILL.md

```
--- frontmatter ---
# writing-bash-scripts

## When to use

## Code Organization (top-to-bottom)

## Strict Mode

## Error Handling

## Argument Parsing

## Subcommand Dispatcher

## Logging

## Quoting & Variables

## Dependency Checking

## Usage/Help

## Temp Files

## Testing & Linting

## Portability

## Gotchas

## Scope Guidance
```

### Optional: Bash template

A single-file reference showing a complete script with all conventions applied. This would go in `references/` and be only ~60-80 lines, giving agents a concrete copy-paste base.

## Pattern Decisions

### Decision 1: Skill type — self-contained guidance vs. thin wrapper

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md with all conventions inline | Agents read one file; no indirection; consistent with simpler existing skills | Larger SKILL.md file |
| B | Thin wrapper that spawns a `writing-bash-scripts` agent | Follows the two-tier pattern used by qrspi-design, qrspi-research, etc. | Requires creating a new agent file; adds complexity for a guidance-only skill |

**Recommendation:** Option A — self-contained SKILL.md
**Rationale:** This skill encodes conventions and best practices, not a multi-step workflow. It needs no Linear API calls, no artifact generation, and no sub-agent coordination. The existing `qrspi-work` skill includes inline bash snippets as examples rather than delegating to agents (ref: Q5). A guidance skill is a single document by nature — wrapping it in an agent adds indirection without benefit.
**NEW PATTERN?** No — self-contained guidance skills exist (the body content of every skill is instructional).

### Decision 2: Frontmatter format — agentskills.io vs. project convention

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Use the project's existing frontmatter convention (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Matches all 10 existing skills; the harness already parses this format | Not explicitly "agentskills.io compliant" |
| B | Invent an agentskills.io-compatible frontmatter with `version`, `category`, etc. | Allegedly follows the stated standard | No agentskills.io spec is documented; breaks consistency with existing skills; the project explicitly does not use this standard (ref: Q8) |

**Recommendation:** Option A — project convention
**Rationale:** The research finds that the project uses its own frontmatter convention and has zero reference to agentskills.io (ref: Q8). The ticket mentions agentskills.io, but the actual project standard is the 5-key format. Aligning with the established pattern ensures the skill loads correctly alongside existing ones.
**NEW PATTERN?** No — follows the existing 5-key frontmatter convention.

### Decision 3: Bash template placement — inline example vs. references/ file

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline BATS example and template snippets in the SKILL.md body | Consistent with qrspi-work's pattern of embedding bash code directly; simpler | SKILL.md grows longer |
| B | A complete bash template in `references/bash-template.sh` | SKILL.md stays focused; template is reusable as a starting point | Adds another file; references/ currently unused for templates |

**Recommendation:** Option B — template in `references/` with brief inline examples
**Rationale:** The `references/` directory is already created for this skill (ref: Q5). A complete template showing all conventions in action is too long for inline (would add ~80 lines), but agents need it as a copy-paste base. The gotchas and convention descriptions go inline (short, scannable); the full template goes in references/. This follows the qrspi-work pattern where long procedural content lives in references/.
**NEW PATTERN?** Partially — the `references/` directory exists but has never held a code template (only `review-cascade.md`, a procedural document). A `.sh` file in `references/` would be a new file type in that directory.

### Decision 4: Command field — include `/writing-bash-scripts` vs. omit

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Include `command: /writing-bash-scripts` in frontmatter | Agents can invoke via slash command; consistent with all existing skills | Implies a persistent invocation surface |
| B | Omit `command` — skill is triggered implicitly when agents write bash | No false surface; skill activates when context is relevant | Deviates from every existing skill's frontmatter |

**Recommendation:** Option A — include the command
**Rationale:** Consistency with all 10 existing skills. The `/writing-bash-scripts` command gives users a discoverable entry point. Even if the skill primarily activates implicitly, the command is harmless.
**NEW PATTERN?** No — follows the command convention used by every existing skill.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md exceeds 500 lines | Medium | High — agent context overflow, lower eval scores | Structure content tightly; use references/ for the bash template; target ~200 lines for main body |
| agentskills.io is a real standard the user expects | Low | High — if the user expects compliance and we deliver project convention, the deliverable is misaligned | Confirm with the user whether agentskills.io means something specific or is aspirational |
| skill-creator expectation mismatch | Medium | Medium — ticket says "use skill builder skill" but it doesn't exist; user may expect automation | Clarify that skill-creator does not exist and manual SKILL.md creation is the established project pattern |
| Template in references/ is ignored by agents | Low | Medium — if agents don't read references/ files, the template provides no value | Explicitly instruct agents to read `references/bash-template.sh` in the SKILL.md; test with a skill invocation |
| Bash 3.2 vs 4+ compatibility | Medium | Medium — macOS ships bash 3.2, skill targets 4+; agents on macOS may generate non-portable scripts | Encode the compatibility note as a visible gotcha; suggest `#!/usr/bin/env bash` shebang and flag bash 4+ features explicitly |

## Open Questions

- OQ1: The ticket references `agentskills.io` as a standard, but the project has no reference to it and uses its own frontmatter convention. Does the user want us to adopt a real `agentskills.io` format (if one exists) or does "follows agentskills.io directory structure" just mean the SKILL.md + optional references/scripts/assets layout, while keeping the project's existing frontmatter?

- OQ2: Should the `writing-bash-scripts` skill get its own agent (`.claude/agents/writing-bash-scripts.md`) in addition to the SKILL.md, or is a self-contained skill sufficient? The two-tier pattern is used by all QRSPI workflow skills but this is not a workflow skill.

- OQ3: The ticket mentions "produces ShellCheck-clean output when an agent follows the guidance." Is this a design goal (the skill's guidance should be designed to produce clean scripts) or a measurable acceptance criterion (we should add a ShellCheck eval assertion)? The eval harness currently has no ShellCheck integration.

- OQ4: Should the skill include a `scripts/` directory with example BATS test files, or is the inline BATS mention and the template in `references/` sufficient? No existing skill uses a `scripts/` directory.
