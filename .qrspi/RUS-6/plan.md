# Plan — using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-26
**Phase:** Plan
**Status:** draft

## Summary

Create a new `using-graphite-cli` skill that encodes the Graphite CLI workflow for agent use. This involves creating two new files (SKILL.md + references/cli-reference.md) and updating project CLAUDE.md to register the skill.

**Slice:** 1 of 1 — all steps are self-contained within one slice.

## Steps

### Step 1: Create skill directory and SKILL.md

**File:** `.claude/skills/using-graphite-cli/SKILL.md` (new)
**Purpose:** Primary skill definition — encodes the single-commit-per-branch convention, create/submit/modify/sync workflow, stack navigation, conflict resolution, and git-graphite mixing warning.

**Frontmatter (exact):**
```yaml
---
name: using graphite cli
description: Full Graphite CLI workflow: create, submit, modify, sync stacked PRs. Trigger on any variant of: 'use graphite', 'use gt', 'Graphite CLI', 'gt command', stacked PRs, Graphite branches.
command: /using-graphite-cli
argument-hint: <command>
allowed-tools: Bash(gt:*), Bash(git status:*), Read
---
```

**Body:** Implement the structure.md pseudo-code outline verbatim:
- "When to Use This Skill" section with trigger conditions
- "The Single-Commit-Per-Branch Convention (Hard Rule)" section
- "Create -> Submit -> Modify -> Sync Loop" section with code examples for create, commit, submit, sync
- "Stack Navigation" table and directionality notes
- "Conflict Resolution" section with `gt continue` and warning against `git rebase --continue`
- "Mixing Git and Graphite — Warning" section
- "Reference Material" section pointing to `references/cli-reference.md`

**Constraints:**
- Body must be under 500 lines and 5000 tokens (structure.md targets ~150-200 lines).
- Follow the same style as existing skills: YAML frontmatter, H1 title, H2 sections, H3 subsections, code blocks with language tags.

**Verify:** After writing, confirm the file exists, frontmatter has all 5 required fields, and body line count is under 500.

**Rollback Notes:** None — this is a new file.

---

### Step 2: Create references/cli-reference.md

**File:** `.claude/skills/using-graphite-cli/references/cli-reference.md` (new)
**Purpose:** Comprehensive command reference covering all Graphite CLI commands, edge cases, and the "danger zone" commands. Serves as the detailed reference the skill body points to.

**Content:** Implement the structure.md pseudo-code outline:
- Header note about version snapshot and `gt --help` verification
- Core workflow commands: `gt create`, `gt checkout`, `gt modify`, `gt submit`, `gt sync`
- Stack navigation: `gt bu`, `gt bd`, `gt stack top`, `gt log short`
- Conflict resolution: `gt continue`
- Danger zone: `gt delete`, `gt move`, `gt merge`
- Edge cases section

**Constraints:**
- Target ~100-150 lines (structure.md estimate).
- Each command documented with signature, behavior notes, and flags.

**Verify:** After writing, confirm file exists and contains all commands from the outline.

**Rollback Notes:** None — this is a new file.

---

### Step 3: Update CLAUDE.md to register the skill

**File:** `.claude/CLAUDE.md` (modify)
**Action:** Add one line to the "Available skills" list, after the last `/qrspi-*` entry.

**Current state (exact lines to append after):**
```
- `/qrspi-pr <ticket-id>` — Prepare pull request summary
```

**After (add this line):**
```
- `/using-graphite-cli <command>` — Full Graphite CLI workflow: create, submit, modify, sync stacked PRs
```

**Contract:** The line must follow the exact format: `- /<command> <description>` with a tab-like appearance (matching existing entries). This is how the harness discovers and auto-invokes the skill.

**Rollback Notes:** Revert to the exact previous line list if needed — only one line added.

---

## Verify Checkpoint

**Command:** Validate all three artifacts:

```bash
# 1. SKILL.md frontmatter has all 5 fields
grep -c '^name:' .claude/skills/using-graphite-cli/SKILL.md && \
grep -c '^description:' .claude/skills/using-graphite-cli/SKILL.md && \
grep -c '^command:' .claude/skills/using-graphite-cli/SKILL.md && \
grep -c '^argument-hint:' .claude/skills/using-graphite-cli/SKILL.md && \
grep -c '^allowed-tools:' .claude/skills/using-graphite-cli/SKILL.md

# 2. SKILL.md body under 500 lines
body_lines=$(tail -n +8 .claude/skills/using-graphite-cli/SKILL.md | wc -l)
echo "SKILL.md body lines: $body_lines"
[ "$body_lines" -lt 500 ] && echo "PASS: under 500 lines" || echo "FAIL: exceeds 500 lines"

# 3. CLAUDE.md lists the skill
grep -q '/using-graphite-cli' .claude/CLAUDE.md && echo "PASS: skill registered in CLAUDE.md" || echo "FAIL: skill not in CLAUDE.md"

# 4. Reference file exists
test -f .claude/skills/using-graphite-cli/references/cli-reference.md && echo "PASS: cli-reference.md exists" || echo "FAIL: cli-reference.md missing"

# 5. All three files exist
test -f .claude/skills/using-graphite-cli/SKILL.md && \
test -f .claude/skills/using-graphite-cli/references/cli-reference.md && \
echo "PASS: all files present"
```

## Rollback Summary

All changes are additive or single-line edits. To fully rollback:
1. Delete the `.claude/skills/using-graphite-cli/` directory.
2. Remove the added line from `.claude/CLAUDE.md`.

No database migrations, config changes, or destructive operations involved.
