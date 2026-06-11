# Questions — Resolver mis-classifies partially-landed stacks as entry_blocked, stranding tickets

**Ticket:** RUS-69
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What stack information (branches, PRs, merge states, ticket assignment/status) does the resolver receive as input, and in what shape is it structured?
  **Target:** scripts/qrspi_resolve_state.py and scripts/qrspi_pr_state.py
- Q2: How does the gather step represent a PR that has already merged versus one still open, and does that representation distinguish merged-lower PRs from open-upper slice PRs?
  **Target:** scripts/qrspi_pr_state.py (the module that gathers PR review state via gh GraphQL)
- Q3: How does the one-shot orchestrator (qrspi_resolve.py) detect existing branches/artifacts and pass that detection into the resolver's decision?
  **Target:** scripts/qrspi_resolve.py

## API Surface

- Q4: What is the set of action/state values the resolver can return (e.g., entry_blocked, advance, submit, land, wait, reset, revise), and what is the signature of the function that produces them?
  **Target:** scripts/qrspi_resolve_state.py
- Q5: Which return value corresponds to "finish landing the remaining slices", and what inputs currently cause the resolver to emit it?
  **Target:** scripts/qrspi_resolve_state.py (the land-action branch)

## State Management

- Q6: What condition produces the "No design branch and ticket is not assigned+Selected; nothing begins" entry_blocked reason, and which input fields are checked to reach it?
  **Target:** scripts/qrspi_resolve_state.py (the entry-gate branch)
- Q7: How does the resolver determine whether a ticket has "started", and does that determination depend on the design branch/PR still being open rather than merged?
  **Target:** scripts/qrspi_resolve_state.py
- Q8: How does the batch orchestrator consume the resolver's returned action, and which actions does it treat as terminal skips versus actionable?
  **Target:** .claude/workflows/qrspi-batch.js

## Edge Cases

- Q9: How does the resolver behave when the design and plan PRs are merged but one or more slice PRs remain open and approved — what action does it currently return for that stack shape?
  **Target:** scripts/qrspi_resolve_state.py
- Q10: How does the resolver distinguish a genuinely un-started ticket (not assigned, not Selected, zero merged PRs) from a partially-landed in-flight ticket (some merged PRs, open upper slices)?
  **Target:** scripts/qrspi_resolve_state.py (the entry-gate branch)
- Q11: How does the resolver handle a stack mid-merge where only some lower PRs are merged and the design branch no longer exists locally/remotely?
  **Target:** scripts/qrspi_resolve_state.py and scripts/qrspi_pr_state.py

## Testing

- Q12: What existing resolver unit tests cover stack shapes, and is there any test fixture representing merged-lower / open-upper PRs?
  **Target:** scripts/qrspi_resolve_state_test.py
- Q13: How do existing resolver tests construct PR-state input fixtures (merged vs open, approved vs not), and what helper or data structure builds them?
  **Target:** scripts/qrspi_resolve_state_test.py

## Observability

- Q14: What diagnostic reason strings does the resolver attach to each returned action, and how are entry_blocked reasons surfaced in the batch run output?
  **Target:** scripts/qrspi_resolve_state.py and .claude/workflows/qrspi-batch.js
