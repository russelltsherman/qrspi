# Hook Configuration

Hooks run custom commands at lifecycle events during CLI execution.
They enable cost monitoring, automated reporting, and CI/CD integration.

## Hook Event Types

### `on_turn_start`

**Payload:** Session ID, turn number, model, estimated cost.

**Use case:** Begin per-turn cost tracking, log session start for analytics.

```bash
# Example: log session start with timestamp
claude --hook on_turn_start="echo 'turn $CLAUDE_TURN_COUNT model=$CLAUDE_MODEL started at $(date -Iseconds)' >> /tmp/claude-log.txt"
```

### `on_turn_end`

**Payload:** Turn number, actual cost, token usage, status (success/error), response excerpt.

**Use case:** Accumulate running costs, detect expensive turns, trigger budget warnings.

```bash
# Example: append cost to running total
claude --hook on_turn_end="curl -s -X POST http://metrics.internal/claude/turn -d '{'turn': '$CLAUDE_TURN_COUNT', 'cost_usd': '$CLAUDE_TURN_COST'}'"
```

### `on_session_start`

**Payload:** Session name, session ID, model, flags used.

**Use case:** Allocate resources, set up per-session environments, notify team channels.

```bash
# Example: notify a Slack channel on session start
claude --hook on_session_start="curl -s -X POST $SLACK_WEBHOOK -d '{\"text\": \"Session $CLAUDE_SESSION_NAME started\"}'"
```

### `on_session_end`

**Payload:** Session name, session ID, total cost, total turns, duration, final status.

**Use case:** Generate session reports, clean up per-session resources, archive logs.

```bash
# Example: generate a session summary
claude --hook on_session_end="echo 'Session $CLAUDE_SESSION_NAME: $CLAUDE_TOTAL_TURNS turns, \$${CLAUDE_TOTAL_COST} total' >> /tmp/claude-reports.txt"
```

### `on_budget_warning`

**Payload:** Current cost, budget limit, remaining budget.

**Use case:** Alert before hard budget cutoff, adjust model to cheaper variant.

```bash
# Example: downgrade model when approaching budget limit
claude --max-budget-usd 5.00 \
  --hook on_budget_warning="echo 'WARNING: budget threshold reached, current cost=${CLAUDE_CURRENT_COST}, limit=${CLAUDE_BUDGET_LIMIT}'"
```

### `on_error`

**Payload:** Error code, error message, turn number (if applicable).

**Use case:** Send alerts on failures, capture diagnostics, retry logic.

```bash
# Example: capture errors for debugging
claude --hook on_error="echo 'ERROR [$CLAUDE_ERROR_CODE]: $CLAUDE_ERROR_MESSAGE' >> /tmp/claude-errors.txt"
```

## Configuration Schema

Hooks can be configured in two ways:

### CLI Flag (per-invocation)

```bash
claude --hook on_turn_start="command" --hook on_session_end="command" -p "prompt"
```

Multiple `--hook` flags attach handlers to different events.

### settings.json / settings.local.json

```json
{
  "hooks": {
    "on_turn_start": ["echo 'Turn $CLAUDE_TURN_COUNT started'"],
    "on_turn_end": ["curl -s http://metrics.internal/turn"],
    "on_session_end": ["echo 'Session done' >> /tmp/claude.log"],
    "on_budget_warning": ["curl -s http://alerts.internal/warning"],
    "on_error": ["echo 'Error: $CLAUDE_ERROR_MESSAGE' >> /tmp/errors.log"]
  }
}
```

**Settings paths:**
- **Global:** `~/.claude/settings.json` or `~/.claude/settings.local.json`
- **Project:** `<repo>/.claude/settings.json` or `<repo>/.claude/settings.local.json`

### Environment Variables in Hook Payloads

| Variable | Event(s) |
|----------|----------|
| `$CLAUDE_SESSION_ID` | All |
| `$CLAUDE_SESSION_NAME` | All |
| `$CLAUDE_TURN_COUNT` | on_turn_start, on_turn_end |
| `$CLAUDE_MODEL` | on_turn_start, on_turn_end |
| `$CLAUDE_TURN_COST` | on_turn_end |
| `$CLAUDE_TOTAL_COST` | on_session_end |
| `$CLAUDE_TOTAL_TURNS` | on_session_end |
| `$CLAUDE_BUDGET_LIMIT` | on_budget_warning |
| `$CLAUDE_CURRENT_COST` | on_budget_warning, on_session_end |
| `$CLAUDE_ERROR_CODE` | on_error |
| `$CLAUDE_ERROR_MESSAGE` | on_error |

## Exit Code Meanings

| Code | Meaning |
|------|---------|
| `0` | Success — task completed normally |
| `1` | Generic error — unexpected failure |
| `2` | Usage error — invalid flags or arguments |
| `3` | Auth error — authentication or authorization failure |
| `4` | Budget exceeded — `--max-budget-usd` threshold reached |
| `5` | Turn limit exceeded — `--max-turns` threshold reached |
| `10` | MCP server error — MCP server connection failure |
| `11` | Config error — invalid configuration file |
| `130` | Interrupted — Ctrl+C or SIGINT |

## Use Case Examples

### CI/CD Cost Dashboard

```bash
# Attach hook to push metrics after every turn
claude --headless \
  --hook on_turn_end="curl -sf http://dashboard.internal/api/claude/turn \
    -H 'Authorization: Bearer $METRICS_TOKEN' \
    -d '{'session':'$CLAUDE_SESSION_ID','turn':$CLAUDE_TURN_COUNT,'cost':$CLAUDE_TURN_COST}'" \
  -p "Run migrations and report any issues"
```

### Pre-Merge Budget Guard

```bash
# Abort and report if cost exceeds project threshold
claude --max-budget-usd 2.00 \
  --hook on_budget_warning="curl -s -X POST $SLACK_WEBHOOK \
    -d '{\"text\": \"Budget warning: \$${CLAUDE_CURRENT_COST}/\$${CLAUDE_BUDGET_LIMIT}\"}'" \
  --hook on_session_end="echo 'Final: \$${CLAUDE_TOTAL_COST} for session \$CLAUDE_SESSION_NAME' >> /tmp/cost-log.txt" \
  -p "Review all failing tests and suggest fixes"
```
