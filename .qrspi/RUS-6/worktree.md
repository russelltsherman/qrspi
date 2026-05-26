# Work Tree -- Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Plan basis:** plan.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

---

## Critical Path

T1 -> T2 -> T3 -> T7 -> T8 -> T9

- T1 (command reference) and T2 (conflict resolution) can run in parallel, but T3 (SKILL.md) depends on both.
- T4 and T5 (eval edits) are independent of T1-T3 but must complete before T8 (content validation, which checks both skill files and evals).
- T6 (JSON validation) depends on T4+T5.
- T7 (frontmatter validation) depends on T3.
- T8 (content validation) depends on T3+T6.
- T9 (skill-creator invocation) depends on T7+T8.

Longest chain by cost: T1(M) -> T3(M) -> T7(S) -> T8(S) -> T9(L) = ~M+M+S+S+L

---

## Task Table

| ID  | Description                                              | Depends On | Plan Step | Cost | Status  |
|-----|----------------------------------------------------------|------------|-----------|------|---------|
| T1  | Create command reference file                            | --         | 1.1       | M    | pending |
| T2  | Create conflict resolution reference file                | --         | 1.2       | S    | pending |
| T3  | Create SKILL.md with frontmatter and body                | T1, T2     | 1.3       | M    | pending |
| T4  | Update graphite-evals.json: fix skill_name               | --         | 1.4       | S    | pending |
| T5  | Update graphite-evals.json: fix eval case 1 assertion    | T4         | 1.5       | S    | pending |
| T6  | Validate graphite-evals.json is valid JSON               | T5         | 1.6       | S    | pending |
| T7  | Validate SKILL.md frontmatter and body constraints       | T3         | 1.7       | S    | pending |
| T8  | Validate skill content against acceptance criteria       | T3, T6     | 1.8       | S    | pending |
| T9  | Invoke skill-creator to validate and refine              | T7, T8     | 1.9       | L    | pending |

---

## Sessions

### Session 1: Create reference files and fix evals

**Estimated context:** ~15%

**Load manifest:**
- `plan.md` Steps 1.1, 1.2, 1.4, 1.5
- `structure.md` Contracts (SKILL.md Frontmatter Contract, Reference File Loading Contract, Eval Suite Contract, Staging Rule Contract)
- `design.md` Desired End State (AC on command reference, conflict resolution, staging)
- `design.md` Delta (New Files table, Modified Files table)
- `research.md` Q2 (directory structure), Q5 (reference loading), Q8 (reference naming), Q11 (--no-interactive), Q12-Q13 (eval patterns)
- `research.md` Inconsistencies 1, 2, 4 (eval format, missing skill, -a flag contradiction)
- `evals/graphite-evals.json` (full file -- needed for editing)

**Tasks executed:**
- T1: Create `references/command-reference.md` (200-400 lines)
- T2: Create `references/conflict-resolution.md` (50-100 lines)
- T4: Fix `skill_name` in `graphite-evals.json`
- T5: Fix eval case 1 staging assertion in `graphite-evals.json`

**Rationale:** T1 and T2 are independent and can be written in parallel. T4 and T5 are small edits to a single file and naturally batch together. All four tasks have no upstream dependencies. Completing these first means Session 2 can focus entirely on SKILL.md authoring with the reference files already on disk.

---

=== SESSION BOUNDARY ===
Reason: Session 1 produces the reference files that SKILL.md must point to via Read instructions, and the eval fixes that validation tasks will check. Starting fresh ensures the SKILL.md author has clean context focused on the skill body, not reference content details.

---

### Session 2: Author SKILL.md and run all validations

**Estimated context:** ~30%

**Load manifest:**
- `plan.md` Steps 1.3, 1.6, 1.7, 1.8
- `structure.md` Contracts (SKILL.md Frontmatter Contract, Reference File Loading Contract, Staging Rule Contract)
- `design.md` Desired End State (all ACs)
- `design.md` Pattern Decisions 1-4
- `research.md` Q4 (frontmatter fields), Q5 (reference loading), Q11 (--no-interactive)
- `research.md` Discovered Patterns 1, 2, 8
- `.claude/skills/using-graphite-cli/references/command-reference.md` (full file -- must verify Read targets exist)
- `.claude/skills/using-graphite-cli/references/conflict-resolution.md` (full file -- must verify Read targets exist)
- `evals/graphite-evals.json` (full file -- needed for validation in T6 and T8)
- `plan.md` Verify section (Slice 1 Checkpoint commands)

**Tasks executed:**
- T3: Create SKILL.md (150-300 line body, 5-field frontmatter, Read instructions, core workflow rules)
- T6: Validate graphite-evals.json is valid JSON
- T7: Validate SKILL.md frontmatter and body constraints
- T8: Validate skill content against all acceptance criteria

**Rationale:** T3 is the core authoring task and needs the reference files from Session 1 to exist so it can write accurate Read instructions. T6, T7, and T8 are validation tasks that run sequentially after T3 and T5 are complete. Grouping all validation into this session allows immediate feedback and correction if any check fails.

---

=== SESSION BOUNDARY ===
Reason: Session 2 produces a validated SKILL.md and confirmed-passing evals. Session 3 invokes the external skill-creator which may propose changes requiring a fresh context to evaluate without bias from the authoring session.

---

### Session 3: Skill-creator validation and refinement

**Estimated context:** ~25%

**Load manifest:**
- `plan.md` Step 1.9
- `structure.md` Contracts (SKILL.md Frontmatter Contract -- to enforce during refinement)
- `structure.md` Unverified Assumptions 1 (skill-creator availability)
- `.claude/skills/using-graphite-cli/SKILL.md` (full file -- skill-creator input)
- `.claude/skills/using-graphite-cli/references/command-reference.md` (full file -- may need updates)
- `.claude/skills/using-graphite-cli/references/conflict-resolution.md` (full file -- may need updates)
- `plan.md` Verify section (Slice 1 Checkpoint -- re-run after any refinement)

**Tasks executed:**
- T9: Invoke skill-creator skill to validate and refine the SKILL.md through its eval loop. Accept changes that improve quality; reject changes that violate the 5-field frontmatter contract, the sub-500-line body constraint, or the staging rule. Re-run Slice 1 Checkpoint after any modifications.

**Rationale:** The skill-creator is an external tool whose behavior is not fully predictable (Unverified Assumption 1). Isolating it in its own session ensures that any proposed changes can be evaluated with full context of the contracts, and that the Slice 1 Checkpoint can be re-run cleanly after modifications.

---

## Session Summary

| Session | Tasks      | Estimated Context | Primary Output                              |
|---------|------------|-------------------|---------------------------------------------|
| 1       | T1 T2 T4 T5 | ~15%            | Reference files + eval fixes                |
| 2       | T3 T6 T7 T8 | ~30%            | SKILL.md + all validations passing          |
| 3       | T9           | ~25%            | Skill-creator validated, final checkpoint   |
