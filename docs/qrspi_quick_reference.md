# QRSPI Quick Reference Card

One-page cheat sheet for QRSPI workflow. Print and keep at desk.

---

## The 8 Phases (At a Glance)

```txt
┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI ALIGNMENT PHASES                           │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 1: QUESTIONS (Q) — 20 minutes                                 │
│ └─ Input: Feature description                                       │
│ └─ Output: 12-15 specific exploration questions                     │
│ └─ Purpose: Force investigation of codebase                         │
│ └─ Validation: Each question has specific file references           │
│                                                                     │
│ PHASE 2: RESEARCH (R) — 45 minutes                                  │
│ └─ Input: questions.md                                              │
│ └─ Output: 2-4K word factual codebase map                           │
│ └─ Purpose: Document existing system (zero recommendations)         │
│ └─ Validation: Zero "should" language, all claims code-referenced   │
│                                                                     │
│ PHASE 3: DESIGN (D) — 40 minutes                                    │
│ └─ Input: research.md + feature ticket (hidden until now)           │
│ └─ Output: design.md with architectural decisions                   │
│ └─ Purpose: Propose architecture, get human feedback (brain surgery)│
│ └─ Validation: All decisions reference research, options considered │
│                                                                     │
│ PHASE 4: STRUCTURE (S) — 30 minutes                                 │
│ └─ Input: approved design.md                                        │
│ └─ Output: 3-5 vertical slices, end-to-end testable                 │
│ └─ Purpose: Decompose into independent, reviewable chunks           │
│ └─ Validation: Each slice has clear entry/exit, not horizontal      │
│                                                                     │
│ PHASE 5: PLAN (P) — 40 minutes                                      │
│ └─ Input: approved structure.md                                     │
│ └─ Output: File-by-file implementation roadmap                      │
│ └─ Purpose: Detailed plan for coding (zero new decisions!)          │
│ └─ Validation: Zero new architecture, references all prior phases   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    QRSPI EXECUTION PHASES                           │
├─────────────────────────────────────────────────────────────────────┤
│ PHASE 6: WORK TREE (W) — 30 minutes (per slice)                     │
│ └─ Input: approved plan.md                                          │
│ └─ Output: 30-minute tasks with clear dependencies                  │
│ └─ Purpose: Granular task breakdown for implementation              │
│ └─ Validation: Each task <40 min, independent, testable             │
│ └─ Note: Optional for simple features (skip if obvious)             │
│                                                                     │
│ PHASE 7: IMPLEMENT (I) — Variable (typically 2-6 hours per slice)   │
│ └─ Input: approved plan.md + work_tree.md                           │
│ └─ Output: Code committed per task, tests passing                   │
│ └─ Purpose: Build the feature following plan exactly                │
│ └─ Validation: Code matches plan, tests pass, quality gates green   │
│                                                                     │
│ PHASE 8: PULL REQUEST (PR) — 15 minutes (review) + merge            │
│ └─ Input: implemented code                                          │
│ └─ Output: PR description referencing prior artifacts               │
│ └─ Purpose: Code review with zero surprises                         │
│ └─ Validation: Everything aligns with design/plan, no new decisions │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

TOTAL ALIGNMENT: 2.5 hours
TOTAL IMPLEMENTATION: Variable (2-6 hours per slice, depends on complexity)
TOTAL REVIEW: 15-30 minutes
```

---

## Failure Modes QRSPI Prevents

```txt
FAILURE MODE 1: Instruction Budget Overflow
├─ What happens: Agent silently skips alignment steps
├─ Where caught: Phase 1-5 validation (not in code)
├─ QRSPI defense: Small, focused phases, explicit validation
│
FAILURE MODE 2: Magic Words Dependency
├─ What happens: Agent needs specific phrases to behave correctly
├─ Where caught: Phase 3 design discussion (explicit feedback loop)
├─ QRSPI defense: Default behavior is correct, no secret incantations
│
FAILURE MODE 3: Plan-Reading Illusion
├─ What happens: Plans read well but don't actually work
├─ Where caught: Phase 6-7 (forces concrete task breakdown)
├─ QRSPI defense: Design must validate, plan must implement exactly
```

---

## Key Validation Checklist

```txt
After PHASE 1 (Questions):
  ☐ 12+ questions generated
  ☐ Each question references specific files
  ☐ Zero "should" language
  ☐ Covers 4+ system areas

After PHASE 2 (Research):
  ☐ Zero prescriptive language
  ☐ All claims code-referenced
  ☐ Database schema exact
  ☐ Uncertainty flagged explicitly

After PHASE 3 (Design):
  ☐ All decisions reference research.md
  ☐ Options explicitly considered
  ☐ Trade-offs stated (not hidden)
  ☐ Human feedback incorporated cleanly

After PHASE 4 (Structure):
  ☐ Slices are end-to-end testable
  ☐ Each slice has clear Definition of Done
  ☐ No horizontal layering
  ☐ Dependencies explicit

After PHASE 5 (Plan):
  ☐ Zero new architectural decisions
  ☐ All decisions reference design.md
  ☐ Testing strategy detailed
  ☐ No TODOs or vague work

After PHASE 7 (Implement):
  ☐ Code matches plan exactly
  ☐ All tests pass
  ☐ TypeScript/lint/coverage gates green
  ☐ Actual effort within 10% of estimate

After PHASE 8 (PR):
  ☐ Code follows existing patterns
  ☐ No new architectural decisions
  ☐ Tests pass, coverage >90%
  ☐ Zero surprises for reviewer
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
Familiar codebase         → MAY SKIP (research faster)
Crisis/hotfix mode        → SKIP (no time for alignment)
Greenfield project        → USE (design phase essential)
```

---

## Time Investment (Typical)

```txt
Simple Feature (1-2 hours):
  Unstructured: 30 min prompt + 1.5 hours coding + 30 min debug = 2.5 hours
  QRSPI: Skip it (too much overhead)

Medium Feature (2-6 hours):
  Unstructured: 30 min + 5 hours coding + 1.5 hours debug = 7 hours
  QRSPI: 2.5 hours align + 3.5 hours coding + 30 min review = 6.5 hours
  QRSPI Wins: Similar time, much better quality

Complex Feature (6+ hours):
  Unstructured: 1 hour + 8 hours coding + 3 hours debug = 12 hours
  QRSPI: 3 hours align + 6 hours coding + 30 min review = 9.5 hours
  QRSPI Wins: 2.5 hours faster, much better code
```

---

## Document Navigation

```txt
I need to...                  USE THIS DOCUMENT FIRST
──────────────────────────────────────────────────
Understand QRSPI purpose      Practical Application (Part 1)
Start my first feature        Practical Application (Part 2)
See a real example            Working Example
Validate an artifact          Artifacts Templates
Write an artifact             Artifacts Specification
Train an agent                Practical Application (Part 3)
Adapt for my team             Practical Application (Part 6-7)
Debug a problem               Practical Application (Part 4, 8)
Test an agent                 Test Prompts
Measure progress              Working Example (metrics section)
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

Do you know the codebase?
  ├─ YES → Shorten research phase
  └─ NO → Full research phase

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
❌ Skipping phases
   What happens: Design makes wrong assumptions
   Fix: Do all 5 alignment phases, every time

❌ Letting agent introduce new architecture in Plan
   What happens: Architectural drift into code
   Fix: After Phase 5, scan for new decisions

❌ Not saving artifacts between phases
   What happens: Agent has to re-generate or hallucinates
   Fix: Save every artifact to disk

❌ Asking agent to do multiple phases at once
   What happens: Agent does each phase poorly
   Fix: One phase per prompt

❌ Treating Design phase feedback as optional
   What happens: Feedback isn't actually incorporated
   Fix: After feedback, re-read entire design.md

❌ Confusing vertical slices with horizontal layers
   What happens: Slices aren't independently testable
   Fix: Each slice = mock → real → optimized

❌ Not providing human feedback on Design
   What happens: Agent uses outdated patterns
   Fix: Always review and correct design.md
```

---

## Measuring Success

After 3 features with QRSPI, measure these:

| Metric | Unstructured | QRSPI | Winner |
| ------ | ------------ | ----- | ------ |
| Time to Merge | 7-8 hours | 6 hours | QRSPI |
| Review Cycles | 2-3 | 0-1 | QRSPI |
| Post-Merge Rework | 30-40% | <10% | QRSPI |
| Estimate Accuracy | 50% off | 10% off | QRSPI |

If QRSPI wins 3/4: You've found value.

---

## The QRSPI Mantra

```txt
ALIGNMENT PHASE:
"Spend time upfront to save time overall."

EXECUTION PHASE:
"Follow the plan exactly. No surprises."

CODE REVIEW:
"This should be boring. No new decisions."

DEPLOYMENT:
"Confidence. Integrated. Works first time."
```

---

## Quick Commands

```bash
# Start Phase 1
Copy Q1.1 or Q1.2 from qrspi_test_prompts.md
Paste into Claude
Save output as artifacts/questions.md

# Start Phase 2
Copy R2.1 or R2.2 from qrspi_test_prompts.md
Include questions.md as input
Save output as artifacts/research.md

# Validate artifact
grep "should" research.md     # Should be empty
grep "[A-Z]:" research.md    # Check file references
wc -w research.md             # Check size (2K-4K words)

# Check for new architecture in plan
grep "class\|interface\|enum" design.md | sort > /tmp/d.txt
grep "class\|interface\|enum" plan.md | sort > /tmp/p.txt
diff /tmp/d.txt /tmp/p.txt    # Should be empty
```

---

## Print This Card

Frame it or print it for your desk. The 8 phases should be muscle memory:

```txt
Q → R → D → S → P → W → I → PR

Questions → Research → Design → Structure → Plan → Work Tree → Implement → PR
```

---

## One More Thing

QRSPI isn't perfect. It's a framework you'll adapt:

- Skip Work Tree for small features (saves 30 min)
- Combine Q-R if you're familiar with codebase
- Run Structure and Plan in single session if simple
- Add your own validation checks based on your codebase

The framework is the skeleton. Your judgment is the muscle.

Use it flexibly, but don't skip the core principles:

1. Explore before designing
2. Document facts before proposing changes
3. Get human feedback before planning
4. Plan before coding
5. Follow the plan during implementation

Everything else is optimization.

Good luck. You got this.
