---
name: review-implementation
description: On-demand advisory review of a QRSPI ticket's IMPLEMENTATION (the slice stack). Run the full read-only implementation review panel (node-validity + fidelity + completeness lenses) over the implemented code + tests against the real codebase, then post ONE rolled-up axis-enumerated advisory synopsis comment to the top slice PR and append a ledger row — WITHOUT mutating any PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's implementation/code (e.g. "/review-implementation RUS-89", "review the implementation for RUS-42", "is the code for RUS-50 correct?", "run the impl panel on RUS-7"). This is the implementation-phase entry of the /review-* family; for the design use /review-design, for the plan use /review-plan.
allowed-tools: Workflow
---

# /review-implementation

Run an **advisory, propose-only** review of a ticket's implementation (its slice stack) and post a single rolled-up synopsis to the top slice PR. This is the implementation-phase member of the `/review-*` family.

This command is a **thin wrapper** over the deterministic review engine (`.claude/workflows/qrspi-review.js`). The engine owns the whole run — resolving the worktree + the **top slice PR** (derived with `gh pr list --state all` so a partially-landed stack still resolves the frontier), scratch-copying the implementation record, fanning out the implementation review panel **once** (round 0, no revise loop) over the aggregated slice stack against the real code **and its tests**, posting ONE rolled-up axis-enumerated advisory synopsis comment to the top slice PR, and appending the ledger row — all while holding the top slice PR head SHA **unchanged** (propose-only: it issues no `gt`/`gh` branch-mutating command, only the one PR comment + the ledger append). There is **no** decision-readiness lens for the implementation phase — that lens is design-phase-only.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## What to do

Invoke the review engine for the **implementation** phase, passing the ticket id:

```
Workflow({ name: "qrspi-review", args: { ticket: "<ticket-id>", phase: "impl" } })
```

The engine returns `{ ok, ticket, phase, pr, terminalAction, shaUnchanged, summary }` (or `{ ok:false, error }` on a missing implementation phase / slices / top-slice PR, a resolve error, or a propose-only violation). Report its `summary` to the user: the single rolled-up synopsis comment was posted to the top slice PR, a `mode:"on-demand-review"` ledger row was appended, and no branch was touched. On `ok:false`, surface the `error` verbatim and stop — do not fabricate a PR or a verdict.

## Notes

- **Advisory only.** This command does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
- **Propose-only.** The engine never mutates any slice PR branch; it captures the top slice PR head SHA before the panel and re-asserts it unchanged at the end. The only GitHub write is the single advisory PR comment.
- **One rolled-up synopsis.** The panel runs ONE pass over the aggregated slice stack (not per-slice) and the engine posts exactly one comment, to the top slice PR.
- **Single round.** The engine runs the panel exactly once (terminal action `converged` when the round-0 panel passes, else `exhausted`); there is no revise loop and no agreement line.
- The node-validity `impl-review` lens carries the configured model override (`critics.review.lensModel`, when set) and stays research+code-only; the `impl-fidelity`/`impl-completeness` lenses receive the ticket text. The engine's header documents the full contract.
