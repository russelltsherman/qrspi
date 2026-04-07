# Project: qrspi

## QRSPI Workflow

This project uses the QRSPI structured workflow for feature development.
Artifacts are stored in `.qrspi/<ticket-id>/`.

### Available skills (invoke with / or let Claude auto-invoke)
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket
- `/qrspi-research <ticket-id>` — Map the codebase (ticket is hidden)
- `/qrspi-design <ticket-id>` — Produce a design document
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

### Codebase conventions
- Agent prompt definitions live in `.qrspi/agents/`
- Artifact templates live in `.qrspi/templates/`
- Eval harness lives in `evals/` and `scripts/`
