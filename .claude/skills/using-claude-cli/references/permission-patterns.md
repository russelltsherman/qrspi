# Permission Rules

Permission rules control which tools and operations Claude can invoke
without explicit user approval. They are defined at multiple levels in
the configuration hierarchy.

## Rule Syntax

### allowed-tools

List of tool access patterns that are automatically approved:

```json
{
  "allowed-tools": [
    "Bash(ls:*)",
    "Bash(cat:*)",
    "Bash(grep:*),
    "Bash(git status)",
    "Read",
    "Glob",
    "Grep"
  ]
}
```

### disallowed-tools

Explicitly deny tools regardless of `allowed-tools`:

```json
{
  "disallowed-tools": [
    "Bash(rm:*)",
    "Bash(chmod:*)",
    "Bash(sudo:*)"
  ]
}
```

### Bash Pattern Syntax

Bash rules use glob patterns against the command prefix:

| Pattern | Matches |
|---------|---------|
| `"Bash(ls:*)"` | Any command starting with `ls ` |
| `"Bash(git status)"` | Only exact `git status` |
| `"Bash(git commit -m*)"` | `git commit -m` with any message |
| `"Bash(.*)"` | All bash commands (use with extreme caution) |
| `"Read"` | All file reads |
| `"Glob"` | All file globbing |
| `"Grep"` | All grep/search operations |

## Settings Hierarchy

Rules are evaluated in order of precedence. More specific (narrower)
scopes override broader ones.

| Level | File | Scope | Override |
|-------|------|-------|----------|
| 1 (lowest) | Global CLAUDE.md | All projects, all users | — |
| 2 | Project CLAUDE.md | Single repository | Global CLAUDE.md |
| 3 | `settings.json` | Single user, all projects | Project CLAUDE.md |
| 4 (highest) | `settings.local.json` | Single user, overrides all | `settings.json` |

### File Locations

| File | Path |
|------|------|
| Global CLAUDE.md | `~/.claude/CLAUDE.md` |
| Project CLAUDE.md | `<repo>/.claude/CLAUDE.md` |
| settings.json | `~/.claude/settings.json` or `<repo>/.claude/settings.json` |
| settings.local.json | `~/.claude/settings.local.json` or `<repo>/.claude/settings.local.json` |

### Conflict Resolution

When the same tool appears in both `allowed-tools` and `disallowed-tools`
at the same level, `disallowed-tools` takes precedence. When the same
tool appears at different levels, the higher-precedence level wins.

## CI/CD Configuration Examples

### GitHub Actions with Auto-Approve

```yaml
- name: Claude Code Review
  run: |
    claude --headless \
      --auto-approve \
      --max-budget-usd 3.00 \
      --output json \
      -p "Review all changed files for security issues and report findings"
```

### CI Permission Profile

```json
{
  "allowed-tools": [
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(cat:*)",
    "Bash(grep:*)",
    "Bash(npm install)",
    "Bash(npm test)",
    "Bash(npm run lint)",
    "Read",
    "Glob",
    "Grep",
    "Bash(echo:*)"
  ],
  "disallowed-tools": [
    "Bash(rm:*)",
    "Bash(chmod:*)",
    "Bash(sudo:*)",
    "Bash(npm publish)",
    "Bash(git push)",
    "Bash(git push --force)"
  ]
}
```

## Common Patterns

### Commit Automation

```json
{
  "allowed-tools": [
    "Bash(git status)",
    "Bash(git diff:*)",
    "Bash(git add:*)",
    "Bash(git commit -m*)",
    "Bash(git push origin main)",
    "Read",
    "Bash(cat:*)"
  ]
}
```

### Code Review Only

```json
{
  "allowed-tools": [
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(grep:*)",
    "Read",
    "Glob",
    "Grep"
  ],
  "disallowed-tools": [
    "Bash(git add:*)",
    "Bash(git commit:*)",
    "Bash(git push:*)",
    "Bash(rm:*)",
    "Write"
  ]
}
```

### Piped Analysis

For headless analysis pipelines where output flows through `jq`:

```json
{
  "allowed-tools": [
    "Bash(claude --output stream-json:*)",
    "Bash(jq:*)",
    "Bash(cat:*)",
    "Bash(grep:*)",
    "Read",
    "Grep"
  ]
}
```

### Scripting with Restricted Execution

```json
{
  "allowed-tools": [
    "Bash(python:*)",
    "Bash(pip install:*)",
    "Bash(node:*)",
    "Bash(npm:*)",
    "Bash(ruby:*)",
    "Read",
    "Write",
    "Glob",
    "Grep",
    "Bash(cat:*)",
    "Bash(mkdir:*)"
  ],
  "disallowed-tools": [
    "Bash(rm:*)",
    "Bash(rmdir:*)",
    "Bash(chmod:*)",
    "Bash(chown:*)",
    "Bash(sudo:*)"
  ]
}
```

## Environment-Specific Defaults

| Environment | Default Permission Mode |
|-------------|------------------------|
| Interactive (TTY) | `ask` — prompt for each tool use |
| Headless (`--headless`) | Follows `allowed-tools` / `disallowed-tools` rules |
| CI/CD pipelines | Typically `auto-approve` with narrow allowed list |
| Agent Teams | Inherits parent session permissions |

## Audit Trail

All tool access is logged regardless of permission mode. Logs are
written to the session directory and can be reviewed via:

```bash
claude --doctor
```

This reports current permissions, MCP server status, and any denied
tool accesses during the active session.
