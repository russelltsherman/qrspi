# Design — Create a new agent skill called using claude cli

**Ticket:** RUS-9
**Research basis:** research.md @ 2026-06-02T15:00:00Z
**Generated:** 2026-06-02T16:00:00Z
**Status:** draft

## Current State

The QRSPI project uses a dual-layer architecture for agent orchestration. Skills live at `.claude/skills/<name>/SKILL.md` with YAML frontmatter containing five fields: `name`, `description`, `command`, `argument-hint`, and `allowed-tools` (ref: Q1). There are 10 existing skills, all thin slash-command wrappers that invoke phase agents via the `Agent` tool (ref: Q1, Q2). Subagent definitions live in `.claude/agents/<name>.md` with YAML frontmatter containing only `name`, `description`, and a flat `claude.tools:` list (ref: Q4). No `skill-creator` skill exists in this codebase despite being referenced (ref: Q2, Inconsistency #1).

The project has no built-in session management — no session ID tracking, no persistence files, no CLI flag parsing for sessions. The workflow relies on fresh-session-per-phase patterns enforced by the orchestrator spawning phase agents as subagents (ref: Q6). No hook events (`PreToolUse`, `PostToolUse`, `SubagentStop`) or hook dispatching logic exist in the project; these are external to Claude Code's runtime (ref: Q7). The permissions model is limited to per-phase tool lockdowns via YAML frontmatter — no `acceptEdits`, `plan`, `auto`, `dontAsk`, or `bypassPermissions` modes are encoded (ref: Q9, Inconsistency #6).

The eval harness (`evals/`) is a non-functional placeholder with zero agent invocation logic; all three critical paths (agent execution, LLM judge, script check) are stubs returning empty values (ref: Q11). Testing relies on pure-logic Python unit tests (`qrspi_resolve_state_test.py`, `qrspi_pr_state_test.py`) and manual end-to-end runs (ref: Q11, Inconsistency #5).

For the "using claude cli" skill specifically, the following are external to this codebase: CLI modes (interactive, headless/print, bare), output formats (`--output-format text|json|stream-json`), MCP server configuration files (`~/.claude.json`, `.mcp.json`), hook systems, permission rules, session management flags (`-c`, `-r`, `-n`, `--continue`, `--resume`, `--fork-session`), cost/resource metadata emission, and the settings hierarchy (Managed > CLI args > Local project > Shared project > User). The only CLI flag observed is `--dangerously-skip-permissions` in `post-create.sh` (ref: Q8, Inconsistency #4).

## Desired End State

After this skill ships, agents should be able to use Claude Code CLI programmatically for orchestration. Concretely:

- **AC1 (agentskills.io directory structure):** A new skill at `.claude/skills/using-claude-cli/SKILL.md` with valid frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) matching the observed pattern across all 10 existing skills (ref: Q1). Body under 500 lines / 5000 tokens.

- **AC2 (built via skill builder):** The skill is created through the skill-creator workflow, even though the tool is not yet implemented in this repo. The resulting SKILL.md follows the frontmatter pattern observed at `.claude/skills/*/SKILL.md` (ref: Q2).

- **AC3 (body under 500 lines):** SKILL.md body text stays under 500 lines and 5000 tokens, focusing on the most common patterns (headless mode, subagents, sessions, permissions) in the main file, with advanced orchestration (teams, worktrees, hooks) deferred to `references/` (ref: Q3).

- **AC4 (reference material):** A `references/` directory under the skill directory containing detailed reference docs for: advanced CLI flags, hook configuration examples, agent team orchestration, and permission rule patterns (ref: Q3, Inconsistency #3). No `scripts/` or `assets/` directories are needed — only one existing skill has a `references/` dir (ref: Q3).

- **AC5 (all three CLI modes):** The skill documents all five CLI modes (interactive, headless/print, bare, piped input, background) with correct flag usage. Since these patterns are external to this codebase, the skill must be authored as reference documentation derived from Claude Code's CLI specification rather than extracted from project source (ref: Q8).

- **AC6 (sub-agent spawning):** The skill documents built-in subagent types (Explore, Plan, General-purpose), custom subagent definitions via `.claude/agents/` markdown files with YAML frontmatter, CLI-defined ephemeral agents via `--agents '{JSON}'`, and the constraint that subagents cannot spawn other subagents (ref: Q4).

- **AC7 (session management):** The skill documents session ID capture (`session_id` from JSON output), continuation (`-c`), resumption (`-r`), naming (`-n`), forking (`--fork-session`), and ephemeral mode (`--no-session-persistence`) (ref: Q6).

- **AC8 (MCP integration):** The skill documents `.mcp.json` and `~/.claude.json` configuration, `claude mcp add` CLI command, session-specific `--mcp-config`, strict mode `--strict-mcp-config`, and the `mcp__<server>__<tool>` permission pattern (ref: Q5).

- **AC9 (permissions):** The skill encodes permission modes (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`), rule evaluation order (deny -> ask -> allow), `--allowedTools` / `--disallowedTools`, and the read-only auto-approved command list for CI/CD safety (ref: Q9).

- **AC10 (cost control):** The skill documents `--max-budget-usd`, `--max-turns`, `--model` selection, `--effort` levels, and `/compact` usage, including interaction between budget, turn limits, and context compaction to prevent runaway loops (ref: Q10).

- **AC11 (actionable examples):** The skill includes concrete examples for common orchestration patterns: commit automation (e.g., CI pipeline commits via headless mode), code review (piped diff input with structured output), and piped analysis (stdin piping like `cat file | claude -p "analyze"`).

## Delta

### New files

| Path | Purpose |
|------|---------|
| `.claude/skills/using-claude-cli/SKILL.md` | Main skill body with frontmatter; documents all CLI modes, sub-agent patterns, session management, MCP integration, hooks summary, permissions model, and cost control. ~200-300 lines. |
| `.claude/skills/using-claude-cli/references/advanced-cli-flags.md` | Exhaustive flags for all five CLI modes (interactive, headless, bare, piped, background), output formats, streaming, model selection. |
| `.claude/skills/using-claude-cli/references/hook-examples.md` | Hook configuration examples: matcher syntax, exit code semantics, pre/post tool use patterns, prompt-based vs agent-based hooks. |
| `.claude/skills/using-claude-cli/references/agent-team-orchestration.md` | Agent teams (experimental), git worktrees for parallel branches, background agents, teammate communication patterns. |
| `.claude/skills/using-claude-cli/references/permission-rule-patterns.md` | Permission rule syntax (Tool vs Tool(specifier) with globs), evaluation order (deny->ask->allow), read-only command lists, CI/CD safety patterns. |

### Modified files

None. This skill is a new addition; it does not modify any existing `.claude/skills/` or `.claude/agents/` files.

### New entries in `.claude/CLAUDE.md`

The project-level CLAUDE.md should be updated to list `using-claude-cli` under the "Available skills" section, alongside the other 10 QRSPI skills.

## Pattern Decisions

### Decision 1: Skill file location and frontmatter format

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Match existing skill pattern (`.claude/skills/<name>/SKILL.md` with `name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Consistent with all 10 existing skills; no new parser needed; agents can consume it without changes | Does not match the "agentskills.io standard" described in the ticket's implied model |
| B | Create a new frontmatter format matching the agentskills.io fields (`model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`) | Aligns with the ticket's stated goal of following an external standard | No existing codebase pattern supports this; would require changes to Claude Code CLI and all agent/skill consumers; undefined field semantics (how does `model` in frontmatter differ from `--model` CLI flag?) |

**Recommendation:** Option A
**Rationale:** All 10 existing skills use the same five-field frontmatter. The "agentskills.io standard" referenced in the ticket is an external specification — no codebase evidence supports fields like `model`, `permissionMode`, `mcpServers`, or `hooks` as YAML frontmatter keys on SKILL.md (ref: Q2, Inconsistency #1, #6). Introducing new frontmatter fields would break all existing skill consumers. The skill body (prose after frontmatter) is the right place to document these concepts without requiring parser changes.
**NEW PATTERN?** No — we are following the established `.claude/skills/<name>/SKILL.md` pattern exactly.

### Decision 2: Scope of the SKILL.md main body vs references/

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep SKILL.md to ~200 lines covering only the most common patterns (headless mode, subagents, sessions, permissions); put all advanced orchestration (agent teams, hooks, worktrees, cost control) in references/ | SKILL.md stays within 500-line/token limit; focused entry point for agents; follows ticket's scope guidance ("focus on most common patterns... put advanced orchestration in references/") | Agents must read multiple files to get complete picture; more files to maintain |
| B | Put everything in SKILL.md body | Single file to find; no cross-referencing needed | Will exceed 500-line limit given the breadth of topics (CLI modes, output formats, subagents, sessions, MCP, hooks, permissions, cost control, orchestration examples) |

**Recommendation:** Option A
**Rationale:** The ticket explicitly states "Focus the main SKILL.md on the most common patterns... and put advanced orchestration in `references/`" (Acceptance Criteria description). With 6+ CLI modes, output formats, sub-agent types, session management, MCP integration, hooks, permissions, cost control, and examples, Option B would easily exceed 500 lines. The one existing `references/` directory (`.claude/skills/qrspi-work/references/`) follows the same split: core logic in SKILL.md, cross-reference docs in references/ (ref: Q3).
**NEW PATTERN?** No — mirrors the pattern of `.claude/skills/qrspi-work/references/`.

### Decision 3: Handling externally-defined concepts (CLI modes, hooks, permissions)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Author the skill as reference documentation synthesized from Claude Code's CLI specification, since no source code in this repo encodes these patterns | Honest about external dependency; skill is still actionable for agents calling the CLI | No codebase-grounded evidence; potential for inaccurate documentation of CLI behavior |
| B | Only document patterns verified to exist in this codebase (e.g., `--dangerously-skip-permissions`, per-phase tool lockdowns via YAML) and explicitly note gaps for other concepts | Fully honest with research findings | Skill would be extremely thin (~50 lines) and miss most acceptance criteria; does not fulfill the ticket's intent |

**Recommendation:** Option A with explicit provenance
**Rationale:** The ticket asks to "guide agents when using the Claude Code CLI" — this is inherently about external behavior. The skill should document CLI patterns faithfully while marking where concepts are from the CLI spec vs verified in-project (e.g., "`--bare` mode skips `.claude/` discovery — confirmed by observation that bare mode would not find skills defined in `.claude/skills/`" per Q8 edge case). This balances honesty about provenance with actionability.
**NEW PATTERN?** Yes — this is the first skill whose content is primarily reference documentation for an external system rather than internal workflow logic. The `using-claude-cli` skill documents the CLI itself, not the QRSPI project.

### Decision 4: Skill entry in project CLAUDE.md

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add `using-claude-cli` to the "Available skills" list in `.claude/CLAUDE.md` alongside existing QRSPI skills | Agents can discover the skill via CLAUDE.md scanning; consistent with how 10 other skills are registered | Slight drift from listing only QRSPI-phase skills (this is a utility/infra skill) |
| B | Do not add to CLAUDE.md; rely on agent self-discovery of `.claude/skills/` directory | Keeps CLAUDE.md as QRSPI-only; avoids scope confusion | Agent may not discover the skill without explicit listing |

**Recommendation:** Option A with a note distinguishing it from QRSPI-phase skills
**Rationale:** The CLAUDE.md "Available skills" section is the canonical discovery point. Adding the new skill ensures visibility, but it should be noted as a utility skill (not a QRSPI phase wrapper) to maintain clarity about its purpose.

### Decision 5: Testing strategy for the skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Leverage the existing eval harness skeleton — add test cases to `evals/suite.json` that verify SKILL.md frontmatter and body structure (valid YAML, field counts, line limits) without executing agents | Aligns with project's stated test infrastructure; low implementation cost | Eval runner is a stub; tests would not actually execute; only validates structure, not CLI behavior |
| B | Test via manual end-to-end: create the skill file, invoke it from an agent team, verify output matches expected patterns | Tests actual end-to-end behavior as intended | The eval harness stub cannot support this; no test fixtures for CLI flag behavior exist (ref: Q11) |

**Recommendation:** Option A
**Rationale:** The eval harness is confirmed non-functional (all 3 critical paths are stubs returning empty values, ref: Q11). Attempting full end-to-end testing (Option B) is not viable. Structure tests (frontmatter validation, line count, reference file existence) are the only testable assertions with the current infrastructure. The ticket's acceptance criteria about "valid SKILL.md frontmatter" and "under 500 lines" are directly testable via this approach.
**NEW PATTERN?** Partially — structure tests (YAML parsing of frontmatter, line counting) are new; they apply to a skill file rather than code logic.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The `skill-creator` tool referenced by the ticket does not exist in this repo | high | medium | Document that the skill must be created manually following the observed `.claude/skills/<name>/SKILL.md` pattern; propose implementing `skill-creator` as a follow-up ticket |
| Agentskills.io standard fields (`model`, `permissionMode`, etc.) do not match any existing frontmatter — agents may ignore the new fields or fail parsing | medium | high | Use only the five observed fields in frontmatter; document external-standard concepts in the prose body, not YAML; flag this as a deviation from the ticket's stated goal and request human judgment on whether to extend frontmatter format |
| CLAUDE.md is scanned by all agent orchestration — adding a non-QRSPI skill may confuse discovery logic that expects only `/qrspi-*` commands | low | medium | Add a clear section marker or comment in CLAUDE.md distinguishing "Utility Skills" from "QRSPI Phase Agents"; use naming convention `using-<tool>` to signal it is not a phase |
| SKILL.md body exceeds 500 lines / 5000 tokens given the breadth of topics (6 CLI modes + output formats + subagents + sessions + MCP + hooks + permissions + cost control + examples) | medium | low | Enforce line count during authoring; strict cutoff in main body, push details to references/; use the pattern from `qrspi-work/references/` as a size anchor |
| Hook system and permission mode documentation is synthesized rather than codebase-verified — may contain inaccuracies about actual CLI behavior | high | medium | Mark all externally-derived concepts with explicit provenance notes (e.g., "from CLI spec, not verified in-project"); recommend manual verification before wide adoption; note the `--dangerously-skip-permissions` observation as the only permission-mode evidence in-project |
| The `using-claude-cli` skill duplicates information already present in project docs (e.g., session management guidance in `docs/qrspi_claude_code_guide.md`) | medium | low | Cross-reference existing docs rather than reproducing content; position this skill as the canonical CLI reference for agent use, not a duplicate of QRSPI workflow documentation |

## Open Questions

- OQ1: Should the `skill-creator` tool be implemented before or after `using-claude-cli`? The ticket says "Use the Anthropic skill builder skill" but it does not exist. Is creating `skill-creator` a prerequisite, or should this skill be authored manually as a one-off?
- OQ2: Does the agentskills.io specification exist outside this codebase? If so, what are its exact frontmatter requirements? The five-field format (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) observed in 10 existing skills contradicts the ticket's implied field list (`model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`). Human judgment is needed on which spec to follow.
- OQ3: Should `using-claude-cli` be listed under a separate "Utility Skills" section in `.claude/CLAUDE.md` rather than the "Available skills" (QRSPI phases) section, to avoid confusing skill discovery logic that may expect only `/qrspi-*` commands?
- OQ4: The ticket requests documentation for hook events (`PreToolUse`, `PostToolUse`, etc.) and permission modes (`acceptEdits`, `plan`, `auto`, etc.) that are entirely external to this codebase. Should these be documented from CLI spec with a "not verified in-project" disclaimer, or omitted until they can be verified?
- OQ5: For the eval harness structure tests — what assertions should validate SKILL.md frontmatter? Options include: YAML parsability (5 fields present), line count <= 500, body non-empty, reference files exist. Is there a preferred assertion framework to use given the stub eval infrastructure?
