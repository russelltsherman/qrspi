# QRSPI Quick Reference Card

One-page cheat sheet for the QRSPI workflow. Print and keep at desk.

---

## The 9 Phases (At a Glance)

```txt
┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI PLANNING — DESIGN PR                       │
│              (branch <id>/design, off trunk)                        │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 0: TICKET (T)                                                 │
│ └─ Input: A sentence or two describing the feature                  │
│ └─ Output: a LINEAR ISSUE (your Linear team, project QRSPI)     │
│ └─ Purpose: Produce a well-formed ticket via guided conversation    │
│ └─ Note: the ticket is NOT a local file; IDs look like RUS-42       │
│                                                                     │
│ PHASE 1: QUESTIONS (Q)                                              │
│ └─ Input: the Linear ticket                                         │
│ └─ Output: questions.md — 8-15 technical questions                  │
│ └─ Purpose: Force investigation of the codebase                     │
│ └─ Firewall: this phase CANNOT explore the codebase                 │
│                                                                     │
│ PHASE 2: RESEARCH (R)                                               │
│ └─ Input: questions.md                                              │
│ └─ Output: research.md — factual codebase map answering each Q      │
│ └─ Purpose: Document the existing system, no recommendations        │
│ └─ Firewall: ticket is HIDDEN; no Linear access (anchoring guard)   │
│                                                                     │
│ PHASE 3: DESIGN (D)                                                 │
│ └─ Input: research.md + the ticket (fetched now)                    │
│ └─ Output: design.md — pattern decisions, risk register, delta,     │
│            open questions                                           │
│ └─ Purpose: Make architectural decisions (brain-surgery phase)      │
│ └─ GATE: submit the DESIGN PR (<id>/design). Approval auto-advances.│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI PLANNING — PLAN PR                         │
│   (branch <id>/plan, stacked on <id>/design; built when design      │
│    PR is approved + clean)                                          │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 4: STRUCTURE (S)                                              │
│ └─ Input: approved design.md                                        │
│ └─ Output: structure.md — vertical slices, types, contracts         │
│ └─ Purpose: Decompose into end-to-end testable slices               │
│                                                                     │
│ PHASE 5: PLAN (P)                                                   │
│ └─ Input: approved structure.md                                     │
│ └─ Output: plan.md — atomic steps per slice, verification           │
│ └─ Purpose: Tactical roadmap for coding (zero new decisions)        │
│                                                                     │
│ PHASE 6: WORK TREE (W)                                              │
│ └─ Input: plan.md                                                   │
│ └─ Output: worktree.md — session-aware task DAG, per-session        │
│            context budgets                                          │
│ └─ Purpose: Sequence work into fresh-session-sized chunks           │
│ └─ GATE: submit the PLAN PR (<id>/plan). Approval auto-advances.    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI EXECUTION — SLICE PRs                      │
│   (branches <id>/slice-1..N, stacked on <id>/plan; built when       │
│    plan PR is approved + clean)                                     │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 7: IMPLEMENT (I)                                              │
│ └─ Input: structure.md + plan.md + worktree.md                      │
│ └─ Output: code + impl-log.md, one slice per FRESH session          │
│ └─ Purpose: Build each slice following the plan exactly             │
│ └─ Each slice is its own stacked PR (<id>/slice-N)                  │
│                                                                     │
│ PHASE 8: PULL REQUEST (PR)                                          │
│ └─ Input: implemented code + impl-log.md                            │
│ └─ Output: pr-summary.md mapping ACs to code + tests                │
│ └─ Purpose: Code review with zero surprises                         │
│ └─ GATE: slice PRs reviewed as a whole stack. When EVERY PR in the  │
│          stack is approved + clean, the stack LANDS bottom-up.      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

All planning artifacts (questions, research, design, structure, plan, work tree)
live as local files under `.qrspi/<ticket-id>/`, committed onto the matching phase
branch. Linear holds a best-effort reporting status only — artifacts are never
uploaded to Linear, and Linear never gates advancement.

---

## The PR-Gated Lifecycle

**PR review state — not Linear status — is the authority for advancement.** Each phase
is its own stacked PR, built bottom-up and **held OPEN** until the whole feature is
approved, then landed bottom-up. Nothing merges mid-feature.

```txt
trunk
 └── <id>/design   Design PR  — questions.md, research.md, design.md
      └── <id>/plan  Plan PR   — structure.md, plan.md, worktree.md   (stacked on design)
           └── <id>/slice-1..N  slice PRs — code                       (stacked on plan)
```

- **ADVANCE is automatic.** Approving a phase PR (`reviewDecision == APPROVED` AND zero
  unresolved review threads) builds the next phase stacked on top.
- **RESET is automatic.** A formal `CHANGES_REQUESTED` on an *upstream* phase PR discards
  every downstream phase (close PRs, delete branches, remove stale artifacts) and returns
  the ticket to that phase. Symmetric across phases.
- **REVISE is manual.** Addressing review comments within a phase happens only on an
  explicit invocation — never from passive automation.
- The single `<id>/planning` branch is GONE — there is no shared planning branch and no
  amended-commit-of-all-six-artifacts. Each phase is its own branch and PR.

> A plain comment or unresolved nit thread does NOT reset — it only blocks approval and
> must be resolved. Only a formal change request resets downstream phases.

---

## PR-State → Action Model

The action is computed by the tested resolver `scripts/qrspi_resolve_state.py`
(fed PR state gathered by `scripts/qrspi_pr_state.py`). `/qrspi-work` does NOT
hand-derive a Linear-status state machine.

```txt
Action        When                                  What happens
──────────────────────────────────────────────────────────────────────────────────
entry_blocked No <id>/design branch AND ticket is   Stop — nothing begins.
              not (assigned + Selected).
run_design    Entry gate satisfied; no design       Build Q→R→D on <id>/design,
              branch yet.                           open the Design PR.
advance       Active phase PR is approved + clean    AUTO-ADVANCE: build the next
              and a next phase exists.               phase stacked on top, open its PR.
submit        Phase branch exists but its PR was     Finish artifacts if needed,
              never opened (crashed run).            submit the PR.
wait          Active phase PR open, awaiting         Nothing to do — a human must
              review (not approved, no unresolved    approve. Re-run after review.
              threads).
revise        Active phase PR has unresolved         MANUAL: address feedback within
              review threads.                        the phase, amend, re-submit.
reset         Upstream phase PR is CHANGES_REQUESTED. AUTOMATIC: discard downstream
                                                     phases, return to that phase.
land          EVERY PR in the stack is approved +    Merge the whole stack bottom-up,
              clean.                                 then report Done.
```

Predicates: `READY(pr) ≔ reviewDecision == APPROVED AND zero unresolved review threads`
(unresolved threads checked via GitHub GraphQL `reviewThreads`). Advance a phase when its
PR is `READY`; land the stack when every PR is `READY`.

---

## Linear's Two Roles (Reporting, Not Gating)

```txt
1. ENTRY GATE (read, once):
   A ticket may BEGIN only if it is ASSIGNED to a user AND in the `Selected` status.
   Nothing else is ever read from Linear for gating.

2. REPORTING PROJECTION (write, best-effort):
   Agents project the active phase as the ticket moves. A failed Linear write logs a
   warning and NEVER blocks git/PR work.

Reporting statuses:  Selected → Design Review → Plan Review → Code Review → Done
                     (a status regresses on reset)

The old `Design Approved` / `Plan Approved` / `Code Approved` statuses were DROPPED —
approval lives in the PR.
```

---

## Components

```txt
.claude/agents/qrspi-<phase>.md     Purpose-built phase agents with per-phase
                                    tool lockdowns. The orchestrator spawns
                                    them via subagent_type.
.claude/skills/qrspi-<phase>/       Slash-command wrappers around the agents.
  SKILL.md
.claude/skills/qrspi-work/          /qrspi-work — autonomous orchestrator. Resolves
  SKILL.md                          PR review state into an action and dispatches it.
.claude/skills/qrspi-ticket/        /qrspi-ticket — creates a Linear ticket via
  SKILL.md                          guided conversation.
.claude/workflows/qrspi-batch.js    Batch driver — pushes MANY assigned tickets one
                                    PR-gated step forward (autonomous actions only).
scripts/qrspi_resolve_state.py      Tested resolver — computes the action from PR state.
scripts/qrspi_pr_state.py           Gathers PR review state via gh GraphQL reviewThreads.
scripts/test_qrspi_*.py             stdlib-only unit tests for the resolver/state.
.qrspi/<ticket-id>/                 Per-ticket local artifacts (committed per phase).
.qrspi/templates/                   Canonical artifact formats (single source of truth).
.worktrees/<ticket-id>/             Isolated git worktree per ticket (gitignored).
evals/                              NON-FUNCTIONAL placeholder. Verification = unit
                                    tests + manual end-to-end runs, not the harness.
```

---

## Firewalls (Structural, Not Optional)

```txt
QUESTIONS phase  → CANNOT explore the codebase (no Glob/Grep/Bash).
RESEARCH phase   → CANNOT read the ticket and has NO Linear access.
                   Prevents anchoring bias — facts before the framing.
```

---

## Worktrees

```txt
- Each ticket gets its own git worktree at .worktrees/<ticket-id>/ (gitignored).
- The main checkout stays on `main`; all ticket work happens in the worktree.
- The worktree is checked out to the stack tip (highest existing phase branch).
- Multiple tickets can be worked concurrently, no branch-checkout conflicts.
```

---

## When to Use QRSPI

```txt
Feature Complexity          QRSPI Recommendation
────────────────────────────────────────────────
Simple (1-2 hour task)    → SKIP (overhead too high)
Medium (2-6 hours)        → USE (saves time + quality)
Complex (6+ hours)        → MUST USE (critical)
Distributed system        → MUST USE (alignment is essential)
Team project              → MUST USE (alignment prevents conflicts)
Refactor/migration        → MUST USE (coordination critical)
Unfamiliar codebase       → USE (research phase is essential)
Crisis/hotfix mode        → SKIP (no time for alignment)
Greenfield project        → USE (design phase essential)
```

---

## The Decision Tree

```txt
Is feature complex?
  ├─ NO → Can you do it in <2 hours?
  │   ├─ YES → Skip QRSPI
  │   └─ NO → Use QRSPI
  │
  └─ YES → Use QRSPI

Is this a team project?
  ├─ YES → MUST use QRSPI (alignment critical)
  └─ NO → Use if medium+ complexity

Are you in crisis mode?
  ├─ YES → Skip QRSPI (no time)
  └─ NO → Use QRSPI (prevents crisis later)
```

---

## Common Mistakes (Don't Do These)

```txt
❌ Treating the ticket as a local markdown file
   Reality: the ticket is a Linear issue; only the phase artifacts are local.

❌ Reading Linear status to decide what to do next
   Reality: PR review state is the authority. Linear is the entry gate + reporting only.

❌ Looking for a single <id>/planning branch
   Reality: that branch is gone. Each phase is its own stacked branch/PR
   (<id>/design → <id>/plan → <id>/slice-N).

❌ Letting agent introduce new architecture in Plan
   Fix: the plan phase makes zero new decisions — it references design.md.

❌ Asking the agent to do multiple phases at once
   Fix: one phase per spawn; advance is gated on the upstream PR being approved + clean.

❌ Merging a phase PR mid-feature
   Fix: the stack is held OPEN. Nothing lands until EVERY PR is approved + clean,
   then the whole stack lands bottom-up.

❌ Auto-revising review comments
   Fix: revise is MANUAL (explicit invocation only). Only reset/advance are automatic.

❌ Confusing vertical slices with horizontal layers
   Fix: each slice is end-to-end testable, not "all DB" then "all API."

❌ Running implementation slices in one long session
   Fix: one slice per FRESH session; /clear between slices.
```

---

## The QRSPI Mantra

```txt
DESIGN PR:
"Explore and document facts before deciding. Submit the design PR."

PLAN PR:
"Decompose and sequence. No new decisions. Submit the plan PR on approval."

IMPLEMENTATION:
"Follow the plan exactly. One slice per session. One stacked PR per slice."

CODE REVIEW:
"This should be boring. The PR matches the plan. Land the stack when all-green."
```

---

## Quick Commands

```bash
# Create a Linear ticket (Phase 0) via guided conversation
/qrspi-ticket <brief description>

# Autonomous orchestrator — resolves PR review state, runs the matching action
/qrspi-work <ticket-id>

# Individual phase skills (mostly for the orchestrator; available manually)
/qrspi-questions  <ticket-id>
/qrspi-research   <ticket-id>
/qrspi-design     <ticket-id>
/qrspi-structure  <ticket-id>
/qrspi-plan       <ticket-id>
/qrspi-worktree   <ticket-id>
/qrspi-implement  <ticket-id> <slice-number>
/qrspi-pr         <ticket-id>

# Drive many assigned tickets one PR-gated step forward. Runs the autonomous
# actions (run_design, advance, submit, land, automatic reset); leaves `wait`
# and the manual `revise` untouched.
# → run the "qrspi-batch" workflow via Claude Code's Workflow tool
#   (e.g. ask Claude to "run the qrspi-batch workflow"); it is not a shell command.
```

```bash
# Context hygiene
/clear      # fresh session — required between implementation slices
/compact    # if context grows large within a phase
/context    # check utilization; if over 40%, compact or start fresh
```

---

## Graphite Stack Commands (orchestrator-owned)

```bash
# Open the design branch off trunk, then submit its PR
gt create <id>/design --no-interactive -m "<id> [QR]: Design"
gt submit --no-edit --no-interactive

# Build the plan PR stacked on the approved design branch
gt checkout <id>/design --no-interactive
gt create <id>/plan --no-interactive -m "<id> [SP]: Plan"
gt submit --no-edit --no-interactive

# Build each slice stacked on <id>/plan (or the prior slice)
gt create <id>/slice-<N> --no-interactive -m "<id> [I] <N>/<total>: <goal>"
gt submit --stack --no-edit --no-interactive

# RESET: discard a downstream phase after an upstream change request (tip-down)
gt delete <id>/slice-<k> --force --close --no-interactive
gt delete <id>/plan       --force --close --no-interactive

# LAND: only when EVERY PR is approved + clean — merge bottom-up
gt checkout <id>/slice-1 --no-interactive   # or <id>/design if plan-only
gt merge --no-interactive                    # merges the stack bottom-up (NOT --confirm: forces a prompt --no-interactive can't satisfy)
```

> The held-open stack is never `gt sync`'d mid-feature (that would delete branches
> whose PRs are closed). Only `land` cleanup syncs after the merge.

---

## Tooling

```txt
Claude Code CLI   The agent host.
Graphite (gt)     Stacked PRs — one per phase (design, plan, each slice).
GitHub CLI (gh)   PR operations + GraphQL reviewThreads (unresolved-thread check).
Linear MCP        Entry gate + best-effort reporting status for the
                  your Linear workspace (never a gate after entry).
```

---

## Print This Card

The 9 phases should be muscle memory:

```txt
T → Q → R → D → S → P → W → I → PR

Ticket → Questions → Research → Design → Structure → Plan → Work Tree → Implement → PR
        └──── design PR ──────┘ └──── plan PR ─────┘ └──── slice PRs ────┘
         <id>/design             <id>/plan            <id>/slice-1..N
   approve → auto-advance    approve → auto-advance   all approve → land stack
```

---

## One More Thing

QRSPI's core principles, in order:

1. The ticket defines the problem (in Linear), not the solution.
2. Explore the codebase before designing — and research never sees the ticket.
3. Decide in the design PR; advancement is gated on PR approval, not Linear status.
4. Plan and sequence in the plan PR; it auto-builds once design is approved + clean.
5. Follow the plan during implementation — one slice per fresh session, one PR each.
6. Hold the stack open; land bottom-up only when every PR is approved + clean.

Everything else is optimization.

Good luck. You got this.
