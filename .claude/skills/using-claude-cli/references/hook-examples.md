# Hook examples

> **Provenance.** Everything here is **[CLI-spec]** — synthesized from the Claude Code
> CLI/settings specification and **not** verified against this repository. Hook event
> names, the matcher grammar, exit-code semantics, and the JSON payload shape are
> externally-derived; confirm them against your installed version's settings schema
> before relying on them.

Hooks are user-defined shell commands the harness runs automatically at defined points in
the agent loop (before/after a tool call, on session events). They are configured in
`settings.json` — **the harness executes them, not the model** — so they are the right
mechanism for "always do X before/after Y" automation that must not depend on the model
remembering.

## Where hooks live [CLI-spec]

Hooks are declared under a `hooks` key in `settings.json` (project `.claude/settings.json`,
project-local `.claude/settings.local.json`, or user `~/.claude/settings.json`). Each
entry binds a **hook event** to a **matcher** and one or more **commands**.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/guard-bash.sh" }
        ]
      }
    ]
  }
}
```

## Hook events [CLI-spec]

Common events (names are **[CLI-spec]**):

- **PreToolUse** — fires before a tool call executes. Can inspect the proposed call and
  **block** it. The primary enforcement point.
- **PostToolUse** — fires after a tool call completes. For reactions: format, lint, log,
  notify.
- **UserPromptSubmit** — fires when a prompt is submitted; can inject context or reject.
- **Stop** / session-lifecycle events — fire when the agent finishes a turn or the
  session ends; useful for cleanup or notifications.

## Matcher syntax [CLI-spec]

The `matcher` selects which tool calls (or events) a hook applies to:

- A bare tool name — `"Bash"`, `"Edit"`, `"Write"` — matches that tool.
- A `Tool(specifier)` form narrows by argument — e.g. matching only certain Bash
  commands or certain file paths.
- An empty/omitted matcher (or `"*"`) matches everything for that event.
- Multiple tool names can be combined (e.g. pipe-separated) so one hook covers a set.

The matcher grammar mirrors the permission-rule specifier grammar; see
[permission-rule-patterns.md](permission-rule-patterns.md) for the `Tool(specifier)`
forms in detail.

## Exit-code semantics [CLI-spec]

A hook command communicates back through its exit code (and, for richer control, JSON on
stdout):

- **Exit 0** — success. The tool call proceeds (PreToolUse) or the post-action is
  recorded (PostToolUse). Anything the hook prints to stdout may be surfaced as context.
- **Exit 2** — **block.** For PreToolUse this denies the tool call; stderr is fed back to
  the model as the reason. This is how a hook vetoes a dangerous action.
- **Other non-zero** — treated as a hook error (surfaced/logged) without necessarily
  cleanly blocking; prefer exit 2 for an intentional veto.

A hook may also emit a JSON object on stdout to return structured decisions (allow/deny
plus a reason) where the exit-code channel is too coarse. The JSON decision schema is
**[CLI-spec]**.

## Prompt-based vs agent-based hooks [CLI-spec]

Two styles of enforcement:

- **Prompt/command hooks (deterministic):** a fixed shell command (the examples above).
  Fast, free, and predictable — the harness runs the script and reads its exit code. Best
  for mechanical rules (block writes outside a directory, run a formatter, reject a
  forbidden command).
- **Agent-based hooks (judgment):** the hook invokes `claude -p` (or a subagent) to make
  a contextual decision the model is better at than a regex. Costs tokens and adds
  latency; reserve for checks that genuinely need reasoning (e.g. "does this commit
  message describe the diff?").

```bash
# agent-based PreToolUse guard (pseudo): ask a cheap model whether a Bash command is safe
DECISION="$(printf '%s' "$TOOL_INPUT" | claude -p \
  "Reply ALLOW or DENY: is this shell command destructive?" --model <small-model> \
  --output-format text)"
case "$DECISION" in *DENY*) echo "blocked by guard" >&2; exit 2;; esac
```

## Worked examples [CLI-spec]

**PostToolUse — auto-format after every edit:**

```json
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [ { "type": "command", "command": "prettier --write \"$CLAUDE_FILE\"" } ] }
    ]
  }
}
```

**PreToolUse — block writes outside the project tree (`guard-write.sh`):**

```bash
#!/usr/bin/env bash
# Receives the proposed tool input on stdin as JSON (shape is [CLI-spec]).
target="$(jq -r '.path // .file_path // empty')"
case "$target" in
  "$PWD"/*) exit 0 ;;            # inside project: allow
  *) echo "refusing write outside project: $target" >&2; exit 2 ;;  # block
esac
```

See also: [permission-rule-patterns.md](permission-rule-patterns.md) — for static
allow/deny rules, which are simpler than a hook when no shell logic is required.
