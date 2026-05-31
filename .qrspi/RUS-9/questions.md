# Questions — Create a new agent skill for using the Claude CLI

**Ticket:** RUS-9
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory structure and required files does an existing skill in this repo use (SKILL.md, references/, scripts/, assets/), and where on disk are skills authored so the new skill lands in the correct location?
  **Target:** the existing skill definitions directory (e.g. `.claude/skills/` or wherever skill-creator output is written)
- Q2: How does the skill-creator skill consume its inputs and where does it write generated skill output, so the new CLI skill is produced through the mandated builder rather than authored ad-hoc?
  **Target:** the skill-creator skill (SKILL.md and any scripts/templates it invokes)

## API Surface

- Q3: What YAML frontmatter fields are required and validated for a SKILL.md in this repo (name, description, and any others), and what are the format constraints on each?
  **Target:** the SKILL.md frontmatter schema referenced by skill-creator or an existing skill's frontmatter
- Q4: What is the documented `claude` CLI flag set currently available in this environment (interactive, `-p`, `--bare`, `--bg`, `--output-format`, session flags, permission flags), so the skill encodes flags that actually exist versus aspirational ones?
  **Target:** the module responsible for `claude` CLI flag parsing / `claude --help` output

## State Management

- Q5: How are Claude CLI sessions persisted and resumed (`-c`, `-r`, `-n`, `--fork-session`, `--no-session-persistence`), and where is `session_id` exposed in JSON output for multi-step orchestration capture?
  **Target:** the module responsible for session persistence and JSON output formatting
- Q6: How are custom subagents and their frontmatter (`name`, `description`, `model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`) loaded from `.claude/agents/` versus passed ephemerally via `--agents '{JSON}'`?
  **Target:** the module responsible for subagent discovery and definition loading

## Edge Cases

- Q7: What is the documented behavior when piped stdin exceeds the 10MB cap, and how is that surfaced to the caller?
  **Target:** the module responsible for stdin handling in print/headless mode
- Q8: In bare mode, which auto-discovered resources (hooks, skills, plugins, MCP servers, CLAUDE.md) are skipped, and what must be passed explicitly (e.g. `--mcp-config`) for MCP tools to function?
  **Target:** the module responsible for `--bare` mode resource discovery
- Q9: What is the documented constraint that subagents cannot spawn other subagents, and how does that differ from agent teams where teammates each get their own context window?
  **Target:** the module responsible for subagent vs. agent-team orchestration

## Testing

- Q10: What eval harness exists for skills in this repo (`evals/`, `scripts/`), and what format do skill eval cases take so the new CLI skill can be benchmarked per the skill-creator eval loop?
  **Target:** the eval harness in `evals/` and `scripts/`

## Observability

- Q11: What metadata does `--output-format json` emit beyond `result` and `session_id` (cost, token usage, budget), and how are `--max-budget-usd` and `--max-turns` limits reported when hit?
  **Target:** the module responsible for JSON output metadata and cost/turn accounting

## Permissions

- Q12: What are the documented permission modes (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`), the deny->ask->allow rule evaluation order, and the settings hierarchy (Managed > CLI args > Local > Shared > User)?
  **Target:** the module responsible for permission rule evaluation and settings precedence
- Q13: What is the exact rule syntax for `--allowedTools` / `--disallowedTools` including glob specifiers and the `mcp__<server>__<tool>` pattern used to scope MCP tools in headless runs?
  **Target:** the module responsible for tool permission rule parsing
