# QRSPI System: Practical Application Guide

How to actually use the QRSPI workflow with AI agents to build features reliably. This is an educational walkthrough, not a reference document.

---

## Part 1: Understanding the System's Purpose

Before diving into mechanics, understand what problem QRSPI solves.

### The Core Problem It Solves

**Without QRSPI:**

```txt
Engineer says: "Build a real-time notification system"
Agent hallucinates and produces:
  ✗ Code that doesn't integrate with existing event system
  ✗ Data models incompatible with replication lag
  ✗ Authentication pattern that doesn't match existing codebase
  ✗ Architecture that requires refactoring after 4 hours

Result: Agent output is plausible but broken. Engineer spends 2x time fixing than writing from scratch.
```

**With QRSPI:**

```txt
Engineer guides agent through the QRSPI phases, each gated by its own pull request:
  Ticket:     What are we building? (10-20 min, conversational ticket authoring → Linear issue)
  --- Design PR (<id>/design) — runs autonomously, then stops for review ---
  Questions:  What do we need to ask? (20 min)
  Research:   What does the codebase actually do? (45 min, ticket hidden)
  Design:     How does this fit? (40 min)
  ==> DESIGN PR: human approves it → the plan PR auto-builds stacked on top
  --- Plan PR (<id>/plan, stacked on design) ---
  Structure:  How do we build this in testable slices? (30 min)
  Plan:       What's the atomic step-by-step plan? (40 min)
  Worktree:   What's the session-aware task DAG? (varies)
  ==> PLAN PR: human approves it → the slice PRs auto-build stacked on top
  --- Slice PRs (<id>/slice-1..N, stacked on plan) ---
  Implement:  Build it, one slice per fresh session (follows plan exactly)
  PR:         Summarize for reviewers (no surprises)
  ==> All PRs approved → land the whole stack bottom-up

Result: Code integrates seamlessly, estimates are accurate, PRs have zero surprises.

Time investment: +2.5 hours upfront → -4 hours debugging → Net: 1.5 hours saved per feature
More importantly: Code quality is higher, architectural debt is lower, confidence is higher.
```

### The Key Insight

**QRSPI shifts the cost curve.**

```txt
Traditional (unstructured prompting):
  Upfront time: 30 min (quick to start)
  Debugging time: 4-5 hours (surprises everywhere)
  Total: 4.5-5.5 hours
  Quality: Medium (hallucinations surface in code review)
  
QRSPI:
  Alignment time: 2.5 hours (front-loaded)
  Implementation time: 3 hours (follows plan, fewer surprises)
  Review time: 30 min (no surprises)
  Total: 6 hours (seems longer!)
  Quality: High (hallucinations caught in design phase, not code)
```

**But here's the catch:** The 6-hour estimate assumes the codebase is unfamiliar or the feature is complex. For a simple feature on familiar code, QRSPI might take 4 hours total (1.5 hours alignment + 2 hours implementation + 30 min review).

**The ROI equation:**

- Feature complexity < Medium: QRSPI adds overhead (skip it for simple CRUD)
- Feature complexity = Medium to High: QRSPI saves time (use it)
- Feature complexity > High (distributed systems, migrations, refactors): QRSPI is essential (must use it)

---

## Part 2: How to Start (Quickstart)

### The Fastest Path: Two Commands

In day-to-day use you don't drive the phases by hand. Two commands cover almost everything:

1. **`/qrspi-ticket <brief description>`** — author a Linear ticket through guided conversation.
2. **`/qrspi-work <ticket-id>`** — the autonomous orchestrator. It reads the ticket's **PR review
   state** (not its Linear status), figures out which action is next, and runs it. Call it
   repeatedly to push the ticket forward; it advances automatically when a phase PR is approved
   and stops on its own whenever a PR is awaiting review.

The rest of this Part walks the phases one at a time, because understanding what `/qrspi-work`
does under the hood is how you learn to review its output well. Every individual phase also has
its own slash command (`/qrspi-questions`, `/qrspi-research`, etc.) if you want to re-run a single
step manually.

### The Phase Map

There are nine phases. The ticket lives in Linear; the other eight produce artifacts grouped into
three stacked pull requests — design, plan, and the slice PRs:

```txt
Ticket (T)         → Linear issue, authored conversationally
--- DESIGN PR  (branch <id>/design, off trunk) ---
Questions (Q)      → questions.md      (20 min)
Research  (R)      → research.md       (45 min; ticket hidden)
Design    (D)      → design.md         (40 min)
  ==> approve the Design PR → plan PR auto-builds stacked on top
--- PLAN PR  (branch <id>/plan, stacked on <id>/design) ---
Structure (S)      → structure.md      (30 min)
Plan      (P)      → plan.md           (40 min)
Worktree  (W)      → worktree.md       (varies)
  ==> approve the Plan PR → slice PRs auto-build stacked on top
--- SLICE PRs  (branches <id>/slice-1..N, stacked on <id>/plan) ---
Implement (I)      → code + impl-log.md (one slice per fresh session)
PR        (PR)     → pr-summary.md
  ==> all PRs approved → land the whole stack bottom-up
```

The planning artifacts are NOT optional add-ons. The first three (questions, research, design)
form the Design PR on branch `<id>/design`; the next three (structure, plan, worktree) form the
Plan PR on branch `<id>/plan`, stacked on top of design. Each phase is its own branch and its own
PR — there is no single combined planning branch. The whole stack is held open (nothing merges to
trunk) until every PR is approved, then landed bottom-up.

### Step 1: Draft Your Ticket

Run `/qrspi-ticket <brief description>` and work with the agent conversationally until a
**Linear issue** is created in the Russelltsherman team, QRSPI project. The agent assigns the
Linear ID (e.g., `RUS-42`) — there is no local `ticket.md`. The ticket holds the problem
statement; QRSPI artifacts are stored locally under `.qrspi/<ticket-id>/`, while Linear holds
only status and phase-transition comments.

### Step 2: Identify Your Feature

Confirm the ticket reflects a medium-complexity feature. Avoid:

- Super simple features (one file change)
- Greenfield rewrites (no codebase to research)
- Crisis/hotfix mode (no time for alignment)

**Good candidates:**

- Add payment method management (new model, new endpoints, new UI)
- Implement rate limiting (infrastructure change, multiple touch points)
- Add real-time notifications (distributed systems complexity)

### Step 3: Set Up Your Tooling

QRSPI runs in the Claude Code CLI. The phases need:

- **Access to your codebase** (the research phase reads it; the ticket is hidden from research)
- **Linear MCP** configured for the Russelltsherman workspace (the entry gate — a ticket may
  begin only when it is *assigned* and in `Selected` — plus best-effort status reporting)
- **Graphite (`gt`)** for stacked PRs and **GitHub CLI (`gh`)** for PR operations (PR review state
  is the real driver of the workflow)
- **A human feedback loop on each phase PR** (you review and approve — or request changes on —
  the design, plan, and slice PRs)

The phase logic lives in purpose-built agents under `.claude/agents/qrspi-<phase>.md`, each with
its own per-phase tool lockdown. The slash commands you type (`/qrspi-questions`, `/qrspi-design`,
…) are thin wrappers under `.claude/skills/qrspi-<phase>/SKILL.md` that invoke those agents. You
rarely call the per-phase commands directly — `/qrspi-work` spawns the typed agents for you.

The "what do I do next?" decision is **not** a hand-coded Linear-status state machine. Both
`/qrspi-work` and the batch workflow gather PR review state with `scripts/qrspi_pr_state.py`
(which reads `reviewDecision` and unresolved `reviewThreads` via the GitHub GraphQL API) and feed
it to the tested resolver `scripts/qrspi_resolve_state.py`, which returns the next action
(`run_design`, `advance`, `submit`, `wait`, `revise`, `reset`, or `land`). That resolver carries
the unit tests; the `evals/` harness is a non-functional placeholder, so verification is unit
tests plus a manual end-to-end run.

#### **Two ways to drive the workflow:**

##### **Option A: Autonomous orchestrator (recommended)**

Let `/qrspi-work` resolve PR state and run the next action for you:

```txt
1. Run /qrspi-ticket <brief description> to author the Linear ticket; assign it and move
   it to Selected (this is the entry gate)
2. Run /qrspi-work <ticket-id> — it runs the design phase, opens the Design PR
   (<id>/design), and reports Design Review in Linear
3. Review and APPROVE the Design PR on GitHub
4. Run /qrspi-work <ticket-id> again — seeing the Design PR approved + clean, it
   auto-advances: builds the plan phase, opens the Plan PR (<id>/plan, stacked), reports
   Plan Review
5. Review and APPROVE the Plan PR
6. Run /qrspi-work <ticket-id> once more — it builds the slice PRs (<id>/slice-1..N,
   stacked) and reports Code Review
7. Approve every slice PR; run /qrspi-work <ticket-id> a final time — it lands the whole
   stack bottom-up and reports Done
```

Advancement is driven entirely by PR approval: there are no `Approved` statuses to flip in Linear.
Approving a phase PR is what unlocks the next phase.

##### **Option B: Phase-by-phase (manual / learning)**

Invoke each phase command yourself, starting a fresh `/clear` session where noted. You still
approve each PR on GitHub between phases:

```txt
1. /qrspi-questions <ticket-id>   for Questions
2. /clear, then /qrspi-research <ticket-id>   for Research (ticket hidden)
3. /qrspi-design <ticket-id>      for Design  → submit & approve the Design PR
4. /qrspi-structure <ticket-id>   for Structure
5. /qrspi-plan <ticket-id>        for Plan
6. /qrspi-worktree <ticket-id>    for Worktree  → submit & approve the Plan PR
7. /qrspi-implement <ticket-id> <slice-number>   one slice per fresh session
8. /qrspi-pr <ticket-id>          for the PR summary  → approve all slice PRs, then land
```

Each command fetches the inputs it needs (the ticket from Linear, prior artifacts from
`.qrspi/<ticket-id>/`) and writes its artifact automatically.

##### **Driving many tickets at once: batch**

`.claude/workflows/qrspi-batch.js` drives every assigned in-flight ticket one PR-gated step
forward. For each ticket it resolves the PR review state (via the same tested resolver
`/qrspi-work` uses) and spawns the typed phase agents directly from the workflow script. It runs
only the autonomously-runnable actions — `run_design` (entry gate satisfied), `advance` (a phase
PR was approved), `submit`, `land`, and the automatic `reset`/discard — and deliberately leaves
the human turns alone: it does not perform the manual `revise`, and it does nothing for a ticket
whose active PR is still awaiting review (`wait`). Use it after assigning tickets and moving them
to `Selected`, or after approving a batch of phase PRs.

### Step 4: Run Phase 1 (Questions)

**Your action:**

1. Run `/qrspi-questions <ticket-id>` (or provide the ticket to Claude and ask for exploration questions)
2. Wait for output

**What you'll get:**

```markdown
# Codebase Exploration Questions

## Category 1: Authentication
### Q1.1: How are users currently identified...
### Q1.2: What auth mechanisms exist...

## Category 2: Database
### Q2.1: What ORM is in use...
```

**How to validate it's good:**

- [ ] 8-15 questions (count them)
- [ ] Each references specific files
- [ ] Zero "should" language
- [ ] Spans multiple system areas (auth, DB, API, services)

**If validation fails:**

- Too few questions? → "Generate 5 more specific questions about [area]"
- Generic questions? → "Make each question reference specific filenames, not just 'the API'"
- Not spanning codebase? → "Add questions about [missing area]"

**Time investment:** 20 minutes

---

### Step 5: Run Phase 2 (Research)

**Your action:**

1. Run `/clear`, then `/qrspi-research <ticket-id>` (or provide questions.md to Claude and ask for a factual codebase map)
2. Wait for output

**The research firewall:** the research phase cannot read the ticket and has no Linear access.
This is deliberate — it prevents the agent from anchoring its codebase map to the feature's
intended shape. Research answers the questions purely from what the code actually does. (The
questions phase has the complementary firewall: it cannot explore the codebase.)

**What you'll get:**

```markdown
# Codebase Research: Factual Map

## 1. Current Architecture Overview
- UserService: Authentication and user management
  Files: src/services/user.service.ts
  
## 2. Request/Response Patterns
- API endpoints use GET /api/v1/[resource]
- Response format: { success: bool, data: object, error: null | ErrorObject }

## 3. Data Models
- Users table: id, email, password_hash, created_at
  ORM: Prisma
  
[etc.]
```

**How to validate it's good:**

- [ ] Zero "should" language ("The API should...")
- [ ] Every claim references specific files
- [ ] Database schema is exact (could copy into migrations)
- [ ] Uncertainty flagged ("Unclear: How NotificationService is used")
- [ ] Known issues documented ("Bug: Pagination doesn't handle deletes")
- [ ] You could hand this to new team member and they'd learn system

**If validation fails:**

- Making recommendations? → "Remove all 'we should' language. Just state what exists."
- Vague claims? → "Every pattern you describe, cite the file and line number"
- Missing areas? → "You didn't cover [area]. Research it and add to document."
- Hallucinating code that doesn't exist? → Point out the specific mistake, agent will correct

**Time investment:** 45 minutes

---

### Step 6: Run Phase 3 (Design) - The "Brain Surgery" Phase

This is where human judgment matters most.

**Your action:**

1. Run `/qrspi-design <ticket-id>` (or provide ticket + questions + research to Claude and ask for an architectural design)
2. Wait for agent's design proposal

**Agent's output:**

```markdown
# Design Document: Real-Time Notifications

## Current State Analysis
- Event system uses Kafka
- No real-time sync currently exists
- WebSocket infrastructure not in place

## Desired End State
- Users see notifications in real-time
- Preferences sync across browser tabs

## Architectural Decisions

### Decision 1: Real-Time Delivery Mechanism
Options: WebSocket, SSE, Polling
Decision: WebSocket
Rationale: Lower latency, better for real-time

[...more decisions...]
```

**Your job at the Design PR (the "brain surgery"):**

Design is the last artifact in the Design PR. Once it's written, the orchestrator submits the
Design PR on branch `<id>/design` (containing questions, research, and design) and reports
**Design Review** in Linear. The PR is the gate — the orchestrator will not build the plan phase
until you approve this PR. You review it now, before any structure or plan exists.

Read the design. For each decision, ask:

- "Is this the pattern we use?"
- "Does this respect the constraints we discovered?"
- "Is there a better approach we've used elsewhere?"

If answer is "no" to any, give feedback:

```txt
Agent's design says: "Use WebSocket for real-time delivery"

Your feedback: "We moved away from WebSocket in 2023 because 
of scaling issues with sticky sessions. Use Server-Sent Events (SSE) instead. 
It integrates with our existing HTTP load balancing."

Agent's response (good): "Understood. Updating design to use SSE. 
This avoids sticky session complexity and works with our load balancer."

Agent's response (bad): "But WebSocket is better for real-time..."
(If this happens, say firmly: "SSE is our standard. Use it.")
```

**How to validate design is good:**

- [ ] All decisions reference research findings
- [ ] Options were considered (not just one way)
- [ ] Trade-offs are stated
- [ ] Integration points are concrete
- [ ] No "we should consider later"
- [ ] Design respects team standards

**If design is bad:**

- Missing architectural decisions? → "How will you handle [constraint]? Update design."
- Using outdated patterns? → "We moved away from this. Here's the pattern we use now."
- Integration points vague? → "Which service calls this? Where do events publish?"
- Risky approach? → "This approach has this risk. How do you mitigate?"

**Important:** After feedback, agent rewrites design. This is the "brain surgery"—agent accepts your corrections cleanly without arguing. There are two distinct ways feedback flows back, and they behave differently:

- **Unresolved comment threads / nit feedback on the Design PR** are addressed by the *manual*
  `revise` path: on an explicit invocation, the orchestrator re-runs the affected design artifacts
  (Questions → Research → Design), amends the `<id>/design` commit in place, and re-submits. This
  is never automated — it only happens when you ask for it.
- **A formal `CHANGES_REQUESTED` review** is the heavier signal. On any upstream phase PR it
  triggers an automatic *reset*: every downstream phase is discarded (PRs closed, branches deleted,
  stale artifacts removed) and the ticket returns to that phase. On the Design PR there is nothing
  downstream yet, so a change request simply puts design back into the revise loop.

**Advancing past the gate:** when you're satisfied, **approve the Design PR on GitHub**
(`reviewDecision == APPROVED` with zero unresolved threads). That approval — not any Linear
status — is what unlocks the plan phase. The next `/qrspi-work <ticket-id>` (or batch run) sees the
approved, clean PR and auto-advances: it builds Structure, Plan, and Worktree on a new `<id>/plan`
branch stacked on top of design.

**Time investment:** 40 minutes (30 min agent work + 10 min your feedback)

---

### Step 7: Run Phase 4 (Structure) — first step of the Plan PR

Structure runs only after the **Design PR is approved**. It opens the plan phase
(structure → plan → worktree) on a fresh `<id>/plan` branch stacked on `<id>/design`. All three
plan artifacts share that one branch as a single commit; they do not touch the design branch.

**Your action:**

1. Run `/qrspi-structure <ticket-id>` (or provide design.md to Claude and ask for vertical slice breakdown)
2. Agent breaks down feature into vertical slices
3. Review for feasibility

**Agent's output:**

```markdown
# Structure Outline: Real-Time Notifications

## Slice 1: Mock Event Stream (2 hours)
Objective: Event handlers return mocked data
Files to Create:
  - src/services/notification.service.ts (mock)
  - frontend/components/NotificationBell.tsx
Tests:
  - Integration test: Event triggers mock handler

## Slice 2: Real Kafka Integration (3 hours)
Objective: Events actually publish and subscribe
Files to Modify:
  - src/services/notification.service.ts (add Kafka)
  - src/events/notification.events.ts (event schema)
Tests:
  - Event publishes to Kafka
  - Subscriber receives event

## Slice 3: Real-Time Client Sync (2 hours)
Objective: WebSocket connection receives events
Files:
  - frontend/hooks/useNotifications.ts (WebSocket subscription)
Tests:
  - Client receives notification within 100ms
```

**How to validate it's good:**

- [ ] Each slice is testable (has clear entry/exit)
- [ ] Slices are independent (can be reviewed separately)
- [ ] No horizontal layering ("do all database, then all API")
- [ ] Data model introduced gradually
- [ ] Effort estimates are realistic
- [ ] Can be deployed slice-by-slice

**If structure is bad:**

- Too many slices? → "Consolidate some. Too much overhead."
- Too few slices? → "Break down further. Each should be ~2 hours."
- Horizontal layering? → "Restructure so each slice is end-to-end testable."
- Slices not independent? → "Slice B depends on Slice A's database schema. Make it independent or reorder."

**Time investment:** 30 minutes

---

### Step 8: Run Phase 5 (Plan)

**Your action:**

1. Run `/qrspi-plan <ticket-id>` (or provide structure.md to Claude and ask for a file-by-file implementation plan)
2. Agent writes detailed implementation plan
3. Validate zero new architectural decisions

**Agent's output:**

```markdown
# Implementation Plan: Real-Time Notifications - Slice 1

## File: src/services/notification.service.ts
Purpose: Business logic for notifications
Types: Notification, NotificationPreferences
Functions:
  - getNotifications(userId): Promise<Notification[]>
  - markAsRead(notificationId): Promise<void>
Dependencies: PrismaClient, logger
Testing: Mock database, test all functions
Estimated LOC: 80-100

## File: frontend/components/NotificationBell.tsx
Purpose: UI component showing notification count
Props: userId
State: notifications, isOpen
Functions:
  - fetchNotifications()
  - handleClick()
Testing: Render component, test click behavior
Estimated LOC: 60-80

## Implementation Sequence
1. Define types (20 min, no dependencies)
2. Service methods (30 min, depends on: types)
3. API endpoint (25 min, depends on: service)
4. Frontend component (30 min, parallel with API)
5. Integration tests (30 min, depends on: all above)
```

**How to validate plan is good:**

- [ ] Zero new architectural decisions introduced
- [ ] All decisions reference design.md
- [ ] File breakdown is specific (types, functions, dependencies)
- [ ] Implementation sequence respects dependencies
- [ ] Testing strategy is detailed
- [ ] Code quality gates are explicit
- [ ] No TODOs or vague work

**The critical check: Does plan introduce anything not in design?**

```txt
Design said: "Use mock events in Slice 1"
Plan says: "Create notification service"

✅ GOOD: Plan implements design decision (mockable service)

Plan says: "Service uses Redis cache for fast lookups"
Design never mentioned caching.

❌ BAD: Plan introduces new decision not approved in design
→ Feedback: "Caching wasn't in design. Remove it or move to design phase."
```

**Time investment:** 40 minutes

---

### Step 9: Worktree, the Plan PR, then Implementation + landing

**Phase 6 (Worktree):** The third and final artifact on the Plan PR. The worktree agent turns the
plan into a session-aware task DAG with a per-session context budget, so implementation can run
one slice per fresh session without blowing the context window. This produces `worktree.md` on the
`<id>/plan` branch. (Do not confuse this artifact with the *git worktree* the orchestrator checks
out at `.worktrees/<ticket-id>/` — same word, different thing.)

**The Plan PR:** once the worktree artifact exists, the orchestrator submits the Plan PR
(`<id>/plan`, carrying structure, plan, and worktree, stacked on the design PR) and reports **Plan
Review**. Review it. Unresolved comment threads route through the manual `revise` path (re-run the
affected plan artifacts, amend `<id>/plan`, re-submit). A formal `CHANGES_REQUESTED` on the
*Design* PR at this point is an upstream change request: it automatically resets — the plan phase
is discarded (PR closed, branch deleted, structure/plan/worktree removed) and the ticket returns to
design. When satisfied, **approve the Plan PR**. That approval — not a Linear status — unlocks
implementation.

**Phase 7 (Implement):** runs only after the **Plan PR is approved**.

- The orchestrator implements each vertical slice in its own fresh session, following plan.md and
  the worktree DAG exactly.
- Each slice becomes its own branch (`<id>/slice-N`) and its own **stacked PR** via Graphite
  (`gt`), built on top of `<id>/plan`.
- You run the gates: `npm test`, `npm run type-check`, `npm run lint`. Code should pass all of them.
- If code diverges from plan, send it back to be fixed.
- An `impl-log.md` records what each slice did and any notes for the next session.

**Phase 8 (PR):**

- Agent writes `pr-summary.md`, mapping acceptance criteria to implementation and tests; it is
  amended into the last slice commit and used as the PR body.
- The orchestrator reports **Code Review**. You review the slice PRs for:
  - No surprises (everything aligns with prior artifacts)
  - Code follows patterns
  - Tests pass
  - No architectural changes
- The slice PRs are reviewed **as a whole stack**: the feature is "ready to land" only when
  *every* slice PR is approved + clean, not slice by slice. Once they all are, the next
  `/qrspi-work` run **lands the whole stack bottom-up** via Graphite and reports **Done**, which
  triggers cleanup of the artifacts and the git worktree. Nothing merges to trunk mid-feature —
  the entire stack lands together at the end.

**Time investment:**

- Slice 1 implementation: 2-3 hours
- Slice 2 implementation: 3-4 hours
- Slice 3 implementation: 2-3 hours
- PR review: 30 minutes
- Total: 7-11 hours for full feature

---

## Part 3: Training Your Agent to Follow QRSPI

Most AI agents (including Claude) don't know QRSPI by default. You need to teach them.

### Method 1: Prompting (Simplest)

Write a per-phase prompt describing the expected behavior and output format. Below is an example of what a Phase 1 prompt looks like (the actual prompt used by the `/qrspi-questions` skill):

#### **Example: Phase 1 prompt**

```txt
You are an expert code archaeologist. Your job is NOT to plan or implement anything yet.

Your goal is to generate 8-15 specific, technical questions that will force you to understand:
1. The current payment flow and all existing integrations
2. How user sessions and authentication work
[etc.]

Format each question as:
- [FILENAME] - Question text
- Why this matters: [one line justification]

You will use these questions to guide your Research phase.
```

This prompt teaches agent what "Phase 1" means and what output is expected.

### Method 2: Few-Shot Examples (Better)

Provide examples of good and bad outputs for each phase.

```txt
# GOOD Questions Phase Output
- src/services/payment.service.ts - How are Stripe payments currently handled?
  Why this matters: New refund feature will integrate with this.

- src/db/schema.prisma - What fields does the Payment table have?
  Why this matters: Refund record needs to reference Payment table.

[8-15 examples]

# BAD Questions Phase Output (Don't do this)
- How does the API work?
  Why: Too generic, not specific to files

- Should we use WebSocket for real-time?
  Why: This is design thinking, not exploration
```

Showing examples trains agent faster than prose instructions.

### Method 3: System Prompt (Best for Production)

If you're using Claude API programmatically:

```python
SYSTEM_PROMPT = """
You are implementing the QRSPI workflow for AI-assisted software engineering.

QRSPI has nine phases, each gated by its own pull request. PR review state — not Linear
status — is the authority for advancement:

  TICKET (T): Author a well-formed ticket as a Linear issue (guided conversation)

  --- Design PR  (branch <id>/design, off trunk) ---
  QUESTIONS (Q): Generate 8-15 specific exploration questions
  RESEARCH  (R): Document facts about the current system (zero recommendations; ticket hidden)
  DESIGN    (D): Propose architecture with explicit trade-offs (accept human feedback)
  ==> Approve the Design PR → the Plan PR auto-builds, stacked on top

  --- Plan PR  (branch <id>/plan, stacked on <id>/design) ---
  STRUCTURE (S): Break into vertical slices (each testable end-to-end)
  PLAN      (P): Atomic implementation steps per slice (zero new decisions)
  WORKTREE  (W): Session-aware task DAG with per-session context budgets
  ==> Approve the Plan PR → the slice PRs auto-build, stacked on top

  --- Slice PRs  (branches <id>/slice-1..N, stacked on <id>/plan) ---
  IMPLEMENT    (I): Write code following the plan exactly, one slice per fresh session
  PULL REQUEST (PR): PR summary with zero surprises
  ==> All PRs approved + clean → land the whole stack bottom-up

Key principles:
- Each phase produces a standalone artifact stored under .qrspi/<ticket-id>/
- Each phase is its own branch and its own PR, stacked: <id>/design → <id>/plan → <id>/slice-1..N
- The stack is held open (nothing merges to trunk) until every PR is approved, then lands bottom-up
- Later phases ONLY introduce execution details, never new architecture
- A phase PR is "ready" when reviewDecision == APPROVED AND zero unresolved review threads
- Approving a phase PR auto-advances; a formal CHANGES_REQUESTED on an upstream PR resets
  (discards every downstream phase) and returns the ticket to that phase
- Linear is not a gate: it is only an entry gate (assigned + Selected) plus best-effort reporting
- All decisions reference previous phase findings
- Uncertainty is flagged explicitly (don't hide unknowns)

When prompted to execute a phase:
1. Identify which phase you're in
2. Reference the previous phase's output
3. Produce artifact in markdown format
4. Include validation checklist
5. Stop—wait for next phase prompt

Never skip phases or combine them.
Never introduce architectural decisions outside the Design phase.
"""

response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=4000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": phase_prompt}]
)
```

This teaches the agent the entire workflow in one instruction.

---

## Part 4: Common Mistakes and How to Avoid Them

### Mistake 1: Skipping Phases

**What happens:**

```txt
Engineer: "I know the codebase. Skip Questions and Research, go straight to Design."

Agent proceeds directly to Design.

Result: Design makes assumptions about codebase that are wrong.
Code doesn't integrate.

Example:
Design says: "Add userId field to Notifications table"
Research (if done) would have revealed: "User table uses email as primary key, not userId"
```

**How to avoid:**

- Do all six planning phases (Q-R-D on the Design PR, S-P-W on the Plan PR) every time
- No exceptions for "simple" features
- No shortcuts for teams that "know the codebase"

**The truth:** The phases aren't about learning. They're about forcing assumptions into the open.

---

### Mistake 2: Letting Agent Introduce New Architecture in Plan Phase

**What happens:**

```txt
Design approved: "Use existing service layer pattern"

Plan says: "Create new AbstractNotificationHandler base class"

Engineer misses it, code gets merged.

Result: Codebase has new pattern no one agreed to.
```

**How to avoid:**

- After Phase 5 (Plan), scan for new classes/functions/patterns not in Phase 3 (Design)
- If you see new architecture: "Stop. This pattern wasn't in design. Add it to design phase and re-plan."
- Use grep to check: "Is this class mentioned in design.md?"

**Automated check:**

```bash
# Get classes from design.md
grep "class " design.md | sort > /tmp/design_classes.txt

# Get classes from plan.md
grep "class " plan.md | sort > /tmp/plan_classes.txt

# See what's new in plan
diff /tmp/design_classes.txt /tmp/plan_classes.txt
# If output appears here, something's new and should have been in design
```

---

### Mistake 3: Conflating "Spending Time on Alignment" with "Wasting Time"

**What happens:**

```txt
Engineer (at 2.5 hours): "We've spent 2.5 hours on alignment 
and haven't written a line of code yet. This is slow."

Engineer gives up on QRSPI, goes back to unstructured prompting.
```

**How to avoid:**

- **Measure total time, not phase time**
  - QRSPI: 2.5 alignment + 3.5 implementation + 0.5 review = 6.5 hours total
  - Unstructured: 0.5 prompting + 5 debugging + 2 review = 7.5 hours total
  
- **Measure quality, not speed**
  - QRSPI: Code integrates first try, no rework needed
  - Unstructured: Code needs rework, architectural debt accumulates

- **Measure confidence**
  - QRSPI: PR reviewer has full context, approves in 15 min
  - Unstructured: PR reviewer finds surprises, requests changes, 2 cycles of feedback

---

### Mistake 4: Treating Design Phase Feedback as Optional

**What happens:**

```txt
Agent proposes design using old pattern.

Engineer gives feedback: "Use pattern X instead"

Agent says: "I'll incorporate that" but doesn't really change anything substantive.

Engineer doesn't catch it because they're tired from earlier phases.

Code gets merged with wrong pattern.
```

**How to avoid:**

- **After agent incorporates feedback, re-read the entire design.md**
- Check: Does design.md now reflect your feedback?
- If you're not sure: "Show me the specific section where you changed this. Quote it back to me."
- Don't proceed to Structure phase until design clearly reflects your feedback

---

### Mistake 5: Misunderstanding "Vertical Slices"

**What happens:**

```txt
Engineer thinks vertical slices means "thin layers" and structures like:

Slice 1: Database schema
Slice 2: API endpoints  
Slice 3: Frontend UI

Result: After Slice 1, nothing is testable. Slice 2 depends on complete Slice 1. etc.
```

**How to avoid:**

- Vertical slice = end-to-end testable
- **Not:** "All database, then all API"
- **Yes:** "Mock API → Real API → Database"

```txt
WRONG (Horizontal):
Slice 1: Create schema, create migrations
Slice 2: Create API endpoints (now that schema exists)
Slice 3: Create frontend (now that API exists)

RIGHT (Vertical):
Slice 1: Hardcoded API endpoint + frontend (no DB)
        → Testable: UI renders, button clicks work
        
Slice 2: Real database, still mocked data
        → Testable: API queries return real data
        
Slice 3: Real-time sync + events
        → Testable: Changes propagate across clients
```

Each slice is independently reviewable and deployable.

---

### Mistake 6: Losing the Artifacts

**What happens:**

```txt
Agent generates research in chat only.
Engineer reads it, closes the session, context clears.

Later in the Design phase, the agent needs to reference research
and has to re-generate it from scratch (or hallucinates).
```

**How to avoid:**

- **Let QRSPI persist artifacts for you.** Each phase writes its artifact to
  `.qrspi/<ticket-id>/` automatically (questions.md, research.md, design.md, …). You don't
  copy-paste between phases — the next phase reads the prior artifact from disk.
- **The planning artifacts live in git, not just on disk.** They sit on per-phase stacked
  branches — questions/research/design on `<ticket-id>/design`, structure/plan/worktree on
  `<ticket-id>/plan` — so they survive a closed session and are reviewable as PRs.
- **The ticket itself lives in Linear**, not in a local file. But Linear status does NOT decide
  which phase comes next — PR review state does. The orchestrator re-derives the current phase
  from the branches and their PR states on every invocation.
- **Never rely on agent memory across sessions** — rely on the artifacts on disk and the PR/branch
  state in git.

---

### Mistake 7: Asking Agent to Do Multiple Phases at Once

**What happens:**

```txt
Engineer: "Do Questions, Research, and Design in one prompt"

Agent tries to do all three and does none well.
```

**How to avoid:**

- One phase per prompt
- Complete one phase fully before moving to next
- Agent state resets between phases (load prior artifacts)

---

## Part 5: Measuring If QRSPI Is Working

How do you know if QRSPI is actually helping?

### Metric 1: Time to First Deployable Slice

**How to measure:**

- Track time from "feature starts" to "Slice 1 passes code review and is deployable"
- With unstructured: 4-6 hours (lots of back-and-forth)
- With QRSPI: 3-4 hours (alignment happened upfront)

### Metric 2: Code Review Cycles

**How to measure:**

- Count: How many times does PR get "Changes Requested" before merge?
- With unstructured: 2-3 cycles (architecture surprises, integration issues)
- With QRSPI: 0-1 cycle (everything aligned beforehand)

**Ideal:** PR is approved on first review with no requested changes (except minor style).

### Metric 3: Hallucination Rate

**How to measure:**

- In Plan phase (Phase 5): Count how many architectural decisions appear that weren't in Design (Phase 3)
- With unstructured: 3-5 new decisions per plan (agent keeps inventing)
- With QRSPI: 0-1 new decisions per plan (agent respects design)

**Ideal:** Zero new decisions. Every implementation detail is in the plan because it was in the design.

### Metric 4: Post-Merge Rework

**How to measure:**

- After feature merges, track: How much code changes in next 2 weeks?
- With unstructured: 30-40% (bugs, integration issues, refactors)
- With QRSPI: 5-10% (minor optimizations only)

**Ideal:** <5% post-merge changes (feature ships and stays).

### Metric 5: Estimate Accuracy

**How to measure:**

- Estimated effort (from Plan phase) vs. Actual effort
- With unstructured: 50% off (estimated 4 hours, took 6)
- With QRSPI: 10% off (estimated 6 hours, took 5.5)

**Ideal:** Within 10% of estimate.

### How to Calculate ROI

```txt
QRSPI ROI = (Time Saved) - (Alignment Overhead)

Time Saved = (Unstructured Total Time) - (QRSPI Total Time)
Alignment Overhead = (Q + R + D + S + P) phases

Example:
Unstructured: 0.5 (prompt) + 5 (coding) + 2 (debugging) + 1 (extra review cycles) = 8.5 hours
QRSPI: 2.5 (alignment) + 3 (coding) + 0.5 (review) = 6 hours
Time Saved: 8.5 - 6 = 2.5 hours
Alignment Overhead: 2.5 hours
Net ROI: 0 hours (same total time)

BUT: Code quality is higher, architectural debt is lower, team confidence is higher.
So even with 0 hours of time savings, ROI is positive in other ways.

For complex features:
Unstructured: 0.5 + 8 + 4 + 2 = 14.5 hours
QRSPI: 2.5 + 6 + 0.5 = 9 hours
Time Saved: 14.5 - 9 = 5.5 hours
Alignment Overhead: 2.5 hours
Net ROI: 3 hours saved (plus quality improvements)
```

**The truth:** QRSPI breaks even on time for medium features, and saves significant time for complex features. The real win is quality and confidence.

---

## Part 6: Adapting QRSPI for Your Context

QRSPI is a framework, not a law. Adapt it.

### Scenario 1: You Have a Small Team (2-3 engineers)

**Adapt this way:**

- Use QRSPI for all features >Medium complexity
- For small features: keep the full planning sequence (the canonical workflow runs all six
  planning phases — skipping Structure or Worktree means stepping outside QRSPI), but expect each
  phase to be short
- For simple features: Just discuss in Slack, no QRSPI needed

**Time allocation:**

- Small feature: 1 hour QRSPI + 2 hours coding = 3 hours total
- Medium feature: 2.5 hours QRSPI + 3 hours coding = 5.5 hours total
- Complex feature: 3 hours QRSPI + 6 hours coding = 9 hours total

### Scenario 2: You're on a Distributed Team

**Adapt this way:**

- QRSPI becomes async-friendly
- Each phase is a document hand-off
- Design phase takes longer (more back-and-forth feedback)
- But alignment is more durable (all in writing)

**Time changes:**

- Questions: 20 min (no change)
- Research: 45 min (no change)
- Design: 2 hours (60+ min waiting for feedback, agent does revisions)
- Structure: 30 min (no change)
- Plan: 40 min (no change)
- Implementation: Same (maybe async if timezone spread)
- Total: 5-6 hours vs. 6 hours (async adds 1 hour due to wait times)

### Scenario 3: Your Codebase is Greenfield (New Project)

**Adapt this way:**

- Questions phase might be shorter (less to explore)
- Research phase might be shorter (less existing code)
- Design phase becomes MORE important (no patterns to follow yet)
- Structure and Plan phases are same length

**Time changes:**

- Total: 5 hours vs. 6 hours (greenfield saves 1 hour on research)
- But: Design is more critical (you're setting patterns for whole project)

### Scenario 4: Your Codebase is Legacy (10+ years old)

**Adapt this way:**

- Questions phase is LONGER (more complex interactions)
- Research phase is LONGER (lots of implicit patterns)
- Design phase includes more "brain surgery" (correcting assumptions)
- Everything else is same

**Time changes:**

- Questions: 30 min (10 min longer)
- Research: 60 min (15 min longer)
- Design: 90 min (50 min longer due to corrections)
- Total: 8 hours (2 hours longer due to legacy complexity)

### Scenario 5: You're Building with Agents in Loop (This Workshop's Use Case)

**Adapt this way:**

- Lean on the per-phase PR approvals (Design PR, Plan PR, slice PRs) as the formal checkpoints
- Use `worktree.md` (the session-aware task DAG) as the explicit per-session task hand-off
- Track metrics (hallucination rate, estimate accuracy)
- Feed metrics back into the phase agents for the next feature

**Additional considerations:**

- The planning artifacts are already in version control (on the `<ticket-id>/design` and
  `<ticket-id>/plan` branches); keep them there for review
- Build up a library of good design.md examples to show agents
- Tune the phase agents under `.claude/agents/` based on what worked vs. what didn't
- Measure context window usage (keep under 40%)

---

## Part 7: Integrating QRSPI into Your Workflow

How do you make this part of how your team works?

### Week 1: Learn (Solo)

**Your job:**

1. Pick a medium-complexity feature
2. Do QRSPI end-to-end with Claude (ticket → Design PR → Plan PR → slice PRs → land)
3. Compare to how you normally build
4. Document what worked, what didn't

**Deliverable:** "QRSPI Experience Report"

- Time breakdown per phase
- Hallucination rate (count new architecture decisions)
- Code review cycles
- Post-merge rework

### Week 2: Teach (Team)

**Your job:**

1. Show team the artifacts you created
2. Walk through why alignment phases matter
3. Point out where unstructured prompting failed (hallucinations in design vs. found in code)
4. Propose: Try QRSPI on next complex feature

**Deliverable:** "QRSPI Workshop" (1 hour)

- What is QRSPI
- How it compares to unstructured
- When to use it vs. when to skip it
- How we'll adapt it for our team

### Week 3: Trial (Team)

**Your job:**

1. Have agent build next feature using QRSPI
2. Have another engineer code-review as normal
3. Track metrics (time, hallucinations, review cycles)
4. Retrospect with team

**Deliverable:** "QRSPI Trial Results"

- Did it save time?
- Was code quality better?
- Should we do it again?
- What should we adapt?

### Week 4+: Integrate (Team Standard)

**Your job:**

1. Make QRSPI the default for features >Medium complexity
2. Adjust phases based on team feedback
3. Build up template library for your codebase
4. Measure improvement over time

**Deliverable:** "QRSPI Standard Operating Procedure"

- Which features use QRSPI
- Which phases are mandatory
- How we adapt per context
- Metrics we track

---

## Part 8: The Agent's Perspective

Understanding what's happening from the agent's side helps you prompt better.

### What the Agent is Thinking in Phase 1 (Questions)

```txt
Agent: "I'm being asked to generate exploration questions.
The prompt says: 'Zero assumptions, be specific, reference files.'

I'll generate questions that force investigation of different code areas.
Each question should reveal a system property I need to understand."

Agent produces: 14 specific questions
Agent's internal confidence: "I'll score these on specificity and coverage"
```

### What the Agent is Thinking in Phase 2 (Research)

```txt
Agent: "Now I have exploration questions. I need to map the codebase.
I'm told: 'Zero prescriptive language, facts only.'

For each question, I'll find the answer in code.
I'll document what EXISTS, not what should be.
I'll flag uncertainty."

Agent reads code, documents findings.
Agent's internal confidence: "Am I being descriptive or prescriptive?
Let me remove 'should' language."
```

### What the Agent is Thinking in Phase 3 (Design)

```txt
Agent: "I have facts about the codebase. Now I design.
I'm told: 'Ground design in research, consider options, state trade-offs.'

I'll propose an architecture.
Each decision references research findings.
I'll show why I chose option A over option B."

Agent proposes design.
Human gives feedback: "Use pattern X, not Y"

Agent's internal reaction: "The human has context I don't.
I'll accept this feedback and rewrite design accordingly."

Agent's internal confidence: "Wait, am I just accepting?
Or am I arguing back? The prompt said 'accept feedback cleanly.'
I should rewrite, not negotiate."
```

### What the Agent is Thinking in Phase 5 (Plan)

```txt
Agent: "I have approved design. Now I plan implementation.
I'm told: 'Zero new architectural decisions.'

I'll break down each file, function, and test.
I'll reference every decision to the design.
If I think of something new, I'll ask: 'Was this in design?'
If no, I'll remove it or flag it."

Agent writes plan.
Agent double-checks: "Does plan introduce anything not in design?
Let me scan for new patterns... [checks] ... none. Good."

Agent's confidence: "This plan is purely tactical, not strategic."
```

**Key insight:** The agent is trying to stay in bounds. Help it by being clear about boundaries.

---

## Part 9: Troubleshooting Common Issues

### Issue: Agent Hallucinates Code That Doesn't Exist (In Research Phase)

**What you see:**

```txt
research.md says: "The UserService uses a validateEmail() function 
at line 45 of src/services/user.service.ts"

You check the file. No validateEmail() exists.
```

**Why it happens:**

- Agent is pattern-matching ("services probably validate")
- Agent hasn't actually read the code carefully
- Context window ran out, agent is guessing

**How to fix:**

- In Research prompt, add: "If you're unsure about a detail, say 'Unclear'
  rather than guessing. Don't invent functions that don't exist."
- After Research, spot-check 5 random claims in the document
- If >1 is wrong, send back: "Lines 45-50 of user.service.ts don't contain
  validateEmail(). Research what's actually there."

### Issue: Agent Keeps Proposing New Architecture in Plan Phase

**What you see:**

```txt
Design says: "Use service layer pattern"
Plan says: "Create AbstractServiceBase class to reduce boilerplate"

You never discussed AbstractServiceBase.
```

**Why it happens:**

- Agent is "optimizing" unprompted
- Agent doesn't see "introducing new architecture" as a violation
- Plan prompt didn't warn against it strongly enough

**How to fix:**

- Make it explicit in Plan prompt: "If you propose anything new (classes,
  patterns, abstractions), it's a violation. Stop immediately and ask:
  'Should this be in Design instead?'"
- After Plan, scan for new classes/interfaces not in Design
- If found: "These are new. Remove them or move to Design phase."

### Issue: Effort Estimates are Wildly Off

**What you see:**

```txt
Plan says: Slice 1 will take 2 hours
Actual: Slice 1 took 6 hours
```

**Why it happens:**

- Agent underestimated complexity
- Agent didn't account for testing, debugging, quality gates
- LOC estimate was too low
- Hidden dependencies weren't surfaced in Design

**How to fix:**

- After implementing first slice, calculate actual hours per LOC

  ```txt
  Actual: 6 hours, 200 LOC = 0.03 hours per LOC = 1.8 min per LOC
  Plan estimated: 2 hours, 200 LOC = 0.01 hours per LOC = 0.6 min per LOC
  Agent is off by 3x
  ```

- In next Plan prompt, reference this: "In past features, we see 2-3 min
  per LOC including tests. Use that as baseline."
- Ask agent to re-estimate with this calibration

### Issue: Design Phase Feedback Isn't Actually Incorporated

**What you see:**

```txt
You say: "Use pattern X, not Y"
Agent rewrites design.

You read new design carefully.
Agent just renamed variables but kept same approach.
Same wrong pattern, different language.
```

**Why it happens:**

- Agent didn't truly understand the difference between X and Y
- Agent is shallow-editing instead of deep restructuring
- Context window limit hit, agent couldn't rewrite fully

**How to fix:**

- Ask specifically: "Show me the section where you changed from pattern Y
  to pattern X. Quote the new text."
- If agent quotes something that's still pattern Y, say: "This is still Y.
  Here's what pattern X looks like: [example]. Rewrite using this example."
- If rewrite still doesn't work: "This is taking too long. Let's move to
  a fresh session with your new understanding. Reset and rewrite design.md."

---

## Part 10: Building Confidence

The hardest part of QRSPI is trusting the process.

### The Doubt You'll Have

**At 2 hours into alignment:**
> "We've spent 2 hours and haven't written code.
> This is slow. I could code this myself in 4 hours."

**The truth:**

- You could code it in 4 hours unstructured
- But then you'll spend 2 hours debugging
- And the code won't integrate
- And you'll have technical debt

QRSPI is slower upfront to be faster overall.

### How to Build Confidence

1. **Do one full feature with QRSPI**
   - Measure actual time (alignment + coding + review)
   - Compare to your normal process
   - See if estimate accuracy improves

2. **Show team the artifacts**
   - The design.md is a beautiful thing
   - It captures intent, trade-offs, risks
   - Compare to: "We discussed this in Slack"

3. **Count hallucinations**
   - Unstructured: "Agent made 5 architectural decisions we didn't approve"
   - QRSPI: "Agent made 0 new decisions (all were in design)"
   - This is the win

4. **Feel the review lightness**
   - PR reviewer: "No surprises, code aligns with design, shipping it"
   - Vs. "Wait, why did they do it this way? That doesn't fit our pattern"

5. **Experience the compounding benefit**
   - After 3 features with QRSPI:
     - Agents are better at following the pattern
     - You're faster at giving feedback
     - Team understands architecture more deeply

---

## Summary: How to Use This System

### The 30-Second Version

```txt
0. /qrspi-ticket <description>   → author the Linear ticket; assign it + move to Selected
1. /qrspi-work <ticket-id>       → runs the design phase (Q-R-D), opens the Design PR
                                    (<id>/design), reports Design Review
2. Approve the Design PR on GitHub
3. /qrspi-work <ticket-id>       → auto-advances: runs the plan phase (S-P-W), opens the
                                    Plan PR (<id>/plan, stacked), reports Plan Review
4. Approve the Plan PR on GitHub
5. /qrspi-work <ticket-id>       → builds the slice PRs (<id>/slice-1..N, stacked), reports
                                    Code Review
6. Approve every slice PR (reviewed as a whole stack — no surprises)
7. /qrspi-work <ticket-id>       → lands the whole stack bottom-up, reports Done → cleanup
```

(Artifacts persist automatically under `.qrspi/<ticket-id>/`; the ticket lives in Linear, but
**PR approval — not Linear status — drives advancement.** A formal change request on an upstream
PR auto-resets the downstream phases. Linear only acts as the entry gate (assigned + `Selected`)
and a best-effort status report: `Selected` → `Design Review` → `Plan Review` → `Code Review` →
`Done`.)

### The Decision Tree

```txt
Is feature complex? → YES → Use QRSPI (run the full planning sequence)
                    → NO  → Still run the full sequence, but each phase is short

Is codebase unfamiliar? → YES → Spend more time on Research
                        → NO  → Research can be shorter

Do you have time for alignment? → YES → Do QRSPI
                                → NO  → Use unstructured (but expect more rework)

Is this a refactor or migration? → YES → Use QRSPI (critical for complex changes)
                                 → NO  → Maybe skip for simple features

Are you trying to improve code quality? → YES → Use QRSPI (catches issues early)
                                        → NO  → Unstructured is fine

```

### The Measurement You Should Care About

Not: "How much time does QRSPI take?"

But: "What's the total time from idea to shipped code, including all rework?"

QRSPI loses on phase time, wins on total time.

---
