# Design — Create a new agent skill using cmux CLI

**Ticket:** RUS-10
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

A skill in this repo is a directory under `.claude/skills/<name>/` containing a `SKILL.md`, with the directory name identical to the frontmatter `name` and to the `command` minus its leading slash — a 1:1:1 naming convention consistent across all ten existing `qrspi-*` skills (ref: Q2). The de facto frontmatter schema is a fixed five-key YAML set delimited by `---`: `name`, `description`, `command`, `argument-hint`, `allowed-tools`; no skill deviates and no validator enforces it in-repo (ref: Q3). Skill discovery is by directory convention — there is no index, manifest, or `settings.json`; the harness recognizes a skill from the presence of `.claude/skills/<name>/SKILL.md` with valid frontmatter (ref: Q5). Only one skill, `qrspi-work`, ships a `references/` subdirectory, and it cites that file by relative prose path (`see references/review-cascade.md`) for on-demand loading; no skill uses `scripts/` or `assets/` subdirectories (ref: Q6).

Both core feature tools — the cmux CLI and the Anthropic `skill-creator` skill — are absent from `REPO_ROOT`; a repo-wide search matched only the questions file, and there is no in-repo `skill-creator` skill (ref: Q1, Q4). `skill-creator` is an external/global Claude Code skill and is in fact listed as available in this session (it appears in the skill list). There is no in-repo linter, token counter, or line-count check for the "500 lines / 5000 tokens" body constraint, and no eval scoring description trigger accuracy — both are owned by the external skill-creator and are unverifiable here (ref: Q7, Q8). The repo's own `scripts/run_eval.py` harness is a non-functional placeholder whose executor returns empty output, so skill verification must rely on the skill-creator eval loop plus manual checks (ref: Q11). No in-repo example contains keyboard-shortcut notation (`Cmd+N`) or OSC escape sequences, so their handling in `SKILL.md` is unverified; the one observed escaping convention is that a `description` containing YAML-special characters is double-quoted, as `qrspi-work` does (ref: Q9).

Most existing skills are thin wrappers whose body is a numbered "Steps" procedure that spawns a `qrspi-*` agent via the `Agent` tool, with the substantive prompt living in the agent rather than the skill (ref: Discovered Patterns). Adding a skill requires three manual, unenforced edits: the skill directory, the `README.md` skill table, and the `.claude/CLAUDE.md` bullet list (ref: Q5, Inconsistencies).

## Desired End State

A new self-contained content skill named `cmux` exists at `.claude/skills/cmux/SKILL.md` with a `references/` directory, conforming to the in-repo on-disk convention (ref: Q2, Q6). Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure with valid frontmatter** → `.claude/skills/cmux/SKILL.md` carries the fixed five-key frontmatter; `name: cmux`, `command: /cmux`, directory `cmux/` (ref: Q2, Q3). The agentskills.io standard itself is unverifiable in-repo; the repo convention is the binding target (ref: Q3 inconsistency).
- **Built using the skill-creator skill** → the implementing slice invokes the external `skill-creator` skill (available this session) to generate and validate the scaffold.
- **Body under 500 lines / 5000 tokens** → SKILL.md body stays a high-level overview plus pointers; all exhaustive material is pushed into `references/` (no in-repo enforcer exists, so this is met by construction and manual count — ref: Q7).
- **Detailed reference material in `references/`** covering full keyboard shortcuts, CLI/socket API commands, and per-agent hook setup → three (or grouped) reference files cited from the body by relative prose path, mirroring the `qrspi-work` pattern (ref: Q6).
- **Workspace, surface, and pane lifecycle** → documented in SKILL.md body with detail in references (create/navigate/rename/close workspaces; surface tabs; split/navigate panes).
- **Notification system integration** → OSC 9/99/777 sequences, `cmux notify`, and hook wiring documented.
- **Claude Code Teams workflow** → `cmux claude-teams` and native-split teammate behavior documented.
- **Session restore and agent resume** → `cmux hooks setup`, `terminal.autoResumeAgentSessions`, custom resume commands, and manual restore documented.
- **Multi-agent orchestration patterns** → one-workspace-per-agent-task guidance, notification-driven monitoring, and metadata tracking documented, encoding the ticket's judgment calls and the macOS-only limitation.

The skill becomes `/`-invocable purely by file presence (ref: Q5); `README.md` and `.claude/CLAUDE.md` listings are updated as a documentation convention.

## Delta

**New files:**
- `.claude/skills/cmux/SKILL.md` — body: overview, installation/setup, workspace/surface/pane lifecycle, notifications, Claude Code Teams, session restore, multi-agent orchestration, scope/macOS caveats, and relative-path pointers into `references/`.
- `.claude/skills/cmux/references/keyboard-shortcuts.md` — full keyboard shortcut reference.
- `.claude/skills/cmux/references/cli-and-socket-api.md` — CLI commands, socket API, custom commands, in-app browser scripting, SSH.
- `.claude/skills/cmux/references/agent-hooks.md` — `cmux hooks setup` and per-supported-agent resume integration (Claude Code, Codex, Grok, OpenCode, Pi, Amp, Cursor CLI, Gemini, Rovo Dev, Copilot, others).

**Modified files (documentation sync, not enforced gates — ref: Q5):**
- `README.md` — add `cmux` to the skills table.
- `.claude/CLAUDE.md` — add `cmux` to the "Available skills" bullet list.

**No changes to:** `scripts/` (no new tests — this is content, not pure logic; the eval harness is a placeholder, ref: Q11), no manifest/registry (none exists, ref: Q5), no `scripts/` or `assets/` subdirectory under the skill (no in-repo precedent, ref: Q6).

## Pattern Decisions

### Decision 1: Skill shape — thin agent-wrapper vs. self-contained content skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin wrapper: SKILL.md is a "Steps" procedure spawning a `cmux` agent in `.claude/agents/` | Matches the dominant in-repo pattern (ref: Discovered Patterns) | No procedure to orchestrate — this is reference knowledge, not a phase agent; would add an empty/contrived agent |
| B | Self-contained content skill: SKILL.md holds the guidance directly, references/ for depth | Fits the deliverable (a knowledge skill); mirrors `qrspi-work`'s references pattern (ref: Q6); satisfies the body-budget AC by offloading to references | Diverges from the wrapper-majority pattern |

**Recommendation:** Option B
**Rationale:** The ticket asks for a guidance skill about an external CLI, not a workflow that spawns an agent. The wrapper pattern exists to keep substantive *agent* prompts out of skills (ref: Discovered Patterns); there is no agent here. `qrspi-work` already establishes the in-repo precedent for a content-bearing skill with a `references/` directory (ref: Q6).
**NEW PATTERN?** Partial — a content skill with no agent wrapper is new relative to the nine wrapper skills, but the references mechanism reuses the existing `qrspi-work` precedent (ref: Q6). Justification: no existing pattern fits a pure-knowledge skill, and `qrspi-work` shows multi-file content skills are already sanctioned.

### Decision 2: Reference file granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single `references/cmux-reference.md` | Fewer files; one pointer | Large monolith; on-demand loading pulls everything at once, defeating laziness (ref: Q6) |
| B | Three files split by AC theme (shortcuts / CLI+socket / agent-hooks) | Maps 1:1 to the references AC; lazy load only what's needed (ref: Q6) | Three pointers to maintain |

**Recommendation:** Option B
**Rationale:** The references AC explicitly enumerates three coverage areas (keyboard shortcuts, CLI/socket API, per-agent hooks); a 1:1 split keeps each file focused and supports the on-demand load convention (ref: Q6).
**NEW PATTERN?** No — extends the single existing `references/` precedent (ref: Q6) to multiple files within it.

### Decision 3: `description` frontmatter quoting and trigger phrasing

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Unquoted single-line description (nine skills' default) | Simpler; matches the majority (ref: Q9) | Breaks if the value needs commas/colons/quotes for trigger phrasing |
| B | Double-quoted multi-clause description with explicit "Use when…" triggers (the `qrspi-work` style) | Improves auto-invocation; safe against YAML-special chars (ref: Q8, Q9) | Slightly heavier; matches only one existing skill |

**Recommendation:** Option B
**Rationale:** Trigger accuracy is the documented purpose of `description` (ref: Q8), and packing explicit usage triggers is observed in-repo practice; quoting is the established convention when the value contains YAML-special characters (ref: Q9).
**NEW PATTERN?** No — directly reuses the `qrspi-work` quoting-and-trigger convention (ref: Q8, Q9).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Documented cmux commands/shortcuts/config keys are inaccurate or outdated (tool is external, unverifiable in-repo — ref: Q1, Inconsistencies) | high | high | Treat the ticket body as the authoritative spec for v1; cross-check against the external skill-creator pass and cmux docs during implementation; mark anything uncertain rather than asserting |
| Body exceeds the 500-line / 5000-token budget with no in-repo enforcer to catch it (ref: Q7) | med | med | Keep SKILL.md to overview + pointers; offload exhaustive lists to references; manually count before submission |
| `Cmd+N` notation or OSC escape sequences in SKILL.md break frontmatter/render — no in-repo precedent for such content (ref: Q9) | med | med | Keep escape sequences inside code fences in references, not frontmatter; keep frontmatter to plain text; verify rendering after generation |
| README and CLAUDE.md listings drift from the new skill (three unenforced manual edits — ref: Q5, Inconsistencies) | med | low | Make all three edits in the same slice as the skill files |
| In-repo eval harness gives no real verification signal (placeholder — ref: Q11) | high | low | Rely on the external skill-creator eval loop and manual review; do not depend on `run_eval.py` |

## Open Questions

- OQ1: Should this skill take a slash `command` (e.g. `/cmux`) and `argument-hint`, or is it purely an auto-invoked knowledge skill? The frontmatter schema includes both fields (ref: Q3), but a knowledge skill may not need a meaningful argument.
- OQ2: Is the external `skill-creator` invocation a hard gate for this slice (the AC says "built using" it), and must its eval/variance pass be evidenced, given it cannot be run or verified in-repo (ref: Q8, Q11)?
- OQ3: Which cmux version/release do the documented commands, config keys, and shortcuts target? The ticket lists specifics, but with no in-repo source of truth (ref: Q1) a human should confirm the version baseline.
- OQ4: Should the supported-agent hook coverage in `references/agent-hooks.md` be exhaustive (all ~11 listed agents) or limited to Claude Code plus a generic pattern, to bound maintenance?
