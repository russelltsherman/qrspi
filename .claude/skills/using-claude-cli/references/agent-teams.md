**Experimental:** Agent Teams require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to be set in the environment.

Multi-agent orchestration lets a parent CLI session delegate to multiple
sub-agents that work in parallel or sequence. This reference covers the
patterns, configurations, and operational details.

## Orchestration Patterns

### Team Pattern

Define a named team of agents, each with a role and area of responsibility:

```bash
claude --agent-team team.yaml -p "analyze the test failures and propose fixes"
```

Team config (`team.yaml`):

```yaml
team: test-fixers
agents:
  - name: analyzer
    type: Explore
    role: "Find the root cause of test failures"
  - name: fixer
    type: General-purpose
    role: "Implement fixes for identified issues"
  - name: reviewer
    type: General-purpose
    role: "Review proposed changes for correctness"
```

Agents in a team share the parent's context window but can run
concurrently on different tasks.

### Task List Pattern

Assign a sequence of tasks to agents. The CLI dispatches each task in
order, using output from the previous task as context:

```bash
claude --agent-team tasks.yaml -p "complete the defined tasks in sequence"
```

Task config (`tasks.yaml`):

```yaml
tasks:
  - agent: analyzer
    prompt: "Run tests and capture failure output"
  - agent: fixer
    prompt: "Fix the failures identified in the previous step"
  - agent: reviewer
    prompt: "Verify fixes don't introduce regressions"
```

### Parallel Worktree Pattern

Each agent in a team can operate on its own git worktree, enabling
truly parallel development:

```bash
claude --agent-team parallel.yaml -p "work on all slices in parallel"
```

Config with worktree isolation:

```yaml
team: parallel-dev
worktree_isolation: true
agents:
  - name: slice-1
    type: General-purpose
    worktree: .worktrees/slice-1
    role: "Implement auth module"
  - name: slice-2
    type: General-purpose
    worktree: .worktrees/slice-2
    role: "Implement API endpoints"
```

Worktree isolation ensures agents do not conflict on the same files.
Each agent operates in its own branch and directory.

## Inter-Agent Coordination

Agents coordinate through shared artifacts rather than direct messaging:

| Mechanism | Description |
|-----------|-------------|
| Shared filesystem | Agents read/write to common directories |
| Worktree branches | Agents publish changes to named branches |
| Shared prompt context | Later agents inherit summaries from earlier agents |
| Task output files | Agents write structured output for downstream consumers |

### Summary Pass Pattern

A coordinator agent runs after all other agents complete, reviewing
their work and producing a unified report:

```yaml
agents:
  - name: builder
    type: General-purpose
    prompt: "Implement the feature in src/"
  - name: tester
    type: Explore
    prompt: "Run tests and report failures"
  - name: coordinator
    type: Plan
    prompt: "Review builder and tester output, write summary"
```

## Background Agent Patterns

Agents can run in the background while the parent CLI session continues:

```bash
claude --spawn-agent background-resolver -- bg
```

Background agent characteristics:
- Runs asynchronously relative to the parent session.
- Writes output to a log file for later review.
- Does not block the parent session's prompt.
- Useful for long-running tasks (e.g., large refactors, test suites).

## Runtime Requirements

| Requirement | Version |
|-------------|---------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Must be set to `1` |
| Git | Required for worktree isolation |
| `team.yaml` or `tasks.yaml` | Required for team/task configuration |

## Limitations and Caveats

- **Experimental status:** Agent Teams may change or be removed without
  notice. Do not depend on this feature for production-critical
  workflows.
- **Context window:** All agents in a team share the parent's context
  window budget. Large teams may exhaust the window quickly.
- **Cost:** Each agent turn incurs separate API charges. Budget flags
  (`--max-budget-usd`, `--max-turns`) apply to the total across all
  agents in the team.
- **Worktree conflicts:** When `worktree_isolation` is false, agents
  may overwrite each other's changes. Always enable worktree isolation
  for parallel agents working on the same codebase.
