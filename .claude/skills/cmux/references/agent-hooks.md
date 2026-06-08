# cmux agent hooks and session resume

How to wire cmux hooks and per-agent session resume. This is the setup that makes
notification-driven monitoring and "bring my agents back after a restart" work. Read this
when configuring hooks or resume for a specific agent.

cmux is external and fast-moving; commands and config keys reflect documented behavior at
authoring time. The notification and resume integrations are macOS-first / macOS-only —
confirm against your installed build and platform; mismatches are version drift, not error.

## Table of contents

- [`cmux hooks setup`](#cmux-hooks-setup)
- [Notification hooks](#notification-hooks)
- [Session restore and auto-resume](#session-restore-and-auto-resume)
- [Claude Code resume (detailed)](#claude-code-resume-detailed)
- [Generic per-agent resume pattern](#generic-per-agent-resume-pattern)
- [Supported agents](#supported-agents)

## `cmux hooks setup`

Run once after install:

```
cmux hooks setup
```

This installs the integration hooks cmux needs into your shell and your agents' hook
configs. It is the single most important step for agent workflows — without it,
lifecycle notifications do not fire automatically and automatic session resume has nothing
to resume from. Re-run it after installing a new agent CLI so cmux can wire that agent too.

## Notification hooks

The hooks bind agent lifecycle events to desktop notifications so you do not instrument
each prompt by hand. The canonical example is a **Stop hook**: when an agent finishes its
turn, the hook fires a notification (via `cmux notify` or an OSC sequence) so you get a
ping the moment the agent is done or blocked. With this in place, the orchestration loop
is "act on pings, not on a tab-by-tab sweep" — the foundation of supervising many agents
at once. The exact notification mechanics are in `cli-and-socket-api.md`.

## Session restore and auto-resume

cmux can reopen your workspaces and resume each agent session after a restart instead of
leaving dead terminals:

```
terminal.autoResumeAgentSessions   true   # config key; resume agent sessions on relaunch
```

With this enabled, on relaunch cmux reopens each saved workspace and runs that agent's
**resume command** to continue the session. Auto-resume depends on:

1. `cmux hooks setup` having recorded enough per-workspace metadata (agent type, cwd,
   session id) to reconstruct the session, and
2. a correct resume command for each agent — built-in for supported agents, configurable
   for the rest (below).

For one-off restores without enabling full auto-resume, reopen a workspace and reattach
its session manually from the CLI (see `cli-and-socket-api.md`).

## Claude Code resume (detailed)

Claude Code is the primary integration. cmux tracks each Claude Code session per workspace
and resumes it using Claude Code's own continuation flags. The resume command cmux runs is
of the form:

```
# Resume the most recent session in this workspace's cwd
claude --continue

# Or resume a specific session by id (what cmux records per workspace)
claude --resume <session-id>
```

`cmux hooks setup` installs the Claude Code hooks (including the Stop hook for completion
notifications) and records the session id so auto-resume can pass the right `--resume`
target. If you launch Claude Code with non-default flags, register that launch as a custom
command (see `cli-and-socket-api.md`) so resume reproduces the same environment.

## Generic per-agent resume pattern

For any agent, resume reduces to three things cmux needs:

1. **Detection** — how cmux knows which agent runs in the workspace (recorded at setup).
2. **Session reference** — the id, directory, or transcript the agent resumes from.
3. **Resume command** — the exact command line cmux re-runs on relaunch.

When an agent is not auto-detected, set a **custom resume command** in cmux config for that
workspace/agent — the command line that continues its session (often the agent's own
`resume`/`continue`/`--resume <id>` subcommand). Model it on the Claude Code example: find
the agent's documented "continue last session" invocation and register it. This keeps the
integration bounded — one configurable hook point rather than bespoke code per agent.

## Supported agents

cmux ships resume/hook support (or accepts a custom resume command) for a range of coding
agents. Claude Code has first-class, detailed support (above). The following are
documented as supported; for any of them, rely on the built-in wiring where present and
otherwise apply the generic pattern above with that agent's continuation command:

- Claude Code (first-class — see detailed section)
- Codex
- Grok
- OpenCode
- Pi
- Amp
- Cursor CLI
- Gemini
- Rovo Dev
- Copilot
- Others as cmux adds them — apply the generic per-agent resume pattern

Because per-agent continuation flags differ and change over time, verify each agent's
resume invocation against its own current docs rather than assuming; cmux's job is to
re-run that command, not to define it.
