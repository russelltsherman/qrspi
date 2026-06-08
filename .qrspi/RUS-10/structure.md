# Structure Outline — Create a new agent skill using cmux CLI

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This ticket produces a **content/knowledge skill**, not code. There are
> no runtime types, function signatures, or unit tests (the in-repo eval harness
> is a placeholder — ref: design §Risk Register, Q11). "Types" and "Contracts"
> below describe the on-disk file conventions the artifact must satisfy, which
> are the only enforceable interfaces here.

## New Types

- `SkillFrontmatter { name: string, description: string (double-quoted; multi-clause with "Use when…" triggers), command: string ("/<name>"), argument-hint: string, allowed-tools: string }`
  — fixed five-key YAML set delimited by `---`; `name == directory == command minus leading slash` (ref: design §Desired End State, Q2/Q3, Decision 3).
- `ReferenceFile { path: ".claude/skills/cmux/references/<topic>.md", body: markdown }`
  — depth content loaded on-demand, cited from SKILL.md by relative prose path (ref: Decision 2, Q6).

## Modified Types

- none (no runtime/code types are added or changed; README and CLAUDE.md edits are documentation sync, not type changes — ref: design §Delta).

## Contracts

- **Frontmatter contract:** `SKILL.md` opens with the exact five-key `SkillFrontmatter` block; `name: cmux`, `command: /cmux`, directory `cmux/`. `description` is double-quoted (YAML-special-char safe) and carries explicit auto-invocation triggers (ref: Decision 3, Q8/Q9).
- **Discovery contract:** the skill becomes `/`-invocable purely by presence of `.claude/skills/cmux/SKILL.md` with valid frontmatter — no index/manifest/settings edit (ref: Q5).
- **Reference-pointer contract:** SKILL.md body cites each `references/<topic>.md` by relative prose path (mirroring `qrspi-work`'s `see references/...` pattern); every pointer must resolve to a file created in the same slice (ref: Q6, Decision 2).
- **Body-budget contract:** SKILL.md body stays < 500 lines / < 5000 tokens by holding overview + pointers only; exhaustive material lives in `references/` (no in-repo enforcer — met by construction + manual count, ref: Q7).
- **Escape-safety contract:** keyboard notation (`Cmd+N`) and OSC 9/99/777 escape sequences appear only inside code fences in `references/`, never in frontmatter (ref: Risk Register, Q9).

## Slice 1: Author the cmux content skill (SKILL.md + references + doc sync)

**Goal:** A complete, `/`-invocable `cmux` knowledge skill: valid frontmatter, an
overview-plus-pointers SKILL.md body covering all eight acceptance areas, three
focused reference files, and synchronized README/CLAUDE.md listings. End-to-end
testable path = invoke `/cmux` (or trigger auto-invocation) and confirm the skill
resolves with working reference pointers and a within-budget body, validated by the
external `skill-creator` eval loop.

**Files touched:**

- ✨ `.claude/skills/cmux/SKILL.md` — five-key frontmatter + body: overview, installation/setup, workspace/surface/pane lifecycle, notification system (OSC 9/99/777, `cmux notify`, hooks), Claude Code Teams (`cmux claude-teams`, native split), session restore & agent resume (`cmux hooks setup`, `terminal.autoResumeAgentSessions`, custom/manual resume), multi-agent orchestration (one-workspace-per-task, notification-driven monitoring, metadata, macOS-only caveat), scope caveats, and relative-path pointers into `references/`.
- ✨ `.claude/skills/cmux/references/keyboard-shortcuts.md` — full keyboard shortcut reference (escape sequences inside code fences).
- ✨ `.claude/skills/cmux/references/cli-and-socket-api.md` — CLI commands, socket API, custom commands, in-app browser scripting, SSH.
- ✨ `.claude/skills/cmux/references/agent-hooks.md` — `cmux hooks setup` and per-supported-agent resume integration (scope of coverage per OQ4 — see Unverified Assumptions).
- ⚠️ `README.md` — add `cmux` row to the skills table.
- ⚠️ `.claude/CLAUDE.md` — add `cmux` to the "Available skills" bullet list.

**Verification:**

- [ ] Skill is built/validated via the external `skill-creator` skill and its eval/variance loop (AC: "built using skill-creator").
- [ ] Frontmatter parses, contains exactly the five keys, `name: cmux` / `command: /cmux`, directory name matches; `description` is double-quoted with "Use when…" triggers.
- [ ] `/cmux` is discoverable/auto-invocable by file presence (no manifest edit needed).
- [ ] Every relative `references/…` pointer in the body resolves to an existing file; each of the three reference files covers its mapped AC area (shortcuts / CLI+socket / agent-hooks).
- [ ] SKILL.md body manually counted < 500 lines and < 5000 tokens.
- [ ] No `Cmd+N` notation or OSC escape sequences appear in frontmatter; they render correctly inside code fences in references.
- [ ] All eight acceptance areas (frontmatter+structure, skill-creator build, body budget, references depth, workspace/surface/pane lifecycle, notifications, Claude Code Teams, session restore/resume, multi-agent orchestration) are addressed.
- [ ] README table and CLAUDE.md bullet list both list `cmux`.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **cmux command/shortcut/config-key accuracy** — cmux is external and absent from the repo; all documented commands, shortcuts, and config keys (e.g. `terminal.autoResumeAgentSessions`, `cmux notify`, `cmux claude-teams`, `cmux hooks setup`) cannot be validated in-repo. Treat the ticket body as the v1 spec; a human must confirm the version baseline (design Risk 1, OQ3, Q1).
- **agentskills.io directory standard** — the external standard cited in the AC is unverifiable in-repo; the binding target is the in-repo convention (design §Desired End State, Q3 inconsistency).
- **skill-creator as a hard gate** — the AC says "built using skill-creator," but its eval/variance pass cannot be executed or evidenced from within this repo; whether a passing eval is a required, recorded gate is unresolved (OQ2, Q8/Q11).
- **OQ1 — command vs. pure auto-invoke** — the structure assumes `command: /cmux` + a meaningful `argument-hint` per the five-key schema, but a pure knowledge skill may not need a real argument; human to confirm whether `/cmux` takes args.
- **OQ4 — agent-hooks coverage breadth** — `references/agent-hooks.md` scope (all ~11 listed agents vs. Claude Code + a generic pattern) is undecided and affects file size/maintenance; assumption defers to human choice before authoring.
- **Body-budget enforcement** — the 500-line / 5000-token limit has no in-repo checker; compliance is assumed via manual count and cannot be machine-verified here (Q7).
- **No testability sub-boundary within the slice** — SKILL.md, its three references, and the doc-sync edits are mutually dependent (body pointers must resolve; skill-creator validates the whole package; risk register requires doc edits alongside the skill files), so they are intentionally kept as one slice rather than split.
