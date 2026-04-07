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
Engineer guides agent through 8 phases:
  Phase 1: What questions do we need to ask? (20 min)
  Phase 2: What does the codebase actually do? (45 min)
  Phase 3: How does this fit? (40 min with human feedback)
  Phase 4: How do we build this in testable chunks? (30 min)
  Phase 5: What's the detailed plan? (40 min)
  Phase 6: What are the individual tasks? (varies per phase)
  Phase 7: Build it (follows plan exactly)
  Phase 8: Review (no surprises)

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

### The Minimal Viable QRSPI Flow

You don't have to do all 8 phases. Start with the core flow:

**Minimal QRSPI (Core Phases Only):**

1. Questions (Q) - 20 min
2. Research (R) - 45 min
3. Design (D) - 40 min (with human feedback)
4. Structure (S) - 30 min
5. Plan (P) - 40 min
6. Implement (I) - Implementation time varies
7. PR (P) - Review time

**Skip these initially (add later as you mature):**

- Work Tree (Phase 6) - Useful for large features, overkill for small ones
- Implementation Commit Log (Phase 7) - Useful for team coordination, not needed solo
- Metrics (JSON artifacts) - Useful for measuring improvement over time

### Step 1: Identify Your Feature

Pick a medium-complexity feature. Avoid:

- Super simple features (one file change)
- Greenfield rewrites (no codebase to research)
- Crisis/hotfix mode (no time for alignment)

**Good candidates:**

- Add payment method management (new model, new endpoints, new UI)
- Implement rate limiting (infrastructure change, multiple touch points)
- Add real-time notifications (distributed systems complexity)

### Step 2: Find Your Agent

You'll be prompting Claude (or another AI agent). The agent needs:

- **Access to your codebase** (read-only, for research phase)
- **Clear instructions** (use the prompts I provided)
- **Human feedback loop** (you'll review and correct designs)

**Three ways to set this up:**

**Option A: Chat with Claude (claude.ai)**

```txt
1. Copy your codebase into the chat
   (Paste key files, or use file upload)

2. Use the prompts from qrspi_test_prompts.md
   (Copy Q1.1 or Q1.2 prompt, paste into chat)

3. Agent responds with questions.md
   
4. Copy questions.md to file
   (Save locally for later phases)

5. Continue phases sequentially in chat
```

**Option B: Claude API (Programmatic)**

```python
import anthropic

client = anthropic.Anthropic()

# Phase 1: Questions
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=2000,
    messages=[
        {"role": "user", "content": QUESTIONS_PROMPT}
    ]
)
questions = response.content[0].text

# Save to file
with open("artifacts/questions.md", "w") as f:
    f.write(questions)

# Phase 2: Research (feed questions to agent)
research_prompt = RESEARCH_PROMPT + "\n\n" + questions
# ... continue
```

**Option C: Claude Code (Command Line)**

```bash
# If you have Claude Code installed
claude code --task "QRSPI Phase 1: Generate exploration questions" \
  --context /path/to/codebase
```

### Step 3: Run Phase 1 (Questions)

**Your action:**

1. Copy the Q1.1 or Q1.2 prompt from qrspi_test_prompts.md
2. Paste into Claude
3. Wait for output

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

- [ ] 12+ questions (count them)
- [ ] Each references specific files
- [ ] Zero "should" language
- [ ] Spans multiple system areas (auth, DB, API, services)

**If validation fails:**

- Too few questions? → "Generate 5 more specific questions about [area]"
- Generic questions? → "Make each question reference specific filenames, not just 'the API'"
- Not spanning codebase? → "Add questions about [missing area]"

**Time investment:** 20 minutes

---

### Step 4: Run Phase 2 (Research)

**Your action:**

1. Copy the research prompt from qrspi_test_prompts.md (R2.1 or R2.2)
2. Provide it to agent along with the questions from Phase 1
3. Wait for output

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

### Step 5: Run Phase 3 (Design) - The "Brain Surgery" Phase

This is where human judgment matters most.

**Your action:**

1. Copy design prompt from qrspi_test_prompts.md (D3.1 or D3.2)
2. Provide it to agent along with the feature ticket (hidden until now)
3. Wait for agent's design proposal

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

**Your job (the "brain surgery"):**

Read the design. For each decision, ask:

- "Is this the pattern we use?"
- "Does this respect the constraints we discovered?"
- "Is there a better approach we've used elsewhere?"

If answer is "no" to any, give feedback:

```
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

**Important:** After feedback, agent rewrites design. This is the "brain surgery"—agent accepts your corrections cleanly without arguing.

**Time investment:** 40 minutes (30 min agent work + 10 min your feedback)

---

### Step 6: Run Phase 4 (Structure)

**Your action:**

1. Copy structure prompt from qrspi_test_prompts.md (S4.1 or S4.2)
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

### Step 7: Run Phase 5 (Plan)

**Your action:**

1. Copy plan prompt from qrspi_test_prompts.md (P5.1)
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

```
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

### Step 8: Run Phase 6-8 (Implementation + Review)

**For medium complexity features (which is what you're learning on):**

**Phase 6 (Work Tree):** Optional. Skip if feature is straightforward.

**Phase 7 (Implement):**

- Agent writes code following plan.md exactly
- You run it: `npm test`, `npm run type-check`, `npm run lint`
- Code should pass all gates
- If code diverges from plan, ask agent to fix

**Phase 8 (PR):**

- Agent writes PR description
- You review for:
  - No surprises (everything aligns with prior artifacts)
  - Code follows patterns
  - Tests pass
  - No architectural changes
- Approve and merge

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

Copy the phase prompts directly from qrspi_test_prompts.md. They're designed to train agents.

**Example: Phase 1 prompt**

```
You are an expert code archaeologist. Your job is NOT to plan or implement anything yet.

Your goal is to generate 12-15 specific, technical questions that will force you to understand:
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

```
# GOOD Questions Phase Output
- src/services/payment.service.ts - How are Stripe payments currently handled?
  Why this matters: New refund feature will integrate with this.

- src/db/schema.prisma - What fields does the Payment table have?
  Why this matters: Refund record needs to reference Payment table.

[12-15 examples]

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

QRSPI has 8 phases:
1. QUESTIONS (Q): Generate 12-15 specific exploration questions
2. RESEARCH (R): Document facts about current system (zero recommendations)
3. DESIGN (D): Propose architecture with explicit trade-offs (accept human feedback)
4. STRUCTURE (S): Break into vertical slices (each testable end-to-end)
5. PLAN (P): File-by-file implementation plan (zero new decisions)
6. WORK TREE (W): Task breakdown (30-minute tasks with dependencies)
7. IMPLEMENT (I): Write code following plan exactly
8. PULL REQUEST (PR): Code review document with zero surprises

Key principles:
- Each phase produces a standalone artifact
- Later phases ONLY introduce execution details, never new architecture
- Human provides feedback (especially in Design phase)
- All decisions reference previous phase findings
- Uncertainty is flagged explicitly (don't hide unknowns)

When prompted to execute a phase:
1. Identify which phase you're in
2. Reference the previous phase's output
3. Produce artifact in markdown format
4. Include validation checklist
5. Stop—wait for next phase prompt

Never skip phases or combine them.
Never introduce architectural decisions outside Design phase.
"""

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=4000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": phase_prompt}]
)
```

This teaches agent the entire workflow in one instruction.

### Method 4: Fine-Tuning (Overkill)

If you have >100 features using QRSPI, fine-tune a model on correct QRSPI outputs. But start with prompting first.

---

## Part 4: Common Mistakes and How to Avoid Them

### Mistake 1: Skipping Phases

**What happens:**

```
Engineer: "I know the codebase. Skip Questions and Research, go straight to Design."

Agent proceeds directly to Design.

Result: Design makes assumptions about codebase that are wrong.
Code doesn't integrate.

Example:
Design says: "Add userId field to Notifications table"
Research (if done) would have revealed: "User table uses email as primary key, not userId"
```

**How to avoid:**

- Do all 5 alignment phases (Q-R-D-S-P) every time
- No exceptions for "simple" features
- No shortcuts for teams that "know the codebase"

**The truth:** The phases aren't about learning. They're about forcing assumptions into the open.

---

### Mistake 2: Letting Agent Introduce New Architecture in Plan Phase

**What happens:**

```
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

```
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

```
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

```
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

```
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

### Mistake 6: Not Saving Artifacts

**What happens:**

```
Agent generates research.md in chat.
Engineer reads it.
Engineer closes chat.
Agent context clears.

Later in Design phase, agent needs to reference research.
Agent has to re-generate from scratch (or hallucinates).
```

**How to avoid:**

- **Save every artifact to disk immediately**
- After Phase 1: Save questions.md
- After Phase 2: Save research.md
- After Phase 3: Save design.md
- etc.

- **In next phase, load artifacts from disk**

  ```
  "Here's the research from Phase 2: [paste research.md]
   
  Now generate design.md using this as foundation."
  ```

- **Never rely on agent memory across sessions**

---

### Mistake 7: Asking Agent to Do Multiple Phases at Once

**What happens:**

```
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

```
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
- For small features: Skip phases, just do Q-R-D-P (skip S and W)
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

- Add human checkpoint after each phase
- Use work_tree.md (Phase 6) as explicit task hand-off
- Track metrics (hallucination rate, estimate accuracy)
- Feed metrics back into prompts for next feature

**Additional considerations:**

- Save all artifacts to version control
- Build up a library of good design.md examples to show agents
- Track which agent prompts worked vs. which didn't
- Measure context window usage (keep under 40%)

---

## Part 7: Integrating QRSPI into Your Workflow

How do you make this part of how your team works?

### Week 1: Learn (Solo)

**Your job:**

1. Pick a medium-complexity feature
2. Do QRSPI manually with Claude (all 8 phases)
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

```
Agent: "I'm being asked to generate exploration questions.
The prompt says: 'Zero assumptions, be specific, reference files.'

I'll generate questions that force investigation of different code areas.
Each question should reveal a system property I need to understand."

Agent produces: 14 specific questions
Agent's internal confidence: "I'll score these on specificity and coverage"
```

### What the Agent is Thinking in Phase 2 (Research)

```
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

```
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

```
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

```
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

```
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

```
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

  ```
  Actual: 6 hours, 200 LOC = 0.03 hours per LOC = 1.8 min per LOC
  Plan estimated: 2 hours, 200 LOC = 0.01 hours per LOC = 0.6 min per LOC
  Agent is off by 3x
  ```

- In next Plan prompt, reference this: "In past features, we see 2-3 min
  per LOC including tests. Use that as baseline."
- Ask agent to re-estimate with this calibration

### Issue: Design Phase Feedback Isn't Actually Incorporated

**What you see:**

```
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

```
1. Define feature
2. Prompt agent through Q-R-D-S-P phases (one per prompt)
3. Save each artifact
4. Load prior artifacts into next phase
5. Human provides feedback (especially Design phase)
6. Agent implements per plan
7. Review code (should have no surprises)
8. Merge
```

### The Decision Tree

```
Is feature complex? → YES → Use full QRSPI (all 8 phases)
                   → NO → Skip Work Tree and Implementation Log

Is codebase unfamiliar? → YES → Spend more time on Research
                        → NO → Research can be shorter

Do you have time for alignment? → YES → Do QRSPI
                                → NO → Use unstructured (but expect more rework)

Is this a refactor or migration? → YES → Use QRSPI (critical for complex changes)
                                 → NO → Maybe skip for simple features

Are you trying to improve code quality? → YES → Use QRSPI (catches issues early)
                                        → NO → Unstructured is fine

```

### The Measurement You Should Care About

Not: "How much time does QRSPI take?"

But: "What's the total time from idea to shipped code, including all rework?"

QRSPI loses on phase time, wins on total time.

---
