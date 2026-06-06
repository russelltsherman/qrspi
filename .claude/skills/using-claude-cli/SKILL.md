---
name: using-claude-cli
description: Reference for driving the Claude Code CLI itself — headless/print mode, subagents, session resume, permission control, cost management, and scripted orchestration. Use when scripting Claude Code, automating commits or code review, piping input, or wiring Claude into CI/agent pipelines.
command: /using-claude-cli
argument-hint: <topic, e.g. "headless" or "permissions">
allowed-tools: Read, Bash
---

# /using-claude-cli

Utility reference skill for **operating the `claude` CLI itself** — not a QRSPI phase
wrapper. Covers the common-path patterns inline; advanced topics are deferred to the
`references/` docs linked at the bottom.

> **Provenance.** Items marked **[CLI-spec]** are synthesized from the Claude Code CLI
> specification and are **not** verified against this repository; treat them as
> externally-derived and review before relying on them. Items marked **[in-project]**
> are observed in this codebase. The only in-project CLI evidence here is
> `--dangerously-skip-permissions`, used in `.devcontainer/post-create.sh`
> (**[in-project]**).

## CLI modes summary [CLI-spec]

The `claude` binary runs in three common modes:

- **Interactive (REPL):** plain `claude` opens an interactive session in the current
  directory. The default for hands-on work.
- **One-shot interactive with a starting prompt:** `claude "explain this repo"` opens
  interactively but seeds the first turn.
- **Headless / print mode:** `claude -p "<prompt>"` (a.k.a. `--print`) runs
  non-interactively, prints the final result to stdout, and exits. This is the mode used
  for scripting and CI.

Common headless flags:

- `-p, --print` — non-interactive; emit result and exit.
- `--output-format <text|json|stream-json>` — `text` (default) for humans; `json` for a
  single structured result object; `stream-json` for incremental events. Use `json` when
  a script needs to parse the result.
- `--input-format <text|stream-json>` — accept piped/streamed input.
- `--model <name>` — pick the model for the run.
- `--add-dir <path>` — grant access to additional directories beyond the cwd.

Headless mode reads stdin, so you can pipe content into it (see Orchestration examples).

## Orchestration examples [CLI-spec]

These are the common scripted patterns. Each is **[CLI-spec]** — adapt and review before
use.

**Generate a commit message from the staged diff:**

```bash
git diff --cached | claude -p "Write a concise conventional-commit message for this diff. Output only the message."
```

**Automated code review of a PR diff (machine-readable):**

```bash
gh pr diff 123 | claude -p "Review this diff. List correctness bugs only, as a JSON array of {file, line, issue}." --output-format json
```

**Pipe arbitrary stdin for a one-shot transformation:**

```bash
cat error.log | claude -p "Summarize the root cause in two sentences."
```

**Chain into a pipeline (exit code reflects success/failure):**

```bash
claude -p "$PROMPT" --output-format json | jq -r '.result' > out.txt
```

For the full flag catalog (every `--output-format` field, streaming event shapes, and
less-common flags), see [advanced CLI flags](references/advanced-cli-flags.md).

## Subagents [CLI-spec]

Subagents are separate, fresh-context Claude instances the main session can delegate to.
Each subagent has its own context window, its own allowed-tools scope, and its own system
prompt, so delegating isolates a task and keeps the parent context clean.

Common path:

- Define a subagent type once (name, description, tool scope, instructions).
- The orchestrating session spawns it with a scoped prompt; the subagent returns a
  single result string.
- Use subagents to fan out independent work (e.g. one slice per subagent) or to wall off
  a noisy task (large file scan) from the main thread.

For multi-agent fan-out, team coordination, and worked orchestration patterns, see
[agent team orchestration](references/agent-team-orchestration.md).

## Sessions [CLI-spec]

Each `claude` run is a session with a persisted transcript you can return to:

- `--continue` (or `-c`) — resume the **most recent** session in the current directory.
- `--resume <session-id>` — resume a **specific** session by id.
- `--session-id <uuid>` — assign an explicit id to a new run so a script can resume it
  deterministically later.

Common path: a script starts a run with a known `--session-id`, does other work, then
re-enters the same conversation with `--resume <that-id>` to continue with full prior
context. In headless pipelines, capture the session id from `--output-format json` to
chain follow-up turns.

## Permissions summary [CLI-spec]

Claude Code gates tool use (file writes, command execution, network) behind a permission
system. Common-path controls:

- `--permission-mode <mode>` — set how prompts are handled for the run (e.g. a plan/
  read-only posture vs. an accept-edits posture). **[CLI-spec]**
- `--allowedTools` / `--disallowedTools` — allow- or deny-list specific tools (and tool
  argument patterns) for the run, so a script can pre-authorize exactly what it needs and
  nothing more. **[CLI-spec]**
- `--dangerously-skip-permissions` — bypass all permission prompts. **[in-project]** —
  used in `.devcontainer/post-create.sh`. Only safe in an already-isolated/sandboxed
  environment (such as a throwaway dev container); never on a host with real credentials.

Prefer the narrowest allow-list that lets the task run. Reach for
`--dangerously-skip-permissions` only inside disposable sandboxes.

For concrete allow/deny rule syntax and worked rule sets, see
[permission rule patterns](references/permission-rule-patterns.md). For hook-based
enforcement (running a check before/after a tool call), see
[hook examples](references/hook-examples.md).

## Cost control [CLI-spec]

Headless runs consume tokens per invocation; in loops or CI this adds up. Common-path
levers:

- **Pick the right model** with `--model` — use a smaller/cheaper model for routine
  transforms (commit messages, summaries) and reserve the largest model for hard
  reasoning.
- **Scope the context** — run from the narrowest directory and use `--add-dir` only when
  needed; smaller context means fewer input tokens.
- **Read the usage** — `--output-format json` returns usage/cost fields per run; log them
  in scripts to track spend.
- **Avoid redundant turns** — resume an existing session (`--resume`) instead of
  re-establishing context from scratch when continuing related work.

## References

Advanced depth lives in these files (created in Slice 2):

- [advanced-cli-flags.md](references/advanced-cli-flags.md) — full flag catalog,
  `--output-format` shapes, streaming events.
- [hook-examples.md](references/hook-examples.md) — PreToolUse/PostToolUse and other hook
  patterns for enforcement and automation.
- [agent-team-orchestration.md](references/agent-team-orchestration.md) — multi-agent
  fan-out, coordination, and worked orchestration patterns.
- [permission-rule-patterns.md](references/permission-rule-patterns.md) — allow/deny rule
  syntax and worked permission rule sets.
