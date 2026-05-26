---
name: using-claude-cli
description: |
  Use when the user asks about Claude CLI flags, modes, invocation patterns,
  sub-agent spawning, session management, or script-level orchestration.
  Trigger on: 'run claude', 'spawn a subagent', 'claude headless',
  'claude bare mode', 'claude session', 'claude MCP config',
  'claude permission rules', 'claude cost control',
  'claude --max-budget', 'claude --model', 'claude run',
  'claude doctor', 'claude config', 'claude permission',
  'claude headless mode', 'claude bare mode', 'claude session continue',
command: using-claude-cli
argument-hint: <topic>
allowed-tools: Read, Glob, Grep, Bash(claude:*), Bash(cat:*), Bash(jq:*)
---

# using-claude-cli

The Claude CLI is the primary command-line interface for Claude Code.
This skill documents invocation patterns across all CLI modes, sub-agent
orchestration, session management, output formats, and cost controls.

## CLI Modes

The CLI runs in three modes, selected by flags or by environment.

| Mode | Flag | Typical Use |
|------|------|-------------|
| Interactive | (default) | TTY session with human in the loop |
| Headless | `--headless` | Automated scripts, CI pipelines |
| Bare | `--bare` | Machine-readable output, integration |

### Interactive mode (default)

Run without flags for an interactive session:

```
claude
```

The CLI presents a prompt, accepts input, and returns formatted responses.
All tool permissions are enforced interactively with user confirmation.

### Headless mode (`--headless`)

Use for non-interactive automation:

```
claude --headless -p "summarize the changes in this PR"
```

Key behaviors:
- Single-turn execution: processes the prompt and exits.
- No interactive permission prompts — permissions follow settings rules.
- Exit codes: `0` success, non-zero on error.
- Cannot spawn sub-agents or start sessions.

### Bare mode (`--bare`)

Use for machine-readable integration:

```
claude --bare -p "what files are in src/"
```

Key behaviors:
- Minimal formatting — output is plain text without markdown decorations.
- Exit codes are preserved and returned to the caller.
- Some interactive-only features (sub-agent spawning, session management)
  are unavailable.

For a complete flag table with mode-specific behavior, see `references/advanced-flags.md`.

## Sub-Agent Spawning

The CLI can delegate work to sub-agents for focused analysis.

### Built-in types

Three built-in sub-agent types are available in interactive sessions:

| Type | Purpose | Invocation |
|------|---------|------------|
| Explore | Codebase exploration and mapping | `@Explore` in prompt |
| Plan | Task planning and breakdown | `@Plan` in prompt |
| General-purpose | General task delegation | `@agent` in prompt |

Built-in agents run as child processes within the CLI and share the
parent's context and permissions.

### Custom sub-agents

Custom agent types can be defined via SKILL.md frontmatter with a
`delegate` field. This allows domain-specific agents tailored to
your project's needs.

For multi-agent orchestration patterns and worktree-based parallel
work, see `references/agent-teams.md`.

## Session Management

The CLI manages conversational state across turns.

| Action | Flag / Command | Description |
|--------|----------------|-------------|
| Continue a session | `--continue` | Resume the most recent session |
| Resume by name | `--session <name>` | Resume a named session |
| Name a session | `--session-name <name>` | Assign a name to the current session |
| Fork a session | `--fork` | Duplicate the current session state |
| Disable persistence | `--no-persist` | Do not save session state |

Session data is stored locally and survives CLI restarts. Use
`--no-persist` for ephemeral tasks that should not consume storage
or pollute session history.

For session-related permission rules, see `references/permission-patterns.md`.

## Output Formats

The CLI supports multiple output serialization modes.

| Format | Flag | Output Style |
|--------|------|--------------|
| Text (default) | (none) | Human-readable markdown |
| JSON | `--output json` | Structured JSON per turn |
| Stream JSON | `--output stream-json` | One JSON object per line |

### JSON extraction with `jq`

When using `--output json` or `--output stream-json`, pipe output
through `jq` for structured extraction:

```
claude --output stream-json -p "list functions in src/" \
  | jq '.[] | select(.type == "assistant") | .content[0].text'
```

This is especially useful in CI pipelines and automated reports.

For the full flag reference including output-related flags, see
`references/advanced-flags.md`.

## Cost Control

Control spend and token usage with built-in CLI flags.

| Flag | Purpose | Example |
|------|---------|---------|
| `--max-budget-usd <amount>` | Hard cap on total spend | `--max-budget-usd 5.00` |
| `--max-turns <n>` | Maximum conversation turns | `--max-turns 20` |
| `--model <model>` | Select model variant | `--model sonnet` |
| `--effort <level>` | Set thinking effort level | `--effort high` |

### Budget enforcement

`--max-budget-usd` acts as a hard stop. The CLI will terminate the
session when the cumulative cost reaches the threshold, returning the
partial result accumulated so far.

### Model selection

Use `--model` to target specific model families or variants:

```
claude --model haiku -p "quick question"
```

Lower-cost models (e.g., haiku) are appropriate for simple queries;
higher-effort models for complex reasoning tasks.

For hook-based cost monitoring and permission configuration, see
`references/hooks-config.md` and `references/permission-patterns.md`.

## Quick Reference

For the most common operations:

- Run interactively: `claude`
- Single prompt, exit: `claude -p "your question"`
- Continue last session: `claude --continue`
- Machine-readable output: `claude --bare` or `claude --output json`
- Cap spending: `claude --max-budget-usd 10.00`

For deep reference:
  Advanced flag tables, mode-specific behavior, and mutually exclusive combinations, Read `references/advanced-flags.md`
  Hook event types, configuration schema, and exit code meanings, Read `references/hooks-config.md`
  Multi-agent orchestration, worktree patterns, and background agents, Read `references/agent-teams.md`
  Permission rule syntax, settings hierarchy, and CI/CD patterns, Read `references/permission-patterns.md`
