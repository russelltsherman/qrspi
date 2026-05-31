# QRSPI

A structured workflow for agentic feature development using Claude Code. QRSPI decomposes feature work into sequential phases — each producing a reviewable artifact — so that AI agents plan thoroughly before writing code and humans retain control at every decision point.

## Inspiration

This project was inspired by [Dex Horthy's talk](https://www.youtube.com/watch?v=YwZR6tc7qYg) on structured approaches to agentic software development.

## Why

LLMs are capable implementers but poor planners when given unbounded scope. They skip ahead, conflate problem definition with solution design, and lose coherence on large tasks. QRSPI constrains each phase to a specific job: the ticket defines the problem, questions probe the codebase, research gathers facts, design makes decisions, and implementation follows the plan. No phase sees more context than it needs.

## Workflow Phases

```
Ticket  -->  Questions  -->  Research  -->  Design  -->  Structure  -->  Plan  -->  Worktree  -->  Implement  -->  PR
  T             Q              R             D             S              P           W              I
```

| Phase | Artifact | What it does |
|-------|----------|--------------|
| **Ticket** | Linear issue | Defines the problem, goals, and acceptance criteria. No solutions. |
| **Questions** | `questions.md` | Generates 8-15 targeted technical questions from the ticket. |
| **Research** | `research.md` | Answers questions by reading the codebase. Ticket is hidden to prevent anchoring. |
| **Design** | `design.md` | Combines ticket + research into pattern decisions, risk register, and delta. |
| **Structure** | `structure.md` | Defines vertical slices, types, and cross-slice contracts. |
| **Plan** | `plan.md` | Atomic implementation steps per slice with verification checkpoints. |
| **Worktree** | `worktree.md` | Session-aware task DAG with context budgets per session. |
| **Implement** | Code + `impl-log.md` | Implements one slice per session within a git worktree. |
| **PR** | `pr-summary.md` | Maps acceptance criteria to implementation and tests. |

Phases run sequentially. Each artifact must be reviewed before the next phase starts.

## Usage

### Primary skills

Most workflows require only two commands:

**`/qrspi-ticket <description>`** creates a new feature ticket through guided conversation. It gathers problem context, drafts a structured Linear issue, and sets up the local artifact directory. This is the starting point for any new feature.

**`/qrspi-work <ticket-id>`** is the autonomous orchestrator. It reads the ticket's Linear status, determines the current phase, and executes the appropriate action — planning, implementation, or review response — without manual phase-by-phase invocation. Use this to drive a ticket from backlog through to PR.

```
# Start a new feature
/qrspi-ticket Add webhook support for deployment notifications

# After the ticket is created (e.g., RUS-42), drive it forward
/qrspi-work RUS-42
```

### Individual phase skills

Each phase has a standalone skill that can be invoked manually. These exist primarily for the orchestrator's internal use, but are available when you need to re-run a specific phase or work step-by-step:

| Skill | Command |
|-------|---------|
| Questions | `/qrspi-questions <ticket-id>` |
| Research | `/qrspi-research <ticket-id>` |
| Design | `/qrspi-design <ticket-id>` |
| Structure | `/qrspi-structure <ticket-id>` |
| Plan | `/qrspi-plan <ticket-id>` |
| Worktree | `/qrspi-worktree <ticket-id>` |
| Implement | `/qrspi-implement <ticket-id> <slice-number>` |
| PR | `/qrspi-pr <ticket-id>` |

### Context management

- Start a fresh `/clear` session between implementation slices.
- Use `/compact` if context grows large within a phase.
- Use `/context` to check utilization. If over 40%, compact or start fresh.

## Project Structure

```
.claude/
  agents/              # Phase agent definitions — the actual phase logic the orchestrator spawns
    qrspi-questions.md
    qrspi-research.md
    qrspi-design.md
    qrspi-structure.md
    qrspi-plan.md
    qrspi-worktree.md
    qrspi-implement.md
    qrspi-pr.md
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/
    qrspi-questions/
    qrspi-research/
    qrspi-design/
    qrspi-structure/
    qrspi-plan/
    qrspi-worktree/
    qrspi-implement/
    qrspi-pr/
    qrspi-work/        # Autonomous orchestrator (Linear-status state machine)
  workflows/
    qrspi-batch.js     # Batch orchestrator — drives many tickets through the autonomous states
.qrspi/
  templates/           # Canonical output formats (single source of truth)
    ticket.md
    questions.md
    research.md
    design.md
    structure.md
    plan.md
    worktree.md
    impl-log.md
    pr-summary.md
    revision-log.md
  <ticket-id>/         # Per-ticket artifacts (created at runtime)
.worktrees/            # Isolated git worktrees per ticket (gitignored)
.devcontainer/         # Container sandbox for CI
docs/                  # Guides and reference documentation
```

## Design Principles

**Phase isolation.** Each phase sees only the artifacts it needs. Research never sees the ticket. Implementation sees only its slice of the plan. This prevents context contamination and anchoring bias.

**Templates as single source of truth.** Output formats live in `.qrspi/templates/`. Skills reference templates rather than embedding formats inline. Change the template, change every phase that uses it.

**Vertical slices over horizontal layers.** Structure decomposes work into end-to-end testable paths, not "all database changes" then "all API changes." Each slice delivers something verifiable.

**Human review at every gate.** Artifacts are drafted, not shipped. Planning stops at two review gates — Design Review (after the design half) and Plan Review (after the plan half) — before implementation. `/qrspi-work` automates execution within a stage, but Linear status transitions signal the human checkpoints.

**Worktree isolation.** Each ticket gets its own git worktree at `.worktrees/<ticket-id>/`. Multiple agents can work on different tickets concurrently without branch checkout conflicts.

## Linear Integration

Tickets are created and tracked as Linear issues in the Russelltsherman team, QRSPI project. Linear statuses drive the `/qrspi-work` state machine. Planning is split into a **design half** (questions, research, design) and a **plan half** (structure, plan, work tree), separated by two human review gates:

| Linear Status | Action |
|---------------|--------|
| Backlog / Selected | Run the design half (questions, research, design); submit planning PR |
| Design Review | Address review feedback on the design-half artifacts (gate) |
| Design Approved | Run the plan half (structure, plan, work tree); update the planning PR |
| Plan Review | Address review feedback on the plan-half artifacts (gate) |
| Plan Approved | Implement all slices, submit stacked PRs |
| Code Review | Address review feedback on implementation |
| Code Approved | Report ready to merge (human-owned) |
| Done | Clean up artifacts and worktree |

All six planning artifacts live on one `<ticket-id>/planning` branch as a single amended commit; the planning PR is submitted at Design Review and re-submitted (grown with the plan-half artifacts) at Plan Review.

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- [Graphite CLI](https://graphite.dev) (`gt`) for stacked PRs
- [GitHub CLI](https://cli.github.com) (`gh`) for PR operations
- Linear MCP server configured for the Russelltsherman workspace
