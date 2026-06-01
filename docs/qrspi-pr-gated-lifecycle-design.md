# QRSPI PR-Gated Lifecycle — Design

**Status:** draft — all decisions locked (12); ready for implementation planning
**Author:** design conversation, 2026-06-01
**Scope:** Replace Linear-status-as-state-machine with PR-status-as-gate across the
QRSPI lifecycle. This is an architecture change to `.claude/skills/qrspi-work/SKILL.md`
and `.claude/workflows/qrspi-batch.js`, plus supporting helpers and docs.

---

## 1. Motivation

The current workflow treats **Linear status as the authoritative state machine**: the
orchestrator reads the ticket's status to decide which phase to run, and advancement
depends on a human manually flipping the status (`Design Approved`, `Plan Approved`,
`Code Approved`). Two problems:

1. **Linear's single status enum cannot represent a multi-cycle review.** Review and
   revision are inherently iterative ("round 3, two threads still unresolved"); a PR
   models this natively, a status field does not.
2. **A Linear transition is a hard dependency in the critical path.** This session hit
   the workflow stalling/failing twice because a finalize step depended on a Linear
   write. Status updates should *report* state, not *gate* it.

**Principle:** PR status is the real gate. Linear is primarily a project-reporting tool
(with one control responsibility: deciding which tickets may *begin*).

---

## 2. Locked decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Authority for advancement | **PR status**, not Linear |
| 2 | PR topology | One PR per phase, **stacked**, held open until the end |
| 3 | Merge cadence | **Land the whole stack bottom-up only when all phases are approved** |
| 4 | Auto-advance | Approving phase K's PR auto-builds phase K+1 stacked on top |
| 5 | Advance/land predicate | `reviewDecision == APPROVED` **AND** zero unresolved review threads |
| 6 | Linear role | **Entry gate** (assigned + `Selected`) + best-effort reporting projection; never read for gating after entry |
| 7 | Reset trigger | A formal **CHANGES_REQUESTED** review on an upstream phase PR |
| 8 | Reset scope | **Symmetric** — a change request on phase K discards every phase above K and returns to K's review |
| 9 | Revise (addressing feedback) | **Manual** — happens only on explicit re-invocation, never by passive automation |
| 10 | Downstream discard on reset | **Automatic** — on detecting an upstream CHANGES_REQUESTED, the invalidated downstream phases are discarded without confirmation (close PRs, delete branches, remove stale artifacts). Rationale: the skip-if-exists resume logic would otherwise treat a stale `plan.md`/`structure.md` as done and never regenerate it. |
| 11 | Linear `*Approved` states | **Dropped** — approval lives in the PR. Reporting uses phase-reflective states only (§7). |
| 12 | Existing in-flight tickets | **Drain**, not migrate — finish them under the current SKILL; the new model applies only to tickets starting after the change. |

---

## 3. Target topology

A single Graphite stack per ticket, built bottom-up, **held open** (nothing merges to
trunk) until the whole feature is approved:

```
trunk
 └── <id>/design      Design PR     — questions.md, research.md, design.md
      └── <id>/plan    Plan PR      — structure.md, plan.md, worktree.md   (stacked on design)
           └── <id>/slice-1  PR     — slice 1 code                          (stacked on plan)
                └── <id>/slice-2 PR — slice 2 code                          (stacked on slice-1)
                     └── ...
```

This **replaces** today's single `<id>/planning` branch carrying one amended commit of
all six planning artifacts. See §8 for migration.

Implementation slices are reviewed **as a whole stack** (decided earlier): the feature
advances to "ready to land" only when *every* slice PR is approved + clean, not per slice.

---

## 4. State-resolution algorithm (per invocation)

The orchestrator no longer reads Linear status to decide what to do (except the entry
gate). On each `qrspi-work <id>` (or batch dispatch) it resolves state from the **stack +
PR review states**:

```
1. ENTRY GATE
   If no <id>/design branch exists:
     - Require: ticket assigned to a user AND Linear status == "Selected".
     - If not satisfied → stop (nothing begins).
     - If satisfied → run the Design phase, open the Design PR, project Linear → "Design Review".
     - Done.

2. RESET CHECK (upstream change requests win)
   Inspect every open phase PR in the stack (design, plan, slice-1..N).
   Find the LOWEST phase K whose PR has an open CHANGES_REQUESTED review.
   If such a K exists:
     - DISCARD every phase above K, AUTOMATICALLY and without confirmation (decision 10):
         · close those PRs,
         · delete those branches,
         · remove the now-stale downstream artifacts from the worktree working tree
           (structure.md/plan.md/worktree.md and/or slice code) so the existence-detection
           in setup sees them as ABSENT — otherwise the skip-if-exists resume logic would
           treat them as done and never regenerate them.
       (Trunk is untouched — nothing was merged, so discard never rewrites shared history.)
     - This discard runs on any invocation that observes the trigger, INCLUDING a batch
       sweep. It is the one autonomous destructive action in the lifecycle; it is bounded
       to ticket-local branches/artifacts and never touches trunk.
     - Active phase := K, in "revise" state. Project Linear → K's review status.
     - Revise of K's artifacts is MANUAL: address K's feedback only if this invocation is
       for that; otherwise report the reset and stop.
     - Done.

3. ACTIVE-PHASE CHECK (no upstream change request)
   Active phase := highest phase whose branch exists. Read its PR:
     a. Not APPROVED, or unresolved threads present → awaiting revision.
        - If invoked to revise: address feedback (bounded within this phase), amend,
          re-submit, request re-review. Project Linear → "<phase> Review".
        - Else: report "waiting on review" and stop.
     b. APPROVED + zero unresolved threads:
        - If a next phase exists → AUTO-ADVANCE: build it, stacked on top; open its PR;
          project Linear → "<next phase> Review".
        - If this is the top phase (implementation) AND all slice PRs are approved+clean →
          LAND the whole stack bottom-up. Project Linear → "Done".
```

`Advance` and `Land` are decoupled: per-phase approval **builds the stack up**; a single
all-green condition **lands it**.

---

## 5. Predicates

### Ready-to-advance / ready-to-land
```
APPROVED(pr)  ≔  reviewDecision == "APPROVED"
CLEAN(pr)     ≔  zero unresolved review threads
READY(pr)     ≔  APPROVED(pr) AND CLEAN(pr)

advance phase K   when  READY(pr_K)
land the stack    when  READY(pr_design) AND READY(pr_plan) AND ∀ slices READY(pr_slice_i)
```

### Reset
```
RESET_TRIGGER(pr)  ≔  the PR carries a CHANGES_REQUESTED review (reviewDecision)
reset to phase K   when  K is the LOWEST phase with RESET_TRIGGER(pr_K)
                          ⇒ discard all phases > K
```

A plain comment / unresolved nit thread does **not** reset; it only blocks
`READY` (advance/land) and must be resolved. Only a formal change request resets.

---

## 6. Required technical mechanisms

1. **Unresolved-thread detection — GraphQL, not REST.** `CLEAN(pr)` requires true
   resolved/unresolved thread state via GitHub GraphQL
   `pullRequest { reviewThreads { nodes { isResolved } } }`. The current SKILL uses
   `gh api .../pulls/<n>/comments`, which lists all comments with no resolution state —
   this is the root of the existing non-idempotent "Address Feedback" bug. PR-gating
   makes fixing it mandatory.
2. **`reviewDecision`** via `gh pr view <n> --json reviewDecision,reviews` — drives both
   `APPROVED` and `RESET_TRIGGER`.
3. **Phase-PR resolver.** A reliable "find THE open PR for branch `<id>/<phase>`" helper.
   PR identity churns under Graphite restacks (the SKILL already carries dead/stale-PR
   handling); this becomes load-bearing now that PR state is the source of truth.
4. **Best-effort Linear projection.** A helper that writes the reporting status and
   **never throws into the critical path** — a failed Linear update logs a warning and
   continues. (Inverts today's behavior, where the Linear write could block finalize.)

---

## 7. Linear's responsibilities (narrowed)

- **Control (read):** only at entry — a ticket must be **assigned + `Selected`** to begin
  design. Nothing else is read for gating.
- **Report (write, best-effort):** agents project the active phase as the ticket moves.
  Suggested reporting states (see Open Decision B): `Selected` → `Design Review` →
  `Plan Review` → `Code Review` → `Done`, with a phase regressing on reset.

---

## 8. Change surface

| Area | Change |
|------|--------|
| `.claude/skills/qrspi-work/SKILL.md` | Rewrite the state machine from "read Linear status → act" to the §4 PR-driven algorithm. Keep only the entry-gate Linear read. Add the reset/discard cascade. Make Linear writes best-effort. |
| Branch model | Replace single `<id>/planning` amended commit with the §3 per-phase stacked branches. Affects every commit/submit/amend step in SKILL.md. |
| `.claude/workflows/qrspi-batch.js` | Entry query stays `Selected` (+assigned). Add a sweep of in-flight assigned tickets so the batch can detect approvals and **auto-advance** (build the next phase). Revise + reset stay manual. Finalize workers rewritten for the stacked-branch model. Replace the single-`planning`-branch assumptions. |
| New helper(s) | GraphQL `reviewThreads` check, phase-PR resolver, `READY`/`RESET` predicates, best-effort Linear projection. Shared by SKILL + batch. |
| `references/review-cascade.md` | Re-scope: within-phase cascade still applies; cross-phase cascade is now "discard + regenerate," not "patch in place." |
| Docs | `.claude/CLAUDE.md` lifecycle diagram, `docs/qrspi_*` guides describe the Linear-gated two-half model and must be updated. |

**Migration → DRAIN** (decision 12). Existing in-flight tickets are on the old single
`<id>/planning` branch (e.g. RUS-5/6/9/21/22, currently at Design Review with one planning
PR each). Rather than migrate live review state into the new per-phase branch model, those
tickets **finish under the current SKILL**, and the new PR-gated model applies only to
tickets that start after the change ships. Implication: the SKILL must either keep the old
state-machine path available during the drain window, or the redesign ships only once the
in-flight set is empty. Decide the cutover mechanics during implementation planning.

---

## 9. Resolved decisions (formerly open)

- **A — Discard automation → AUTOMATIC** (decision 10). The downstream discard executes
  automatically on any invocation that observes an upstream CHANGES_REQUESTED, including a
  batch sweep. Decisive rationale: leaving the derived branches/artifacts intact would let
  the skip-if-exists resume logic treat a stale `plan.md`/`structure.md` as done and ship
  plan/impl derived from a superseded design. The discard is bounded to ticket-local
  branches/artifacts and never touches trunk (nothing is merged until the end), so it is
  destructive but contained. This is the one autonomous destructive action in the
  lifecycle; a confirmation guard can be added later if it proves too aggressive.
- **B — Linear vocabulary → DROP** (decision 11). `Design Approved` / `Plan Approved` /
  `Code Approved` are removed; approval lives in the PR. Reporting uses the
  phase-reflective states in §7.

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Long-lived held stack drifts from an advancing trunk → restack/conflict cost | med | med | `gt sync`/restack on each invocation; keep features small; accept that fast features have negligible drift |
| Discarded **human review effort** when a late design change resets downstream | med | med | This is by design — it pressures reviewers to catch design issues at the design gate (aligned with QRSPI's "design is highest-leverage" philosophy). Reset trigger limited to formal CHANGES_REQUESTED (not nits) to avoid trivial resets. |
| PR identity churn under Graphite restacks breaks the phase-PR resolver | med | high | Robust resolver keyed on head branch; reuse existing dead/stale-PR handling; treat "no PR found for an existing branch" as an explicit error, not a silent skip |
| Best-effort Linear writes drift from real state | low | low | Linear is reporting only; PR state is authoritative, so drift is cosmetic and self-heals on the next projection write |
