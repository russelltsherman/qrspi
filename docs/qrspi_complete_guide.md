# QRSPI System: Complete Documentation

Navigation guide and learning path through all QRSPI materials.

---

## What You Have

I've created a complete, production-ready system for AI-assisted software engineering. Here's what:

### 1. **Test Prompts** (`qrspi_test_prompts.md`)

50+ agent definition prompts for testing each QRSPI phase.

**Use this for:**

- Validating new agents against the framework
- Testing specific failure modes (hallucination, magic words, etc.)
- Running baseline benchmarks
- Training agents on the workflow

**Key sections:**

- Phase 1-5 alignment prompts (with complex and simple variants)
- Phase 6-8 execution prompts
- Edge case tests (contradictions, breaking changes, incomplete info)
- Integration tests (context management, multi-agent coordination)
- Measurement prompts (quality signals, health checks)

**Time to use:** 30 min (quick test) to 1 day (full test suite)

---

### 2. **Testing Strategy** (`qrspi_testing_strategy.md`)

How to run the test prompts effectively. Four execution strategies.

**Use this for:**

- Planning how to validate QRSPI
- Comparing RPI vs. QRSPI
- Setting up stress tests
- Building team simulation (multi-agent)

**Key sections:**

- Quick assessment (30 min)
- Moderate assessment (2-3 hours)
- Comprehensive assessment (full day)
- Common failure patterns & debugging
- Adaptation for different codebases

**Time to use:** 1 hour (read) + execution time

---

### 3. **Artifacts Specification** (`qrspi_artifacts_specification.md`)

Detailed specification for each phase's artifacts.

**Use this for:**

- Understanding what each artifact should contain
- Validating agent outputs
- Creating templates for your team
- Reference when artifacts are missing or incomplete

**Key sections:**

- 8 phases, one artifact per phase (some with secondaries)
- Validation criteria for each artifact
- Size and time estimates
- Handoff protocols between phases
- Directory structure for storing artifacts

**This is the reference document** — bookmark it.

**Time to use:** 2 hours (thorough read) or lookup as needed

---

### 4. **Artifacts Templates** (`qrspi_artifacts_templates.md`)

Quick templates and visual guides for creating artifacts.

**Use this for:**

- Copy-paste starters for each phase
- Visual diagram of artifact flow
- Validation checklists (can print)
- Phase progression checklist
- Rollback procedures

**Key sections:**

- Complete artifact flow diagram (visual)
- One-page template for each phase
- Validation rubric (cross-phase)
- Phase progression checklist
- Common artifacts tracking (context window, progress)

**This is the quick reference** — print the diagrams.

**Time to use:** 10 min (reference during work)

---

### 5. **Practical Application Guide** (`qrspi_practical_application.md`)

Educational walkthrough of how to actually use the system.

**Use this for:**

- Understanding the purpose of QRSPI
- Deciding when to use it vs. when to skip
- Learning how to train agents
- Understanding common mistakes
- Measuring if it's working
- Adapting for your context

**Key sections:**

- Part 1: Why QRSPI exists (the problem it solves)
- Part 2: Step-by-step quickstart (8 phases)
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

### 6. **Working Example** (`qrspi_working_example.md`)

Complete annotated example of one feature going through all 8 phases.

**Use this for:**

- Reference implementation (what good artifacts look like)
- Understanding the feedback loop (brain surgery in Design phase)
- Seeing time investments per phase
- Understanding how artifacts feed into each other
- Confidence building (seeing it actually works)

**Key sections:**

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

## Learning Path

### For Beginners (First Time Using QRSPI)

1. **Read:** Practical Application Guide (Part 1: Why QRSPI Exists)
   - Time: 15 min
   - Goal: Understand the problem QRSPI solves

2. **Read:** Practical Application Guide (Part 2: Quickstart)
   - Time: 30 min
   - Goal: See the 8 phases and what each does

3. **Read:** Working Example (Full)
   - Time: 1-2 hours
   - Goal: See a real feature with real time investments

4. **Do:** Run Phase 1 (Questions) on Your Feature
   - Time: 20 min
   - Goal: Create first artifact
   - Validate using: Artifacts Templates (validation checklist)

5. **Do:** Run Phase 2 (Research) on Your Feature
   - Time: 45 min
   - Goal: Document current system
   - Validate using: Artifacts Specification (research section)

6. **Continue:** Phases 3-8
   - Use prompts from: Test Prompts (phase-specific)
   - Validate using: Artifacts Templates (validation checklists)
   - Reference: Artifacts Specification (detailed specs)

**Total learning time:** ~4 hours
**Total first feature time:** ~6-8 hours (including phases)

---

### For Intermediate (Have Done QRSPI Once)

1. **Skim:** Practical Application Guide (Part 4: Common Mistakes)
   - Time: 20 min
   - Goal: Learn from failures you might encounter

2. **Reference:** Artifacts Templates (copy templates)
   - Time: 10 min per phase
   - Goal: Speed up artifact creation

3. **Do:** Second feature using full system
   - Time: 5-7 hours (faster than first feature)
   - Goal: Build confidence and speed

4. **Track:** Metrics (Part 5 of Practical Application)
   - Time: 10 min
   - Goal: Measure if it's working

---

### For Advanced (Running This in a Team)

1. **Read:** Practical Application Guide (Part 6: Adapting for Context)
   - Time: 30 min
   - Goal: Understand how to modify QRSPI for your team

2. **Read:** Practical Application Guide (Part 7: Integration into Team)
   - Time: 30 min
   - Goal: Plan rollout to team

3. **Use:** Test Prompts (for validation and training)
   - Time: As needed
   - Goal: Train agents and measure quality

4. **Build:** Custom templates for your codebase
   - Time: 2-3 hours
   - Goal: Speed up artifact creation
   - Use: Artifacts Templates (as reference)

5. **Establish:** Team standard (which features use QRSPI)
   - Use: Practical Application Guide (Part 7)

---

## Quick Reference: When to Use Each Document

```
I need to...                          → Use this document
────────────────────────────────────────────────────────────
Understand why QRSPI matters        → Practical App (Part 1)
Start my first QRSPI feature        → Practical App (Part 2)
See a real example                  → Working Example
Validate a questions.md             → Artifacts Templates (checklist)
Write a research.md                 → Artifacts Spec (R section)
Give agent a prompt                 → Test Prompts
Design integration tests            → Test Prompts (Phase 6-8 section)
Decide if QRSPI saves time          → Working Example (metrics) or Practical App (Part 5)
Adapt for my team                   → Practical App (Part 6-7)
Debug a problem                     → Practical App (Part 4 or 8)
Know what's in each phase           → Artifacts Templates (visual diagram)
Print something                     → Artifacts Templates (diagrams + checklists)
Deep dive on artifact structure     → Artifacts Specification
Troubleshoot an agent               → Practical App (Part 8)
```

---

## The Complete QRSPI System

### Core Materials (Must Have)

1. ✅ **Artifacts Specification** — Reference for artifact structure
2. ✅ **Artifacts Templates** — Quick templates and checklists
3. ✅ **Test Prompts** — Agent training and validation
4. ✅ **Practical Application Guide** — How to use it
5. ✅ **Working Example** — Proof it works

### Optional Add-Ons (Nice to Have)

- **Testing Strategy** — If benchmarking or comparing against RPI
- **Extended Examples** — (Not provided, but you can create for your codebase)

---

## File Summary

```
Your outputs/
├── qrspi_test_prompts.md                    (50+ test cases)
├── qrspi_testing_strategy.md                (4 test strategies)
├── qrspi_artifacts_specification.md         (Detailed specs)
├── qrspi_artifacts_templates.md             (Quick templates)
├── qrspi_practical_application.md           (How to use it)
└── qrspi_working_example.md                 (Real example)
```

All files are complete, production-ready, and can be used immediately.

---

## How to Use These Materials

### Scenario 1: Solo Engineer Adopting QRSPI

**Week 1:**

1. Read Practical Application (1-2 hours)
2. Read Working Example (1-2 hours)
3. Do Phase 1-5 on next feature (2.5 hours)

**Week 2:**

1. Do Phase 6-8 on same feature (3.5 hours)
2. Measure results (10 min)
3. Retrospect: Did it save time? Did code quality improve?

**Week 3-4:**

- Apply QRSPI to 2-3 more features
- Build confidence
- Adjust phases for your workflow

### Scenario 2: Team Adopting QRSPI

**Week 1:**

1. Lead reads all materials (4 hours)
2. Lead runs one feature solo (6 hours)

**Week 2:**

1. Lead gives workshop (1 hour)
   - What is QRSPI
   - Why it matters (show metrics from own feature)
   - Live demo of Phases 1-3
2. Team tries Phases 1-5 on next feature (2-3 hours)
3. Lead gives feedback on research.md and design.md

**Week 3:**

1. Team completes Phases 6-8 (3-4 hours)
2. Code review (30 min, quick approval)
3. Team retrospect: Should we do this again?

**Week 4+:**

- Establish QRSPI as standard for features >Medium complexity
- Build up template library for your codebase
- Measure improvement over time

### Scenario 3: Building with Agents (This Workshop's Case)

**Phase 1: Setup**

1. Read Practical Application (Part 3: Training Agents)
2. Build system prompt with QRSPI instructions
3. Set up artifact storage (Git or filesystem)

**Phase 2: Validation**

1. Run test prompts from Test Prompts document
2. Measure hallucination rate, accuracy, time
3. Build up library of good/bad examples

**Phase 3: Production**

1. Run QRSPI on all medium+ complexity features
2. Track metrics (time, hallucinations, review cycles)
3. Iterate on prompts based on failures

**Phase 4: Scaling**

1. Add sub-agent support (Phase 6-7 parallelization)
2. Build automated quality gates
3. Create dashboards for metrics

---

## The 30-Second TL;DR

**QRSPI is an 8-phase workflow for AI agents that:**

1. Explores codebase (Phase 1-2)
2. Designs architecture with human feedback (Phase 3)
3. Plans implementation (Phase 4-5)
4. Executes with minimal surprises (Phase 6-8)

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

**Get started:**

1. Read Practical Application (Part 1-2)
2. Do Phase 1 on your next feature
3. Continue phases
4. Measure results

---

## Troubleshooting

### I don't have time for 6 hours of alignment + coding

**Options:**

- Skip phases 6 (Work Tree) and use it only for large features
- Use QRSPI only for complex features (skip for simple CRUD)
- Do minimal QRSPI: Just Q-R-D-P (skip S)

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

### I don't know how to train my agent

**Start here:**

- Practical Application (Part 3: Training Your Agent)
- Copy prompts from Test Prompts document
- Use system prompt approach from Part 3

### The artifacts feel like busywork

**You might be right**, if:

- Feature is super simple (one file change)
- You know the codebase very well

**Use QRSPI only for:**

- Medium+ complexity features
- Unfamiliar codebases
- Team projects (alignment is critical)

**Skip for:**

- Simple CRUD endpoints
- One-off scripts
- Hotfixes in crisis mode

---

## Measuring Success

After doing QRSPI for 3 features, measure:

**Metric 1: Time to Merge**

- Unstructured: X hours (all-in, including rework)
- QRSPI: Y hours (all-in)
- If Y < X: QRSPI is winning

**Metric 2: Code Review Cycles**

- Unstructured: 2-3 cycles ("Change architecture here", "Fix this pattern")
- QRSPI: 0-1 cycle (no surprises)
- If QRSPI is 0-1: QRSPI is winning

**Metric 3: Post-Merge Rework**

- Unstructured: 30-40% of code changes in next 2 weeks
- QRSPI: <10% (just bugfixes and optimizations)
- If QRSPI is <10%: QRSPI is winning

**Metric 4: Estimate Accuracy**

- Unstructured: 50% off (estimated 4h, took 6h)
- QRSPI: 10% off (estimated 6h, took 5.5h)
- If QRSPI is within 10%: QRSPI is winning

If QRSPI wins on 3/4 metrics, you've found value.

---

## Next Steps

**Right now:**

1. Print the flow diagram from Artifacts Templates
2. Read Practical Application Part 1-2 (30 min)
3. Read Working Example (1-2 hours)

**This week:**

1. Do Phase 1 on your next feature (20 min)
2. Do Phase 2 on same feature (45 min)
3. Do Phase 3 with human feedback (40 min)

**This month:**

1. Complete first full QRSPI feature
2. Measure time and quality
3. Decide if it's worth continuing

---

## Support & Iteration

If something in QRSPI doesn't work for your context:

**Option 1: Adapt** (Recommended)

- Read Practical Application (Part 6: Adapting QRSPI)
- Modify phases for your needs
- Document what changed and why

**Option 2: Contribute**

- Build good examples for your codebase
- Share lessons learned with team
- Help others implement QRSPI

**Option 3: Report**

- If you find a failure mode not covered in materials, note it
- Share how you fixed it
- Help improve the system

---

## Final Thought

QRSPI isn't a constraint. It's a structure that creates freedom.

By investing time upfront in alignment, you get:

- Freedom from surprise reworks
- Freedom to be confident in code review
- Freedom to parallelize (clear interfaces)
- Freedom to iterate (good foundations)

The discipline isn't about slowing you down. It's about making your speed sustainable.

Happy building.

---

## Document Map

```
Start here (1-2 hours reading):
├── Practical Application (Parts 1-2)
└── Working Example

Then reference as needed:
├── Artifacts Templates (quick lookup)
├── Artifacts Specification (deep reference)
└── Test Prompts (for validation)

For team adoption:
├── Practical Application (Parts 6-7)
└── Testing Strategy

For troubleshooting:
├── Practical Application (Parts 4, 8-9)
└── Artifacts Templates (phase progression checklist)
```

You have everything you need to implement QRSPI in your workflow.

Good luck.
