# Work Tree — Create a skill for writing bash scripts
**Ticket:** RUS-5
**Generated:** 2026-05-25
**Status:** draft

---

## Critical Path

T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10

All tasks are sequential. Slice 1 is the foundation (SKILL.md), Slices 2 and 3 produce reference files that SKILL.md points to, and Slice 4 requires all three files to exist before skill-creator review.

---

## Session 1 — SKILL.md Core

**Load manifest:**
- `structure.md` §Types and Signatures (frontmatter schema)
- `structure.md` §Contracts → "Cross-Slice Interface: SKILL.md references/ pointers"
- `plan.md` §Slice 1 (Steps 1.1–1.3 + Verify)

**Estimated context:** ~15%

| ID | Description | Depends On | Plan Step | Cost | Status |
|----|-------------|------------|-----------|------|--------|
| T1 | Create directory `.claude/skills/bash-scripts/` | — | 1.1 | S | pending |
| T2 | Create SKILL.md with YAML frontmatter and full body (When to Use, Template, ShellCheck, Testing, References) | T1 | 1.2 | M | pending |
| T3 | Validate SKILL.md frontmatter parses correctly and all fields present | T2 | 1.3 + Verify | S | pending |

---

**SESSION BOUNDARY**
**Reason:** Slice 1 is complete and verified. Slice 2 introduces a new file with distinct content (conventions catalog). Fresh context avoids accumulating draft iterations from SKILL.md authoring.

---

## Session 2 — Convention Catalog

**Load manifest:**
- `structure.md` §Types and Signatures → "references/conventions.md"
- `structure.md` §Contracts → "Convention consistency contract"
- `plan.md` §Slice 2 (Steps 2.1–2.2 + Verify)

**Estimated context:** ~15%

| ID | Description | Depends On | Plan Step | Cost | Status |
|----|-------------|------------|-----------|------|--------|
| T4 | Create directory `.claude/skills/bash-scripts/references/` | T3 | 2.1 | S | pending |
| T5 | Create conventions.md with all 11 sections (150-250 lines) | T4 | 2.2 | M | pending |
| T6 | Validate conventions.md has all sections, correct line count, and codebase-consistent conventions | T5 | Verify | S | pending |

---

**SESSION BOUNDARY**
**Reason:** Slice 2 is complete. Slice 3 is a separate reference file with distinct content (gotchas). Keeping sessions aligned to slices maintains clean context.

---

## Session 3 — Gotchas Catalog

**Load manifest:**
- `structure.md` §Types and Signatures → "references/gotchas.md"
- `plan.md` §Slice 3 (Step 3.1 + Verify)

**Estimated context:** ~10%

| ID | Description | Depends On | Plan Step | Cost | Status |
|----|-------------|------------|-----------|------|--------|
| T7 | Create gotchas.md with all 6 categories, each having problem/bad/fix/ShellCheck (50-100 lines) | T6 | 3.1 | M | pending |
| T8 | Validate gotchas.md has all 6 categories, correct line count, and required components per entry | T7 | Verify | S | pending |

---

**SESSION BOUNDARY**
**Reason:** Slices 1-3 are complete. Slice 4 invokes skill-creator which is an interactive M-cost session that may modify any of the three files. Fresh context ensures maximum room for skill-creator interaction and eval loop.

---

## Session 4 — Skill-creator Review and Refinement

**Load manifest:**
- `.claude/skills/bash-scripts/SKILL.md` (full file — skill-creator needs complete context)
- `.claude/skills/bash-scripts/references/conventions.md` (full file)
- `.claude/skills/bash-scripts/references/gotchas.md` (full file)
- `structure.md` §Contracts → "Frontmatter triggering contract"
- `plan.md` §Slice 4 (Steps 4.1–4.4 + Verify)

**Estimated context:** ~30%

| ID | Description | Depends On | Plan Step | Cost | Status |
|----|-------------|------------|-----------|------|--------|
| T9 | Invoke skill-creator skill on SKILL.md for review; incorporate feedback into SKILL.md and references | T8 | 4.1, 4.2, 4.3 | M | pending |
| T10 | Re-validate frontmatter and structure after skill-creator modifications | T9 | 4.4 + Verify | S | pending |

---

## Task Summary

| ID | Cost | Session |
|----|------|---------|
| T1 | S | 1 |
| T2 | M | 1 |
| T3 | S | 1 |
| T4 | S | 2 |
| T5 | M | 2 |
| T6 | S | 2 |
| T7 | M | 3 |
| T8 | S | 3 |
| T9 | M | 4 |
| T10 | S | 4 |

**Total tasks:** 10
**Total sessions:** 4
**Max session context:** 30% (Session 4)
