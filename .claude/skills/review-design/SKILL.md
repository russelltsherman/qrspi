---
name: review-design
description: On-demand advisory review of a QRSPI ticket's DESIGN artifact. Run the full read-only design review panel (node-validity + edge lenses) over design.md against the real codebase, partition decision-readiness out as terminal-advisory, then post one axis-enumerated advisory synopsis comment to the design PR and append a ledger row — WITHOUT mutating the PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's design (e.g. "/review-design RUS-89", "review the design for RUS-42", "is the design for RUS-50 sound?", "run the design panel on RUS-7"). This is the design-phase entry of the /review-* family; for the plan use /review-plan, for code use /review-implementation.
allowed-tools: Workflow
---

# /review-design

Run an **advisory, propose-only** review of a ticket's design artifact and post a synopsis to its design PR. This is the design-phase member of the `/review-*` family.

This command is a **thin wrapper** over the deterministic review engine (`.claude/workflows/qrspi-review.js`). The engine owns the whole run — resolving the worktree + design PR, scratch-copying `design.md`, fanning out the design review panel **once** (round 0, no revise loop) against the real codebase, running the terminal-advisory decision-readiness lens, posting the axis-enumerated advisory synopsis comment to the design PR, and appending the ledger row — all while holding the PR head SHA **unchanged** (propose-only: it issues no `gt`/`gh` branch-mutating command, only the one PR comment + the ledger append).

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## What to do

Invoke the review engine for the **design** phase, passing the ticket id:

```
Workflow({ name: "qrspi-review", args: { ticket: "<ticket-id>", phase: "design" } })
```

The engine returns `{ ok, ticket, phase, pr, terminalAction, shaUnchanged, summary }` (or `{ ok:false, error }` on a missing design phase/PR, a resolve error, or a propose-only violation). Report its `summary` to the user: the synopsis comment was posted to the design PR, a `mode:"on-demand-review"` ledger row was appended, and the branch is untouched. On `ok:false`, surface the `error` verbatim and stop — do not fabricate a PR or a verdict.

## Notes

- **Advisory only.** This command does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
- **Propose-only.** The engine never mutates the design PR branch; it captures the PR head SHA before the panel and re-asserts it unchanged at the end. The only GitHub write is the single advisory PR comment.
- **Single round.** The engine runs the panel exactly once (terminal action `converged` when the round-0 panel passes, else `exhausted`); there is no revise loop and no agreement line.
- The node-validity `design-review` lens carries the configured model override (`critics.review.lensModel`, when set) and stays research+code-only; decision-readiness is terminal-advisory (it feeds the synopsis, never a loop). The engine's header documents the full contract.
