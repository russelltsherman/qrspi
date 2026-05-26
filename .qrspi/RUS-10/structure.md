# Structure Outline — Create a new agent skill called using cmux cli

**Design basis:** design.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

## New Types

None. This ticket produces static markdown files (a skill definition and reference documents), not executable code with types or data structures.

## Modified Types

None.

## Contracts

### Cross-file references within the skill

The SKILL.md body contains explicit `Read` instructions pointing to each reference file. These constitute the contract between the skill body and its reference material:

- `Read ~/.agents/skills/using-cmux-cli/references/keyboard-shortcuts.md` — loaded when agent needs keyboard shortcut lookup for workspace, surface, or pane operations
- `Read ~/.agents/skills/using-cmux-cli/references/cli-socket-api.md` — loaded when agent needs CLI subcommand flags, socket API endpoints, or programmatic control patterns
- `Read ~/.agents/skills/using-cmux-cli/references/hook-setup.md` — loaded when agent needs hook configuration for Claude Code, Codex, Grok, or other supported agents

### Frontmatter contract

```yaml
---
name: using-cmux-cli
description: "<pushy trigger description covering cmux, workspace, claude-teams, notification panel, split pane, session restore, multi-agent, terminal orchestration>"
command: /using-cmux-cli
argument-hint: "<cmux subcommand or terminal orchestration task>"
allowed-tools: Bash(cmux:*), Read
---
```

All five fields (name, description, command, argument-hint, allowed-tools) are required. No additional fields are permitted.

### User-level skill location contract

The skill lives at `~/.agents/skills/using-cmux-cli/`, not project-level `.claude/skills/`. This follows the cross-project pattern used by graphite-workspace, mcp-builder, and skill-creator.

### AGENTS.md registration contract

A new entry must be added to `~/.agents/AGENTS.md` skill list, following the existing format:

```
- `/using-cmux-cli <cmux subcommand or task>` — Guide agents using the cmux terminal multiplexer for workspace management, multi-agent orchestration, and session restore
```

## Slice 1: cmux CLI Skill — Complete File Set

**Goal:** Deliver the complete `using-cmux-cli` skill at `~/.agents/skills/using-cmux-cli/` — SKILL.md with frontmatter and compact body, three topic-based reference files, and AGENTS.md registration — as a testable, self-contained unit. Invoke `skill-creator` as the final validation step.

**Rationale for single slice:** The SKILL.md body loads all three reference files via Read instructions -- it cannot be verified without them. The skill-creator eval loop requires all files to be in place before testing trigger behavior. The AGENTS.md registration is a trivial one-line addition that must accompany the skill to be discoverable. Splitting these into multiple slices would create artificial dependencies where each slice is unverifiable without the next. The design explicitly requires the skill-creator's interview-then-write process (AC2), which inherently produces content iteratively within the slice.

**Files touched:**

- **New `~/.agents/skills/using-cmux-cli/SKILL.md`** -- Frontmatter (name, description, command, argument-hint, allowed-tools) + compact skill body (target 200-300 lines, under 500-line limit) covering: macOS-only constraint, prerequisite check (cmux installation), fail-fast error surfacing, workspace/surface/pane lifecycle (create, navigate, split, close), notification system (ring/tab indicators, Cmd+I, Cmd+Shift+U, OSC sequences), Claude Code Teams workflow (claude-teams mode, native split spawning, sidebar metadata), session restore (auto-resume, Cmd+Shift+O, custom resume commands, terminal.autoResumeAgentSessions config), multi-agent orchestration (parallel sessions, notification-based attention monitoring, coordinated workflows), and Read instructions pointing to all three reference files. Trigger description follows the pushy convention with negatives.

- **New `~/.agents/skills/using-cmux-cli/references/keyboard-shortcuts.md`** -- Complete keyboard shortcut reference table organized by operation category (workspace, surface/tab, pane, notification, session, Claude Code Teams). Each entry documents the key combination, what it does, and CLI equivalent where available. Target: 60-100 lines.

- **New `~/.agents/skills/using-cmux-cli/references/cli-socket-api.md`** -- CLI commands with flag descriptions (create, list, notify, restore, hooks), socket API endpoints for programmatic control, example commands. Notes unverified aspects where local documentation is unavailable. Target: 60-100 lines.

- **New `~/.agents/skills/using-cmux-cli/references/hook-setup.md`** -- Hook configuration for each supported agent (Claude Code as primary, then Codex, Grok, OpenCode, Pi, Amp, Cursor CLI, Gemini, Rovo Dev, Copilot). Per-agent setup steps, config file paths, and resume command examples. Target: 80-120 lines.

- **Modify `~/.agents/AGENTS.md`** -- Add `using-cmux-cli` to the global skill list under `~/.agents/skills/`, following the existing alphabetical or categorical listing pattern.

**Verification:**

- [ ] `SKILL.md` has valid YAML frontmatter with exactly 5 required fields (name, description, command, argument-hint, allowed-tools)
- [ ] `SKILL.md` `name` field is `using-cmux-cli`, `command` is `/using-cmux-cli`
- [ ] `SKILL.md` body is under 500 lines (`wc -l`)
- [ ] `SKILL.md` body documents macOS-only constraint prominently
- [ ] `SKILL.md` body includes fail-fast error surfacing guidance
- [ ] `SKILL.md` body covers workspace lifecycle (create, navigate, close)
- [ ] `SKILL.md` body covers surface/tab lifecycle (create, navigate, close)
- [ ] `SKILL.md` body covers pane lifecycle (split, focus, close)
- [ ] `SKILL.md` body covers notification system (ring/tab indicators, Cmd+I, Cmd+Shift+U, OSC sequences)
- [ ] `SKILL.md` body covers Claude Code Teams workflow (claude-teams mode, native split spawning)
- [ ] `SKILL.md` body covers session restore (auto-resume, Cmd+Shift+O, custom resume commands)
- [ ] `SKILL.md` body covers multi-agent orchestration (parallel sessions, attention monitoring, coordinated workflows)
- [ ] `SKILL.md` body contains Read instructions for all 3 reference files
- [ ] `SKILL.md` description follows pushy convention (enumerates trigger phrases + negatives)
- [ ] `references/keyboard-shortcuts.md` documents shortcuts for workspace, surface, pane, notification, and session operations
- [ ] `references/cli-socket-api.md` documents CLI commands with flags and socket API endpoints
- [ ] `references/hook-setup.md` covers Claude Code as primary agent plus at least 3 other agents
- [ ] `~/.agents/AGENTS.md` contains the new skill entry
- [ ] Invoke `skill-creator` to validate the skill through its interview-then-write process and eval loop

**Context cost:** S

**Depends on:** none

---

## Unverified Assumptions

1. **No local cmux documentation exists.** All content is sourced from the ticket description and external web research. The skill may contain incomplete or inaccurate documentation of CLI subcommands, flags, and config options. The implementation agent should cross-reference with GitHub releases and any available cmux documentation, noting uncertainties explicitly. (ref: design Q4, Risk Register row 1)

2. **Socket API documentation may be unavailable.** The ticket mentions a "socket API for programmatic control" but provides no details. If no public documentation exists, the socket API section in `cli-socket-api.md` should note this as unverified rather than speculating. (ref: design Q4)

3. **Ghostty configuration is out of scope.** The ticket says the skill covers cmux CLI usage, not Ghostty configuration. However, cmux reads Ghostty's config for themes and fonts (mentioned in ticket). The skill should document how to trigger cmux features via CLI/keys, not how to configure Ghostty. A boundary note in SKILL.md would clarify this. (ref: design Open Question 1)

4. **Hook setup for 10+ agents may inflate the reference file.** The ticket lists Claude Code, Codex, Grok, OpenCode, Pi, Amp, Cursor CLI, Gemini, Rovo Dev, and Copilot as supported agents. Hook setup docs for all of them could push `hook-setup.md` beyond the 100-line estimate. The design recommends prioritizing Claude Code as primary and marking others as "available but agent-specific." (ref: design Open Question 3)

5. **Bash permission scoping for `cmux:*` syntax.** The design recommends `Bash(cmux:*)` in allowed-tools. No existing skill scopes Bash to a third-party CLI binary by name -- all existing scoped permissions target standard Unix utilities or well-known CLIs (git, gt, argo, kubectl). Whether `Bash(cmux:*)` syntax works for a non-standard binary is unverified. Fallback: use unrestricted `Bash` if scoped syntax is unsupported. (ref: design RUS-7 precedent, AGENTS.md directive)

6. **skill-creator validation scope at user-level.** The skill-creator is a platform built-in whose internal validation logic is not inspectable. It is unclear whether skill-creator validates at user-level paths (`~/.agents/skills/`) the same way it does at project-level paths (`.claude/skills/`). If the eval loop fails due to path conventions, the implementation agent may need to work around this. (ref: design AC2, risk register)

7. **Open Question 2 resolution: keybindings prioritized over CLI.** The design flags that this is a terminal UI tool where keybindings are the primary interaction mode. The structure assumes the skill should prioritize keyboard shortcuts (documented in SKILL.md body) with CLI equivalents as secondary. The keyboard shortcuts reference file provides the complete table. (ref: design Open Question 2)

8. **Open Question 5 resolution: upload to Linear on approval.** Standard QRSPI workflow convention (per project CLAUDE.md) applies: the structure.md artifact will be uploaded to the RUS-10 Linear issue as an attachment upon phase approval. (ref: design Open Question 5)
