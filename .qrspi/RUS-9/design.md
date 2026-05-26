# Design — Create a new agent skill called using-claude-cli

**Ticket:** RUS-9
**Status:** draft
**Generated:** 2026-05-26

---

## 1. Current State

The project has 10 skills under `.claude/skills/`, all following an identical pattern: YAML frontmatter with five fields (name, description, command, argument-hint, allowed-tools), followed by a markdown body (ref: Q1).

No existing skill in the project documents Claude CLI flags, modes, or invocation patterns. All 10 skills operate within a running Claude Code session rather than documenting how to invoke Claude Code itself (ref: Q4).

Only one skill (`qrspi-work`) uses a `references/` subdirectory, containing a single markdown file that is lazy-loaded at runtime when the agent encounters an instruction to read it (ref: Q5, ref: Q8).

There is no `agentskills.io` standard, specification, or schema validator in the codebase. The term appears nowhere except in `questions.md` (ref: Q1).

The `skill-creator` skill exists as a system-level capability (listed in the runtime's available skills) but has no project-local SKILL.md file (ref: Q2). The project's memory directives require invoking `skill-creator` when creating new skills (ref: Q2).

Skill discovery is filesystem-based: any directory under `.claude/skills/` containing a `SKILL.md` is automatically available. No registry or manifest tracks skills (ref: Q7).

There is no token counting, line counting, or size enforcement for skill files (ref: Q9). The largest skill (`qrspi-work`) is exactly 500 lines, which may be a de facto ceiling (ref: Q9).

No skill in the project documents experimental features, mode-dependent flags, or mutually exclusive CLI flag combinations (ref: Q10, ref: Q11).

---

## 2. Desired End State

An installed skill under `.claude/skills/using-claude-cli/` that:

- Follows the established five-field frontmatter convention (name, description, command, argument-hint, allowed-tools) (ref: Q6).
- Documents all three CLI modes (interactive, headless/print, bare) with correct flag usage (ticket AC).
- Documents sub-agent spawning patterns, including built-in types (Explore, Plan, General-purpose) and custom definitions via Markdown frontmatter (ticket AC).
- Covers session management patterns for multi-turn orchestration: continue, resume, name, fork, no-persistence (ticket AC).
- Documents MCP server configuration (`.mcp.json`, `claude mcp add`, `--mcp-config`, `--strict-mcp-config`) and permission rules (ticket AC).
- Encodes the permission model (permission modes, `--allowedTools`, `--disallowedTools`, settings hierarchy) for CI/CD and scripted usage (ticket AC).
- Documents output formats (text, json, stream-json) with guidance on using `jq` for JSON extraction (ticket AC).
- Includes cost control flags (`--max-budget-usd`, `--max-turns`, `--model`, `--effort`) and resource management guidance (ticket AC).
- Provides actionable examples for common orchestration patterns: commit automation, code review, piped analysis (ticket AC).
- Main SKILL.md body stays under 500 lines / 5000 tokens (ticket AC).
- Reference material in `references/` covering: advanced CLI flags, hook configuration examples, agent team orchestration, permission rule patterns (ticket AC).
- Agent Teams marked with explicit experimental status warning (ticket AC, ref: Q10).

---

## 3. Delta

### New files
- `.claude/skills/using-claude-cli/SKILL.md` — main skill, ~200 lines, covers the five core topics
- `.claude/skills/using-claude-cli/references/advanced-flags.md` — advanced CLI flags not covered in the main body
- `.claude/skills/using-claude-cli/references/hooks-config.md` — hook event types, configuration, exit codes, use cases
- `.claude/skills/using-claude-cli/references/agent-teams.md` — multi-agent orchestration, worktrees, background agents (experimental)
- `.claude/skills/using-claude-cli/references/permission-patterns.md` — permission rule syntax, settings hierarchy, CI/CD examples

### Modified files
- `.claude/CLAUDE.md` — add the new skill to the available skills list for human reference (documentation convention, ref: Q7)

### No changes to
- `evals/suite.json` — no eval coverage for this skill (not required by ticket)
- `scripts/` — no new validation or runner code
- Existing 10 skills — no modifications to avoid scope creep

---

## 4. Pattern Decisions

### PD-1: Frontmatter convention

| Option | Approach | Pros | Cons |
|---|---|---|---|
| A | Use the standard 5 fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q6) | Matches all 10 existing skills; zero deviation risk | `command` implies a slash command; this skill is auto-triggered, not invoked by `/using-claude-cli` |
| B | Omit `command` field; use a descriptive `description` for auto-triggering | More honest representation of auto-trigger behavior | Deviates from the uniform frontmatter schema; may confuse the runtime |
| C | Use `command: /claude-cli` as a manual invocation fallback, set `argument-hint: none` | Keeps standard schema; provides explicit invocation path | Creates a command users are unlikely to use; wastes a field |

**Recommendation: A.** The slash command field is harmless as metadata even if the skill primarily auto-triggers via description matching. The runtime discovers both paths. Use a description with explicit trigger phrases like "Use when the user asks about Claude CLI flags, modes, subagents, or session management" (consistent with existing skills, ref: Q6).

### PD-2: References directory structure

| Option | Approach | Pros | Cons |
|---|---|---|---|
| A | Follow `qrspi-work` precedent: flat `references/*.md` files (ref: Q5, ref: Q8) | Matches existing convention; simplest structure | All reference files at one level; no grouping |
| B | Subdivide by topic: `references/cli/`, `references/agents/`, etc. | Logical grouping for 4+ reference files | No existing precedent; adds nesting complexity |

**Recommendation: A.** Flat `references/` directory with descriptive filenames (ref: Q5). The only precedent is `qrspi-work/references/review-cascade.md`. Four flat files keeps things simple and matches the loading pattern (the SKILL.md body contains explicit "Read references/..." instructions, ref: Q8).

### PD-3: skill-creator invocation

| Option | Approach | Pros | Cons |
|---|---|---|---|
| A | Invoke `skill-creator` skill and let it generate the SKILL.md | Follows user memory directive; may produce better structured output | skill-creator is system-level; implementation unknown; output quality uncertain |
| B | Write SKILL.md manually following established patterns | Full control; deterministic; consistent with project conventions | Violates the "never write SKILL.md ad-hoc" directive (ref: Q2) |
| C | Use skill-creator for scaffolding, then hand-edit to match project style | Best of both worlds | Adds complexity; may conflict if skill-creator disagrees with project conventions |

**Recommendation: C.** Use skill-creator to generate the initial scaffold and frontmatter, then hand-edit the body to match the established five-field pattern, the flat references convention, and the tone/structure of existing skills. This satisfies the directive while ensuring consistency with the project's actual conventions (ref: Q2, ref: Q6).

### PD-4: Experimental feature marking

| Option | Approach | Pros | Cons |
|---|---|---|---|
| A | Markdown disclaimer: "**Experimental:** Agent Teams require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`" at section start | Clear, actionable, no new conventions | No existing precedent (ref: Q10) |
| B | Add an `experimental: true` frontmatter field | Machine-readable | New frontmatter field; no runtime support |
| C | Use an emoji flag (e.g., `:warning:`) at the top of the reference file | Visually prominent | Emoji convention not established in project |

**Recommendation: A.** Plain text disclaimer at the section level. The experimental flag is a runtime requirement (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), not a skill-level concern. Adding new frontmatter fields or conventions (Options B and C) has no precedent and risks confusing the skill system (ref: Q10).

### PD-5: New patterns

The CLI flag documentation with mode-dependent behavior (bare mode excluding other features) is a **NEW PATTERN** — no existing skill documents mutually exclusive CLI modes (ref: Q11). The recommendation is to use a table format with mode columns, similar to the state dispatch table in `qrspi-work` (ref: Q11 evidence).

The hook configuration examples in references are a **NEW PATTERN** — no existing skill documents hooks (ref: Q4). The structure will mirror the existing reference file pattern (flat markdown, lazy-loaded).

---

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| agentskills.io standard does not exist and the ticket's requirement is based on a misidentification | High | Medium — the SKILL.md format would follow an invented standard | Research Q1 confirms the term appears nowhere in the codebase. Design defaults to the established 5-field pattern. Confirm with reviewer before implementation. |
| SKILL.md body exceeds 500 lines despite splitting into references | Medium | Medium — no technical enforcement exists; could degrade agent performance | The 500-line limit is a soft convention (ref: Q9). Monitor line count during writing. The main body targets ~200 lines by keeping deep content in four reference files. |
| skill-creator produces output incompatible with the five-field frontmatter convention | Medium | Low — requires hand-editing anyway | PD-3 recommendation to hand-edit after scaffolding. The skill-creator is system-level with unknown implementation (ref: Q2). |
| Documentation contradicts actual Claude CLI behavior | Low | High — agents following incorrect flags will fail | The ticket's conventions come from a specification that should be validated against a live Claude Code instance. Include a note about verifying flags before committing. |
| Too much content creates context pressure for the agent | Medium | Low — references are lazy-loaded, not pre-loaded | The runtime only loads SKILL.md at trigger time; references are read on demand (ref: Q8). Keeping main body under 200 lines keeps initial context low. |

---

## 6. Open Questions

- **OQ1:** What is the actual agentskills.io standard if it exists outside this codebase? Research found zero evidence of it in the project (ref: Q1). Is this a real external standard, or was the requirement based on a misidentification? The implementation should not invent a standard.

- **OQ2:** Should the `command` field use a slash command (`/claude-cli`) or be omitted for an auto-trigger skill? The established convention requires all five fields (ref: Q6), but omitting the command field may be more semantically correct.

- **OQ3:** What is the expected scope of the `description` field for triggering accuracy? The description field drives skill matching (ref: Q6). How specific should trigger phrases be to avoid false positives on unrelated CLI questions?

- **OQ4:** Should CLI flag documentation be validated against a live Claude Code instance before the skill is marked complete? The ticket's conventions are authoritative but unverified within this codebase.
