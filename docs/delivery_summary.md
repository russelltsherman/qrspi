# QRSPI System: Delivery Summary

## What's Here

A complete system for AI-assisted software engineering using Claude Code. Four documentation files plus a working set of Claude Code skills.

---

## The Four Documents

### 1. **QRSPI Quick Reference Card** ← START HERE (5 min read)

`qrspi_quick_reference.md`

Your one-page cheat sheet.

Contains:

- All 9 phases summarized (2 lines each)
- Validation checklists for each phase
- When to use QRSPI (decision tree)
- Common mistakes list
- Time investment chart
- Quick commands

**When to use:** Pin it to your desk, reference during work.

---

### 2. **Practical Application Guide** ← READ SECOND (2-3 hours)

`qrspi_practical_application.md`

The educational foundation. How QRSPI actually works and why.

Contains:

- Part 1: The problem QRSPI solves
- Part 2: Step-by-step quickstart (9 phases explained)
- Part 3: How to train your AI agent on the framework
- Part 4: Common mistakes & how to avoid them
- Part 5: Measuring if it's working (5 key metrics)
- Part 6: Adapting QRSPI for your context
- Part 7: Integrating into team workflow
- Part 8: Troubleshooting agent issues
- Part 9: Building confidence
- Part 10: Decision tree (when to use QRSPI)

**When to use:** Read once thoroughly. Then reference Part 4 when problems arise.

---

### 3. **Working Example** ← READ THIRD (1-2 hours)

`qrspi_working_example.md`

Real example: Email preferences feature, Phases 0-8, with actual agent outputs.

Contains:

- Complete walkthrough of one feature
- Real artifacts (the Linear ticket, questions.md, research.md, design.md, etc.)
- Human feedback and agent incorporation (brain surgery example)
- Time per phase, actual vs. estimated
- Code snippets showing what "done" looks like
- Metrics at the end

**When to use:** Reference when creating your own artifacts. "Is my questions.md similar to this one?"

---

### 4. **Claude Code Implementation Guide** ← SETUP REFERENCE

`qrspi_claude_code_guide.md`

Step-by-step instructions for installing QRSPI in a Claude Code project using skills and `CLAUDE.md`.

Contains:

- Project directory structure
- CLAUDE.md template (copy into your project)
- All skill file definitions (copy-paste ready)
- Step-by-step walkthrough of one feature
- Context management (when to `/clear`, `/compact`)
- Handling revisions
- Adapting for your project (test commands, allowed-tools, conventions)
- Team sharing guidance

**When to use:** When setting up a new project. Reference when skill behavior is unexpected.

---

## The Skills

The `.claude/skills/` directory contains the actual Claude Code skill files:

```
.claude/skills/
├── qrspi-feature/SKILL.md   ← front door for new feature work
├── qrspi-ticket/SKILL.md
├── qrspi-questions/SKILL.md
├── qrspi-research/SKILL.md
├── qrspi-design/SKILL.md
├── qrspi-structure/SKILL.md
├── qrspi-plan/SKILL.md
├── qrspi-worktree/SKILL.md
├── qrspi-implement/SKILL.md
└── qrspi-pr/SKILL.md
```

Each skill handles one QRSPI phase. Invoked via `/qrspi-<phase> <ticket-id>`.

---

## How to Get Started

### Solo Engineer

1. **Today (30 min):**
   - Read Quick Reference (5 min)
   - Read Practical Application Parts 1-2 (25 min)

2. **Tomorrow (1-2 hours):**
   - Read Working Example

3. **Setup (30 min):**
   - Follow Claude Code Implementation Guide to install skills in your project

4. **This Week:**
   - Identify a medium-complexity feature
   - Run `/qrspi-feature` through `/qrspi-pr` on it
   - Measure total time including debugging

### Team Adoption

1. Lead reads all four documents (4 hours)
2. Lead runs one feature solo, captures metrics
3. Lead gives 1-hour workshop (what is QRSPI, live demo of Phases 0-3)
4. Team tries Phases 0-5 on next feature together
5. Team retrospect: did it help?
6. Establish QRSPI as standard for medium+ complexity features

---

## Critical Success Factors

1. **Do all phases, don't skip** — Skipped phases are where hallucinations hide
2. **Save artifacts** — Each skill writes to `.qrspi/<ticket-id>/`; never rely on agent memory
3. **Give feedback in Design** — This is the "brain surgery" moment; the agent learns your patterns from it
4. **Measure it** — Track time, hallucinations, review cycles, post-merge rework
5. **Adapt it** — QRSPI is a framework, not a law; document what you change and why

---

## FAQ

**Q: Does QRSPI take longer than unstructured prompting?**
A: No. Similar time for medium features, saves time for complex features. Include debugging time in your comparison.

**Q: Can I use this with other AI models?**
A: The skills are written for Claude Code, but the framework is model-agnostic. Adapt the skill prompts for your model.

**Q: Can I skip Work Tree (Phase 6)?**
A: Yes, for straightforward features. Keep it for large or complex ones.

**Q: What if agent feedback in Design gets extensive?**
A: That's normal — it's the "brain surgery" phase. Better to catch issues now than in code review.

---

## Next Action

1. Open `qrspi_quick_reference.md` — skim the 9 phases (5 min)
2. Read `qrspi_practical_application.md` Parts 1-2 (30 min)
3. Read `qrspi_working_example.md` (1-2 hours)
4. Follow `qrspi_claude_code_guide.md` to install skills in your project
5. Identify a medium-complexity feature and run it through the full workflow
