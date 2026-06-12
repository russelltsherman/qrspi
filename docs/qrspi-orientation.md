# QRSPI Orientation Guide

QRSPI is a structured workflow for agentic feature development in Claude Code. It decomposes feature work into sequential phases — Ticket, Questions, Research, Design, Structure, Plan, Worktree, Implement, PR — each producing a reviewable artifact. The goal is to spend upfront alignment time so that implementation integrates cleanly on the first attempt, while humans retain control at every decision point.

This guide walks through every step. Each phase shows what goes in, what comes out, and where to find the agent that runs it.

---

## Two ways to drive a ticket

QRSPI offers an autonomous path and a manual path. Most work uses the autonomous path.

- **`/qrspi-work <ticket-id>`** is the autonomous orchestrator. It reads the ticket's **PR review state** (not Linear status), determines the current phase, runs the matching phase agents, commits artifacts, submits stacked PRs, and projects the active phase back to Linear best-effort. Each invocation does exactly one PR-gated step. Use this to drive a ticket from `Selected` through to a landed stack.
- **Individual phase skills** (`/qrspi-questions`, `/qrspi-research`, etc.) exist primarily for the orchestrator's internal use, but are available when you need to re-run a single phase or work step-by-step. The per-phase sections below document each one.

A feature starts with `/qrspi-feature <description>` — the front door. It elicits requirements, proposes a *reviewed* ticket decomposition (one ticket vs several, a dependency DAG, an overlap scan against in-flight work), and gates on your approval before any Linear write, then creates the ticket(s). For a single, already-scoped ticket you want filed directly, `/qrspi-ticket <description>` is the direct entry (same interview and writer, no decomposition). From there, `/qrspi-work <ticket-id>` advances each ticket.

```
# Start a new feature (decompose + review gate + create tickets)
/qrspi-feature "Add webhook support for deployment notifications"
# → answer a few questions, approve the decomposition; tickets are created (e.g., RUS-42)

# Drive it forward through the lifecycle
/qrspi-work RUS-42
```

---

## Prerequisites

- Claude Code CLI installed and authenticated
- [Graphite CLI](https://graphite.dev) (`gt`) for stacked PRs
- [GitHub CLI](https://cli.github.com) (`gh`) for PR operations
- Linear MCP server configured for your Linear workspace
- This repository cloned locally

---

## Tickets are Linear issues

The ticket is **not** a local markdown file. `/qrspi-ticket` creates a Linear issue in your Linear team, **QRSPI** project, with an ID in Linear's format (e.g., `RUS-42`). Linear holds the ticket, but it does **not** drive advancement — PR review state does. Linear has exactly two roles:

- **Entry gate (read).** A ticket may *begin* only if it is assigned to a user **and** in the `Selected` status. Nothing starts otherwise. This is the only thing Linear is read for.
- **Reporting projection (write, best-effort).** Once work starts, agents update the Linear status to reflect the active phase (`Design Review` → `Plan Review` → `Code Review` → `Done`). A failed Linear write logs a warning and is never allowed to block git/PR work.

Planning and implementation artifacts are local files — they are **not** uploaded to Linear as attachments. The `Design Approved` / `Plan Approved` / `Code Approved` statuses that an older version of this workflow used were **dropped**: approval now lives in the PR, not in a Linear status.

---

## Directory Layout

```txt
.qrspi/<ticket-id>/        ← all local artifacts for a ticket live here
  questions.md             ← Questions phase output
  research.md              ← Research phase output
  design.md                ← Design phase output
  structure.md             ← Structure phase output
  plan.md                  ← Plan phase output
  worktree.md              ← Worktree phase output
  impl-log.md              ← Implement phase output (appended per slice)
  pr-summary.md            ← PR phase output
  # (the ticket itself lives in Linear, not here)

.claude/agents/            ← phase agent definitions — the actual phase logic
.claude/skills/            ← slash-command wrappers (incl. /qrspi-ticket, /qrspi-work)
.claude/workflows/         ← qrspi-batch.js (multi-ticket batch orchestrator)
scripts/                   ← PR-gated decision logic + its tests
  qrspi_pr_state.py        ← gathers PR review state (gh GraphQL reviewThreads)
  qrspi_resolve_state.py   ← tested resolver: PR state → next action
  test_qrspi_*.py          ← stdlib-only unit tests for the above
.qrspi/templates/          ← canonical output formats (reference only — single source of truth)
evals/fixtures/            ← example tickets you can learn from
docs/                      ← extended documentation
```

> The `evals/` harness is a **non-functional placeholder**. Verification of QRSPI itself
> is done by the `scripts/test_qrspi_*.py` unit tests (pure decision logic) plus manual
> end-to-end runs of the orchestration — not by the eval harness.

### Agents vs. skills

The two-layer split is deliberate:

- **`.claude/agents/qrspi-<phase>.md`** holds the phase logic — purpose-built agents with per-phase tool lockdowns and hard-constraint blocks. The orchestrator spawns these directly via `subagent_type`. There is one agent per phase from Questions through PR.
- **`.claude/skills/qrspi-<phase>/SKILL.md`** are the slash-command wrappers that invoke the phase agents. `/qrspi-ticket` and `/qrspi-work` are skills with no corresponding phase agent (ticket creation is a guided conversation; `/qrspi-work` is the orchestrator).

---

## Lifecycle — per-phase stacked PRs

Each phase is its own pull request, and **PR review state — not Linear status — is the authority for advancement**. The phases stack into a single Graphite stack per ticket, built bottom-up off trunk and **held open** (nothing merges to trunk) until the whole feature is approved, then landed bottom-up.

```txt
  Ticket (Linear issue, assigned + Selected)   ← ENTRY GATE
     │
     ▼
  trunk
   └── <id>/design   Design PR   ── questions.md, research.md, design.md
        │  ◆ approved (reviewDecision APPROVED + 0 unresolved threads) → auto-advance
        └── <id>/plan   Plan PR   ── structure.md, plan.md, worktree.md      (stacked on design)
             │  ◆ approved → auto-advance
             └── <id>/slice-1..N   slice PRs ── code                          (stacked on plan)
                  │  ◆ every slice PR approved + clean
                  ▼
             LAND the whole stack bottom-up → Done → cleanup
```

The old single `<ticket-id>/planning` branch (one amended commit carrying all six planning artifacts) is **gone**. There is no "design half / plan half" framing anymore — design, plan, and implementation are three independently-reviewed, stacked PRs.

### How the orchestrator decides what to do

`/qrspi-work` does **not** hand-derive state from a Linear status. It gathers the live PR review state and runs a **tested resolver** to compute the next action:

```
scripts/qrspi_pr_state.py   →  gathers PR state (gh GraphQL reviewThreads, reviewDecision)
scripts/qrspi_resolve_state.py  →  PR state → { action, phase, nextPhase, … }
```

The resolver — not a hand-coded Linear-status state machine — is the single source of decision truth; both `/qrspi-work` and the batch orchestrator call it rather than re-deriving logic. The resolved actions:

| Action | When | What happens |
|--------|------|--------------|
| `entry_blocked` | No `<id>/design` branch and the ticket is not assigned + `Selected` | Stop; nothing begins |
| `run_design` | Entry gate satisfied | Build the design PR (questions → research → design) on `<id>/design`; project Linear → `Design Review` |
| `advance` → plan | Design PR is **READY** (APPROVED + 0 unresolved threads) | Build the plan PR (structure → plan → worktree) stacked on design; project → `Plan Review` |
| `advance` → implementation | Plan PR is READY | Build the slice PR stack (one PR per slice) on top of plan; project → `Code Review` |
| `wait` | Active phase PR is open but not yet APPROVED (and no unresolved threads) | Nothing to do until a human reviews; stop |
| `revise` | Active phase PR has unresolved review threads | **Manual** — address feedback within that phase only, on explicit invocation |
| `reset` | A formal **CHANGES_REQUESTED** on an *upstream* phase PR | **Automatic** — discard every downstream phase, return the ticket to the upstream phase |
| `land` | **Every** PR in the stack is READY | Merge the whole stack bottom-up; project → `Done`; clean up |

### The advance predicate

A phase PR is **ready** when:

- `reviewDecision == APPROVED`, **and**
- there are **zero unresolved review threads** (checked via the GitHub GraphQL `reviewThreads` API — a plain comment or unresolved nit blocks readiness but is not itself an approval).

Approving a phase PR **auto-advances**: the next phase is built and submitted stacked on top, with no manual step. Advance and land are decoupled — per-phase approval *builds the stack up*; only the all-green condition (every PR ready) *lands it*. Nothing merges mid-feature.

### Reset vs. revise

These are deliberately different, and symmetric across phases:

- **Reset is automatic and destructive (bounded).** A formal `CHANGES_REQUESTED` on an *upstream* phase PR means every downstream phase is derived from a now-superseded upstream. On any invocation that observes the trigger, the orchestrator automatically **discards** all downstream phases — closes their PRs, deletes their branches, and removes the stale downstream artifacts from the working tree — and returns the ticket to the change-requested phase. (Removing the artifacts matters: the skip-if-exists resume logic would otherwise treat a stale `plan.md`/`structure.md` as already done and never regenerate it.) Trunk is never touched — nothing was merged, so discard only affects ticket-local branches and artifacts.
- **Revise is manual.** Addressing review comments *within* a phase happens only on an explicit re-invocation, never from passive automation. A change request that invalidates downstream work is handled by `reset`, not `revise`.

---

## Worktrees

Each ticket gets its own git worktree at `.worktrees/<ticket-id>/` (gitignored). The main repo checkout stays on `main`; all ticket work happens inside the worktree. Because each ticket is isolated in its own worktree, **multiple tickets can be worked concurrently** without branch-checkout conflicts.

---

## Batch processing

`.claude/workflows/qrspi-batch.js` drives **many** assigned tickets at once, one PR-gated step each. For every in-flight assigned ticket it resolves the PR review state (via the same `scripts/qrspi_resolve_state.py` resolver `/qrspi-work` uses) and runs the **autonomously-runnable** actions: `run_design`, `advance`, `submit`, `land`, and the automatic `reset` discard. It deliberately **leaves the human-dependent actions alone** — it does not perform the manual `revise`, and it does nothing for tickets in `wait` (awaiting a human review). Use it after assigning tickets and moving them to `Selected`, or after approving phase PRs.

---

## Hard rules

- Phases are sequential. Never skip ahead.
- Each phase is its own PR and must be approved (APPROVED + zero unresolved threads) before the next phase is built on top.
- Approval lives in the PR, not in Linear. The orchestrator auto-advances on approval but never advances a PR awaiting review.
- `revise` (addressing feedback) is manual; `reset` (discarding downstream work after an upstream change request) is automatic.
- Nothing merges mid-feature — the stack lands bottom-up only when every PR is ready.
- Run `/clear` between every implementation slice.
- If context exceeds 40%, run `/compact` or start a fresh session. Use `/context` to check utilization.

---

## Phase 0 — Ticket

**Command:** `/qrspi-ticket <initial description>`

**Creates:** a Linear issue in your Linear team, QRSPI project (e.g., `RUS-42`)

**Skill definition:** [.claude/skills/qrspi-ticket/SKILL.md](../.claude/skills/qrspi-ticket/SKILL.md)

Start every feature here. Describe what you want to build in one sentence or a few. The agent works back and forth with you until it has enough to draft a structured ticket, then creates the Linear issue. The Linear ID it returns (e.g., `RUS-42`) is what you pass to every subsequent phase.

### What the agent produces

A well-formed Linear issue with: Title, Description, Acceptance Criteria, Constraints, and Out of Scope.

### What to review

- Does the title clearly convey the feature?
- Are acceptance criteria testable and observable (not vague goals)?
- Are constraints real — not invented?
- Is Out of Scope explicit enough to prevent scope creep?

**Example tickets** (local fixtures used for evals — illustrative of well-formed ticket content):

| Fixture | Scenario |
|---------|----------|
| [ticket_rest_endpoint.md](../evals/fixtures/ticket_rest_endpoint.md) | Simple REST endpoint with auth |
| [ticket_multi_tenancy.md](../evals/fixtures/ticket_multi_tenancy.md) | Cross-cutting architectural change |
| [ticket_websocket.md](../evals/fixtures/ticket_websocket.md) | Real-time infrastructure addition |
| [ticket_15_acceptance_criteria.md](../evals/fixtures/ticket_15_acceptance_criteria.md) | Complex feature with many criteria |

---

## Phase 1 — Questions  *(design PR)*

**Command:** `/qrspi-questions <ticket-id>`

**Reads:** the ticket, fetched from Linear

**Writes:** `.qrspi/<ticket-id>/questions.md`

**Agent definition:** [.claude/agents/qrspi-questions.md](../.claude/agents/qrspi-questions.md)

### What the agent produces

8–15 technical questions organized into categories: Data Flow, API Surface, State Management, Edge Cases, Testing, Observability. Each question names a specific file or module as its target. No solution language — questions are purely investigative.

> **Firewall:** the questions agent cannot explore the codebase. `Glob`, `Grep`, and `Bash` are excluded from its tools, so it must derive questions from the ticket alone.

### Output format

```markdown
# Questions — <ticket title>
**Ticket:** <ticket-id>
**Generated:** <ISO-8601>
**Status:** draft

## Data Flow
- Q1: How does X currently flow through the system?
  **Target:** src/services/foo.ts

## Edge Cases
- Q8: What happens when Y is null?
  **Target:** the module responsible for Y validation
...
```

### What to review

- Are all acceptance criteria covered by at least one question?
- Does every question target a specific file or module?
- Is there at least 1 Observability question and 2 Edge Cases questions?
- Are questions free of solution language ("should we", "we could")?

---

## Phase 2 — Research  *(design PR)*

**Command:** `/qrspi-research <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/questions.md` *(the ticket is intentionally hidden)*

**Writes:** `.qrspi/<ticket-id>/research.md`

**Agent definition:** [.claude/agents/qrspi-research.md](../.claude/agents/qrspi-research.md)

### What the agent produces

A factual codebase map: one section per question, answered with file paths, function signatures, data types, and call chains. Code snippets are kept under 20 lines and always include `file:line` citations.

> **Firewall:** the research agent cannot read the ticket and has no Linear access. This anchoring-prevention firewall is enforced two ways — the agent's tool definition excludes the Linear MCP and ticket reads, and the orchestrator never passes ticket content into the research input contract. The agent gathers facts without forming implementation opinions.

### Output format

```markdown
# Research — Codebase Map
**Questions source:** questions.md @ <timestamp>
**Generated:** <ISO-8601>
**Status:** draft

## Q1: <question text>
**Answer:** <facts>
**Evidence:** `file:line` — <snippet>
**Dependencies:** <upstream / downstream modules>
**Implicit contracts:** <conventions observed>

...

## Discovered Patterns
...

## Inconsistencies
...
```

### What to review

- Are answers factual with `file:line` citations (not opinions)?
- Is any question marked `NOT FOUND`? If so, should it be answered before proceeding?
- Are the Discovered Patterns and Inconsistencies sections present?

---

## Phase 3 — Design  *(design PR — submitted for review here)*

**Command:** `/qrspi-design <ticket-id>`

**Reads:** the ticket (fetched from Linear), `questions.md`, `research.md`

**Writes:** `.qrspi/<ticket-id>/design.md`

**Agent definition:** [.claude/agents/qrspi-design.md](../.claude/agents/qrspi-design.md)

> **This is the highest-leverage review point.** Errors caught here are cheap. Errors found during implementation are expensive. Design is the last artifact in the design PR: once it's committed, the `<id>/design` PR is submitted and the ticket projects to **Design Review**. A `CHANGES_REQUESTED` here later resets and discards any plan/slice work stacked above.

### What the agent produces

A ~200-line design document (hard max 300 lines) in prose and tables — no code blocks. Every claim in the Current State section cites a specific research answer. Every acceptance criterion from the ticket appears in Desired End State. Pattern Decisions explicitly flag any choice that introduces a new pattern not already in the codebase.

### Output format

```markdown
# Design — <ticket title>
**Ticket:** <ticket-id>
**Status:** draft

## Current State
<Prose with (ref: Q1) citations on every claim>

## Desired End State
<Maps each acceptance criterion to system behavior>

## Delta
<New files, modified files, new queries — no code>

## Pattern Decisions
| Decision | Option A | Option B | Recommendation | Notes |
|----------|----------|----------|----------------|-------|
| ...      | ...      | ...      | Option A       | NEW PATTERN if applicable |

## Risk Register
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| ...  | ...        | ...    | ...        |

## Open Questions
<Things only a human can answer>
```

### What to review (the design PR)

- Does every Current State sentence have a `(ref: QN)` citation?
- Does every acceptance criterion appear in Desired End State?
- Are NEW PATTERN flags legitimate — do they need broader team discussion?
- Are the risks realistic and the mitigations actionable?
- Review the `<id>/design` PR on GitHub. **Approving it** (with no unresolved threads) auto-advances the orchestrator into the plan phase — there is no Linear status to flip. A formal `CHANGES_REQUESTED` sends it back to revise the design.

---

## Phase 4 — Structure  *(plan PR)*

**Command:** `/qrspi-structure <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/design.md`

**Writes:** `.qrspi/<ticket-id>/structure.md`

**Agent definition:** [.claude/agents/qrspi-structure.md](../.claude/agents/qrspi-structure.md)

### What the agent produces

Vertical slices — each one delivers a testable end-to-end path through the system (not a horizontal layer like "all DB changes"). Each slice lists: Goal, Files touched (new/modify), Verification step, Context cost (S/M/L), and Dependencies on other slices. Slices are ordered so dependencies flow forward. No slice touches more than 10 files.

### Output format

```markdown
# Structure — <ticket title>

## Slice 1: <name>
**Goal:** <what this slice proves works end-to-end>
**Files:**
  - new: src/routes/foo.ts
  - modify: src/middleware/auth.ts
**Verification:** `npm test -- --grep "foo route"`
**Context cost:** S
**Depends on:** none

## Slice 2: <name>
...

## Contracts
<Cross-slice interfaces: types, function signatures (pseudo-code, not implementations)>

## Unverified Assumptions
<Claims from design.md that can't be mapped to concrete code>
```

### What to review

- Are slices vertical (end-to-end), not horizontal (by layer)?
- Does each slice have a runnable verification step?
- Is any slice too large (> 10 files)? Ask to split it.
- Are cross-slice contracts (types, function signatures) clearly defined?

---

## Phase 5 — Plan  *(plan PR)*

**Command:** `/qrspi-plan <ticket-id>`

**Reads:** `structure.md`, `design.md` (reference only)

**Writes:** `.qrspi/<ticket-id>/plan.md`

**Agent definition:** [.claude/agents/qrspi-plan.md](../.claude/agents/qrspi-plan.md)

### What the agent produces

Atomic implementation steps — one file, one action per step. Steps reference exact types and signatures from structure.md. Each slice ends with a runnable Verify checkpoint. DB migrations and destructive operations include Rollback Notes. Total steps must not exceed 100 (if exceeded, structure slices are too large).

### Output format

```markdown
# Plan — <ticket title>

## Slice 1: <name>

### Step 1.1
**Action:** Create new file
**File:** src/routes/preferences.ts
**Purpose:** Define GET handler for /api/users/:id/preferences

### Step 1.2
**Action:** Modify existing function
**File:** src/middleware/auth.ts
**Current:** `function checkAuth(req): boolean`
**After:** `function checkAuth(req, resourceOwnerId?: string): boolean`

### Verify Slice 1
```bash
npm test -- --grep "preferences route"
```

## Rollback Notes

...

```

### What to review

- This is a spot-check, not a deep review — major alignment happened in Design.
- Are steps atomic (one file, one action)?
- Are there verify checkpoints at the end of each slice?
- Are rollback notes present for any DB migrations or config changes?

---

## Phase 6 — Worktree  *(plan PR — submitted for review here)*

**Command:** `/qrspi-worktree <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/plan.md`

**Writes:** `.qrspi/<ticket-id>/worktree.md`

**Agent definition:** [.claude/agents/qrspi-worktree.md](../.claude/agents/qrspi-worktree.md)

### What the agent produces

A session-aware task DAG. Each plan step becomes a task with: ID, Description, Depends On, Plan Step reference, Cost (S/M/L), and Status. Tasks are grouped into sessions. Each session has a Load Manifest listing only the artifact sections needed (not whole files) and a context budget. SESSION BOUNDARY markers explain why a new session starts. The critical path is listed at the top.

This is the last artifact in the plan PR: once it's committed, the `<id>/plan` PR (stacked on the approved design PR) is submitted and the ticket projects to **Plan Review**.

### Output format

```markdown
# Worktree — <ticket title>

## Critical Path
T1 → T3 → T5 → T8

## Session 1
**Load manifest:**
- structure.md § Slice 1, § Contracts
- plan.md § Slice 1

| Task | Description | Depends On | Plan Step | Cost | Status |
|------|-------------|-----------|-----------|------|--------|
| T1   | Create preferences route | — | 1.1 | S | pending |
| T2   | Add auth check | T1 | 1.2 | S | pending |

---SESSION BOUNDARY---
**Reason:** Slice 2 introduces DB layer — fresh context prevents drift

## Session 2
...
```

### What to review (the plan PR)

- Does each session have a Load Manifest with only the sections it needs?
- Are session boundaries placed at natural seams (slice boundaries, layer transitions)?
- Is the critical path correct?
- Will each session stay under its context budget (under 40% utilization)?
- Review the `<id>/plan` PR on GitHub. **Approving it** (with no unresolved threads) auto-advances the orchestrator into implementation. A `CHANGES_REQUESTED` here resets to the plan phase (and discards any slice work above it); a change request on the *design* PR below resets even further, discarding both plan and slices.

---

## Phase 7 — Implement

**Command:** `/qrspi-implement <ticket-id> <slice-number>`

**Reads (scoped):** `structure.md` (Slice N + Contracts only), `plan.md` (Slice N only), `worktree.md` (this session only), `impl-log.md` (previous slice notes only)

**Writes:** code changes + appends to `.qrspi/<ticket-id>/impl-log.md`

**Agent definition:** [.claude/agents/qrspi-implement.md](../.claude/agents/qrspi-implement.md)

> **One slice per fresh session.** When running phases manually, `/clear` before starting each slice.

### What the agent produces

Working code for one vertical slice, verified against the plan's Verify checkpoint. Any deviation from structure.md contracts is reported — not silently changed. Results are appended to `impl-log.md`. Each slice becomes its own stacked PR.

### impl-log entry format

```markdown
## Slice 1 — 2026-04-18T14:30:00Z
**Tasks completed:** T1, T2, T3
**Tasks failed:** none
**Tests:** npm test -- --grep "preferences route" → 4 passed, 0 failed
**Deviations from structure.md:** none
**Deviations from plan.md:** none
**Notes for next session:** UserPreference type is exported from src/types/user.ts, not generated
```

### What to review after each slice

- Did tests pass? If not, read the failure output before proceeding.
- Are deviations from structure.md explained?
- Are there notes for the next session that need to carry forward?
- When running manually, `/clear` before the next slice.

### Repeating for multiple slices (manual path)

```
/clear
/qrspi-implement <ticket-id> 1

# review, then:
/clear
/qrspi-implement <ticket-id> 2

# repeat for each slice
```

Under `/qrspi-work`, once the plan PR is approved the orchestrator runs all slices and submits the stacked slice PRs automatically (one PR per slice, stacked on the plan PR).

---

## Phase 8 — PR

**Command:** `/qrspi-pr <ticket-id>`

**Reads:** `impl-log.md`, `design.md` (risk register), `structure.md` (contracts), git diff

**Writes:** `.qrspi/<ticket-id>/pr-summary.md`

**Agent definition:** [.claude/agents/qrspi-pr.md](../.claude/agents/qrspi-pr.md)

### What the agent produces

A complete PR description mapping every acceptance criterion from the ticket to an implementation file and a test. Every file in the git diff is accounted for. The risk register from Design is updated with implementation findings. The summary becomes the body of the bottom slice PR.

### Output format

```markdown
# PR Summary — <ticket title>
**PR title:** <72 characters max>

## Summary
<3–5 sentences: what changed, why, reviewer focus areas>

## Acceptance Criteria Mapping
| Criterion | Implementation File | Test |
|-----------|-------------------|------|
| GET /api/users/:id/preferences returns prefs | src/routes/preferences.ts | test/routes/preferences.test.ts |

## Changes by Slice
| Slice | File | Change Type | Lines |
|-------|------|------------|-------|

## Testing Summary
- [ ] `npm test -- --grep "preferences route"` → 4 passed

## Deviations from Structure
| Deviation | Reason |
|-----------|--------|
| none      |        |

## Risks & Rollback
...

## Open Items
...
```

### What to review

- Does every acceptance criterion have a mapping?
- Is every file in the git diff accounted for?
- Read and own the code before approving — the PR summary does not substitute for code review.
- Review the slice PRs on GitHub. The stack lands only when **every** PR in it is approved + clean; at that point the orchestrator's `land` action merges the whole stack bottom-up and projects the ticket to **Done**. No PR merges mid-feature.

---

## Context Management

| Utilization | Status | Action |
|-------------|--------|--------|
| < 40% | GREEN | Continue |
| 40–60% | YELLOW | Consider `/compact` |
| > 60% | RED | Start a new session with `/clear` |

Use `/context` to check current utilization. Use `/compact` to summarize without losing state. When running implementation manually, a fresh `/clear` between slices is the norm regardless of utilization.

---

## Quick Reference

```bash
# Start a new feature → creates a Linear issue (e.g., RUS-42)
/qrspi-ticket "brief description of the feature"

# Autonomous path: drive the ticket one PR-gated step forward.
# Run it, let a human review/approve the resulting PR, then run it again — it picks up
# from the live PR review state and auto-advances on each approval.
/qrspi-work RUS-42

# --- or, the manual phase-by-phase path ---

# Design PR (questions → research → design) on <id>/design, then human review on GitHub
/qrspi-questions RUS-42          # → questions.md
/qrspi-research RUS-42           # → research.md
/qrspi-design RUS-42             # → design.md  → submit <id>/design PR → Design Review

# (human approves the design PR on GitHub)

# Plan PR (structure → plan → worktree) on <id>/plan, stacked on design
/qrspi-structure RUS-42          # → structure.md
/qrspi-plan RUS-42               # → plan.md
/qrspi-worktree RUS-42           # → worktree.md → submit <id>/plan PR → Plan Review

# (human approves the plan PR on GitHub)

# Implement each slice (clear between each) on stacked <id>/slice-N branches, then PR summary
/clear && /qrspi-implement RUS-42 1
/clear && /qrspi-implement RUS-42 2
# ...
/qrspi-pr RUS-42                 # → pr-summary.md (body of the bottom slice PR)

# (human approves every slice PR → the stack lands bottom-up → Done)
```

---

## Further Reading

| Document | Purpose |
|----------|---------|
| [qrspi_claude_code_guide.md](qrspi_claude_code_guide.md) | Why QRSPI exists, common mistakes, troubleshooting, adapting, team adoption |
| [qrspi_working_example.md](qrspi_working_example.md) | Complete annotated example of one feature through all phases |
