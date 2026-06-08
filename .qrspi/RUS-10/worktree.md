# Work Tree — Create a new agent skill using cmux CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T11 → T14 (10 tasks)

> Single-slice content skill: all files are mutually dependent (body pointers must
> resolve, skill-creator validates the whole package, doc edits ship alongside). The
> slice is split across two sessions purely for context budget, not dependency
> isolation — SKILL.md is authored and committed to disk in Session 1, then the
> reference files (its pointer targets) and doc syncs are added in Session 2 before
> the package-wide verification checkpoint.

## Session 1 — Scaffold + author SKILL.md

**Load:** plan.md §Slice 1 (Setup + Core Logic, steps 1–8), structure.md §Frontmatter contract,
        structure.md §Body-budget contract, structure.md §Escape-safety contract,
        design §Desired End State
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Resolve open structure assumptions (OQ1 command/argument-hint, OQ3 cmux version baseline, OQ4 agent-hooks breadth) or record chosen defaults in slice PR | — | §1.1 | S | pending |
| T2 | Invoke external skill-creator to scaffold `.claude/skills/cmux/` (SKILL.md skeleton + `references/` dir) | T1 | §1.2 | M | pending |
| T3 | Write SKILL.md frontmatter — exact five-key YAML (`name`, `command`, `description`, `argument-hint`, `allowed-tools`), plain text only | T2 | §1.3 | S | pending |
| T4 | Write SKILL.md body — overview + installation/setup, high-level + pointers | T3 | §1.4 | S | pending |
| T5 | Add SKILL.md body — workspace/surface/pane lifecycle section | T4 | §1.5 | M | pending |
| T6 | Add SKILL.md body — notification system section (OSC seqs/`cmux notify`/hooks, escapes via references only) | T5 | §1.6 | S | pending |
| T7 | Add SKILL.md body — Claude Code Teams + session restore/agent resume sections | T6 | §1.7 | M | pending |
| T8 | Add SKILL.md body — multi-agent orchestration + scope/macOS caveats + relative pointers into all three references | T7 | §1.8 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md fully authored and on disk. Reference-file authoring and doc
sync are a distinct concern; a fresh context keeps Session 2 under budget and lets it
load only the section/pointer notes it needs from Session 1 rather than the full body.

## Session 2 — Reference files, doc sync, verification

**Load:** plan.md §Slice 1 (steps 9–14 + Verify Slice 1), structure.md §Files touched,
        structure.md §Reference-pointer contract, structure.md §Escape-safety contract,
        structure.md §Discovery contract, impl-log.md §Slice 1 (SKILL.md section names + relative pointer paths only)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9 | Create `references/keyboard-shortcuts.md` — full shortcut reference, `Cmd+N` notation + escapes inside code fences | T8 | §1.9 | M | pending |
| T10 | Create `references/cli-and-socket-api.md` — CLI, socket API, custom commands, in-app browser scripting, SSH; OSC seqs in code fences | T8 | §1.10 | M | pending |
| T11 | Create `references/agent-hooks.md` — `cmux hooks setup` + per-agent resume at chosen OQ4 breadth | T8 | §1.11 | M | pending |
| T12 | Modify `README.md` — add `cmux` row to skills table | T8 | §1.12 | S | pending |
| T13 | Modify `.claude/CLAUDE.md` — add `/cmux` bullet to Available skills list | T8 | §1.13 | S | pending |
| T14 | **Verify Slice 1** — run skill-creator eval/variance loop + manual structural checks (frontmatter 5 keys, pointers resolve, body <500 lines/<5000 tokens, no escapes in frontmatter, all 8 AC areas, README + CLAUDE.md list cmux) | T9, T10, T11, T12, T13 | §1.14 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session — slice complete. No further sessions; the next action is
the slice PR / package-wide approval (no unit tests exist for a content skill;
verification is the skill-creator eval loop plus the manual structural checks in T14).
