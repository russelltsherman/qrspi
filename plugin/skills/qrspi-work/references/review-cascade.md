# Review Cascade Logic (PR-gated)

Artifacts form a dependency chain, now split across **per-phase PR branches**:

```
  design branch          plan branch              slice branches
┌──────────────────┐  ┌────────────────────┐  ┌──────────────┐
Questions → Research → Design → Structure → Plan → Work Tree → code (slice 1..N)
└──── design phase ────┘└────── plan phase ──────┘└─ implementation ─┘
```

There are **two distinct cascade scopes**, and which one applies depends on *where* the
change was requested relative to the phases that currently exist.

## 1. Within-phase cascade — the manual `revise` path

When the feedback is on the **active (frontier) phase's** PR — i.e. there is nothing
downstream of it yet, or the comment only touches this phase's own artifacts — address it
**in place** by cascading among that phase's artifacts only, then amend and re-submit that
phase's PR. Stay on the phase branch.

Per-phase internal chains:

- **design phase:** Questions → Research → Design
- **plan phase:** Structure → Plan → Work Tree
- **implementation:** slice-1 → slice-2 → … (start from the lowest-numbered affected slice;
  `gt modify` restacks the higher slices automatically)

### Identify the earliest affected artifact (within the phase)

Map each comment to the artifact it targets; if it affects several, use the earliest in the
phase's internal chain.

### Determine cascade depth (within the phase)

| Change type | Cascade within the phase? |
|---|---|
| Typo, wording, clarification | No — fix only the targeted artifact |
| New question added (design phase) | Re-run Research, then Design |
| Research finding corrected (design phase) | Re-evaluate Design (citations may change) |
| Structure slice split/merged (plan phase) | Re-run Plan, then Work Tree |
| Structure contract changed (plan phase) | Re-run Plan, then Work Tree |
| Plan step modified (plan phase) | Re-evaluate Work Tree |
| Work Tree session moved (plan phase) | No — it's the last artifact in the phase |
| Code fix on slice N (implementation) | Address slice N; higher slices restack automatically |

When re-running a downstream artifact **within the phase**, spawn the same phase agent with
the UPDATED upstream artifact — regenerate, never hand-patch. Then:

```bash
git add .qrspi/<ticket-id>/<changed artifacts>
gt modify --no-interactive -m "<ticket-id>: Address <phase> review feedback"
gt submit --no-edit --no-interactive          # --stack for implementation
```

## 2. Cross-phase change — the automatic `reset` path (NOT a patch)

When a formal **CHANGES_REQUESTED** lands on an **upstream phase** PR while **downstream
phases already exist** (e.g. a design change requested while the plan and/or slice PRs are
open), the downstream work is built on a now-superseded upstream and **must not be patched
in place.** Instead it is **discarded and regenerated**:

- The resolver returns `action: reset` with `resetToPhase` and `discardPhases`.
- The orchestrator's `reset` handler **closes the downstream PRs, deletes their branches, and
  removes their stale artifacts**, returns the ticket to the upstream phase's review, and
  stops. Addressing the upstream feedback is then the manual `revise` path; on re-approval the
  downstream phases rebuild fresh from the corrected upstream.

Why discard rather than cascade-patch: plan/implementation are *derived* from design. If the
design changes, the derived work is not selectively salvageable, and the skip-if-exists resume
logic would otherwise treat a stale `plan.md`/`structure.md` as done. Discarding is the
deterministic, consistent choice — and it's cheap, because nothing is merged until the end, so
the discard never touches trunk. See `docs/qrspi-pr-gated-lifecycle-design.md` §4 and decisions
7, 8, 10.

> Rule of thumb: **same phase → revise in place; upstream phase with downstream open → reset.**
> Never reach across a phase boundary to hand-edit a downstream artifact.
