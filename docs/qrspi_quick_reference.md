# QRSPI Quick Reference Card

One-page cheat sheet for the QRSPI workflow. Print and keep at desk.

---

## The 9 Phases (At a Glance)

```txt
┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI PLANNING — DESIGN HALF                     │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 0: TICKET (T)                                                 │
│ └─ Input: A sentence or two describing the feature                  │
│ └─ Output: a LINEAR ISSUE (team Russelltsherman, project QRSPI)     │
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
│ └─ GATE: submit planning PR → Design Review (human gate)            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI PLANNING — PLAN HALF                       │
│              (runs only after Design Approved)                      │
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
│ └─ GATE: update planning PR → Plan Review (human gate)              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI EXECUTION                                  │
│              (runs only after Plan Approved)                        │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 7: IMPLEMENT (I)                                              │
│ └─ Input: structure.md + plan.md + worktree.md                      │
│ └─ Output: code + impl-log.md, one slice per FRESH session          │
│ └─ Purpose: Build each slice following the plan exactly             │
│ └─ Submit: a stacked PR per slice → Code Review (human gate)        │
│                                                                     │
│ PHASE 8: PULL REQUEST (PR)                                          │
│ └─ Input: implemented code + impl-log.md                            │
│ └─ Output: pr-summary.md mapping ACs to code + tests                │
│ └─ Purpose: Code review with zero surprises                         │
│ └─ After Code Approved: report ready to merge (human-owned merge)   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

All planning artifacts (questions, research, design, structure, plan, work tree)
live as local files under `.qrspi/<ticket-id>/`. Linear holds status and
phase-transition comments only — artifacts are never uploaded to Linear.

---

## The Two-Gate Lifecycle

Planning is split into two halves, each ending at a HUMAN review gate. The Linear
status is the authoritative state machine that drives `/qrspi-work`.

```txt
Selected → [Questions · Research · Design] → Design Review → Design Approved
  → [Structure · Plan · Work Tree] → Plan Review → Plan Approved
  → [Implement all slices] → Code Review → Code Approved → Done
```

- **DESIGN HALF** = questions, research, design.
- **PLAN HALF** = structure, plan, work tree.
- All six planning artifacts live on ONE `<ticket-id>/planning` branch as a SINGLE
  amended commit. The planning PR is submitted at Design Review and re-submitted
  (grown with the plan-half artifacts) at Plan Review.
- **Design Review** and **Plan Review** are HUMAN turns. The orchestrator waits or
  addresses PR feedback — it never advances past them autonomously. The human moves
  the ticket to Design Approved / Plan Approved.

---

## Linear Status State Machine

```txt
Status            Orchestrator action
────────────────────────────────────────────────────────────────────
Backlog/Selected  Run design half (Q→R→D); submit planning PR;
                  move to Design Review
Design Review     HUMAN GATE — review design-half PR, address feedback;
                  human moves to Design Approved
Design Approved   Run plan half (S→P→W); update planning PR;
                  move to Plan Review
Plan Review       HUMAN GATE — review full plan PR, address feedback;
                  human moves to Plan Approved
Plan Approved     Implement all slices; submit stacked PRs (one per slice);
                  move to Code Review
Code Review       Address implementation feedback; human moves to Code Approved
Code Approved     Report ready to merge (human-owned merge)
Done              Clean up artifacts + worktree
```

---

## Components

```txt
.claude/agents/qrspi-<phase>.md     Purpose-built phase agents with per-phase
                                    tool lockdowns. The orchestrator spawns
                                    them via subagent_type.
.claude/skills/qrspi-<phase>/       Slash-command wrappers around the agents.
  SKILL.md
.claude/skills/qrspi-work/          /qrspi-work — autonomous orchestrator that
  SKILL.md                          implements the Linear-status state machine.
.claude/skills/qrspi-ticket/        /qrspi-ticket — creates a Linear ticket via
  SKILL.md                          guided conversation.
.claude/workflows/qrspi-batch.js    Batch driver — pushes MANY assigned tickets
                                    through the autonomously-runnable states.
.qrspi/<ticket-id>/                 Per-ticket local artifacts.
.qrspi/templates/                   Canonical artifact formats (reference only).
.worktrees/<ticket-id>/             Isolated git worktree per ticket (gitignored).
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

❌ Skipping the Design Review gate
   Reality: the design half stops at Design Review BEFORE any plan-half work.
   Never produce structure/plan/work tree while status is Selected/Design Review.

❌ Letting agent introduce new architecture in Plan
   Fix: the plan half makes zero new decisions — it references design.md.

❌ Asking the agent to do multiple phases at once
   Fix: one phase per spawn; the orchestrator gates them on Linear status.

❌ Advancing past a human gate autonomously
   Fix: Design Review and Plan Review are human turns. Wait or address feedback.

❌ Confusing vertical slices with horizontal layers
   Fix: each slice is end-to-end testable, not "all DB" then "all API."

❌ Running implementation slices in one long session
   Fix: one slice per FRESH session; /clear between slices.
```

---

## The QRSPI Mantra

```txt
DESIGN HALF:
"Explore and document facts before deciding. Stop at Design Review."

PLAN HALF:
"Decompose and sequence. No new decisions. Stop at Plan Review."

IMPLEMENTATION:
"Follow the plan exactly. One slice per session. No surprises."

CODE REVIEW:
"This should be boring. The PR matches the plan."
```

---

## Quick Commands

```bash
# Create a Linear ticket (Phase 0) via guided conversation
/qrspi-ticket <brief description>

# Autonomous orchestrator — reads Linear status, runs the matching phase
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

# Drive many assigned tickets through the autonomous states (Selected,
# Design Approved, Plan Approved). Leaves the human review gates untouched.
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

## Tooling

```txt
Claude Code CLI   The agent host.
Graphite (gt)     Stacked PRs — one per slice.
GitHub CLI (gh)   PR operations.
Linear MCP        Status + phase-transition comments for the
                  Russelltsherman workspace.
```

---

## Print This Card

The 9 phases should be muscle memory:

```txt
T → Q → R → D → S → P → W → I → PR

Ticket → Questions → Research → Design → Structure → Plan → Work Tree → Implement → PR
        └──── design half ────┘ └──── plan half ────┘
            ↑ Design Review          ↑ Plan Review
```

---

## One More Thing

QRSPI's core principles, in order:

1. The ticket defines the problem (in Linear), not the solution.
2. Explore the codebase before designing — and research never sees the ticket.
3. Decide in the design half; stop for human review before planning.
4. Plan and sequence in the plan half; stop again for human review.
5. Follow the plan during implementation — one slice per fresh session.

Everything else is optimization.

Good luck. You got this.
