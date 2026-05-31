# Project: qrspi

## QRSPI Workflow

This project uses the QRSPI structured workflow for feature development.
Tickets are created as Linear issues (team: Russelltsherman, project: QRSPI).
Ticket IDs follow Linear's format (e.g., RUS-42). Artifacts are stored locally
in `.qrspi/<ticket-id>/`. Linear is used for status tracking and phase-transition
comments only — artifacts are not uploaded as attachments.

### Lifecycle and review gates

Planning is split into two halves, each ending at a human review gate. The Linear
status is the authoritative state machine:

```
Selected → [Questions·Research·Design] → Design Review → Design Approved
  → [Structure·Plan·WorkTree] → Plan Review → Plan Approved
  → [Implementation] → Code Review → Code Approved → Done
```

- **Design Review** and **Design Approved** are review-gate statuses for the design
  half; **Plan Review** and **Plan Approved** for the plan half. Both review statuses
  are human turns — the orchestrator waits (or addresses PR feedback) and never advances
  autonomously past them.
- All six planning artifacts live on one `<ticket-id>/planning` branch as a single
  amended commit. The PR is submitted at Design Review and re-submitted (grown with the
  plan-half artifacts) at Plan Review.
- The `qrspi-batch` workflow only drives the autonomously-runnable statuses
  (`Selected`, `Design Approved`, `Plan Approved`); it does not touch the review gates.

### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-ticket <initial description>` — Create a Linear issue through guided conversation
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket (fetched from Linear)
- `/qrspi-research <ticket-id>` — Map the codebase (ticket is hidden from this phase)
- `/qrspi-design <ticket-id>` — Produce a design document (ticket fetched from Linear)
- `/qrspi-structure <ticket-id>` — Define vertical slices and contracts
- `/qrspi-plan <ticket-id>` — Write tactical implementation steps
- `/qrspi-worktree <ticket-id>` — Build a session-aware task DAG
- `/qrspi-implement <ticket-id> <slice-number>` — Implement one vertical slice
- `/qrspi-pr <ticket-id>` — Prepare pull request summary

### Workflow rules

- Phases run sequentially. Never skip ahead.
- Each artifact must exist and be reviewed before the next phase starts.
- Start a fresh `/clear` session between implementation slices.
- Use `/compact` if context grows large within a phase.
- Use `/context` to check utilization. If over 40%, compact or start fresh.

### Worktrees

Each ticket gets an isolated git worktree at `.worktrees/<ticket-id>/`. This allows
multiple agents to work on different tickets concurrently. The main repo checkout
stays on `main`; all ticket work happens in worktrees. `.worktrees/` is gitignored.

### Codebase conventions

- Agent prompt definitions live in `.qrspi/agents/`
- Artifact templates live in `.qrspi/templates/` (reference only — not written locally)
- Eval harness lives in `evals/` and `scripts/`
