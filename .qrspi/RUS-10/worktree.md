# Work Tree — RUS-10: Create the `using-cmux-cli` skill

**Plan basis:** plan.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft
**Total sessions:** 4
**Total tasks:** 17
**Critical path:** T1 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10 -> T11 -> T12 -> T13 -> T14 -> T15 -> T16 -> T17

## Critical Path Analysis

| Task | Description | Cost |
|------|-------------|------|
| T1 | Create `~/.agents/skills/using-cmux-cli/` and `references/` directories | S |
| T5 | Create SKILL.md with frontmatter (5 fields) | S |
| T6 | Add SKILL.md body intro (what cmux is, macOS constraint) | S |
| T7 | Add `## Workspace lifecycle` section | S |
| T8 | Add `## Surface and pane management` section | S |
| T9 | Add `## Session management and restore` section | S |
| T10 | Add `## Keyboard shortcuts` section | S |
| T11 | Add `## Notifications` section | S |
| T12 | Add `## Claude Code Teams integration` section | S |
| T13 | Add `## In-app browser` section | S |
| T14 | Add `## Multi-agent orchestration` section | S |
| T15 | Add `## Hook setup` section | S |
| T16 | Modify `~/.agents/AGENTS.md` — Add Available Skills section | M |
| T17 | Verify — frontmatter, line count, coverage, skill-creator | M |

T2, T3, T4 (reference files) are on a parallel path: T1 -> T2 -> T17, T1 -> T3 -> T17, T1 -> T4 -> T17. They are smaller and faster than the SKILL.md body chain, so the critical path goes through the SKILL.md body sections.

--- SESSION BOUNDARY ---
**Reason:** End of critical path planning. Below are the session definitions.

## Session 1

**Load:** plan.md (Slice 1 — Steps 1.1 through 1.4, directory setup and reference files)
**Estimated context:** 15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `~/.agents/skills/using-cmux-cli/` and `references/` directories | — | 1.1 | S | pending |
| T2 | Create `references/keyboard-shortcuts.md` (~60-100 lines, shortcut tables by topic) | T1 | 1.2 | S | pending |
| T3 | Create `references/cli-socket-api.md` (~60-100 lines, CLI + socket API reference) | T1 | 1.3 | S | pending |
| T4 | Create `references/hook-setup.md` (~80-120 lines, hook config for 10+ agents) | T1 | 1.4 | S | pending |

### Load Manifest

| Artifact | Section | Purpose |
|----------|---------|---------|
| plan.md | Steps 1.1-1.4 (Directory Setup, Reference Files) | Task definitions, file sizes, content requirements for 3 reference files |

### Task Execution

1. **T1** — Create directory structure
2. **T2, T3, T4** — Create all 3 reference files (parallel)

--- SESSION BOUNDARY ---
**Reason:** Reference files complete. T2, T3, T4 are independent of the SKILL.md body. A fresh context is cleaner than carrying 3 reference file contents into the SKILL.md writing session. Context saving: ~200 lines of reference content freed.

## Session 2

**Load:** plan.md (Slice 1 — Steps 1.5 through 1.15, Skill Body), references/keyboard-shortcuts.md, references/cli-socket-api.md, references/hook-setup.md
**Estimated context:** 30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T5 | Create SKILL.md with frontmatter (5 fields: name, description, command, argument-hint, allowed-tools) | T1 | 1.5 | S | pending |
| T6 | Add SKILL.md body intro: what cmux is, why agents use it, macOS-only constraint | T5 | 1.6 | S | pending |
| T7 | Add `## Workspace lifecycle` section — create, switch, workspace-per-project pattern | T6 | 1.7 | S | pending |
| T8 | Add `## Surface and pane management` section — surfaces, splitting, focus, resizing | T7 | 1.8 | S | pending |
| T9 | Add `## Session management and restore` section — create, detach, kill, restore | T8 | 1.9 | S | pending |
| T10 | Add `## Keyboard shortcuts` section — overview of key shortcuts | T9 | 1.10 | S | pending |
| T11 | Add `## Notifications` section — subscription, acknowledgment, lifecycle | T10 | 1.11 | S | pending |
| T12 | Add `## Claude Code Teams integration` section — agent orchestration via cmux | T11 | 1.12 | S | pending |
| T13 | Add `## In-app browser` section — cmux browser for web content | T12 | 1.13 | S | pending |
| T14 | Add `## Multi-agent orchestration` section — spawning and coordinating agents | T13 | 1.14 | S | pending |
| T15 | Add `## Hook setup` section — high-level explanation, reference to hook-setup.md | T14 | 1.15 | S | pending |

### Load Manifest

| Artifact | Section | Purpose |
|----------|---------|---------|
| plan.md | Steps 1.5-1.15 (Skill Body) | Frontmatter schema, each body section's content requirements and reference directions |
| references/keyboard-shortcuts.md | Full file | Read instruction in SKILL.md body must point here; actual content needed to write T10 |
| references/cli-socket-api.md | Full file | Read instruction in SKILL.md body must point here; content needed for T7-T13 |
| references/hook-setup.md | Full file | Read instruction in SKILL.md body must point here; content needed for T12, T14, T15 |

### Task Execution Order

1. **T5** — Create SKILL.md with frontmatter
2. **T6** — Write intro section
3. **T7** — Workspace lifecycle
4. **T8** — Surface and pane management
5. **T9** — Session management and restore
6. **T10** — Keyboard shortcuts
7. **T11** — Notifications
8. **T12** — Claude Code Teams integration
9. **T13** — In-app browser
10. **T14** — Multi-agent orchestration
11. **T15** — Hook setup

Each body section is additive — load the SKILL.md file, read the plan section for the current step, append the new section. The reference files stay loaded for lookups when writing sections that reference them.

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body complete (~400+ lines). The body is the largest artifact. A fresh context is needed to update AGENTS.md without carrying the full SKILL.md body plus 3 reference files. Context saving: ~600+ lines freed.

## Session 3

**Load:** plan.md (Slice 1 — Step 1.16, Registry Update), ~/.agents/AGENTS.md (current contents for the edit)
**Estimated context:** 10% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Modify `~/.agents/AGENTS.md` — Add Available Skills section with using-cmux-cli entry | T15 | 1.16 | M | pending |

### Load Manifest

| Artifact | Section | Purpose |
|----------|---------|---------|
| plan.md | Step 1.16 (Registry Update) | Exact section format, table structure, and notes for AGENTS.md edit |
| ~/.agents/AGENTS.md | Full file (current) | Locate insertion point; determine if "Available Skills" section already exists |

### Task Execution Order

1. **T16** — Read AGENTS.md, append the Available Skills section with the using-cmux-cli entry.

--- SESSION BOUNDARY ---
**Reason:** All deliverable files complete (SKILL.md, 3 references, AGENTS.md). Fresh context for verification is essential — the verifier needs a clear view of what exists and what is missing. Carrying previous session context risks confirmation bias. Context saving: ~650 lines of file content freed.

## Session 4

**Load:** plan.md (Slice 1 — Steps 1.17, Verify), SKILL.md, 3 reference files, AGENTS.md
**Estimated context:** 15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T17 | Verify Slice 1: frontmatter schema, line counts, coverage checklist, Read instructions, skill-creator validation | T2,T3,T4,T5,T6,T7,T8,T9,T10,T11,T12,T13,T14,T15,T16 | 1.17 | M | pending |

### Load Manifest

| Artifact | Section | Purpose |
|----------|---------|---------|
| plan.md | Step 1.17 (Verify Slice 1) | Complete verification checklist (10 bullet items) |
| SKILL.md | Full file (excluding frontmatter) | Validate line count <500, body coverage, Read instructions to all 3 references |
| SKILL.md | Frontmatter block | Validate YAML with exactly 5 fields, name=using-cmux-cli, command=/using-cmux-cli |
| references/keyboard-shortcuts.md | Full file | Exist + non-empty + >20 lines |
| references/cli-socket-api.md | Full file | Exist + non-empty + >20 lines |
| references/hook-setup.md | Full file | Exist + non-empty + >20 lines |
| ~/.agents/AGENTS.md | Full file | Contains "Available Skills" section with using-cmux-cli entry |

### Task Execution Order

1. **T17** — Run the full verification checklist from plan.md step 1.17:
   a. Parse SKILL.md frontmatter as YAML, confirm exactly 5 fields
   b. Check name = using-cmux-cli, command = /using-cmux-cli
   c. Count SKILL.md body lines (excluding frontmatter), verify <500
   d. Search description for negative exclusions (tmux, screen, SSH)
   e. Verify body sections: macOS constraint, fail-fast, workspace/surface/pane lifecycle, notifications, Claude Code Teams, session restore, multi-agent
   f. Verify Read instructions to all 3 reference files exist in SKILL.md body
   g. Check all 3 reference files exist and have >20 lines each
   h. Verify bidirectional contracts: each reference file is referenced from SKILL.md
   i. Check AGENTS.md contains Available Skills section with using-cmux-cli entry
   j. Run skill-creator validation: `python ~/.agents/skills/skill-creator/scripts/quick_validate.py ~/.agents/skills/using-cmux-cli/SKILL.md`

---

**Estimated context utilization:** 15-30% per session (all under 40% threshold)
**Sessions total:** 4
**Tasks total:** 17
**Dependencies summary:** T1 gates all file creation. T2-T4 run in parallel after T1. T5-T15 form the sequential critical path for SKILL.md body. T16 depends on T15. T17 waits for all prior tasks.
