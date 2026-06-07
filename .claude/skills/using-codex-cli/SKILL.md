---
name: using-codex-cli
description: Operate the OpenAI Codex CLI (the `codex` command) effectively and safely. Use whenever the user wants to run, automate, script, or configure Codex — including approval modes (suggest/auto-edit/full-auto), sandbox modes (read-only/workspace-write/danger-full-access), non-interactive `codex exec` automation and CI, AGENTS.md project instructions, config.toml/profiles, Codex MCP server mode for multi-agent orchestration, or troubleshooting Codex behavior. Trigger even when the user only says "codex", names a `codex` subcommand/flag, or describes piping/automating Codex without naming the skill.
---

# Using the Codex CLI

OpenAI's Codex CLI (`codex`) is a terminal coding agent. It edits files, runs
commands, and answers questions about a repo. The two settings that govern every
session are **approval mode** (when it asks permission) and **sandbox mode** (what
it is technically allowed to touch). Get those two right and everything else
follows. This skill is the operating manual; deep references live under
`references/` and are linked from each section below.

> Codex changes quickly. Treat the specific flags, config keys, and macOS sandbox
> notes here as the current best understanding, and confirm against `codex --help`,
> `codex <subcommand> --help`, and the live docs when something behaves unexpectedly.

## Quick orientation

- Interactive TUI: `codex` (opens a session in the current directory).
- One-shot / scripting: `codex exec "<prompt>"` (non-interactive, prints and exits).
- Resume an interactive session: `codex resume` (or pick from recent sessions).
- Per-run safety overrides: `--ask-for-approval <mode>` and `--sandbox <mode>`.
- Config lives in `config.toml` (user: `~/.codex/config.toml`, project: `.codex/`).
- Project instructions live in `AGENTS.md` files, merged by directory depth.

## Approval modes (when Codex asks before acting)

Approval mode controls how often Codex pauses to ask you before running a command
or writing a file. Set per-run with `--ask-for-approval` (alias for the policy) or
the bundled `--full-auto` shortcut, or persist it in `config.toml`.

| Mode | Behavior | Use when |
| --- | --- | --- |
| **suggest** (default-ish) | Proposes edits/commands; you approve each one | Local dev on code you care about; exploring an unfamiliar repo |
| **auto-edit** | Applies file edits automatically; still asks before running commands | Trusted, iterative work where you watch the diffs |
| **full-auto** | Runs commands and edits without asking, inside the sandbox | CI, containers, throwaway environments, batch jobs |

Decision rule: **local dev → suggest; trusted iterative loop → auto-edit; CI or
disposable container → full-auto**. The higher the autonomy, the more the sandbox
(below) is your real safety net — full-auto is only as safe as the sandbox it runs
in. Approval policy and sandbox are independent knobs; full autonomy with a
read-only sandbox is a safe, common combination for code review.

## Sandbox modes (what Codex is allowed to touch)

Sandbox mode is the OS-enforced boundary around Codex's actions. It is enforced by
**Apple Seatbelt (`sandbox-exec`) on macOS** and by **Landlock + seccomp (often via
bubblewrap) on Linux**.

| Mode | Filesystem | Network |
| --- | --- | --- |
| **read-only** | Read anywhere; no writes | Off |
| **workspace-write** | Read anywhere; write only the workspace (and temp) | Off by default |
| **danger-full-access** | Unrestricted | Unrestricted |

Key points:

- **Network is off by default**, even in `workspace-write`. Commands needing the
  network (installing packages, fetching deps) fail until you explicitly allow it
  (e.g. a `workspace-write` network toggle in config, or `danger-full-access`).
- `danger-full-access` disables the sandbox — only use it inside an already-isolated
  environment (a container/VM you can throw away), never on your daily machine.
- On macOS, prefer setting the sandbox with the `--sandbox` **flag** rather than only
  via `config.toml`; see `references/limitations-and-workarounds.md` for the network
  edge cases this avoids.

Full enforcement details and platform specifics:
[references/limitations-and-workarounds.md](references/limitations-and-workarounds.md).

## Session management

Each `codex` session carries its own context window. Two habits keep results sharp:

- **One discrete task per session.** Start a fresh session for an unrelated task
  rather than piling it onto a long thread — stale context misleads the agent.
- **Watch for context-window pressure.** On a long chain the agent forgets earlier
  constraints and quality drifts. When you notice it repeating mistakes or losing
  the thread, stop, summarize the state, and start fresh (`codex` again, or
  `codex resume` only when continuity genuinely helps). For automation, each
  `codex exec` is already a fresh, stateless run — lean on that.

## AGENTS.md hierarchy (project instructions)

Codex reads `AGENTS.md` files to learn project conventions, and **merges them by
directory depth**: the file closest to the working file wins on conflicts (deeper =
higher precedence), with shallower files providing the base.

- **Override file first:** an `AGENTS.override.md` (when present) takes precedence
  over the regular `AGENTS.md` cascade — use it for local, uncommitted overrides.
- **Cascade / concatenation:** Codex walks from the repo root down to the working
  directory, concatenating the `AGENTS.md` files it finds; nearer files refine or
  override farther ones.
- **Size limit:** each `AGENTS.md` is capped (commonly **32 KiB**, configurable via
  `project_doc_max_bytes`); content beyond the cap is truncated, so keep them tight
  and push detail into linked docs.
- **Nested rules:** subdirectory `AGENTS.md` files let you scope instructions to one
  package or module without polluting the root.

Filename fallbacks and the byte-limit knob are documented in
[references/config-reference.md](references/config-reference.md).

## config.toml quick start

Persistent settings live in TOML — user-level at `~/.codex/config.toml`,
project-level at `.codex/config.toml`. The essentials:

```toml
model = "o4-mini"               # default model
approval_policy = "suggest"      # suggest | auto-edit | full-auto
sandbox_mode = "workspace-write" # read-only | workspace-write | danger-full-access
project_doc_max_bytes = 32768    # AGENTS.md byte cap

[profiles.ci]                    # named profile: codex --profile ci
approval_policy = "full-auto"
sandbox_mode = "workspace-write"
```

The full schema — every key, named `[profiles.<name>]`, feature flags,
`model_instructions_file`, doc-limit and fallback-filename keys, and user-vs-project
precedence — is in
[references/config-reference.md](references/config-reference.md).

## Non-interactive automation: `codex exec`

`codex exec` is the headless entry point for scripts, pipes, and CI. It takes the
prompt as a positional argument or reads it from stdin, runs to completion, prints,
and exits. It composes with normal Unix pipes:

```bash
codex exec "summarize the failing tests"           # prompt as argument
git diff | codex exec "review this diff"            # prompt via stdin pipe
codex exec --json "list TODOs" | jq .               # machine-readable output
```

Flags worth knowing: `--json` (structured output), `--quiet`, and the
config-bypass flags `--ignore-user-config` / `--ignore-rules` for reproducible CI.
All flags, stdin (`-`) handling, prompt+stdin combinations, and full CI pipeline
patterns are in
[references/codex-exec-patterns.md](references/codex-exec-patterns.md).

## MCP server mode (multi-agent orchestration)

Codex can run **as an MCP server**, exposing `codex` (start a session) and
`codex-reply` (continue it) as tools an orchestrator agent calls. This lets one
agent fan work out to Codex subagents.

```
orchestrator → codex(prompt="refactor module A", cwd="/work/a")  → sessionId
            → codex-reply(sessionId, "now add tests")           → continues that session
```

Run separate Codex agents in **separate git worktrees** so their edits never
collide, and only spawn a subagent when the task genuinely needs delegated,
isolated work — not for things the main agent can do directly. Tool schemas and 2–3
worked orchestration examples:
[references/mcp-server-mode.md](references/mcp-server-mode.md).

## When a run goes sideways: re-run non-determinism

Codex is non-deterministic — the same prompt can yield different edits. When a
result looks wrong, don't hand-patch blindly:

```
result looks wrong
   │
   ├─ re-run the same prompt (fresh session)
   │
   ├─ diff the two attempts  → which change is actually correct?
   │
   ├─ run the tests          → do they pass?
   │
   └─ pass → accept   |   fail → roll back (git restore) and refine the prompt
```

This flow plus the macOS network/sandbox bugs, long-chain limits, and
context-window guidance live in
[references/limitations-and-workarounds.md](references/limitations-and-workarounds.md).

## Reference files

- [references/config-reference.md](references/config-reference.md) — full
  `config.toml` schema, profiles, feature flags, AGENTS.md doc-limit keys.
- [references/codex-exec-patterns.md](references/codex-exec-patterns.md) —
  `codex exec` args/flags, stdin piping, `--json`/`--quiet`, Unix-pipe + CI patterns.
- [references/mcp-server-mode.md](references/mcp-server-mode.md) — `codex` /
  `codex-reply` tool schemas, orchestration examples, worktrees, subagent discipline.
- [references/limitations-and-workarounds.md](references/limitations-and-workarounds.md)
  — re-run non-determinism, macOS sandbox/network bugs, long-chain limits, fresh-session
  guidance.
