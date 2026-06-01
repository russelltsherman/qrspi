# Project: qrspi

## QRSPI Workflow

This project uses the QRSPI structured workflow for feature development.
Tickets are created as Linear issues (team: Russelltsherman, project: QRSPI).
Ticket IDs follow Linear's format (e.g., RUS-42). Artifacts are stored locally
in `.qrspi/<ticket-id>/` — not uploaded as attachments.

### Lifecycle — PR-gated

**PR review state — not Linear status — is the authority for advancement.** Linear has
exactly two roles: an **entry gate** (a ticket may only begin if it is *assigned* and in
`Selected`) and a **best-effort reporting projection** (agents update status to reflect the
active phase; a failed Linear write never blocks work). See
`docs/qrspi-pr-gated-lifecycle-design.md` for the full design.

Each ticket is one Graphite stack, built bottom-up and **held open** until the whole feature
is approved, then landed bottom-up:

```
Selected (assigned)
  → design PR   [Questions·Research·Design]   ──approved──┐
  → plan PR     [Structure·Plan·WorkTree]      (stacked)  ──approved──┐
  → slice PRs   [Implementation]               (stacked)   ──all approved──→ land stack → Done
```

- **Branches:** `<id>/design` → `<id>/plan` → `<id>/slice-1..N`, each its own PR, stacked.
  (Replaces the old single `<id>/planning` branch.)
- **Advance** is automatic: approving a phase PR (`reviewDecision == APPROVED` **and** zero
  unresolved review threads) builds the next phase on top.
- **Reset** is automatic: a formal `CHANGES_REQUESTED` on an upstream phase PR discards every
  downstream phase (PRs closed, branches deleted, stale artifacts removed) and returns the
  ticket to that phase. **Revise** (addressing review comments) is *manual* — only on an
  explicit invocation.
- **`*Approved` Linear states were dropped** — approval lives in the PR. Reporting statuses:
  `Selected` → `Design Review` → `Plan Review` → `Code Review` → `Done`.
- The decision is computed by a tested resolver (`scripts/qrspi_resolve_state.py`, unit-tested);
  the orchestrator and batch both call it rather than re-deriving state logic.
- The `qrspi-batch` workflow drives the autonomously-runnable actions across assigned tickets
  (run_design, advance, submit, land, automatic reset); it skips `wait` and the manual `revise`.

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

- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
- The batch orchestrator workflow lives in `.claude/workflows/qrspi-batch.js`
- The PR-gated decision logic lives in `scripts/qrspi_resolve_state.py` (the tested resolver)
  and `scripts/qrspi_pr_state.py` (gathers PR review state via gh GraphQL). Both have
  stdlib-only unit tests as `_test.py` siblings (`scripts/qrspi_*_test.py`, run with `python3`).
- Artifact templates live in `.qrspi/templates/` (reference only — not written locally)
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
