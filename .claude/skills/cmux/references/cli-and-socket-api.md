# cmux CLI and socket API

The scriptable surface of cmux: the `cmux` subcommands, the control socket the CLI talks
to, custom commands, in-app browser scripting, and SSH/remote use. Read this when
automating cmux — from a shell script, a CI step, or another agent driving cmux on your
behalf.

cmux is external and fast-moving; the subcommands and flags below reflect documented
behavior at authoring time. Confirm against `cmux --help` on your installed build before
relying on exact flags — mismatches are version drift, not error.

## Table of contents

- [Model: CLI over a control socket](#model-cli-over-a-control-socket)
- [Core CLI subcommands](#core-cli-subcommands)
- [Notifications from the CLI](#notifications-from-the-cli)
- [OSC notification sequences](#osc-notification-sequences)
- [Custom commands](#custom-commands)
- [In-app browser scripting](#in-app-browser-scripting)
- [SSH and remote use](#ssh-and-remote-use)
- [Configuration keys](#configuration-keys)

## Model: CLI over a control socket

The `cmux` CLI is a thin client. It connects to the **running cmux app** over a local
control socket and issues requests; the app does the work and the CLI prints the reply.
Practical consequences:

- The app must be running for most subcommands to do anything. A subcommand against a
  stopped app fails fast rather than acting.
- Because it is a socket, another process (a script, an agent) can drive cmux exactly as
  you would from the keyboard — this is the basis for scripted multi-agent orchestration.
- The socket is local to the machine; remote control goes through SSH (below), not by
  exposing the socket.

## Core CLI subcommands

Workspace, surface, and notification control mirror the keyboard model:

```
cmux --version                       print version
cmux --help                          list subcommands and flags
cmux workspace new [--name NAME] [--cwd DIR]   create a workspace, optionally named/cwd'd
cmux workspace list                  enumerate workspaces (id, name, cwd, agent state)
cmux workspace focus <id|name>       bring a workspace to front
cmux workspace close <id|name>       close a workspace
cmux surface new [--workspace W] [--type terminal|browser|editor]
cmux pane split [--dir vertical|horizontal]
cmux send <id|name> -- <command...>  run a command in a workspace/surface
```

`cmux workspace list` is the building block for a scripted dashboard: parse its output to
see which agents are idle, running, or blocked, and drive `focus`/`send` accordingly.

## Notifications from the CLI

`cmux notify` posts a desktop notification through the running app — handy when emitting
raw escape bytes from an agent is awkward:

```
cmux notify --title "Build done" --body "tests passed" [--workspace <id|name>]
```

`--workspace` targets the notification at a specific workspace so the
"jump to last notification" shortcut lands you in the right place. On macOS the one-time
notification permission grant must be in place or this silently no-ops.

## OSC notification sequences

The zero-dependency path: any program printing to a cmux terminal can raise a
notification by emitting an OSC sequence. Kept in a code fence so the bytes are exact:

```
# Simple text notification (OSC 9)
printf '\033]9;%s\a' "agent finished"

# Title + body notification (OSC 777)
printf '\033]777;notify;%s;%s\a' "Claude Code" "task complete"

# Structured notification (OSC 99), terminated by ST (ESC backslash)
printf '\033]99;%s;%s\033\\' "metadata" "body text"
```

`\033` is ESC (hex `1b`), `\a` is BEL (hex `07`), and `\033\\` is the ST terminator. These
sequences belong only inside code fences in references — never in SKILL.md frontmatter,
where they would corrupt YAML parsing.

## Custom commands

cmux lets you register **custom commands** — named actions bound to a CLI invocation or
script — so a frequent multi-step action (open a workspace, cd, launch an agent with
flags) becomes one command. Define them in cmux configuration (see Configuration keys),
giving each a name, the command line to run, and optionally a workspace/surface target.
Once registered, invoke from the command picker or the CLI. Use these to standardize how
agents are launched so every workspace starts in a known state.

## In-app browser scripting

A browser surface (`cmux surface new --type browser`, or the in-app browser shortcut) is
scriptable: you can point it at a URL and drive basic navigation from the CLI/custom
commands, which is useful for giving an agent a live preview surface (a running dev server,
a docs page) alongside its terminal. Treat the browser as another surface in the workspace
— it participates in the same navigation and resume model.

## SSH and remote use

To drive cmux on a remote machine, SSH in and run the `cmux` CLI there against that host's
running app — the control socket stays local to each machine, so you do not forward the
socket. A common pattern is an agent on a remote dev box: SSH in, `cmux workspace new`,
`cmux send` the agent's launch command, and let notifications surface back (delivery is
macOS-only, so a headless remote host typically relies on log/exit signals rather than
desktop pings — see the resume/hooks notes in `agent-hooks.md`).

## Configuration keys

Configuration is file-based; relevant keys referenced elsewhere in this skill:

```
terminal.autoResumeAgentSessions   bool   reopen workspaces and resume agent sessions on relaunch
```

Custom commands and keybindings also live in the config file. After editing config,
restart or reload cmux so changes take effect. See `agent-hooks.md` for the resume wiring
that `autoResumeAgentSessions` depends on, and `keyboard-shortcuts.md` for binding
customization.
