# Worktree — Create a new agent skill called writing bash scripts

**Plan basis:** plan.md @ 2026-05-25
**Generated:** 2026-05-25
**Status:** draft

---

## Critical Path

T1 → T2 → T6 → T7 → T8 → T9 → T10 → T11

Rationale: Directory must exist (T1) before any file creation. Template (T2) must exist before ShellCheck validation (T7). SKILL.md (T6) must exist before line-count (T8), frontmatter (T9), and pointer (T10) checks. T3-T5 are parallel with T2 once T1 is done, but T11 (all-files-exist check) depends on T2-T6 all completing.

---

## Session 1: Create directory and all reference files

### Load Manifest

| Artifact | Section |
|----------|---------|
| plan.md | Steps 1.1-1.5 |
| structure.md | Contracts |
| structure.md | Slice 1 — Files touched |

### Tasks

| ID | Description | Depends On | Plan Step | Cost | Status |
|----|-------------|------------|-----------|------|--------|
| T1 | Create skill directory structure (`~/.agents/skills/writing-bash-scripts/references/`) | — | 1.1 | S | pending |
| T2 | Create `references/template.sh` — canonical starter script, ShellCheck-clean | T1 | 1.2 | M | pending |
| T3 | Create `references/conventions.md` — quoting, variables, deps, temp files, exit codes, traps | T1 | 1.3 | M | pending |
| T4 | Create `references/patterns.md` — dispatcher, arg parsing, logging, function organization | T1 | 1.4 | M | pending |
| T5 | Create `references/gotchas.md` — portability, ShellCheck warnings, pitfalls | T1 | 1.5 | M | pending |

---

**--- SESSION BOUNDARY ---**

**Reason:** Session 1 produces all reference files. Session 2 needs to read/reference those files' structure to write SKILL.md with accurate conditional pointers. Splitting avoids loading the full content of four reference documents plus the SKILL.md authoring context simultaneously.

---

## Session 2: Author SKILL.md and run all verification checks

### Load Manifest

| Artifact | Section |
|----------|---------|
| plan.md | Steps 1.6-1.11 |
| structure.md | Contracts |
| structure.md | Slice 1 — Verification |
| references/template.sh | Full file (for pointer accuracy) |
| references/conventions.md | First 5 lines (confirm structure headings) |
| references/patterns.md | First 5 lines (confirm structure headings) |
| references/gotchas.md | First 5 lines (confirm structure headings) |

### Tasks

| ID | Description | Depends On | Plan Step | Cost | Status |
|----|-------------|------------|-----------|------|--------|
| T6 | Create `SKILL.md` — frontmatter, trigger conditions, conventions summary, conditional reference pointers, under 500 lines | T2, T3, T4, T5 | 1.6 | L | pending |
| T7 | Verify: `shellcheck references/template.sh` exits 0 | T2 | 1.7 | S | pending |
| T8 | Verify: `wc -l SKILL.md` under 500 | T6 | 1.8 | S | pending |
| T9 | Verify: frontmatter contains `name`, `description`, `command` fields | T6 | 1.9 | S | pending |
| T10 | Verify: SKILL.md body references all four reference files | T6 | 1.10 | S | pending |
| T11 | Verify: all reference files exist (conventions.md, patterns.md, gotchas.md, template.sh) | T2, T3, T4, T5 | 1.11 | S | pending |

---

## Context Budget Estimate

| Session | Loaded artifacts | Estimated context |
|---------|-----------------|-------------------|
| 1 | plan.md (Steps 1.1-1.5), structure.md (Contracts + Files touched) | ~15% |
| 2 | plan.md (Steps 1.6-1.11), structure.md (Contracts + Verification), reference file headers, template.sh full | ~30% |

Both sessions remain well under the 40% threshold.

---

## Summary

- **Total tasks:** 11
- **Sessions:** 2
- **Critical path length:** 8 tasks
- **Parallelizable in Session 1:** T2, T3, T4, T5 (all depend only on T1)
- **Parallelizable in Session 2:** T7, T11 (independent of T6); T8, T9, T10 (depend on T6, but independent of each other)
