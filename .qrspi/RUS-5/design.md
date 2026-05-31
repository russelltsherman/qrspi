# Design — Create a writing-bash-scripts agent skill

**Ticket:** RUS-5
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31
**Status:** draft

## Current State

The repo's QRSPI skills live under `.claude/skills/<name>/SKILL.md`, each with frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) and a steps section (ref: Q1, Q3). Most skills follow a two-file pattern where a thin SKILL.md delegates to `.claude/agents/qrspi-<name>.md`; `qrspi-work` is the exception, defining its prompt inline (ref: Q2, patterns-1, patterns-2, patterns-6). The `description` field uses "Use when..." language for auto-trigger matching against user utterances (ref: Q4). The eval harness at `evals/suite.json` defines programmatic, llm_judge, and script-type assertions scored by `scripts/grade.py` (ref: Q9, patterns-4). The `skill-creator` skill lives at `/home/vscode/.agents/skills/skill-creator/` with its own `scripts/package_skill.py` and eval infrastructure, outside repo scope (ref: Q5, patterns-5). The `writing-bash-scripts` skill already exists as a built-in skill in the system prompt listing but has no SKILL.md file in the repo — only `update-config` shares this status (ref: patterns-1, patterns-2). There are no existing bash scripting convention skills in the repo; the only scripts are Python eval harness files (ref: Q6).

## Desired End State

After this ticket ships:

- **AC1: Skill exists and is loadable.** A SKILL.md file at `.claude/skills/writing-bash-scripts/SKILL.md` with valid YAML frontmatter (`name`, `description`, `command: /writing-bash-scripts`, `argument-hint`, `allowed-tools`) and a structured SKILL.md body following the agentskills.io standard pattern.
- **AC2: All 13 convention topics covered.** The skill body encodes guidance for: strict mode, error handling, argument parsing, subcommand dispatch, logging, quoting, dependency checking, usage/help, temp files, code organization, testing/linting, portability, and shellCheck compliance.
- **AC3: Skill is triggerable.** The `description` field uses "Use when..." language covering bash script creation, editing, and ShellCheck review. The skill is listed in `.claude/CLAUDE.md` under available skills.
- **AC4: Follows repo skill conventions.** The skill uses the same frontmatter convention as other `.claude/skills/` skills (ref: Q3). The skill is added to the skill listing in `.claude/CLAUDE.md`.
- **AC5: Generates ShellCheck-clean output.** The skill encodes ShellCheck-relevant conventions (SC2034, SC2086, SC2034, SC2006, SC2015, SC2034, SC2046, etc.) and recommends ShellCheck as a post-generation gate (ref: Q8).
- **AC6: Portability guidance for bash 3.2 vs 4+.** The skill documents macOS bash 3.2 limitations (no associative arrays, no `mapfile`, no `<<<` in some contexts) and recommends POSIX-compatible fallbacks (ref: Q7).

## Delta

- **New file:** `.claude/skills/writing-bash-scripts/SKILL.md` — the complete skill definition (~150-200 lines)
- **Modified file:** `.claude/CLAUDE.md` — add `writing-bash-scripts` entry to the "Available skills" list in the QRSPI Workflow section
- **No new agent file** (`.claude/agents/`) — this is a guidance-only skill, not a QRSPI phase delegate

## Pattern Decisions

### Decision 1: Single SKILL.md vs Two-File Pattern

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single SKILL.md (like most `.claude/skills/` skills) | Simpler, one file to maintain, follows pattern of 9/10 repo skills | Cannot define model/agent constraints separately |
| B | Two-file pattern (SKILL.md + `.claude/agents/writing-bash-scripts.md`) | Separates trigger config from prompt logic, matches `qrspi-work` model | Adds a file the agent must manage, overkill for guidance-only skill |

**Recommendation:** Option A — single SKILL.md
**Rationale:** 9 of 10 repo skills use a single SKILL.md. The two-file pattern (`qrspi-work` and the QRSPI phase delegates) is for skills that spawn sub-agents with specific model constraints. This skill is guidance-only — the agent applies the conventions directly, it does not spawn a sub-agent. Adding an agent file would add maintenance overhead without value.
**NEW PATTERN?** No — follows the dominant single-file pattern.

### Decision 2: Guidance-Only vs Reference Artifacts

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Guidance-only: conventions encoded directly in SKILL.md body | Self-contained, no external file dependencies, follows most repo skill pattern | Longer SKILL.md, all conventions in one file |
| B | Split: SKILL.md body references files in `references/` subdirectory (like `qrspi-work` has) | Modular, each topic is a separate file, easier to maintain individual conventions | Adds directory structure complexity, only 1/10 skills use `references/`, increases file count |
| C | Hybrid: SKILL.md has overview + a `references/bash-conventions.md` for detailed examples | Best of both for discoverability | Still two files, creates precedent for a third pattern |

**Recommendation:** Option A — guidance-only in SKILL.md body
**Rationale:** Only `qrspi-work` uses `references/`, and it contains a single file with a tightly coupled concept (review cascade). The writing-bash-scripts skill has 13 independent topic areas — splitting them would create a flat directory of reference files that the SKILL.md body would need to enumerate. A well-structured SKILL.md body with clear section headers is more maintainable than a collection of reference files for this use case. The agentskills.io standard (as inferred from skill-creator's `references/schemas.md`) favors self-contained SKILL.md bodies.
**NEW PATTERN?** No — follows the dominant self-contained SKILL.md pattern.

### Decision 3: Command Definition vs Auto-Invoke Only

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Define `command: /writing-bash-scripts` for explicit invocation | Users can explicitly request bash script help, matches every existing repo skill | Less "always-on" feel for a guidance skill |
| B | No `command` field, rely purely on `description` auto-trigger | More natural for a guidance/consulting skill | Breaks pattern — every existing repo skill defines a `command` field; auto-trigger alone may be unreliable |
| C | Define command + auto-invoke via rich `description` | Covers both explicit and implicit invocation | Slightly redundant, but safe |

**Recommendation:** Option C — define `command: /writing-bash-scripts` AND use rich auto-trigger language in `description`
**Rationale:** Every existing repo skill defines a `command` field — this is an implicit contract that the system expects. The `description` field's "Use when..." language provides auto-triggering as a secondary path. This gives the best of both worlds: explicit invocation when the user types the command, and implicit invocation when the agent detects bash scripting context.
**NEW PATTERN?** No — follows the convention of command + description-based auto-trigger (the system prompt already says "invoke with / or let Claude auto-invoke").

### Decision 4: ShellCheck Integration

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Encourage ShellCheck as a post-generation gate in the skill body | Simple, doesn't add automation complexity, respects the manual-review workflow | Relies on agent discipline; no programmatic enforcement |
| B | Encode specific ShellCheck rule IDs (SC2034, SC2086, etc.) with explanations | Concrete, actionable guidance | Rule coverage may be incomplete; ShellCheck versions differ |
| C | Both A and B | Most thorough coverage | More content in SKILL.md |

**Recommendation:** Option C — encode both encouragement AND specific rule IDs
**Rationale:** The ticket explicitly requires "ShellCheck-clean output." Encoding specific high-surface-area rules (SC2034 unused vars, SC2086 unquoted variables, SC2006 old-style `$()`, SC2015 AND/OR precedence, SC2046 unquoted word splitting) gives the agent concrete targets. The encouragement to run ShellCheck post-generation provides the operational gate. This matches how `writing-bash-scripts` is described in the system prompt — both as a guidance skill and as a verification gate (ref: Q8).
**NEW PATTERN?** No — specific linting rule references would be novel in the repo but follow the same mental model as ShellCheck's own documentation format.

### Decision 5: Bash Portability Scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bash 3.2 (macOS) as floor, document POSIX fallbacks for 4+ features | Maximum compatibility, truly portable | More content, more conditional logic in guidance |
| B | Bash 4+ as floor, note macOS caveat with a single `bash --version` check recommendation | Simpler guidance, targets the modern majority | macOS users get broken scripts by default |
| C | Bash 3.2 as floor with explicit version detection pattern | Automated compatibility, self-documenting | Adds complexity to every script |

**Recommendation:** Option A — bash 3.2 as floor with POSIX fallback documentation
**Rationale:** macOS ships bash 3.2 by default (though `brew install bash` gets users to 5.x). The skill should default to compatible patterns and call out bash 4+ features (associative arrays, `mapfile`, `printf -v`, `shopt -s extglob`) with POSIX fallbacks. The version detection pattern from Q7 is overkill — a documentation note is sufficient and matches the ticket's framing of "should the skill include a conditional detection mechanism (e.g., bash --version check at skill invocation time), or is the documentation note sufficient?"
**NEW PATTERN?** No — portability notes are common in shell scripting guidance.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md grows too large (>300 lines), degrading agent context utilization | medium | high | Structure with clear section headers and concise bullet points. Use the agentskills.io pattern of "trigger/convention/steps" rather than exhaustive examples. Cap each topic to 3-5 bullet points. |
| The `description` field's auto-trigger language is too broad, causing the skill to fire on unrelated shell scripting (e.g., Dockerfiles, Makefiles) | medium | medium | Use precise "Use when..." language that mentions "bash script" explicitly. Do not say "shell scripting" generically. Distinguish from `using-graphite-cli`'s git-related bash usage. |
| ShellCheck rule coverage becomes outdated as ShellCheck adds/removes rules | low | low | Only document stable, high-surface-area rules (SC2034, SC2086, SC2015). Avoid documenting rule behavior changes that are version-specific. Recommend the agent run `shellcheck --version` to check capabilities. |
| Duplicate guidance with other existing skills (e.g., qrspi skills already mention "strict mode" or "ShellCheck-clean output") | low | medium | Reuse the exact same phrasing for shared conventions (e.g., "HARD STOP: Infrastructure Errors" pattern). The writing-bash-scripts skill provides the detailed HOW, while other skills provide the WHAT. |
| Agent applies bash conventions to non-bash contexts (sh, zsh, PowerShell) | medium | low | Explicitly scope the `description` to "bash script". Add a "scope boundary" section noting the skill applies only to bash. The `using-graphite-cli` skill's git operations may use bash but are handled by a different skill. |

## Open Questions

- OQ1: Should the `argument-hint` field be `<script-path>` (for editing guidance) or `<path>` (for broader use), or should it be omitted since the skill's purpose is guidance rather than tool invocation?
- OQ2: The ticket says "following the agentskills.io standard pattern" — should the skill include a `references/` directory with example scripts (the `scripts/` subdirectory from the agentskills.io layout mentioned in Q2), or is pure text guidance sufficient?
- OQ3: Should `allowed-tools` include `Bash(shellcheck:*)` to explicitly permit ShellCheck invocation, or should the skill simply recommend it without restricting tool access?
- OQ4: When the skill is invoked alongside other skills (e.g., `using-graphite-cli` for git operations), should the SKILL.md body include an explicit "precedence" or "delegation" note clarifying when to use each skill's guidance?
