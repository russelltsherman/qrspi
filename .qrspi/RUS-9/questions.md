# Questions — Create a new agent skill called using claude cli

**Ticket:** RUS-9
**Generated:** 2026-06-02T14:30:00Z
**Status:** draft

## Data Flow

- Q1: Where in `.claude/agents/` should the "using claude cli" skill's `SKILL.md` be placed, and what frontmatter fields are required by the agentskills.io standard?
   **Target:** The `.claude/agents/` directory structure and any existing SKILL.md files for reference

- Q2: How does the existing `skill-creator` skill (`.claude/skills/`) generate or scaffold SKILL.md files, and what template or reference does it use?
   **Target:** `.claude/skills/skill-creator/` directory and any agent skill builder code paths

- Q3: What references files (`references/`, `scripts/`, `assets/`) need to be created under the skill directory, and what content belongs in each relative to the CLI modes documented in the ticket?
   **Target:** `.claude/agents/<skill-name>/` directory and any existing reference directories for pattern

## API Surface

- Q4: How are sub-agent definitions encoded as Markdown files with YAML frontmatter in `.claude/agents/`, and what YAML fields (`model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`) map to the CLI flags described in the ticket?
   **Target:** `.claude/agents/` directory structure and any agent definition parser or validator

- Q5: Where is the settings hierarchy (Managed > CLI args > Local project > Shared project > User settings) for MCP configuration (`~/.claude.json`, `.mcp.json`, `~/.claude/settings.json`) encoded in the codebase?
   **Target:** Any settings, config, or CLAUDE.md loading code and the `update-config` skill

## State Management

- Q6: How does the session management system (`-c`, `-r`, `-n`, `--continue`, `--resume`, `--fork-session`) track session IDs, and where is the session persistence logic implemented that `--no-session-persistence` would disable?
   **Target:** The CLI session management code and any SDK or runtime directory handling session state

- Q7: How are hook events (`PreToolUse`, `PostToolUse`, `SubagentStop`, etc.) registered and dispatched in the settings system, and where do matcher patterns (e.g., `"Edit|Write"`) get evaluated?
   **Target:** `.claude/settings.json` loading code and any hooks or event dispatching module

## Edge Cases

- Q8: What edge cases arise when encoding bare mode (`--bare -p`) CLI flags in the skill, given that bare mode skips auto-discovery of hooks, skills, plugins, MCP servers, and CLAUDE.md?
   **Target:** The codebase for CLI flag parsing, hook auto-discovery, and skill/plugin loading logic

- Q9: How does the permissions model (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`) handle the rule evaluation order (deny -> ask -> allow), and where is `--allowedTools` / `--disallowedTools` parsing implemented?
   **Target:** The permissions or sandboxing code and any tool authorization logic

- Q10: What happens when subagents exceed session context limits, and how does `--max-budget-usd`, `--max-turns 3`, and `/compact` interact to prevent runaway loops in headless mode?
   **Target:** Any budget, turns-limiting, or context compaction code path

## Testing

- Q11: How can the generated skill be tested against existing agent teams and sub-agent patterns in the QRPI workflow (`.claude/agents/`, `qrspi-batch.js`), and what test fixtures or mock agents exist for validating CLI flag behavior?
   **Target:** The `evals/` directory, `scripts/run_eval.py`, and any test infrastructure for agent skills

## Observability

- Q12: Where is the cost and resource metadata (`session_id`, cost fields in JSON output) emitted from the CLI, and how would logging or observability hooks surface that data for debugging orchestration flows?
   **Target:** The JSON output serialization code and any observable event emission paths
