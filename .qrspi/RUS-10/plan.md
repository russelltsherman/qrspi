# Implementation Plan — Create a new agent skill called using cmux cli

**Structure basis:** Slice 1 from `.qrspi/RUS-10/structure.md`
**Generated:** 2026-05-26
**Status:** draft
**Total steps:** 17

## Slice 1: Complete `using-cmux-cli` skill at `~/.agents/skills/using-cmux-cli/`

### Directory Setup

1. Create `~/.agents/skills/using-cmux-cli/` directory and `~/.agents/skills/using-cmux-cli/references/` subdirectory.

### Reference Files (write first — SKILL.md body will Read these)

2. Create `~/.agents/skills/using-cmux-cli/references/keyboard-shortcuts.md` (~60-100 lines)

   Contents: A flag/pattern table of cmux keyboard shortcuts relevant to agent workflow. Cover:
   - Create/destroy sessions
   - Switch between sessions/surfaces
   - Split/merge panes
   - Toggle visibility
   - Rename sessions/surfaces
   Format: `## Keyboard Shortcuts` with a subsection per topic, each with a table of shortcut + action + brief note. This is a reference, not prescriptive steps.
   Add `<!-- last-verified: 2026-05-26 -->` footer.

3. Create `~/.agents/skills/using-cmux-cli/references/cli-socket-api.md` (~60-100 lines)

   Contents: A reference of the cmux CLI commands and the underlying socket API for managing workspaces, surfaces, and panes. Cover:
   - `cmux workspace` commands (list, create, switch, delete, rename)
   - `cmux surface` commands (list, create, split, merge, focus, delete)
   - `cmux pane` commands (list, focus, resize, close)
   - `cmux session` commands (create, switch, detach, kill, restore)
   - `cmux notification` commands (list, ack, clear)
   - `cmux browser` commands (open, list, close)
   - `cmux hook` commands (register, deregister, list)
   Format: `## CLI Commands` with one subsection per command group. Each subsection has the command syntax, key flags, and a one-line example. Add `<!-- last-verified: 2026-05-26 -->` footer.

4. Create `~/.agents/skills/using-cmux-cli/references/hook-setup.md` (~80-120 lines)

   Contents: Reference for configuring cmux hooks — the mechanism that lets cmux interact with Claude Code and other agents. Cover:
   - What hooks are and how cmux discovers them
   - Supported hook trigger points (session_start, session_end, notification, surface_switch, etc.)
   - 10+ supported agent integrations (Claude Code, codex, cursor agents, etc.)
   - Hook script template (Bash or Node with shebang)
   - Permissions model for hook execution
   - Debugging hook failures (fail-fast behavior, logging)
   Format: `## Hook Configuration` with subsections per topic. Include a code block showing the hook template. Add `<!-- last-verified: 2026-05-26 -->` footer.

### Skill Body

5. Create `~/.agents/skills/using-cmux-cli/SKILL.md` with frontmatter containing exactly these 5 fields:

   ```yaml
   ---
   name: using-cmux-cli
   description: "Use when managing AI agent workspaces, multi-agent orchestration, or terminal multiplexing with cmux. Trigger on: 'cmux', 'workspace', 'surface', 'pane', 'split', 'session', 'notification', 'Claude Code Teams', 'session restore', 'in-app browser', 'hook setup', 'multi-agent', any request to manage terminal sessions, spawn child agents, or orchestrate concurrent agent work. Do NOT use for general terminal usage, SSH, tmux, screen, or anything not involving cmux specifically."
   command: /using-cmux-cli
   argument-hint: "<cmux subcommand or task>"
   allowed-tools: Bash(cmux:*), Read
   ---
   ```

   Notes on the description:
   - Pushy convention: starts with use case, lists trigger phrases, includes negatives (tmux/screen/SSH exclusion)
   - Concise enough for metadata (~100 words)
   - "Do NOT use for" clause implements the negative filter

6. Add SKILL.md body section `# using-cmux-cli` with a brief intro: what cmux is, why agents use it, and the macOS-only constraint (prose note: "cmux is macOS-only; on other platforms, this skill does not apply — do not attempt to run cmux commands").

7. Add SKILL.md body section `## Workspace lifecycle` — cover creating a workspace, switching between workspaces, workspace-per-project pattern. Emphasize: the workspace is the top-level isolation boundary. Reference: `For full workspace commands, Read references/cli-socket-api.md`

8. Add SKILL.md body section `## Surface and pane management` — cover creating surfaces, splitting panes, switching focus, resizing. Emphasize: surfaces are the visible viewports; panes are subdivisions within a surface. Reference: `For all surface and pane commands, Read references/cli-socket-api.md`

9. Add SKILL.md body section `## Session management and restore` — cover creating sessions, detaching, killing, and restoring from history. Emphasize: session restore is critical for long-running agent tasks that may disconnect. Reference: `For session commands, Read references/cli-socket-api.md`

10. Add SKILL.md body section `## Keyboard shortcuts` — overview of the most important shortcuts (create/switch sessions, split panes, toggle visibility). Emphasize: these are convenience shortcuts; the CLI commands work the same. Reference: `For the complete keyboard shortcut table, Read references/keyboard-shortcuts.md`

11. Add SKILL.md body section `## Notifications` — cover notification subscription, acknowledgment, and lifecycle. Emphasize: notifications are how cmux surfaces inter-agent messages and events. Reference: `For notification commands, Read references/cli-socket-api.md`

12. Add SKILL.md body section `## Claude Code Teams integration` — cover how cmux integrates with Claude Code Teams (the built-in agent orchestration). Emphasize: this is a core use case — managing which Claude Code instances run where and how they communicate via surfaces. Reference: `For hook setup with Claude Code Teams, Read references/hook-setup.md`

13. Add SKILL.md body section `## In-app browser` — cover the cmux browser for viewing web content within sessions. Reference: `For browser commands, Read references/cli-socket-api.md`

14. Add SKILL.md body section `## Multi-agent orchestration` — cover patterns for spawning and coordinating multiple agents via cmux workspaces and surfaces. Reference: `For hook registration patterns and agent integrations, Read references/hook-setup.md`

15. Add SKILL.md body section `## Hook setup` — high-level explanation of hooks and where to find detailed setup instructions. Reference: `For the full hook configuration guide including the 10+ supported agents, Read references/hook-setup.md`

### Registry Update

16. Modify `~/.agents/AGENTS.md` — Add a new section at the end:

    ```markdown
    ## Available Skills

    User-level skills installed in `~/.agents/skills/`. Each skill is a directory with a `SKILL.md` containing YAML frontmatter (name, description, command) and an optional body of instructions.

    | Name | Command | Path |
    |------|---------|------|
    | skill-creator | (none) | `~/.agents/skills/skill-creator/SKILL.md` |
    | using-cmux-cli | `/using-cmux-cli` | `~/.agents/skills/using-cmux-cli/SKILL.md` |
    | (etc.) | | |

    ### Creating a new skill

    1. Create `~/.agents/skills/<name>/SKILL.md` with YAML frontmatter
    2. Add `~/agents/skills/<name>/references/` for any reference files
    3. Add an entry to this table
    4. Run the skill-creator eval loop to validate
    ```

    Notes:
    - Only add the `using-cmux-cli` entry (we don't enumerate every existing skill; the list is illustrative)
    - The section format follows the project CLAUDE.md pattern of documenting available skills

### Verify Slice 1

17. **Checkpoint: Validate the skill**

    Run these checks:
    - [ ] SKILL.md frontmatter parses as valid YAML with exactly 5 fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`)
    - [ ] `name` = `using-cmux-cli`, `command` = `/using-cmux-cli`
    - [ ] SKILL.md body (excluding frontmatter) is under 500 lines
    - [ ] Description contains negative exclusions (tmux, screen, SSH)
    - [ ] Body covers: macOS constraint, fail-fast, workspace/surface/pane lifecycle, notifications, Claude Code Teams, session restore, multi-agent
    - [ ] SKILL.md body has explicit Read instructions for all 3 reference files:
      - `references/keyboard-shortcuts.md`
      - `references/cli-socket-api.md`
      - `references/hook-setup.md`
    - [ ] All 3 reference files exist and have content (non-empty, >20 lines each)
    - [ ] All 3 reference files are referenced from SKILL.md body (bidirectional contract)
    - [ ] `~/.agents/AGENTS.md` contains the "Available Skills" section with `using-cmux-cli` entry
    - [ ] Invoke skill-creator to validate: run `python ~/.agents/skills/skill-creator/scripts/quick_validate.py ~/.agents/skills/using-cmux-cli/SKILL.md` (or equivalent validation from skill-creator scripts)

---

## Rollback Notes

- Steps 1-4 (reference files): Delete the entire `~/.agents/skills/using-cmux-cli/` directory to fully rollback.
- Step 5 (SKILL.md): Delete `~/.agents/skills/using-cmux-cli/SKILL.md`.
- Step 16 (AGENTS.md revert): Remove the "Available Skills" section from `~/.agents/AGENTS.md`. The section starts at `## Available Skills` and ends at the next top-level section or end of file. If no other sections exist after it, just remove from `## Available Skills` to EOF.
