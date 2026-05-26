# Work Tree — Create a new agent skill called using argo workflows cli

**Plan basis:** plan.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

---

## Critical Path

T1 → T2 → T5 → T7 → T8 → T9

- T1: Create directory structure (gate for all file creation)
- T2: Create SKILL.md (largest file, defines Read instructions to reference files)
- T5: Register skill in CLAUDE.md (completes deliverable set)
- T7: Verify line counts (validates size constraints)
- T8: Verify frontmatter fields (validates schema)
- T9: Invoke skill-creator for validation (final gate)

Note: T3, T4 run in parallel with T2 but are not on the critical path because they are smaller and faster.

---

## Task Table

| Task | Description | Depends On | Plan Step | Cost | Status |
|------|-------------|-----------|-----------|------|--------|
| T1 | Create skill directory structure (`.claude/skills/using-argo-workflows-cli/references/`) | — | 1.1 | S | pending |
| T2 | Create SKILL.md with frontmatter and compact body (150-200 lines) | T1 | 1.5 | L | pending |
| T3 | Create `references/template-authoring.md` (DAG vs Steps, WorkflowTemplates, template design) | T1 | 1.2 | M | pending |
| T4 | Create `references/debugging-and-errors.md` (escalation ladder, failure modes, retry config) | T1 | 1.3 | M | pending |
| T5 | Create `references/cron-and-resources.md` (CronWorkflow lifecycle, resources, artifacts) | T1 | 1.4 | M | pending |
| T6 | Register skill in `.claude/CLAUDE.md` (add Advisory skills subsection) | T1 | 1.6 | S | pending |
| T7 | Verify line counts (SKILL.md body < 200, total < 500, each ref < 80) | T2, T3, T4, T5 | 1.7 | S | pending |
| T8 | Verify frontmatter fields (5 required fields present) | T2 | 1.8 | S | pending |
| T9 | Verify command group coverage (all 14 groups mentioned) | T2 | 1.9 | S | pending |
| T10 | Verify Read instructions and prerequisite check | T2 | 1.10 | S | pending |
| T11 | Verify CLAUDE.md registration | T6 | 1.11 | S | pending |
| T12 | Invoke skill-creator for final validation | T7, T8, T9, T10, T11 | 1.12 | S | pending |

---

## Session 1

**Goal:** Create all skill files, register in CLAUDE.md, run all verifications, and invoke skill-creator.

**Reason for single session:** This is a single-slice plan producing 4 new markdown files (~350-440 lines total) and one small edit to an existing file. All tasks share the same context (design.md pattern decisions, structure.md contracts, plan.md content requirements). Splitting into multiple sessions would force redundant context loading with no benefit. Estimated context: ~25% (plan, structure contracts, design pattern decisions, plus generated files).

### Load Manifest

| Artifact | Section | Purpose |
|----------|---------|---------|
| plan.md | Steps 1.1-1.12 | Task definitions and verification commands |
| structure.md | Contracts (Frontmatter contract, CLAUDE.md registration contract, Cross-file references) | Exact contract text for frontmatter fields, Read instructions, and registration entry |
| structure.md | Slice 1 (Verification checklist) | Verification criteria checklist |
| design.md | Desired End State | Acceptance criteria mapped to system behaviors |
| design.md | Pattern Decisions (PD-1 through PD-5) | Architectural decisions governing file organization, Bash permissions, reference split, prereq check, invocation model |
| design.md | Delta (New Files table) | Size targets for each file |
| research.md | Q2 (Frontmatter fields) | Exact frontmatter field schema and existing examples |
| research.md | Q4 (References format) | Reference file format precedent from qrspi-work |
| research.md | Q6 (SKILL.md body structure) | Structural patterns for compact skill bodies |
| research.md | Q10 (Prerequisite checks) | Existing error handling patterns to extend |
| `.claude/CLAUDE.md` | Available skills section | Current content for the registration edit (lines 12-22) |

### Task Execution Order

1. **T1** — Create directory structure
2. **T2, T3, T4, T5** — Create SKILL.md and all 3 reference files (parallel)
3. **T6** — Register skill in CLAUDE.md
4. **T7, T8, T9, T10, T11** — Run all verification checks (parallel)
5. **T12** — Invoke skill-creator for final validation

---

**Estimated context utilization:** ~25%
**Sessions total:** 1
**Tasks total:** 12
