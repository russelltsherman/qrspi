# Advanced CLI Flags

Complete flag reference organized by CLI mode. Flags are grouped by
functional category.

## Flag Tables by Mode

### Core Invocation Flags

| Flag | Interactive | Headless | Bare | Description |
|------|:-----------:|:--------:|:----:|-------------|
| `-p <prompt>` | Yes | Yes | Yes | One-shot prompt |
| `--continue` | Yes | No | No | Resume last session |
| `--session <name>` | Yes | Yes | Yes | Target named session |
| `--no-persist` | Yes | Yes | Yes | Disable session saving |
| `--fork` | Yes | No | No | Fork current session |
| `--headless` | No | Yes | No | Enter headless mode |
| `--bare` | No | No | Yes | Enter bare mode |
| `--output <format>` | Yes | Yes | Yes | Output serialization |
| `--model <model>` | Yes | Yes | Yes | Select model |
| `--effort <level>` | Yes | Yes | Yes | Thinking effort level |
| `--max-budget-usd <amt>` | Yes | Yes | Yes | Spend cap |
| `--max-turns <n>` | Yes | Yes | Yes | Turn limit |
| `--verbose` | Yes | Yes | Yes | Extra debug output |
| `--quiet` | Yes | Yes | Yes | Suppress non-essential output |
| `--log <path>` | Yes | Yes | Yes | Write session log to file |

### Permission Flags

| Flag | Interactive | Headless | Bare | Description |
|------|:-----------:|:--------:|:----:|-------------|
| `--permission <mode>` | Yes | No | No | Override permission mode |
| `--auto-approve` | Yes | Yes | Yes | Skip permission prompts |
| `--no-auto-approve` | Yes | Yes | Yes | Disable auto-approval |

### MCP & Plugin Flags

| Flag | Interactive | Headless | Bare | Description |
|------|:-----------:|:--------:|:----:|-------------|
| `--mcp-config <path>` | Yes | Yes | Yes | Custom MCP config file |
| `--mcp-server <name>` | Yes | Yes | Yes | Start specific MCP server |
| `--plugin <path>` | Yes | Yes | Yes | Load plugin from path |

### Agent & Delegation Flags

| Flag | Interactive | Headless | Bare | Description |
|------|:-----------:|:--------:|:----:|-------------|
| `--delegate <agent>` | Yes | No | No | Delegate to named agent |
| `--agent-team <config>` | Yes | No | No | Load agent team config |
| `--spawn-agent <type>` | Yes | No | No | Spawn sub-agent directly |

## Mode-Exclusive Flags

Some flags only work in specific modes:

### Interactive-only

- `--continue` — Requires an interactive TTY to display session history
- `--fork` — Copies the interactive session state; no meaning in headless
- `--delegate <agent>` — Interactive agent delegation with TTY UI
- `--spawn-agent <type>` — Launches a sub-agent with interactive UI

### Headless/Bare-only

- `--headless` — Cannot be combined with interactive mode
- `--bare` — Cannot be combined with interactive mode

### Unsupported in Headless and Bare

- Sub-agent spawning (`@agent`, `--spawn-agent`)
- Interactive permission prompts (`--permission`)
- Session continuation via interactive UI

## Mutually Exclusive Flag Combinations

| Incompatible Flags | Reason |
|--------------------|--------|
| `--headless` + `--bare` | Two distinct output modes cannot be active simultaneously |
| `--continue` + `-p` | Cannot both resume and provide a new prompt in the same invocation |
| `--output json` + `--bare` | Bare mode has its own minimal format; JSON output conflicts |
| `--permission` + `--auto-approve` | These modes override each other; pick one |
| `--model` + `--effort` | Allowed together — effort is a per-model setting |

## Output Format Details

| `--output` Value | Description | Use Case |
|------------------|-------------|----------|
| `text` (default) | Human-readable markdown with decorations | Interactive review |
| `json` | Single JSON object with full response | Programmatic parsing |
| `stream-json` | One JSON object per line (NDJSON) | Piping to `jq` or log collectors |

## Environment Variable Overrides

Flags can be overridden by environment variables:

| Variable | Overrides | Default |
|----------|-----------|---------|
| `CLAUDE_DEFAULT_MODEL` | `--model` | sonnet |
| `CLAUDE_DEFAULT_EFFORT` | `--effort` | medium |
| `CLAUDE_PERMISSION_MODE` | `--permission` | ask |
| `CLAUDE_SESSION_DIR` | session storage location | `~/.claude/sessions/` |

## Version and Diagnostics

| Flag | Description |
|------|-------------|
| `--version` | Print CLI version and exit |
| `--doctor` | Run diagnostic checks (MCP servers, permissions, config) |
| `--dry-run` | Parse and validate flags without executing |
