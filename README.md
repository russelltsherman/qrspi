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

**`/qrspi-feature <description>`** is the front door for any new feature. It elicits requirements, then proposes a *reviewed* decomposition — one ticket vs several, a dependency DAG, and an overlap scan against in-flight tickets — and **stops for your approval before any Linear write**, so a multi-ticket split is never an unreviewed side effect. On approval it creates the ticket(s) through the shared writer, setting `blockedBy` edges and a Linear parent issue. The bias is hard toward one ticket with slices. (For a single, already-scoped ticket you want filed directly, **`/qrspi-ticket <description>`** is the direct entry — it runs the same guided interview and the same writer, without the decomposition step.)

**`/qrspi-work <ticket-id>`** is the autonomous orchestrator. It reads the ticket's **PR review state** (not Linear status), determines the current phase, and executes the appropriate action — design, plan, implementation, advance, revise, reset, or land — without manual phase-by-phase invocation. Use this to drive a ticket from `Selected` through to a landed stack.

```
# Start a new feature (decompose + review gate + create tickets)
/qrspi-feature Add webhook support for deployment notifications

# After the ticket(s) are created (e.g., RUS-42), drive forward
/qrspi-work RUS-42
```

### Batch orchestration

Where `/qrspi-work` drives **one** ticket, the **`qrspi-batch`** workflow drives **every** assigned, in-flight ticket one PR-gated step forward in a single pass. It is a [Workflow](https://docs.claude.com/) script (`.claude/workflows/qrspi-batch.js`), not a slash command — run it via the `qrspi-batch` skill or the Workflow tool. Use it after assigning a batch of tickets to `Selected`, or after approving phase PRs, to fan the whole queue forward at once.

It does **not** re-derive any decision logic: per ticket it runs the same tested resolver (`scripts/qrspi_resolve_state.py`) that `/qrspi-work` uses, then branches on the resulting action. The pass runs these phases:

| Phase | What it does |
|-------|--------------|
| **Query** | List assigned `Selected` + in-flight (`Design Review`/`Plan Review`/`Code Review`) tickets, scoped to the mapped Linear project (`input.allProjects` > `input.project` > config `linearProject` > `QRSPI`). |
| **Resolve** | Per ticket: set up the worktree, gather PR review state, run the resolver → a decision. |
| **Restack** | Per ticket: restack onto current trunk so drift/conflicts surface early. |
| **Design / Plan / Implementation** | Spawn the typed phase agents for `run_design`, `advance → plan`, and `advance → implementation`. |
| **Finalize** | Commit / submit / reset / land + best-effort Linear projection. |
| **Reconcile** | Opt-in: reap stranded already-merged worktrees via `qrspi_cleanup.py` (dry-run by default). |

**One autonomous step per ticket per run.** Each step lands the ticket in a review-wait state, so the batch is meant to be re-run after each round of human review. The autonomously-runnable actions are: `run_design`, `advance` (plan / implementation), `submit`, `land`, automatic `reset`/discard of downstream phases, and `revise` — addressing a frontier PR carrying a formal `CHANGES_REQUESTED` and/or unaddressed reviewer comments in place, then re-requesting review (which flips `reviewDecision` back to `REVIEW_REQUIRED` — the loop-safe termination signal). It **skips** anything resolving to `wait`: a PR awaiting first review, or one whose only outstanding signal is unresolved review *threads* (only the reviewer can resolve a thread). Tickets blocked by an open Linear blocker are reported `entry_blocked` and held.

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
    qrspi-feature/     # Front door — elicit, decompose, review gate, file ticket(s)
    qrspi-work/        # Autonomous orchestrator (PR-gated state machine)
  workflows/
    qrspi-batch.js     # Batch orchestrator — drives many tickets one PR-gated step forward
scripts/                       # Deterministic helpers (stdlib-only; each has a _test.py sibling)
  qrspi_resolve_state.py       # Tested PR-gated decision logic (the resolver)
  qrspi_pr_state.py            # Gathers PR review state (gh GraphQL reviewThreads)
  qrspi_resolve.py             # One-shot: worktree + gather + decision + artifact detection
  qrspi_persist.py             # Verifies a staged artifact and moves it to the canonical path
  qrspi_pr_body.py             # Splices pr-summary.md into the slice-1 commit message
  qrspi_revise_amend.py        # Stages + verifies a revise edit, then amends the phase commit
  qrspi_restack.py             # Restacks a ticket's stack onto current trunk
  qrspi_cleanup.py             # Reaps stranded already-merged worktrees/branches
  qrspi_comment_reply.py       # Posts in-thread replies to reviewer comments
  qrspi_config.py              # Reads .qrspi/config.json (reviewers, Linear team/project)
  ...                          # plus *_test.py siblings and the evals/ placeholder harness
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

**Human review at every gate.** Artifacts are drafted, not shipped. Each phase becomes its own pull request — design, plan, and implementation — and advancement is gated on that PR being approved with no unresolved review threads. `/qrspi-work` automates execution and auto-advances on approval, but a human approving (or requesting changes on) each PR is the checkpoint. A change request on an upstream phase discards and regenerates the downstream work.

**Worktree isolation.** Each ticket gets its own git worktree at `.worktrees/<ticket-id>/`. Multiple agents can work on different tickets concurrently without branch checkout conflicts.

## Linear Integration

Tickets are created and tracked as Linear issues. The Linear team and project are
config-driven, not hard-coded: `.qrspi/config.json` (gitignored; see `.qrspi/config.example.json`)
supplies `linearTeam` (the skill discovers/asks if unset) and `linearProject` (defaults to `QRSPI`).
`linearProject` scopes both ticket creation and which tickets `qrspi-batch` sweeps.
**Linear does not gate advancement — PR review state does.** Linear has two roles only:

1. **Entry gate.** A ticket may only *begin* if it is assigned to a user and in the `Selected`
   status. Nothing starts otherwise.
2. **Reporting projection.** Once work starts, agents update the Linear status to reflect the
   active phase (`Design Review` → `Plan Review` → `Code Review` → `Done`). These writes are
   best-effort — a failed Linear update never blocks git/PR work. The `*Approved` statuses were
   removed; approval lives in the PR.

What is "ready to advance" is decided wholly by PR status: `reviewDecision == APPROVED` **and**
zero unresolved review threads. Each phase is its own stacked PR (`<id>/design` → `<id>/plan` →
`<id>/slice-N`), held open until the whole feature is approved, then landed bottom-up.

| PR-state action | What `/qrspi-work` does |
|-----------------|--------------------------|
| `run_design` | Entry gate satisfied; build the design PR (questions, research, design) |
| `advance` → plan | Design PR approved; build the plan PR (structure, plan, work tree) stacked on it |
| `advance` → implementation | Plan PR approved; build the slice PR stack |
| `wait` | Active phase PR awaiting review, or whose only signal is unresolved review threads — nothing to do until the reviewer acts (threads can only be resolved by the reviewer) |
| `revise` | Frontier phase PR carrying a formal change request and/or unaddressed reviewer comments — addressed in place, then review is re-requested (automatic) |
| `reset` | Upstream PR change-requested — discard downstream phases, return to it (automatic) |
| `land` | Every PR approved + clean — merge the whole stack bottom-up, then `Done` |

The decision is computed by the tested resolver in `scripts/qrspi_resolve_state.py`. See
`docs/qrspi-pr-gated-lifecycle-design.md` for the full design and rationale.

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- [Graphite CLI](https://graphite.dev) (`gt`) for stacked PRs
- [GitHub CLI](https://cli.github.com) (`gh`) for PR operations
- Linear MCP server configured for the Russelltsherman workspace
