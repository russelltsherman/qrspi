# Agent team orchestration

> **Provenance.** Everything here is **[CLI-spec]** — synthesized from the Claude Code
> CLI specification and **not** verified against this repository. Agent-team features are
> **experimental** and the flags/behaviors below may change; confirm against your
> installed version before relying on them. (The one **[in-project]** orchestration
> pattern in this repo is the QRSPI worktree-per-ticket flow, noted below.)

The SKILL.md body covers single subagents. This file covers fan-out across many agents,
parallel branches via worktrees, background agents, and how teammates coordinate.

## Subagents recap [CLI-spec]

A subagent is a fresh-context Claude instance the orchestrator delegates to: its own
context window, its own allowed-tools scope, its own system prompt. It receives a scoped
prompt and returns a single result string. Delegating isolates a task and keeps the
parent context clean — the core reason to fan out.

## Agent teams (experimental) [CLI-spec]

An **agent team** is multiple subagents working under one orchestrator, each owning a
slice of the work:

- The orchestrator decomposes the goal into independent units and assigns one per
  teammate.
- Each teammate runs in isolation and reports back a result; the orchestrator integrates.
- Because each teammate has a separate context, total useful context scales with the team
  rather than being bottlenecked on one window.

Best when the units are **genuinely independent** (no shared mutable state mid-flight). If
units must edit the same files in sequence, prefer sequential subagents — concurrent edits
to one file are a merge hazard.

## Git worktrees for parallel branches [CLI-spec] / [in-project]

The clean way to parallelize agents that each modify code is to give each its **own git
worktree** on its **own branch**, so concurrent file edits never collide:

```bash
git worktree add ../wt-feature-a feature-a
git worktree add ../wt-feature-b feature-b
# launch one agent per worktree (e.g. headless, backgrounded):
( cd ../wt-feature-a && claude -p "Implement feature A per spec." ) &
( cd ../wt-feature-b && claude -p "Implement feature B per spec." ) &
wait
```

This is exactly the pattern this repo uses **[in-project]**: each QRSPI ticket gets an
isolated worktree at `.worktrees/<ticket-id>/` while `main` stays clean, so multiple
ticket agents run concurrently without stepping on each other. The general lesson: one
worktree + one branch per parallel agent.

## Background agents [CLI-spec]

A long-running unit can be launched detached so the orchestrator continues immediately,
then rejoined later:

```bash
SID="$(uuidgen)"
claude -p "Run the full test suite and summarize failures." \
  --session-id "$SID" --output-format json > /tmp/agent-a.json &
# ... orchestrator does other work ...
wait
jq -r '.result' /tmp/agent-a.json
```

Capture the `--session-id` so you can `--resume <id>` to ask the same agent a follow-up
with its full context intact (see [advanced-cli-flags.md](advanced-cli-flags.md) for the
session/JSON flags).

## Teammate communication [CLI-spec]

Coordination is **through artifacts and structured results**, not shared memory:

- **Scoped prompt in, single result string out.** Pass each teammate everything it needs
  up front; treat its returned string as the integration point.
- **Files as the shared bus.** Teammates that must hand off work write to agreed paths
  (a log, a staging file, a branch) and the orchestrator reads them — exactly like QRSPI's
  staged-artifact + deterministic-move persistence **[in-project]**.
- **Keep contexts disjoint.** Do not assume one teammate can see another's conversation;
  if B needs A's output, the orchestrator must pass it explicitly.
- **Integrate sequentially.** Fan out independent work in parallel, but fold results back
  one at a time to keep merges and reasoning deterministic.

## Choosing a topology [CLI-spec]

| Situation | Use |
|-----------|-----|
| One noisy/large task to wall off | Single subagent |
| Several independent, read-mostly tasks | Agent team (parallel subagents) |
| Several tasks that each edit code | One git worktree + branch per agent |
| A long task you want to background | Background agent (capture session id) |
| Tasks with sequential dependencies | Sequential subagents, integrate one at a time |

See also: [permission-rule-patterns.md](permission-rule-patterns.md) to scope what each
teammate may do, and [hook-examples.md](hook-examples.md) to enforce checks uniformly
across a team.
