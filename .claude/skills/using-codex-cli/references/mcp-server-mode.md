# Codex as an MCP server (multi-agent orchestration)

Codex can run **as an MCP (Model Context Protocol) server**, typically launched as
`codex mcp` (confirm the exact subcommand with `codex --help`). In this mode an outer
**orchestrator** agent — itself an MCP client — drives one or more Codex sessions by
calling Codex's exposed tools. This is how you build multi-agent setups where a planner
delegates isolated coding work to Codex workers.

> This is the inverse of Codex calling *other* MCP servers (configured via
> `[mcp_servers.*]` in `config.toml`, see `config-reference.md`). Here Codex *is* the
> server being called.

## Table of contents

- [Exposed tools](#exposed-tools)
- [Example 1: single delegated task](#example-1-single-delegated-task)
- [Example 2: continue a session with codex-reply](#example-2-continue-a-session-with-codex-reply)
- [Example 3: parallel agents in worktrees](#example-3-parallel-agents-in-worktrees)
- [Discipline: when to spawn a subagent](#discipline-when-to-spawn-a-subagent)

## Exposed tools

Codex-as-server exposes two primary tools:

**`codex`** — start a new Codex session.

```jsonc
{
  "name": "codex",
  "arguments": {
    "prompt": "string — the task for this session",
    "cwd": "string — working directory the session operates in",
    "approval-policy": "suggest | auto-edit | full-auto (optional)",
    "sandbox": "read-only | workspace-write | danger-full-access (optional)"
  }
}
// → returns a result that includes a sessionId (conversation id) to continue later
```

**`codex-reply`** — continue an existing session by id.

```jsonc
{
  "name": "codex-reply",
  "arguments": {
    "sessionId": "string — the id returned by a prior codex call",
    "prompt": "string — the next instruction in that session"
  }
}
```

Exact argument names/casing can shift between releases — inspect the server's advertised
tool schema (the MCP `tools/list` response) rather than assuming.

## Example 1: single delegated task

```
orchestrator
  └─ calls codex(prompt="implement the parser in src/parse.py and add tests",
                 cwd="/repo", sandbox="workspace-write", approval-policy="full-auto")
        → { sessionId: "S1", result: "...created src/parse.py, tests pass..." }
```

The orchestrator hands off a self-contained task and receives the outcome plus a
`sessionId` it can reuse.

## Example 2: continue a session with codex-reply

```
orchestrator
  ├─ codex(prompt="scaffold a FastAPI app in app/", cwd="/repo")        → sessionId S2
  └─ codex-reply(sessionId="S2", prompt="now add a /health endpoint and a test")
        → continues S2 with full prior context, edits app/ further
```

Reusing the session preserves the agent's context, so follow-ups don't re-explain the
codebase.

## Example 3: parallel agents in worktrees

Run independent Codex workers concurrently, each in **its own git worktree**, so their
file edits never collide:

```bash
git worktree add ../wt-auth   feature/auth
git worktree add ../wt-search feature/search
```

```
orchestrator
  ├─ codex(prompt="build login/logout", cwd="../wt-auth",   sandbox="workspace-write") → S-A
  └─ codex(prompt="build full-text search", cwd="../wt-search", sandbox="workspace-write") → S-B
# S-A and S-B run in isolation; merge each branch when its tests pass.
```

Worktrees give each agent a private checkout sharing one object store — the standard way
to parallelize agents without write contention.

## Discipline: when to spawn a subagent

Delegating to a Codex subagent costs a context window, a session, and coordination
overhead. Spawn one **only when the task genuinely benefits from isolation or
parallelism** — a large, self-contained unit of work, or several units that can run at
once. For anything the main agent can do directly in a few steps, do it directly. Prefer
subagents *when requested* or when the workload is clearly partitionable; don't reflexively
fan out, because more agents means more state to reconcile and more ways to drift.
