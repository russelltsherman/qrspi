# QRSPI Orientation Guide

QRSPI is a structured workflow for AI-assisted feature development. It enforces nine sequential phases — Ticket, Questions, Research, Design, Structure, Plan, Worktree, Implement, PR — before and during coding. The goal is to spend upfront alignment time so that implementation integrates cleanly on the first attempt.

This guide walks through every step. Each phase shows what goes in, what comes out, and where to find examples.

---

## Prerequisites

- Claude Code CLI installed and authenticated
- This repository cloned locally

---

## Directory Layout

```txt
.qrspi/<ticket-id>/        ← all artifacts for a ticket live here
  ticket.md                ← phase 0 output (authored via /qrspi-ticket)
  questions.md             ← phase 1 output
  research.md              ← phase 2 output
  design.md                ← phase 3 output
  structure.md             ← phase 4 output
  plan.md                  ← phase 5 output
  worktree.md              ← phase 6 output
  impl-log.md              ← phase 7 output (appended per slice)
  pr-summary.md            ← phase 8 output

.claude/skills/            ← skill prompt definitions (one per phase)
evals/fixtures/            ← example tickets you can learn from
docs/                      ← extended documentation
```

---

## Phase 0 — Ticket

**Command:** `/qrspi-ticket <initial description>`

**Writes:** `.qrspi/<ticket-id>/ticket.md`

**Skill definition:** [.claude/skills/qrspi-ticket/SKILL.md](../.claude/skills/qrspi-ticket/SKILL.md)

Start every feature here. Describe what you want to build in one sentence or a few. The agent will work back and forth with you — asking at most two questions at a time — until it has enough to fill all required fields. The ticket ID is assigned automatically (sequential, e.g. T001, T002).

### What the agent produces

A well-formed ticket with: Title, Description, Acceptance Criteria, Constraints, and Out of Scope. The ticket ID and directory are created automatically.

### Output format

```markdown
# Ticket: <TICKET-ID>

## Title
<one-line summary, max 80 chars>

## Description
<2–5 paragraphs: what problem does this solve, who is affected>

## Acceptance Criteria
- [ ] Specific, testable, observable outcome
- [ ] Measurable where possible (e.g. "< 200ms at p95")
- [ ] Auth/permissions behaviors listed explicitly

## Constraints
- Things the implementation MUST or MUST NOT do
- Existing patterns, tables, or middleware to reuse or avoid

## Out of Scope
- Adjacent work that is explicitly excluded
- Follow-on tickets or deferred concerns
```

### What to review

- Does the title clearly convey the feature?
- Are acceptance criteria testable and observable (not vague goals)?
- Are constraints real — not invented?
- Is Out of Scope explicit enough to prevent scope creep?

**Examples:**

| Ticket | Scenario |
|--------|----------|
| [ticket_rest_endpoint.md](../evals/fixtures/ticket_rest_endpoint.md) | Simple REST endpoint with auth |
| [ticket_multi_tenancy.md](../evals/fixtures/ticket_multi_tenancy.md) | Cross-cutting architectural change |
| [ticket_websocket.md](../evals/fixtures/ticket_websocket.md) | Real-time infrastructure addition |
| [ticket_15_acceptance_criteria.md](../evals/fixtures/ticket_15_acceptance_criteria.md) | Complex feature with many criteria |

---

## Workflow Overview

```txt
  0. Ticket     →  ticket.md           ← conversational; auto-assigns ID
     │  (approved)
     ▼
  1. Questions  →  questions.md
     │  (approved)
     ▼
  2. Research   →  research.md
     │  (approved)
     ▼
  3. Design     →  design.md          ← highest-leverage review
     │  (approved)
     ▼
  4. Structure  →  structure.md
     │  (approved)
     ▼
  5. Plan       →  plan.md
     │  (approved)
     ▼
  6. Worktree   →  worktree.md
     │  (approved)
     ▼
  7. Implement  →  impl-log.md + code  (one /clear per slice)
     │  (all slices done)
     ▼
  8. PR         →  pr-summary.md
```

**Hard rules:**

- Phases are sequential. Never skip ahead.
- Each artifact must be reviewed and approved before the next phase starts.
- Say `"approved"` to advance to the next phase.
- Run `/clear` between every implementation slice.
- If context exceeds 40%, run `/compact` or start a fresh session.

---

## Phase 1 — Questions

**Command:** `/qrspi-questions <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/ticket.md`

**Writes:** `.qrspi/<ticket-id>/questions.md`

**Skill definition:** [.claude/skills/qrspi-questions/SKILL.md](../.claude/skills/qrspi-questions/SKILL.md)

### What the agent produces

8–15 technical questions organized into categories: Data Flow, API Surface, State Management, Edge Cases, Testing, Observability. Each question names a specific file or module as its target. No solution language — questions are purely investigative.

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

## Phase 2 — Research

**Command:** `/qrspi-research <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/questions.md` *(ticket.md is intentionally hidden)*

**Writes:** `.qrspi/<ticket-id>/research.md`

**Skill definition:** [.claude/skills/qrspi-research/SKILL.md](../.claude/skills/qrspi-research/SKILL.md)

### What the agent produces

A factual codebase map: one section per question, answered with file paths, function signatures, data types, and call chains. Code snippets are kept under 20 lines and always include `file:line` citations. The ticket is hidden during this phase so the agent gathers facts without forming implementation opinions.

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

## Phase 3 — Design

**Command:** `/qrspi-design <ticket-id>`

**Reads:** `ticket.md`, `questions.md`, `research.md`

**Writes:** `.qrspi/<ticket-id>/design.md`

**Skill definition:** [.claude/skills/qrspi-design/SKILL.md](../.claude/skills/qrspi-design/SKILL.md)

> **This is the highest-leverage review point.** Errors caught here are cheap. Errors found during implementation are expensive.

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

### What to review

- Does every Current State sentence have a `(ref: QN)` citation?
- Does every acceptance criterion appear in Desired End State?
- Are NEW PATTERN flags legitimate — do they need broader team discussion?
- Are the risks realistic and the mitigations actionable?
- Edit any section that is wrong before approving.

---

## Phase 4 — Structure

**Command:** `/qrspi-structure <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/design.md`

**Writes:** `.qrspi/<ticket-id>/structure.md`

**Skill definition:** [.claude/skills/qrspi-structure/SKILL.md](../.claude/skills/qrspi-structure/SKILL.md)

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

## Phase 5 — Plan

**Command:** `/qrspi-plan <ticket-id>`

**Reads:** `structure.md`, `design.md` (reference only)

**Writes:** `.qrspi/<ticket-id>/plan.md`

**Skill definition:** [.claude/skills/qrspi-plan/SKILL.md](../.claude/skills/qrspi-plan/SKILL.md)

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

## Phase 6 — Worktree

**Command:** `/qrspi-worktree <ticket-id>`

**Reads:** `.qrspi/<ticket-id>/plan.md`

**Writes:** `.qrspi/<ticket-id>/worktree.md`

**Skill definition:** [.claude/skills/qrspi-worktree/SKILL.md](../.claude/skills/qrspi-worktree/SKILL.md)

### What the agent produces

A session-aware task DAG. Each plan step becomes a task with: ID, Description, Depends On, Plan Step reference, Cost (S/M/L), and Status. Tasks are grouped into sessions. Each session has a Load Manifest listing only the artifact sections needed (not whole files). SESSION BOUNDARY markers explain why a new session starts. The critical path is listed at the top.

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

### What to review

- Does each session have a Load Manifest with only the sections it needs?
- Are session boundaries placed at natural seams (slice boundaries, layer transitions)?
- Is the critical path correct?
- Will each session stay under 40% context utilization?

---

## Phase 7 — Implement

**Command:** `/qrspi-implement <ticket-id> <slice-number>`

**Reads (scoped):** `structure.md` (Slice N + Contracts only), `plan.md` (Slice N only), `worktree.md` (this session only), `impl-log.md` (previous slice notes only)

**Writes:** code changes + appends to `.qrspi/<ticket-id>/impl-log.md`

**Skill definition:** [.claude/skills/qrspi-implement/SKILL.md](../.claude/skills/qrspi-implement/SKILL.md)

> **Always run `/clear` before starting each slice.**

### What the agent produces

Working code for one vertical slice, verified against the plan's Verify checkpoint. Any deviation from structure.md contracts is reported — not silently changed. Results are appended to `impl-log.md`.

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
- Run `/clear` before the next slice.

### Repeating for multiple slices

```
/clear
/qrspi-implement <ticket-id> 1

# review, then:
/clear
/qrspi-implement <ticket-id> 2

# repeat for each slice
```

---

## Phase 8 — PR

**Command:** `/qrspi-pr <ticket-id>`

**Reads:** `impl-log.md`, `design.md` (risk register), `structure.md` (contracts), git diff

**Writes:** `.qrspi/<ticket-id>/pr-summary.md`

**Skill definition:** [.claude/skills/qrspi-pr/SKILL.md](../.claude/skills/qrspi-pr/SKILL.md)

### What the agent produces

A complete PR description mapping every acceptance criterion from the ticket to an implementation file and a test. Every file in the git diff is accounted for. The risk register from Design is updated with implementation findings.

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
- Read and own the code before merging — the PR summary does not substitute for code review.

---

## Context Management

| Utilization | Status | Action |
|-------------|--------|--------|
| < 40% | GREEN | Continue |
| 40–60% | YELLOW | Consider `/compact` |
| > 60% | RED | Start a new session with `/clear` |

Use `/context` to check current utilization. Use `/compact` to summarize without losing state. A fresh `/clear` is mandatory between every implementation slice regardless of utilization.

---

## Quick Reference

```bash
# Start a new feature (ticket ID assigned automatically)
/qrspi-ticket "brief description of the feature"
# → converse until approved → ticket.md written to .qrspi/T00N/

# Run the phases (replace T001 with your assigned ticket ID)
/qrspi-questions T001            # → questions.md, then say "approved"
/qrspi-research T001             # → research.md, then say "approved"
/qrspi-design T001               # → design.md, then say "approved"
/qrspi-structure T001            # → structure.md, then say "approved"
/qrspi-plan T001                 # → plan.md, then say "approved"
/qrspi-worktree T001             # → worktree.md, then say "approved"

# Implement each slice (clear between each)
/clear && /qrspi-implement T001 1
/clear && /qrspi-implement T001 2
# ...

# Finish
/qrspi-pr T001                   # → pr-summary.md
```

---

## Further Reading

| Document | Purpose |
|----------|---------|
| [guide.md](guide.md) | Why QRSPI exists, common mistakes, troubleshooting, adapting, team adoption |
| [qrspi_working_example.md](qrspi_working_example.md) | Complete annotated example of one feature through all 9 phases |
