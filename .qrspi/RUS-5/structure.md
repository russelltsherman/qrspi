# Structure — writing-bash-scripts skill update

**Ticket:** RUS-5
**Generated:** 2026-05-27

---

## New/Modified Types and Signatures

No new types or functions are introduced into the codebase. The changes are
pure updates to an existing skill's documentation files. The only "signature"
that changes is the `command` field in SKILL.md YAML frontmatter:

```yaml
# Before
command: writing-bash-scripts

# After
command: /writing-bash-scripts
```

---

## Vertical Slices

### Slice 1 — SKILL.md body additions, command prefix fix, eval cleanup

**Goal:** Add all new content to the SKILL.md body, fix the `command` field in
frontmatter, and delete any eval harness artifacts left by skill-creator.

**What changes:**

- **Modify** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`:
  - Add `declare -f "cmd_${1}"` dynamic dispatch pattern to Function Conventions
  - Add Usage/Help section describing heredoc `usage()` with `${0##*/}` and column alignment
  - Add Logging section with `[[ -t 2 ]]` color detection pattern
  - Add `trap 'echo "Error on line $LINENO"'` debugging pattern
  - Add ~200-line guidance ("scripts over 200 lines should be evaluated for
    whether a different language is more appropriate")
  - Add Gotchas section with key callouts referencing `references/gotchas.md`
  - Change `command` frontmatter from `writing-bash-scripts` to `/writing-bash-scripts`
  - Add explicit seven-section ordered list to Script Structure (compact addition)

- **Delete** any eval harness files at
  `/home/vscode/.claude/skills/writing-bash-scripts-workspace/` if they exist
  (artifacts from skill-creator, not needed for guidance-only skill)

**Files touched (new/modify):**
| File | Action |
|------|--------|
| `.../skills/writing-bash-scripts/SKILL.md` | Modify (frontmatter + multiple body sections) |
| `.../skills/writing-bash-scripts-workspace/` (if exists) | Delete entire directory |

**Verification step:**
- Confirm `command: /writing-bash-scripts` in frontmatter
- Confirm all six new body sections are present and well-formed markdown
- Confirm no eval harness files remain
- Run ShellCheck on `references/template.sh` after Slice 2 updates
- Review SKILL.md line count to stay under 500 lines

**Context cost:** M — requires reading SKILL.md body to find correct insertion
points for each section.

**Dependencies:** None. Standalone slice.

---

### Slice 2 — Template.sh minor additions

**Goal:** Add the debugging trap pattern to `template.sh` so it demonstrates the
new convention in a complete, runnable example.

**What changes:**

- **Modify** `/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh`:
  - Add `trap 'echo "Error on line $LINENO"' debugging trap (in Helpers section)
  - Add inline comment on `${0##*/}` in constants section explaining basename extraction
  - Add `[[ -t 2 ]]` color detection block to demonstrate the pattern from SKILL.md

**Files touched (new/modify):**
| File | Action |
|------|--------|
| `.../skills/writing-bash-scripts/references/template.sh` | Modify (3 small additions) |

**Verification step:**
- Run `bash -n references/template.sh` to confirm no syntax errors
- Run `shellcheck -x references/template.sh` to confirm zero warnings

**Context cost:** S — template is small (105 lines), changes are additive and
isolated.

**Dependencies:** Slice 1 (same skill, but the two files are loosely coupled —
template.sh changes don't depend on SKILL.md content changes, only on the new
conventions being added in this ticket).

---

## Contracts

| Contract | Owner | Consumed By |
|----------|-------|-------------|
| SKILL.md `command` field value | Slice 1 | Claude Code skill loader (external — must equal `/writing-bash-scripts`) |
| SKILL.md section order (7 sections) | Slice 1 | Developer following the skill |
| template.sh conventions match SKILL.md body | Slice 2 | Developer using template as reference |
| Zero ShellCheck warnings on template.sh | Slice 2 | Verification gate |

---

## Unverified Assumptions

| # | Assumption | Source | How to verify |
|---|------------|--------|---------------|
| 1 | The eval workspace (`writing-bash-scripts-workspace/`) does not exist on disk | Checked at design time — returned exit code 2 (directory not found) | Confirmed during implementation via `ls` |
| 2 | The skill directory is at `/home/vscode/.claude/skills/writing-bash-scripts/` | Verified via `find` at design time | Confirmed in Slice 1 before writing |
| 3 | Adding six new sections to SKILL.md will not push it over 500 lines | Design delta estimates ~100 lines of additions on top of 274 current | Check line count after Slice 1 edits |
| 4 | The `command` field with `/writing-bash-scripts` (slash prefix) is recognized by Claude Code as a valid skill trigger | Design delta notes this is a recommendation, not confirmed against Claude Code source | Test by invoking `/writing-bash-scripts` in a session |
| 5 | The 200-line threshold for generated scripts is a ticket-internal convention, not a published standard | Design delta Open Question #4 notes this was not found in any existing spec | Encoding as soft guidance ("suggest a different language over 200 lines") avoids hard commitment |
