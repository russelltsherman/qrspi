# PR Summary — RUS-9: Create the `using-claude-cli` skill

**Branch:** RUS-9
**Files changed:** 13 files, +1528 insertions, 0 deletions

## Summary

This PR creates a new agent skill `using-claude-cli` that documents Claude CLI invocation patterns across all modes, sub-agent orchestration, session management, output formats, and cost controls. The skill follows the project's established five-field frontmatter convention and uses a flat `references/` directory pattern (matching `qrspi-work`) to keep the main SKILL.md body at 188 lines -- well under the 500-line budget. Four reference files provide deep content on advanced flags, hooks, agent teams, and permissions. A companion eval file with 5 test cases exercises all core topic areas.

**Reviewer focus areas:**
1. Accuracy of CLI flags, modes, and behavior descriptions against a live Claude Code instance (the design notes this is unverified within the codebase).
2. `Bash(claude:*)` pattern in `allowed-tools` -- a new pattern not used by any existing skill, not yet validated at runtime.
3. The flat `references/` structure with 4 files -- no existing skill has more than one reference file.

## Acceptance Criteria Mapping

| # | Acceptance Criterion (from design.md) | Implementation File | Test / Verification |
|---|---------------------------------------|---------------------|---------------------|
| 1 | Follows the established five-field frontmatter convention | `.claude/skills/using-claude-cli/SKILL.md` (lines 1-10) | impl-log.md: 5 frontmatter fields confirmed |
| 2 | Documents all three CLI modes (interactive, headless, bare) with correct flag usage | `.claude/skills/using-claude-cli/SKILL.md` (CLI Modes section) | Eval case 1 (flag_check on --headless, --bare) |
| 3 | Documents sub-agent spawning patterns (built-in: Explore, Plan, General-purpose + custom) | `.claude/skills/using-claude-cli/SKILL.md` (Sub-Agent Spawning section) | Eval case 2 (command_check on @Explore, @Plan, @agent) |
| 4 | Covers session management (continue, resume, name, fork, no-persistence) | `.claude/skills/using-claude-cli/SKILL.md` (Session Management section) | Eval case 3 (flag_check on --continue, --session, --fork, --no-persist) |
| 5 | Documents MCP server configuration (`.mcp.json`, `--mcp-config`, `--mcp-server`) | `.claude/skills/using-claude-cli/references/advanced-flags.md` (MCP & Plugin Flags table) | Eval case 1 (content_check on CI/automation context) |
| 6 | Encodes the permission model (permission modes, `--allowedTools`, `--disallowedTools`, settings hierarchy) | `.claude/skills/using-claude-cli/references/permission-patterns.md` (all sections) | Eval case 2 (safety_check on sub-agent permission requirements) |
| 7 | Documents output formats (text, json, stream-json) with `jq` guidance | `.claude/skills/using-claude-cli/SKILL.md` (Output Formats section) | Eval case 4 (workflow_check on jq extraction example) |
| 8 | Includes cost control flags (`--max-budget-usd`, `--max-turns`, `--model`, `--effort`) | `.claude/skills/using-claude-cli/SKILL.md` (Cost Control section) | Eval case 5 (flag_check on --max-budget-usd, --max-turns, --model) |
| 9 | Provides actionable examples for common orchestration patterns (commit automation, code review, piped analysis) | `.claude/skills/using-claude-cli/references/permission-patterns.md` (Common Patterns section) | Eval case 1 (workflow_check on CI pipeline example) |
| 10 | Main SKILL.md body stays under 500 lines / 5000 tokens | `.claude/skills/using-claude-cli/SKILL.md` | impl-log.md: 188 body lines confirmed |
| 11 | Reference material in `references/` covering advanced CLI flags, hooks, agent teams, permissions | `references/advanced-flags.md`, `hooks-config.md`, `agent-teams.md`, `permission-patterns.md` | impl-log.md: all 4 files exist and are referenced via Read instructions |
| 12 | Agent Teams marked with explicit experimental status warning | `references/agent-teams.md` (line 1) | Contract 5 verification in impl-log.md |

## Changes by Slice

### Slice 1: Core skill files (SKILL.md + 4 references + CLAUDE.md update)

| File | Change Type | Lines |
|------|-------------|-------|
| `.claude/skills/using-claude-cli/SKILL.md` | NEW | 188 |
| `.claude/skills/using-claude-cli/references/advanced-flags.md` | NEW | 109 |
| `.claude/skills/using-claude-cli/references/hooks-config.md` | NEW | 157 |
| `.claude/skills/using-claude-cli/references/agent-teams.md` | NEW | 148 |
| `.claude/skills/using-claude-cli/references/permission-patterns.md` | NEW | 227 |
| `.claude/CLAUDE.md` | MODIFY | +1 |

### Slice 2: Eval cases

| File | Change Type | Lines |
|------|-------------|-------|
| `evals/claude-cli-evals.json` | NEW | 73 |

### QRSPI artifacts (not user-facing code changes)

| File | Change Type | Lines |
|------|-------------|-------|
| `.qrspi/RUS-9/design.md` | NEW | 136 |
| `.qrspi/RUS-9/impl-log.md` | NEW | 31 |
| `.qrspi/RUS-9/plan.md` | NEW | 216 |
| `.qrspi/RUS-9/questions.md` | NEW | 58 |
| `.qrspi/RUS-9/structure.md` | NEW | 147 |
| `.qrspi/RUS-9/worktree.md` | NEW | 37 |

## Testing Summary

| Verification | Command | Result |
|--------------|---------|--------|
| SKILL.md body line count | `awk '/^---$/,0' SKILL.md \| wc -l` | 188 lines (< 500 budget) |
| Frontmatter fields | `grep -cE '^(name\|description\|command\|argument-hint\|allowed-tools):' SKILL.md` | 5 fields (all required present) |
| Reference file existence | `ls .claude/skills/using-claude-cli/references/` | 4 files: advanced-flags.md, agent-teams.md, hooks-config.md, permission-patterns.md |
| Read instruction coverage | `grep 'Read.*references/' SKILL.md` | 4 Read instructions matching all 4 reference files |
| CLAUDE.md registration | `grep 'using-claude-cli' .claude/CLAUDE.md` | Skill added to available skills list |
| Eval JSON validity | `python3 -c "import json; d=json.load(open('evals/claude-cli-evals.json')); print(f'Valid JSON, {len(d[\"evals\"])} evals')" ` | Valid JSON, 5 evals |
| Eval assertion types | `set(a['type'] for c in cases for a in c['assertions'])` | {command_check, content_check, flag_check, safety_check, workflow_check} -- all 5 types covered |

## Deviations from Structure

| Contract | Status | Notes |
|----------|--------|-------|
| Contract 1: SKILL.md -> Reference files | MET | All 4 reference files exist and are referenced via Read instructions; all files in `references/` are mentioned in SKILL.md |
| Contract 2: Main body line budget | MET | 188 body lines, target was ~200 |
| Contract 3: Eval coverage | MET | 5 eval cases, one per core topic (CLI modes, sub-agents, sessions, output formats, cost control) |
| Contract 4: skill-creator validation | MET | skill-creator used for scaffolding per PD-3, then hand-edited to match project style |
| Contract 5: Experimental feature marking | MET | `references/agent-teams.md` line 1 contains explicit experimental warning with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` |

## Risks & Rollback

| Risk (from design.md risk register) | Likelihood | Impact | Status | Mitigation |
|-------------------------------------|------------|--------|--------|------------|
| agentskills.io standard does not exist | High | Medium | Confirmed: zero evidence in codebase. Implementation defaults to the established 5-field pattern. | Accepted -- the skill uses the project's actual conventions, not an invented standard. |
| SKILL.md body exceeds 500 lines | Medium | Medium | Mitigated -- actual body is 188 lines. | Acceptable. Deep content is in reference files. |
| skill-creator produces incompatible output | Medium | Low | Mitigated -- skill-creator was used for scaffolding and output was hand-edited to match conventions. | Acceptable. PD-3 recommendation followed. |
| Documentation contradicts actual Claude CLI behavior | Low | High | **Unresolved** -- CLI flags are unverified against a live Claude Code instance. | Flag as a known limitation. Recommend runtime validation before this skill is relied upon in production. |
| Too much content creates context pressure | Medium | Low | Mitigated -- main body is 188 lines; references are lazy-loaded on demand. | Acceptable. Initial context load is low. |

### Rollback

This change is entirely additive (6 new files) plus one append-only update to `.claude/CLAUDE.md`. Rollback is a simple `git revert` of this PR -- no existing functionality is affected, no config schemas are changed, and no destructive operations were performed.

## Open Items

- **Runtime validation of CLI flags** -- The design (OQ4) and risk register both flag that CLI flag documentation has not been verified against a live Claude Code instance. The flags documented in this skill may need adjustment once validated.
- **`Bash(claude:*)` pattern** -- Unverified assumption from structure.md: if the Claude Code permission system does not support the glob pattern in `allowed-tools`, the skill's allowed-tools list will need to be revised.
- **Multiple reference files precedent** -- No existing skill has more than one reference file. The impact of 4 reference files on the runtime's lazy-loading behavior is untested.
- **Slash command `/using-claude-cli`** -- The `command` field is set to `using-claude-cli` per PD-3. If the runtime registers this as a slash command, it may appear in help without being functional.
