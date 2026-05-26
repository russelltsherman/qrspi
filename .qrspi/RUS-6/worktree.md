# Work Tree — using graphite cli

**Plan basis:** plan.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T3 → T6

## Session 1

**Load:** structure.md §SKILL.md Frontmatter, structure.md §SKILL.md Body (pseudo-code outline), structure.md §references/cli-reference.md (pseudo-code outline)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `.claude/skills/using-graphite-cli/SKILL.md` with YAML frontmatter (5 fields) and skill body covering trigger conditions, single-commit convention, create-submit-modify-sync loop, stack navigation, conflict resolution, git-graphite warning, and reference section | — | §1 | M | pending |
| T2 | Create `.claude/skills/using-graphite-cli/references/cli-reference.md` with comprehensive command reference covering core workflow, stack navigation, conflict resolution, danger zone, and edge cases | — | §2 | S | pending |
| T3 | Verify T1: SKILL.md exists, frontmatter has all 5 fields, body under 500 lines | T1 | §1 verify | S | pending |
| T4 | Verify T2: cli-reference.md exists and contains all commands from the outline | T2 | §2 verify | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Skill files (SKILL.md + cli-reference.md) complete. Fresh context for CLAUDE.md registration and final verification.

## Session 2

**Load:** structure.md §CLAUDE.md Update, plan.md §Verify Checkpoint
**Estimated context:** ~20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T5 | Update `.claude/CLAUDE.md` — append one line to "Available skills" list after the last `/qrspi-*` entry | §3 | S | pending |
| T6 | Run all 5 verification checks from plan.md §Verify Checkpoint (frontmatter fields, body line count, CLAUDE.md registration, reference file exists, all files present) | §Verify | S | pending |
