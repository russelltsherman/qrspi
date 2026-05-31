# QRSPI System: Complete Documentation

Navigation guide and learning path through all QRSPI materials.

---

## What You Have

### 1. **Quick Reference Card** (`qrspi_quick_reference.md`)

One-page cheat sheet. Print it.

**Use this for:**

- All phases summarized at a glance
- Validation checklists for each phase
- The Linear-status lifecycle and the two review gates
- When-to-use decision tree
- Common mistakes list

**Time to use:** 5 min (reference during work)

---

### 2. **Practical Application Guide** (`qrspi_practical_application.md`)

Educational walkthrough of how to actually use the system.

**Use this for:**

- Understanding the purpose of QRSPI
- Deciding when to use it vs. when to skip
- Learning how to train agents on the framework
- Understanding common mistakes
- Measuring if it's working
- Adapting for your context

**Key sections:**

- Part 1: Why QRSPI exists (the problem it solves)
- Part 2: Step-by-step quickstart (the phases and the two review gates)
- Part 3: How to train your agent on the framework
- Part 4: Common mistakes & how to avoid them
- Part 5: Measuring success (5 key metrics)
- Part 6: Adapting for your context
- Part 7: Integration into team workflow
- Part 8: Troubleshooting issues
- Part 9: Building confidence
- Part 10: Decision tree (when to use QRSPI)

**Read this first** — it's educational and practical.

**Time to use:** 2-3 hours (thorough read)

---

### 3. **Working Example** (`qrspi_working_example.md`)

Complete annotated example of one feature going through every phase.

**Use this for:**

- Reference implementation (what good artifacts look like)
- Understanding the feedback loop (brain surgery in Design phase)
- Seeing how the two review gates work in practice
- Understanding how artifacts feed into each other

**Key sections:**

- Ticket — the Linear issue that defines the problem
- Questions — `questions.md`
- Research — `research.md` (with the agent's actual output; ticket hidden)
- Design — `design.md` (includes human feedback at the Design Review gate)
- Structure — `structure.md`
- Plan — `plan.md`
- Work Tree — `worktree.md`
- Implementation — code + `impl-log.md`, one slice per session
- PR — `pr-summary.md`

**Read this second** — see it in action.

**Time to use:** 1-2 hours (thorough read)

---

### 4. **Claude Code Implementation Guide** (`qrspi_claude_code_guide.md`)

Step-by-step instructions for installing and running QRSPI using Claude Code agents, skills, and `CLAUDE.md`.

**Use this for:**

- Setting up the phase agents and skill wrappers in a new project
- Understanding the per-phase tool lockdowns
- Copying the CLAUDE.md project template
- Troubleshooting phase behavior

**Key sections:**

- Project directory structure (`.claude/agents/`, `.claude/skills/`, `.claude/workflows/`, `.qrspi/`)
- CLAUDE.md template
- Phase agent definitions and their slash-command wrappers
- The `/qrspi-work` orchestrator and the `qrspi-batch` workflow
- Step-by-step walkthrough of one feature
- Context management commands
- Handling revisions

**Time to use:** 30 min setup, reference as needed

---

## Learning Path

### For Beginners (First Time Using QRSPI)

1. **Read:** Quick Reference Card (5 min)
   - Goal: See the shape of the workflow and the two review gates at a glance

2. **Read:** Practical Application Guide (Parts 1-2, ~45 min)
   - Goal: Understand why QRSPI exists and how to start

3. **Read:** Working Example (1-2 hours)
   - Goal: See a real feature move through the lifecycle

4. **Setup:** Claude Code Implementation Guide (~30 min)
   - Goal: Install the phase agents, skill wrappers, and CLAUDE.md in your project

5. **Do:** Create a ticket for your next feature
   - Command: `/qrspi-ticket <brief description>` — drafts a Linear issue through guided conversation

6. **Continue:** Drive the ticket forward
   - Command: `/qrspi-work <ticket-id>` — reads the ticket's Linear status and runs the matching phase, stopping at each human review gate

**Total learning time:** ~3 hours

---

### For Intermediate (Have Done QRSPI Once)

1. **Skim:** Practical Application Guide (Part 4: Common Mistakes, ~20 min)

2. **Do:** Second feature using `/qrspi-work` to drive the full lifecycle

3. **Track:** Metrics (Part 5 of Practical Application, ~10 min)

---

### For Advanced (Running This in a Team)

1. **Read:** Practical Application Guide (Parts 6-7, ~1 hour)
   - Goal: Plan rollout to team

2. **Build:** Custom CLAUDE.md additions for your codebase (1-2 hours)
   - Goal: Capture project-specific conventions so agents don't hallucinate them

3. **Batch:** Use the `qrspi-batch` workflow to drive many assigned tickets through the autonomously-runnable Linear states (Selected, Design Approved, Plan Approved) at once

4. **Establish:** Team standard (which features use QRSPI)

---

## Quick Reference: When to Use Each Document

```txt
I need to...                          → Use this document
────────────────────────────────────────────────────────────────
Understand why QRSPI matters        → Practical App (Part 1)
Start my first QRSPI feature        → Practical App (Part 2)
See a real example                  → Working Example
Install agents/skills in a project  → Claude Code Guide
Decide if QRSPI saves time          → Working Example (metrics)
Adapt for my team                   → Practical App (Part 6-7)
Debug a problem                     → Practical App (Part 4 or 8)
Know what's in each phase           → Quick Reference Card
```

---

## The Complete QRSPI System

### Core Materials

1. ✅ **Quick Reference Card** — Phases, the lifecycle, and checklists at a glance
2. ✅ **Practical Application Guide** — How to use it
3. ✅ **Working Example** — Proof it works
4. ✅ **Claude Code Implementation Guide** — How to install it

---

## The 30-Second TL;DR

**QRSPI is a structured workflow for AI agents that decomposes feature work into sequential phases, each producing a reviewable artifact:**

| Phase | Artifact |
|-------|----------|
| Ticket | A Linear issue (team Russelltsherman, project QRSPI) — defines the problem |
| Questions | `questions.md` — 8-15 technical questions from the ticket |
| Research | `research.md` — answers from the codebase (ticket hidden to prevent anchoring) |
| Design | `design.md` — pattern decisions, risk register, delta, open questions |
| Structure | `structure.md` — vertical slices, types, cross-slice contracts |
| Plan | `plan.md` — atomic implementation steps, verification checkpoints |
| Work Tree | `worktree.md` — session-aware task DAG with per-session context budgets |
| Implement | code + `impl-log.md` — one slice per fresh session |
| PR | `pr-summary.md` |

The ticket lives in Linear; all other artifacts are local files under `.qrspi/<ticket-id>/`. Linear holds status and phase-transition comments only — artifacts are not uploaded to Linear.

**Planning is split into two halves separated by two human review gates:**

- **Design half** — questions, research, design → **Design Review** gate
- **Plan half** — structure, plan, work tree → **Plan Review** gate

All six planning artifacts live on one `<ticket-id>/planning` branch as a single amended commit. The planning PR is submitted at Design Review and re-submitted (grown with the plan-half artifacts) at Plan Review. Implementation produces a stacked PR per slice.

**Why it works:**

- Aligns agent and human early (before coding)
- Catches hallucinations in Design, not Code Review
- The research firewall (ticket hidden, no Linear access) prevents anchoring bias
- Produces code that integrates first time
- Makes code review boring (no surprises)

---

## How It Runs

- **`/qrspi-ticket <description>`** creates a new Linear ticket through guided conversation.
- **`/qrspi-work <ticket-id>`** is the autonomous orchestrator. It reads the ticket's Linear status, runs the matching action (design half, plan half, implementation, or review response), and stops at the two human review gates. It never advances past Design Review or Plan Review on its own.
- Each phase's logic lives in a purpose-built agent at `.claude/agents/qrspi-<phase>.md` with per-phase tool lockdowns; the orchestrator spawns them by `subagent_type`. Slash-command wrappers live at `.claude/skills/qrspi-<phase>/SKILL.md`.
- **`qrspi-batch`** (`.claude/workflows/qrspi-batch.js`) drives many assigned tickets through the autonomously-runnable Linear states (Selected, Design Approved, Plan Approved) by spawning the typed phase agents. It deliberately leaves the human review gates (Design Review, Plan Review) untouched.

### The Linear status lifecycle

| Linear Status | Action |
|---------------|--------|
| Backlog / Selected | Run the design half (questions → research → design); submit the planning PR; move to Design Review |
| Design Review | **(human gate)** review the design-half PR; address feedback; the human moves the ticket to Design Approved |
| Design Approved | Run the plan half (structure → plan → work tree); update the planning PR; move to Plan Review |
| Plan Review | **(human gate)** review the full plan PR; address feedback; the human moves the ticket to Plan Approved |
| Plan Approved | Implement all slices; submit stacked PRs (one per slice); move to Code Review |
| Code Review | Address implementation review feedback; the human moves the ticket to Code Approved |
| Code Approved | Report ready to merge (human-owned merge) |
| Done | Clean up artifacts and worktree |

### Worktrees

Each ticket gets its own git worktree at `.worktrees/<ticket-id>/` (gitignored). The main checkout stays on `main`; ticket work happens in the worktree, so multiple tickets can be worked concurrently.

---

## Context management

- Start a fresh `/clear` session between implementation slices.
- Use `/compact` if context grows large within a phase.
- Use `/context` to check utilization. If over 40%, compact or start fresh.

---

## Troubleshooting

### The agent advanced past a review gate on its own

It should not. `/qrspi-work` stops at **Design Review** and **Plan Review** — these are human turns. The human moves the ticket to Design Approved / Plan Approved in Linear; only then does the next half run. If the orchestrator skipped a gate, check that the Linear status was actually transitioned by a human and not by the orchestrator.

### I tried QRSPI and it took longer than unstructured

**Likely cause:**

- Skipped or rushed the Design Review gate (the most valuable checkpoint)
- Didn't review artifacts before approving the half
- Agent hallucinated and had to redo work

**Fix:**

- Read Practical Application (Part 4: Common Mistakes)
- Treat the two review gates as real reviews, not rubber stamps
- Measure **total time including debugging**, not just alignment time

### The artifacts feel like busywork

Use QRSPI only for:

- Medium+ complexity features
- Unfamiliar codebases
- Team projects (alignment is critical)

Skip for:

- Simple CRUD endpoints
- One-off scripts
- Hotfixes in crisis mode

---

## Measuring Success

After doing QRSPI for 3 features, measure:

| Metric | Unstructured | QRSPI | Target |
|--------|-------------|-------|--------|
| Time to Merge | 7-8 hours | 6 hours | QRSPI wins |
| Code Review Cycles | 2-3 | 0-1 | QRSPI wins |
| Post-Merge Rework | 30-40% | <10% | QRSPI wins |
| Estimate Accuracy | 50% off | 10% off | QRSPI wins |

If QRSPI wins on 3/4 metrics, you've found value.

---

## Final Thought

QRSPI isn't a constraint. It's a structure that creates freedom.

By investing time upfront in alignment — and by holding the line at the two review gates — you get:

- Freedom from surprise reworks
- Freedom to be confident in code review
- Freedom to parallelize (clear interfaces, isolated worktrees)
- Freedom to iterate (good foundations)

The discipline isn't about slowing you down. It's about making your speed sustainable.
