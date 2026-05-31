# Questions — Create a new agent skill called using-claude-cli

**Ticket:** RUS-9
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the existing skill-creator skill structure its outputs, and what files does it expect a new skill author to produce (e.g., SKILL.md, references/, scripts/, assets/)?
  **Target:** the skill-creator skill definition under `~/.claude/skills/skill-creator/` or the equivalent global skill directory referenced by this repo

- Q2: What format does this repo use for skill frontmatter (name, description, command, argument-hint, allowed-tools, model), and what fields are required vs. optional?
  **Target:** `.claude/skills/*/SKILL.md` files in the repo (e.g., `qrspi-work/SKILL.md`, `qrspi-batch/SKILL.md`)

- Q3: How are existing skills in this repo distributed between SKILL.md, references/, scripts/, and assets/ — what content lives where?
  **Target:** `.claude/skills/` directory tree, especially skills with `references/` subdirectories

## API Surface

- Q4: What CLI flags does `claude` expose for interactive, headless/print, and bare modes, and which flag combinations are valid together?
  **Target:** the module/file responsible for documenting CLI behavior (e.g., `claude --help` output, any captured CLI reference docs in this repo or referenced externally)

- Q5: How are custom subagents declared in this repo (frontmatter shape, tool restrictions, model field, hooks/skills/mcpServers entries), and what is the canonical example?
  **Target:** `.claude/agents/*.md` and `.qrspi/agents/*.md` files

- Q6: What is the syntax for `--agents '{JSON}'`, `--mcp-config`, `--allowedTools`, `--disallowedTools`, `--append-system-prompt`, `--system-prompt-file`, `--max-budget-usd`, `--max-turns`, `--effort`, `--output-format`, `--json-schema`, `--include-partial-messages`, and `--fork-session` as they will be documented in the new skill?
  **Target:** Claude Code CLI reference (external docs) and any examples already captured in `.claude/skills/*/references/` or `evals/` scripts in this repo

## State Management

- Q7: How does Claude Code track and persist sessions on disk, what does `--no-session-persistence` change, and where does `-r <session-id>` look up resumed sessions?
  **Target:** Claude Code session storage layout (e.g., `~/.claude/projects/.../`) referenced by this repo's user MEMORY directory

- Q8: How are MCP server configurations layered (`.mcp.json`, `~/.claude.json`, `--mcp-config`, `--strict-mcp-config`), and what is the precedence order?
  **Target:** MCP configuration files in the repo (`.mcp.json` if present) and the module responsible for documenting MCP integration

- Q9: How does the settings hierarchy (Managed > CLI args > Local project > Shared project > User settings) actually resolve in this repo, given `.claude/settings.json`, `.claude/settings.local.json`, and `~/.claude/settings.json`?
  **Target:** `.claude/settings.json`, `.claude/settings.local.json`, and references in the `update-config` skill

## Edge Cases

- Q10: What does the new skill need to say about bare mode (`--bare -p`) skipping auto-discovery — specifically, which discovery paths are skipped (hooks, skills, plugins, MCP servers, CLAUDE.md), and what must be re-supplied explicitly?
  **Target:** Claude Code CLI bare mode documentation and any bare-mode examples in this repo's `evals/` or `scripts/`

- Q11: What is the documented behavior when a subagent attempts to spawn another subagent (the ticket states this is forbidden), and how should the skill warn the user about this?
  **Target:** Claude Code subagent documentation; verify by reviewing how this repo's qrspi-work orchestrator spawns agents but never has them nest spawns

- Q12: What stdin size cap applies to piped input (the ticket mentions 10MB), and what error/behavior occurs when exceeded?
  **Target:** Claude Code CLI piped input docs and any examples in `.claude/skills/*/` that pipe data through `claude -p`

- Q13: For permission modes (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`), what are the failure modes if the wrong mode is chosen for CI/CD, and what is the safe default for scripted usage?
  **Target:** the `update-config` skill and existing `.claude/settings.json` permission examples in this repo

## Testing

- Q14: How are existing skills in this repo evaluated (the ticket references an `evals/` directory and a skill-creator eval loop), and what is the expected eval format for a new skill?
  **Target:** `evals/` directory and `scripts/` directory in this repo

- Q15: Does this repo have any existing tests, lints, or validators for SKILL.md files (frontmatter validation, line-count limits, broken references), and if so, how are they invoked?
  **Target:** `scripts/` directory, `.github/workflows/` if present, and any Makefile or `package.json` test entries

## Observability

- Q16: What captured examples (commit automation, code review, piped analysis) already exist in this repo's skills or workflows that the new skill should reference rather than re-invent?
  **Target:** `.claude/skills/code-review/`, `.claude/skills/review/`, `.claude/skills/init/`, `.claude/workflows/`, and any `references/` subdirectories
