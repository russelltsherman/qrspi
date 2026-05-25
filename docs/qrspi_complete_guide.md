# QRSPI System: Complete Documentation

Navigation guide and learning path through all QRSPI materials.

---

## What You Have

### 1. **Quick Reference Card** (`qrspi_quick_reference.md`)

One-page cheat sheet. Print it.

**Use this for:**

- All 9 phases summarized at a glance
- Validation checklists for each phase
- When-to-use decision tree
- Common mistakes list
- Time investment chart

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
- Part 2: Step-by-step quickstart (9 phases)
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

Complete annotated example of one feature going through all 9 phases.

**Use this for:**

- Reference implementation (what good artifacts look like)
- Understanding the feedback loop (brain surgery in Design phase)
- Seeing time investments per phase
- Understanding how artifacts feed into each other

**Key sections:**

- Phase 0: Ticket (15 min)
- Phase 1: Questions (20 min)
- Phase 2: Research (45 min, with agent's actual output)
- Phase 3: Design (40 min, includes human feedback)
- Phase 4: Structure (30 min)
- Phase 5: Plan (40 min)
- Phase 6: Work Tree (30 min)
- Phase 7: Implementation (3.5 hours)
- Phase 8: PR (15 min review)

**Read this second** — see it in action.

**Time to use:** 1-2 hours (thorough read)

---

### 4. **Claude Code Implementation Guide** (`qrspi_claude_code_guide.md`)

Step-by-step instructions for installing and running QRSPI using Claude Code skills and `CLAUDE.md`.

**Use this for:**

- Setting up the skill files in a new project
- Understanding the `allowed-tools` constraints per phase
- Copying the CLAUDE.md project template
- Troubleshooting skill behavior

**Key sections:**

- Project directory structure
- CLAUDE.md template
- All 9 skill file definitions (copy-paste ready)
- Step-by-step walkthrough of one feature
- Context management commands
- Handling revisions
- Adapting to your project

**Time to use:** 30 min setup, reference as needed

---

## Learning Path

### For Beginners (First Time Using QRSPI)

1. **Read:** Quick Reference Card (5 min)
   - Goal: See the shape of the workflow at a glance

2. **Read:** Practical Application Guide (Parts 1-2, ~45 min)
   - Goal: Understand why QRSPI exists and how to start

3. **Read:** Working Example (1-2 hours)
   - Goal: See a real feature with real time investments

4. **Setup:** Claude Code Implementation Guide (~30 min)
   - Goal: Install skills and CLAUDE.md in your project

5. **Do:** Run Phase 0 (Ticket) on your next feature
   - Command: `/qrspi-ticket <brief description>`

6. **Continue:** Phases 1-8 sequentially
   - Reference: Quick Reference Card (validation checklists)

**Total learning time:** ~3 hours
**Total first feature time:** ~6-8 hours (including phases)

---

### For Intermediate (Have Done QRSPI Once)

1. **Skim:** Practical Application Guide (Part 4: Common Mistakes, ~20 min)

2. **Do:** Second feature using full system (5-7 hours)

3. **Track:** Metrics (Part 5 of Practical Application, ~10 min)

---

### For Advanced (Running This in a Team)

1. **Read:** Practical Application Guide (Parts 6-7, ~1 hour)
   - Goal: Plan rollout to team

2. **Build:** Custom CLAUDE.md additions for your codebase (1-2 hours)
   - Goal: Capture project-specific conventions so agents don't hallucinate them

3. **Establish:** Team standard (which features use QRSPI)

---

## Quick Reference: When to Use Each Document

```txt
I need to...                          → Use this document
────────────────────────────────────────────────────────────────
Understand why QRSPI matters        → Practical App (Part 1)
Start my first QRSPI feature        → Practical App (Part 2)
See a real example                  → Working Example
Install skills in a new project     → Claude Code Guide
Decide if QRSPI saves time          → Working Example (metrics)
Adapt for my team                   → Practical App (Part 6-7)
Debug a problem                     → Practical App (Part 4 or 8)
Know what's in each phase           → Quick Reference Card
```

---

## The Complete QRSPI System

### Core Materials

1. ✅ **Quick Reference Card** — Phases and checklists at a glance
2. ✅ **Practical Application Guide** — How to use it
3. ✅ **Working Example** — Proof it works
4. ✅ **Claude Code Implementation Guide** — How to install it

---

## The 30-Second TL;DR

**QRSPI is a 9-phase workflow for AI agents that:**

0. Authors a well-formed ticket through guided conversation (Phase 0)
1. Explores codebase (Phases 1-2)
2. Designs architecture with human feedback (Phase 3)
3. Plans implementation (Phases 4-5)
4. Executes with minimal surprises (Phases 6-8)

**Why it works:**

- Aligns agent and human early (before coding)
- Catches hallucinations in Design, not Code Review
- Makes estimates accurate (within 10%)
- Produces code that integrates first time
- Makes code review boring (no surprises)

**Time investment:**

- Unstructured: 4 hours coding + 2 hours debugging = 6 hours
- QRSPI: 2.5 hours alignment + 3 hours coding + 0.5 hours review = 6 hours
- **Same total time, but QRSPI code is better quality**
- **For complex features, QRSPI saves 3-5 hours**

---

## Troubleshooting

### I don't have time for 6 hours of alignment + coding

- Skip Work Tree (Phase 6) for straightforward features
- Use QRSPI only for complex features (skip for simple CRUD)
- Do minimal QRSPI: Just T-Q-R-D-P (skip S and W)

See Practical Application (Part 6) for context-specific adaptations.

### I tried QRSPI and it took longer than unstructured

**Likely cause:**

- Skipped a phase (especially Design feedback)
- Didn't save artifacts between phases
- Agent hallucinated and had to redo work

**Fix:**

- Read Practical Application (Part 4: Common Mistakes)
- Try again, following each phase carefully
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

By investing time upfront in alignment, you get:

- Freedom from surprise reworks
- Freedom to be confident in code review
- Freedom to parallelize (clear interfaces)
- Freedom to iterate (good foundations)

The discipline isn't about slowing you down. It's about making your speed sustainable.
