---
name: review-plan
description: On-demand advisory review of a QRSPI ticket's PLAN artifact. Run the full read-only plan review panel (node-validity + fidelity + completeness lenses) over plan.md against the real codebase, then post one axis-enumerated advisory synopsis comment to the plan PR and append a ledger row — WITHOUT mutating the PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's plan (e.g. "/review-plan RUS-89", "review the plan for RUS-42", "is the plan for RUS-50 sound?", "run the plan panel on RUS-7"). This is the plan-phase entry of the /review-* family; for the design use /review-design, for code use /review-implementation.
allowed-tools: Workflow
---

# /review-plan

Run an **advisory, propose-only** review of a ticket's plan artifact and post a synopsis to its plan PR. This is the plan-phase member of the `/review-*` family.

This command is a **thin wrapper** over the deterministic review engine (`.claude/workflows/qrspi-review.js`). The engine owns the whole run — resolving the worktree + plan PR, scratch-copying `plan.md`, fanning out the plan review panel **once** (round 0, no revise loop) against the real codebase, posting the axis-enumerated advisory synopsis comment to the plan PR, and appending the ledger row — all while holding the PR head SHA **unchanged** (propose-only: it issues no `gt`/`gh` branch-mutating command, only the one PR comment + the ledger append). There is **no** decision-readiness lens for the plan phase — that lens is design-phase-only.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## What to do

Invoke the review engine for the **plan** phase, passing the ticket id:

```
Workflow({ name: "qrspi-review", args: { ticket: "<ticket-id>", phase: "plan" } })
```

The engine returns `{ ok, ticket, phase, pr, terminalAction, shaUnchanged, summary }` (or `{ ok:false, error }` on a missing plan phase/PR, a resolve error, or a propose-only violation). Report its `summary` to the user: the synopsis comment was posted to the plan PR, a `mode:"on-demand-review"` ledger row was appended, and the branch is untouched. On `ok:false`, surface the `error` verbatim and stop — do not fabricate a PR or a verdict.

## Notes

- **Advisory only.** This command does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
- **Propose-only.** The engine never mutates the plan PR branch; it captures the PR head SHA before the panel and re-asserts it unchanged at the end. The only GitHub write is the single advisory PR comment.
- **Single round.** The engine runs the panel exactly once (terminal action `converged` when the round-0 panel passes, else `exhausted`); there is no revise loop and no agreement line.
- The node-validity `plan-review` lens carries the configured model override (`critics.review.lensModel`, when set) and stays research+code-only; the `plan-fidelity`/`plan-completeness` lenses receive the ticket text. The engine's header documents the full contract.
