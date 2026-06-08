---
name: cmux
description: "Guidance for driving cmux, a terminal multiplexer built for running and orchestrating AI coding agents (Claude Code, Codex, and others) across workspaces, surfaces, and panes. Use when the user mentions cmux, asks how to set up or script a cmux workspace, wants desktop notifications from agents (OSC 9/99/777 or `cmux notify`), is configuring Claude Code Teams, needs session restore or per-agent resume after a restart, or is orchestrating multiple background agents and wants one workspace per task with notification-driven monitoring. Trigger even when the user only describes the symptom — e.g. 'my agent finished but I didn't get a ping', 'how do I reattach my agents after rebooting', or 'I want to run five agents in parallel and know when each is done' — and cmux is the tool in play."
command: /cmux
argument-hint: [topic]
allowed-tools: Read, Bash
---

# cmux — terminal multiplexer for AI agents

cmux is a terminal multiplexer designed around running AI coding agents rather than
plain shells. Where a classic multiplexer thinks in sessions and windows, cmux thinks
in **workspaces** (one isolated context, usually one agent task), **surfaces** (tabbed
views inside a workspace — a terminal, an editor, an in-app browser), and **panes**
(splits within a surface). It adds first-class machinery that bare multiplexers lack:
desktop notifications wired to agent activity, a Claude Code Teams integration for
native split teammates, automatic agent-session resume across restarts, and a
CLI + socket API so you (or another agent) can drive it programmatically.

This skill gives you the working model and the common workflows. Exhaustive lists —
every keyboard shortcut, the full CLI/socket surface, per-agent hook wiring — live in
`references/` and should be read on demand, not up front. If the user passed a `[topic]`
argument (`shortcuts`, `cli`, `hooks`), jump straight to the matching reference below.

> **Version caveat.** cmux is an external tool and evolves quickly. The commands,
> config keys, and shortcuts here reflect the documented behavior at authoring time and
> are macOS-first (the desktop notification and Teams integrations are macOS-only —
> see Scope caveats). Confirm against your installed version before relying on exact
> flags; treat anything that does not match your build as a version drift, not a bug in
> your usage.

## Reference map — read on demand

- **Keyboard shortcuts** — full shortcut table (workspace/surface/pane navigation,
  notifications, Teams). Read `references/keyboard-shortcuts.md` when the user wants a
  shortcut, asks "what's the key for…", or is customizing bindings. Keystroke notation
  and any escape sequences live there inside code fences.
- **CLI and socket API** — every `cmux …` subcommand, the control socket protocol,
  custom commands, in-app browser scripting, and SSH/remote use. Read
  `references/cli-and-socket-api.md` when scripting cmux, automating it from another
  agent, or wiring it into a pipeline.
- **Agent hooks and resume** — `cmux hooks setup`, the per-agent resume integration
  (Claude Code in detail plus a generic pattern for Codex, Grok, OpenCode, Pi, Amp,
  Cursor CLI, Gemini, Rovo Dev, Copilot, and others), and notification hooks. Read
  `references/agent-hooks.md` when configuring hooks or resume for a specific agent.

## Installation and setup

cmux installs as a desktop application plus a `cmux` CLI on `PATH`. After install:

1. Launch the cmux app once so it can register its CLI helper and (on macOS) request
   notification permission — without that grant, agent notifications silently no-op.
2. Verify the CLI is reachable: `cmux --version`. The CLI talks to the running app over
   a local control socket, so the app must be running for most subcommands to do
   anything (see `references/cli-and-socket-api.md` for the socket details).
3. Run `cmux hooks setup` to install the shell/agent hooks that drive notifications and
   automatic session resume. This is the single most important setup step for agent
   workflows — see `references/agent-hooks.md`.

## Workspaces, surfaces, and panes

This three-level model is the core mental shift. Map your work onto it deliberately:

- **Workspace** — an isolated context, typically **one per agent task**. It holds its
  own surfaces, working directory, and agent session. Create, name, navigate between,
  and close workspaces; a named workspace is far easier to find later when you have a
  dozen agents running.
- **Surface** — a tab inside a workspace. A surface is usually a terminal running an
  agent, but can also be an editor view or an in-app browser. Open multiple surfaces in
  one workspace when a single task needs, say, an agent terminal plus a browser preview.
- **Pane** — a split within a surface. Use panes to watch two things side by side inside
  one surface (an agent and a `tail -f`, for instance), where surfaces would over-tab.

Rule of thumb: **workspace = task, surface = tool, pane = side-by-side view**. Reach for
a new workspace when the *context* changes (different repo, different agent task), a new
surface when you need a *different tool* for the same task, and a pane only when you want
two views *at once*. The exact create/navigate/rename/close keystrokes are in
`references/keyboard-shortcuts.md`; the scriptable equivalents are in
`references/cli-and-socket-api.md`.

## Notification system

The notification system is what makes background agents practical: instead of babysitting
a terminal, you let the agent ping you when it needs attention or finishes. cmux raises a
desktop notification from three sources:

- **OSC escape sequences** — an agent (or any program) emits an OSC 9, 99, or 777
  sequence to the terminal and cmux turns it into a desktop notification. This is the
  zero-dependency path: the agent just prints to stdout. The exact byte sequences are in
  `references/cli-and-socket-api.md` and `references/keyboard-shortcuts.md`, written
  inside code fences so they render and copy correctly.
- **`cmux notify`** — a CLI helper an agent can shell out to when emitting raw escapes is
  awkward. It posts a notification through the running app. See
  `references/cli-and-socket-api.md` for flags (title, body, workspace targeting).
- **Hooks** — `cmux hooks setup` wires agent lifecycle events (a Claude Code Stop hook,
  for example) to fire notifications automatically, so you do not have to instrument each
  prompt by hand. See `references/agent-hooks.md`.

On macOS, notifications require the one-time permission grant from setup. Notification
delivery is a macOS-only capability today (see Scope caveats).

## Claude Code Teams

cmux integrates with Claude Code Teams so that a teammate agent spawned by the team
appears as a **native split** inside cmux rather than a detached process you cannot see.
Use `cmux claude-teams` to start or attach the Teams integration; teammates then land as
panes/surfaces in the current workspace, so you can watch and steer them with the same
navigation you use for everything else. The Teams-specific keys are in
`references/keyboard-shortcuts.md`; the integration is macOS-only.

## Session restore and agent resume

Agents are long-lived, so surviving a restart matters. cmux can bring your agent sessions
back instead of leaving you with dead terminals:

- **Automatic resume** — set `terminal.autoResumeAgentSessions` (cmux config) so that on
  relaunch cmux reopens each workspace and resumes its agent session where it left off.
  This depends on the per-agent resume wiring installed by `cmux hooks setup`.
- **Custom resume commands** — for agents whose resume invocation is non-standard, you can
  configure the exact command cmux runs to bring a session back. The per-agent specifics
  (Claude Code's `--resume`/`--continue` style, plus the generic pattern for other agents)
  are in `references/agent-hooks.md`.
- **Manual restore** — you can also reopen a workspace and reattach its session by hand
  from the CLI when you do not want full auto-resume. See
  `references/cli-and-socket-api.md`.

## Multi-agent orchestration

The payoff of the model above is running several agents at once without losing track:

- **One workspace per agent task.** Give each its own named workspace so context never
  bleeds between tasks and you can navigate straight to the one that needs you.
- **Notification-driven monitoring.** Let each agent notify on completion or when it
  blocks (via hooks, OSC, or `cmux notify`) instead of polling terminals. You act on
  pings, not on a tab-by-tab sweep — this is what lets one human supervise many agents.
- **Metadata tracking.** Name workspaces after the task/ticket and keep their working
  directory set so you can tell at a glance which agent is doing what; the CLI/socket API
  can enumerate workspaces if you want to script a dashboard
  (see `references/cli-and-socket-api.md`).

A practical loop: spawn N workspaces, one per task, each running an agent with hooks set
up; go do something else; respond to notifications as they arrive; navigate to the
pinging workspace, unblock or review, move on.

## Scope caveats

- **macOS-only integrations.** The desktop notification delivery, the Claude Code Teams
  native-split integration, and the agent-resume hooks are macOS-first / macOS-only at
  authoring time. On other platforms the core multiplexer (workspaces/surfaces/panes,
  CLI/socket) may work while these integrations do not — verify on your platform.
- **External, fast-moving tool.** cmux is not vendored in this repo, so nothing here is
  validated against a pinned version. Confirm exact subcommands, config keys, and
  shortcuts against your installed build; mismatches are version drift.
- **App must be running.** Most CLI subcommands are thin clients over the app's control
  socket — they do nothing useful if the cmux app is not running.
