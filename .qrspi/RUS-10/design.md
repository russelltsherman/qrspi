# Design — Create a new agent skill called using cmux cli

**Ticket:** RUS-10
**Generated:** 2026-05-26
**Status:** draft

## 1. Current State

cmux is not installed in this environment and no local documentation exists for it (ref: Q4). The skill-creator skill at ~/.agents/skills/skill-creator/ provides the process and schema rules for building new skills, but does not produce skills automatically — it runs a conversational interview-then-write loop (ref: Q1). No existing skill in this project depends on an external CLI without a prerequisite check; the convention is to fail fast and report verbatim errors (ref: Q11). Platform-specific skills have no established convention — macOS constraints would need to be documented as prose since no automated platform-gating mechanism exists (ref: Q10). There is no token-counting or line-enforcement tooling; the 500-line limit is soft guidance enforced only by self-regulation of the model (ref: Q5). Existing project skills live in .claude/skills/ (discoverable by file presence), while user-level reusable skills live in ~/.agents/skills/ (ref: Q2, Q7). The project's existing skills all use a pushy description convention that enumerates trigger phrases and includes negative examples (ref: Q6). No existing skill teaches terminal UI operations like split panes, tabs, or notification rings — the graphite-workspace skill teaches workflow management, not UI navigation.

## 2. Desired End State

**AC1 — Skill follows agentskills.io directory structure with valid SKILL.md frontmatter:** The skill exists at ~/.agents/skills/using-cmux-cli/ with a SKILL.md file whose frontmatter contains valid name (kebab-case, <=64 chars) and description (<=1024 chars, no angle brackets) fields. Optionally includes license, allowed-tools, metadata, and compatibility fields. No unexpected keys.

**AC2 — Built using the Anthropic skill builder skill:** The skill is generated via the skill-creator skill's interview-then-write process (ref: Q1), which includes a test/iterate loop with eval-driven description optimization.

**AC3 — SKILL.md body under 500 lines / 5000 tokens:** The SKILL.md body contains the core workflow instructions, keystroke reference, and trigger guidance. Body length stays under 500 lines as soft guidance (ref: Q5).

**AC4 — Detailed reference material in references/ directory:** A references/ subdirectory contains:
- A full keyboard shortcut reference table (all Cmd/Opt/Ctrl combinations documented)
- CLI and socket API commands with flag descriptions
- Hook setup instructions for each supported agent (Claude Code, Codex, Grok, etc.)

**AC5 — Covers workspace, surface, and pane lifecycle management:** The skill documents creation, navigation, splitting, and closing of workspaces, surfaces (tabs), and panes, including all keyboard shortcuts and CLI equivalents.

**AC6 — Documents notification system integration:** The skill covers the notification ring/tab indicators, notification panel (Cmd+I), jump to latest unread (Cmd+Shift+U), terminal sequences (OSC 9/99/777), and the cmux notify CLI command for agent hook integration.

**AC7 — Includes Claude Code Teams workflow:** The skill documents launching Claude Code teammate mode (cmux claude-teams), the native split spawning with sidebar metadata, and hook setup for session resume (cmux hooks setup).

**AC8 — Covers session restore and agent resume configuration:** The skill documents auto-resume on relaunch, manual restore (Cmd+Shift+O or cmux restore-session), custom resume commands (cmux surface resume set), and the terminal.autoResumeAgentSessions config flag.

**AC9 — Addresses multi-agent orchestration patterns:** The skill documents parallel agent sessions across workspaces/splits, notification-based attention monitoring, and coordinated workflows via cmux claude-teams.

## 3. Delta

**New files** (all under ~/.agents/skills/using-cmux-cli/):

| File | Purpose | Est. Lines |
|---|---|---|
| SKILL.md | Core skill: frontmatter, trigger description, workflow instructions, keystroke summary, references pointers | ~300 |
| references/keyboard-shortcuts.md | Complete keyboard shortcut reference table (all commands with key combos) | ~80 |
| references/cli-socket-api.md | CLI commands with flags, socket API endpoints, example commands | ~80 |
| references/hook-setup.md | Hook configuration for each supported agent (Claude Code, Codex, Grok, OpenCode, etc.) | ~100 |

**Modified files:**

| File | Change |
|---|---|
| ~/.agents/AGENTS.md | Add using-cmux-cli to the global skill list under ~/.agents/skills/ |

**NOT created:** No scripts/ or assets/ subdirectories. The skill does not include executable helper scripts or visual assets. No project-level copy in .claude/skills/ — this is a user-level reusable skill.

## 4. Pattern Decisions

### Location: User-level (~/.agents/skills/) vs. Project-level (.claude/skills/)

| Option | Pros | Cons |
|---|---|---|
| User-level ~/.agents/skills/using-cmux-cli/ | Reusable across projects; matches graphite-workspace, mcp-builder, skill-creator pattern; the skill teaches a general-purpose tool, not a qrspi-specific workflow | Would require updating AGENTS.md at the user level; slightly less visible in project context |
| Project-level .claude/skills/using-cmux-cli/ | Visible within this project; follows the existing project skill pattern | Not reusable; would need to be copied to other projects; misaligned with the general-purpose nature of the skill |

**Recommendation:** User-level. The cmux skill is a general-purpose orchestration tool, not specific to the qrspi workflow. Other projects will benefit from having it. All other skills in ~/.agents/skills/ (graphite-workspace, mcp-builder, skill-creator) follow this same model for cross-project tools. This also matches the ticket's intent: "Build an agent skill" (general) not "Build a project skill."

### SKILL.md Content Split: Single File vs. references/ Directory

| Option | Pros | Cons |
|---|---|---|
| references/ directory with keyboard, CLI API, and hook setup split out | Accommodates the volume of shortcut tables and per-agent hook docs; follows qrspi-work pattern for content exceeding ~300 lines; progressive disclosure keeps SKILL.md lean | More files to manage; SKILL.md must include explicit "Read X when Y" pointers (per research Q8) |
| Single monolithic SKILL.md | Simpler structure; no cross-referencing needed | Approaches or exceeds the 500-line guidance; keyboard shortcut tables alone could be 80+ lines; per-agent hook docs for 10+ agents would add another 100+ lines |

**Recommendation:** references/ directory. The acceptance criteria explicitly require "detailed reference material" for three distinct domains (shortcuts, CLI API, hook setup). Combined with the SKILL.md body (~200 lines for workflow + keystroke summary), a single file would exceed 500 lines. The qrspi-work precedent shows this pattern works well (ref: Q8).

### Description Style: Pushy (Existing Convention) vs. Concise

| Option | Pros | Cons |
|---|---|---|
| Pushy (enumerate triggers, include negatives) | Follows existing project convention; skill-creator explicitly recommends pushy descriptions to combat under-triggering (ref: Q6); higher reliability in agent auto-invocation | Longer description (up to 1024-char limit); more text in available-skills context |
| Concise (role + scope only) | Shorter, less context consumption | Lower auto-trigger reliability; diverges from project convention; skill-creator explicitly warns against under-triggering |

**Recommendation:** Pushy. The skill-creator guidance is clear on this (ref: Q6). The description should enumerate trigger phrases like "when the user mentions cmux, workspace, multi-agent, notification panel, session restore, claude-teams, split pane, or terminal orchestration" and include negatives like "Do NOT use for Ghostty configuration, general terminal usage, or agent CLI internals."

### Installation Guidance: Prerequisite Check vs. Fail-Fast

| Option | Pros | Cons |
|---|---|---|
| Skip prerequisite checks, fail fast on error | Matches using-graphite-cli convention (no `gt` check; ref: Q11); matches qrspi-work error surfacing convention; keeps SKILL.md simpler | Agent may attempt cmux commands that fail; user sees raw errors |
| Check for cmux installation before recommending usage | Prevents confusing error messages; provides helpful setup instructions upfront | Deviates from existing project convention; adds lines to SKILL.md; slows execution with a check step |

**Recommendation:** Fail-fast with setup instructions in SKILL.md body. Document the Homebrew and DMG install paths early in the skill, then follow the project convention of not pre-checking. If a command fails, the agent should surface the exact error (per qrspi-work hard stop rule, ref: Q11).

### macOS Platform Constraint Documentation

| Option | Pros | Cons |
|---|---|---|
| Prose in description and SKILL.md body documenting macOS requirement | Simple; no infrastructure needed; follows the pattern where platform constraints are documented as prose (ref: Q10) | No automated enforcement; agents on Linux may attempt to use the skill |
| compatibility frontmatter field with platform constraint | Machine-readable; could enable future tooling to gate the skill | Unused convention in this codebase (ref: Q10); no semantics established for compatibility values; may confuse users |

**Recommendation:** Prose in both the description and SKILL.md body. State clearly: "macOS only — this skill covers a macOS-native terminal multiplexer." The compatibility field is a known unused convention (ref: Q10) and would not provide actual gating. The description should also include a negative: "Do NOT use on non-macOS platforms."

### Pattern Classification: New Pattern Flag

**NEW PATTERN — Terminal UI operation teaching.** No existing skill in either user-level (~/.agents/skills/) or project-level (.claude/skills/) teaches terminal UI operations like split panes, tab navigation, notification rings, or pane focus. Existing skills teach CLI workflows (git, bash scripting, linear project management) or AI agent orchestration workflows. The cmux skill will be the first to encode knowledge about terminal multiplexer UI interactions. This is not a new PATTERN per se — the skill still follows the standard SKILL.md structure — but the domain (terminal UI navigation) is novel within this codebase. Flagging for awareness during implementation and review.

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No local cmux documentation exists; skill content is sourced entirely from ticket description and external web research | HIGH | MEDIUM — incomplete or inaccurate documentation of CLI subcommands, flags, and config options | Cross-reference with GitHub releases page and any available cmux documentation during implementation; note uncertainties explicitly in the skill body; prioritize covering what the ticket describes over speculative additions |
| SKILL.md body exceeds 500-line soft limit despite references/ split | MEDIUM | LOW — no hard enforcement, but violates the convention and increases context consumption | Target ~200 lines for SKILL.md body with references/ containing the bulk of reference tables. The skill-creator's own guidance says "under 500 lines ideal" (ref: Q5), and qrspi-work is exactly at 500 lines as a warning example (ref: research inconsistencies). Use table of contents in reference files >300 lines (ref: Q8) |
| Agents on non-macOS systems attempt to use the skill, producing confusing errors | MEDIUM | LOW — no actual impact since commands simply fail, but wastes agent context | Document "macOS only" prominently in both description and SKILL.md body. Follow the fail-fast convention (ref: Q11) — when cmux commands fail, surface the error immediately rather than attempting workarounds |
| The skill's description is not pushy enough, leading to under-triggering | MEDIUM | MEDIUM — skill exists but is rarely invoked when relevant | Follow the skill-creator's explicit "pushy" convention (ref: Q6). Enumerate all trigger phrases from the ticket (cmux, workspace, claude-teams, notification panel, split pane, session restore, multi-agent). Include negative examples (Ghostty config, general terminal usage) |

## 6. Open Questions

1. **Should the skill include Ghostty configuration guidance or stay strictly at the cmux CLI layer?** The ticket says Ghostty configuration is out of scope, but cmux reads Ghostty's config for themes and fonts (mentioned in ticket). The skill should document how to trigger cmux features, not how to configure Ghostty. A boundary note in SKILL.md would clarify this.

2. **Should the skill include the macOS-native keybindings (Cmd+D, etc.) alongside CLI equivalents?** The graphite-workspace skill focuses on CLI commands but this is a terminal UI tool where keybindings are the primary interaction mode. The skill should prioritize keybindings with CLI alternatives as secondary.

3. **Which hook setup instructions are highest priority?** The ticket lists 10+ supported agents (Claude Code, Codex, Grok, OpenCode, Pi, Amp, Cursor CLI, Gemini, Rovo Dev, Copilot). Hook setup docs for all of them could inflate the references/ size. Prioritize Claude Code (primary use case from ticket) and mark others as "available but agent-specific."

4. **Does the cmux socket API have any tooling or protocol documentation?** The ticket mentions a "socket API for programmatic control" but provides no details. If no public documentation exists, the socket API section should note this as unverified.

5. **Should this design document be uploaded to Linear as a RUS-10 attachment upon approval, per the QRSPI workflow convention?** Standard workflow rule (per project CLAUDE.md): artifacts uploaded to the corresponding Linear issue as attachments on phase approval.
