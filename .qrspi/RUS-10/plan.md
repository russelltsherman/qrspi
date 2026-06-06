# Implementation Plan — Create a new agent skill using cmux CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

> Note: This ticket produces a **content/knowledge skill**, not code. There are no
> runtime types, function signatures, or unit tests (the in-repo eval harness is a
> placeholder — ref: structure §Note, design §Risk Register/Q11). "Tests" below are
> the skill-creator eval loop plus manual structural checks, which are the only
> verification signals available. The structure defines a **single slice**; all
> files in it are mutually dependent (body pointers must resolve, skill-creator
> validates the whole package, doc edits ship alongside), so they are kept together.

## Slice 1: Author the cmux content skill (SKILL.md + references + doc sync)

### Setup

1. ⚠️ Resolve open structure assumptions before authoring — confirm with a human (or
   record the chosen defaults in the slice PR description): OQ1 (does `/cmux` take a
   real argument or is it pure auto-invoke → fixes `command`/`argument-hint`), OQ3
   (cmux version baseline for documented commands/shortcuts/config keys), OQ4
   (agent-hooks coverage breadth: all ~11 agents vs. Claude Code + generic pattern).
   - **Note:** These gate authoring because they change frontmatter values and
     reference-file scope. Default if unanswered: `command: /cmux` with a generic
     `argument-hint`, treat ticket body as v1 spec, cover Claude Code + generic
     pattern in agent-hooks (ref: structure §Unverified Assumptions, design §Open Questions).

2. ✨ Invoke the external `skill-creator` skill to scaffold the new skill directory
   `.claude/skills/cmux/` — use it to generate the initial `SKILL.md` frontmatter +
   body skeleton and the `references/` directory (AC: "built using skill-creator";
   ref: structure Verification, design Decision 1 Option B).
   - **Reference:** `SkillFrontmatter { name, description, command, argument-hint, allowed-tools }`.

### Core Logic

3. ✨ Create `.claude/skills/cmux/SKILL.md` frontmatter — the exact five-key
   `SkillFrontmatter` YAML block delimited by `---`: `name: cmux`, `command: /cmux`,
   `description` (double-quoted, multi-clause with explicit "Use when…" triggers),
   `argument-hint`, `allowed-tools` (ref: structure Frontmatter contract, design Decision 3).
   - **Escape-safety:** plain text only in frontmatter — no `Cmd+N` notation, no OSC
     9/99/777 sequences (ref: structure Escape-safety contract).

4. ✨ Write `.claude/skills/cmux/SKILL.md` body — overview + installation/setup
   section, kept to high-level overview + pointers so the body stays within budget
   (ref: structure Body-budget contract, design §Desired End State).

5. ✨ Add to `.claude/skills/cmux/SKILL.md` body — workspace / surface / pane
   lifecycle section (create/navigate/rename/close workspaces; surface tabs;
   split/navigate panes), overview level with pointer to references for depth
   (ref: structure Files touched, design §Desired End State).

6. ✨ Add to `.claude/skills/cmux/SKILL.md` body — notification system section:
   OSC 9/99/777 sequences, `cmux notify`, hook wiring (overview + pointer; any
   escape sequences shown only via references in code fences) (ref: structure AC area, design §Desired End State).

7. ✨ Add to `.claude/skills/cmux/SKILL.md` body — Claude Code Teams section
   (`cmux claude-teams`, native-split teammate behavior) and session restore /
   agent resume section (`cmux hooks setup`, `terminal.autoResumeAgentSessions`,
   custom + manual resume) (ref: structure AC areas, design §Desired End State).

8. ✨ Add to `.claude/skills/cmux/SKILL.md` body — multi-agent orchestration section
   (one-workspace-per-agent-task, notification-driven monitoring, metadata tracking),
   scope/macOS-only caveats, and the relative prose-path pointers into all three
   `references/<topic>.md` files (ref: structure Reference-pointer contract, design Decision 2).

9. ✨ Create `.claude/skills/cmux/references/keyboard-shortcuts.md` — full keyboard
   shortcut reference; `Cmd+N`-style notation and any escape sequences live inside
   code fences (ref: structure Files touched + Escape-safety contract).

10. ✨ Create `.claude/skills/cmux/references/cli-and-socket-api.md` — CLI commands,
    socket API, custom commands, in-app browser scripting, SSH; OSC escape sequences
    inside code fences (ref: structure Files touched, design §Delta).

11. ✨ Create `.claude/skills/cmux/references/agent-hooks.md` — `cmux hooks setup`
    and per-supported-agent resume integration, at the coverage breadth chosen in
    step 1 (OQ4) (ref: structure Files touched, design §Delta).

12. ⚠️ Modify `README.md` — add a `cmux` row to the skills table.
    - **Current:** skills table without a `cmux` entry.
    - **After:** table includes a `cmux` row describing the skill (ref: structure Files touched, design Risk Register row 4).

13. ⚠️ Modify `.claude/CLAUDE.md` — add `cmux` to the "Available skills" bullet list.
    - **Current:** "Available skills" list without `cmux`.
    - **After:** list includes a `/cmux` bullet (ref: structure Files touched, design Risk Register row 4).

### Tests

(No unit tests — content skill; in-repo eval harness is a placeholder. Verification
is the skill-creator eval loop + manual structural checks, performed at the checkpoint.)

### Verify Slice 1

14. **Checkpoint:** run the external `skill-creator` eval/variance loop against
    `.claude/skills/cmux/`, then perform the manual structural checks below.
    - [ ] Skill built/validated via the external `skill-creator` skill and its eval/variance loop (AC: "built using skill-creator").
    - [ ] Frontmatter parses and contains exactly the five keys; `name: cmux`, `command: /cmux`, directory name `cmux/` matches; `description` is double-quoted with "Use when…" triggers.
    - [ ] `/cmux` is discoverable/auto-invocable by file presence — no manifest/index/settings edit was needed.
    - [ ] Every relative `references/…` pointer in the body resolves to an existing file (`keyboard-shortcuts.md`, `cli-and-socket-api.md`, `agent-hooks.md`); each reference covers its mapped AC area.
    - [ ] SKILL.md body manually counted < 500 lines and < 5000 tokens.
    - [ ] No `Cmd+N` notation or OSC escape sequences in frontmatter; they render correctly inside code fences in references.
    - [ ] All eight acceptance areas addressed (frontmatter+structure, skill-creator build, body budget, references depth, workspace/surface/pane lifecycle, notifications, Claude Code Teams, session restore/resume, multi-agent orchestration).
    - [ ] `README.md` table and `.claude/CLAUDE.md` bullet list both list `cmux`.

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this slice.
- Steps 3–11 (new files under `.claude/skills/cmux/`): to reverse, delete the
  `.claude/skills/cmux/` directory in its entirety; the skill de-registers purely by
  file absence (discovery is by file presence — ref: structure Discovery contract).
- Step 12 (`README.md`): remove the added `cmux` table row.
- Step 13 (`.claude/CLAUDE.md`): remove the added `cmux` bullet.
- These three edits are non-destructive documentation syncs; reverting any one does
  not affect skill function, only listing accuracy.
