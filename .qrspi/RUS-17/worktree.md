# Work Tree — Create a new agent skill using obsidian cli

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T17 → T18 (13 tasks)

> Single-slice plan (18 steps). Steps 3–11 are sequential edits to one file
> (`SKILL.md`), so the body authoring is an unavoidable serial chain and dominates the
> critical path. Reference files (T12–T14) and the list bullet (T15) form an independent
> branch off T1 that rejoins at the link-resolution test (T17).

## Session 1 — Author `SKILL.md` (scaffold + frontmatter + body)

**Load:** structure.md §Types (`SkillFrontmatter`), structure.md §Contracts
        (`frontmatter-name-invariant`, `reference-link-contract`, `property-coverage-contract`,
        `tool-preference-contract`, `error-handling-contract`, `body-budget-contract`),
        plan.md §Slice 1 (Setup + Core Logic, steps 1–11), design.md §Desired End State
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` to scaffold `.claude/skills/obsidian/` | — | §1 | M | pending |
| T2 | Create `SKILL.md` with five-key YAML frontmatter (name/description/command/argument-hint/allowed-tools, fixed order) | T1 | §2 | S | pending |
| T3 | Add capability/trigger description + `## Vault structure` section | T2 | §3 | S | pending |
| T4 | Add `## Note CRUD` overview citing `references/cli-reference.md` | T3 | §4 | S | pending |
| T5 | Add `## Frontmatter / properties` covering all 7 property types | T4 | §5 | S | pending |
| T6 | Add `## Linking` (wikilinks, heading/block refs, pipe-display) | T5 | §6 | S | pending |
| T7 | Add `## Tags` conventions section | T6 | §7 | S | pending |
| T8 | Add `## CLI vs URI vs filesystem` decision table + prefer/forbid prose, cite `references/uri-protocol.md` | T7 | §8 | S | pending |
| T9 | Add `## Idempotency` guidance section | T8 | §9 | S | pending |
| T10 | Add `## Plugin conventions` (Dataview/Templater/Tasks), cite `references/dataview.md` | T9 | §10 | S | pending |
| T11 | Add `## Error handling` (condition → STOP/action style); body complete | T10 | §11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** `SKILL.md` body is complete. Reference-file authoring + mechanical validation
are a distinct workstream that needs the `ReferenceFile` and coverage contracts, not the
per-section body detail — drop the body-editing context and load reference contracts instead.

## Session 2 — Reference files, list bullet, validation

**Load:** structure.md §Types (`ReferenceFile`, `AvailableSkillsList`), structure.md §Contracts
        (`cli-coverage-contract`, `reference-link-contract`, `property-coverage-contract`),
        plan.md §Slice 1 (steps 12–18), design.md §Desired End State,
        impl-log.md §Slice 1 (SKILL.md reference-link list — notes only)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Create `references/cli-reference.md` — all 13 commands w/ params + quoting notes (CLI v1.12.4) | T1 | §12 | M | pending |
| T13 | Create `references/uri-protocol.md` — `obsidian://` actions + URI encoding | T1 | §13 | M | pending |
| T14 | Create `references/dataview.md` — DQL + inline-field syntax | T1 | §14 | M | pending |
| T15 | Add `obsidian` bullet to `.claude/CLAUDE.md` "Available skills" list | T1 | §15 | S | pending |
| T16 | Test: frontmatter parses, exactly 5 keys in order, name/command invariant | T2 | §16 | S | pending |
| T17 | Test: every `(see references/<file>.md)` link resolves | T11, T12, T13, T14 | §17 | S | pending |
| T18 | **Verify Slice 1** — checkpoint: command/property coverage, body budget, skill-creator + human-review gates | T15, T16, T17 | §18 | S | pending |
