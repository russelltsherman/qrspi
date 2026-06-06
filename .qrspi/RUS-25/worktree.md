# Work Tree — Create a new agent skill for writing Architecture Decision Records

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T16 → T17 → T20 → T22 (12 tasks)

> **Human prerequisites before Session 1 (carried from plan §Blocking notes):**
> OQ1 — final skill slug `<name>` must be fixed (gates every path, T1+); OQ2 —
> `allowed-tools` allowlist must be confirmed before T6 writes the frontmatter.
> These are not tasks; they are blocking inputs.

## Session 1 — Slice 1: Author the `adr` skill

**Load:** structure.md §New Types (SkillFrontmatter, MADR4Document, ADRStatusTransition, ADRNaming),
        structure.md §Contracts (ReferenceLink, AssetReference, SupersedeProcedure),
        plan.md §Slice 1, design.md §Desired End State + §Delta (format/section reference only)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/madr-4.0.md` — full MADR 4.0 template + per-section guidance (8 ordered sections) | — | §1.1 | M | pending |
| T2 | Create `references/nygard.md` — Nygard original ADR template | — | §1.2 | S | pending |
| T3 | Create `references/y-statements.md` — Y-statement format reference | — | §1.3 | S | pending |
| T4 | Create `references/examples.md` — worked example ADRs | — | §1.4 | M | pending |
| T5 | Create `assets/NNNN-template.md` — copyable MADR 4.0 starter (8 ordered sections) | — | §1.5 | M | pending |
| T6 | Create `SKILL.md` — YAML frontmatter (SkillFrontmatter, name/command/allowed-tools) | — | §1.6 | S | pending |
| T7 | Modify `SKILL.md` — add "Default format (MADR 4.0)" body section | T6 | §1.7 | S | pending |
| T8 | Modify `SKILL.md` — add ADRStatusTransition lifecycle table | T7 | §1.8 | S | pending |
| T9 | Modify `SKILL.md` — add ADRNaming rules section | T8 | §1.9 | S | pending |
| T10 | Modify `SKILL.md` — add "When to write an ADR" judgment section | T9 | §1.10 | S | pending |
| T11 | Modify `SKILL.md` — add SupersedeProcedure / deprecate / index section | T10 | §1.11 | S | pending |
| T12 | Modify `SKILL.md` — add 4 ReferenceLink + 1 AssetReference pointers (each target once) | T11, T1, T2, T3, T4, T5 | §1.12 | S | pending |
| T13 | Validate skill via `skill-creator`; confirm by manual review | T12 | §1.13 | S | pending |
| T14 | Run `python3 scripts/grade.py` line_count vs `SKILL.md` (≤500 lines / ≤5000 tokens) | T12 | §1.14 | S | pending |
| T15 | Run grep for `references/` + `assets/NNNN-template.md` (each pointed to exactly once) | T12 | §1.15 | S | pending |
| T16 | **Verify Slice 1** — checkpoint: files exist, frontmatter complete, pointers/budget/sections | T13, T14, T15 | §1.16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. Slice 2 needs only the *final* `name`/`command`/`description`
from the now-frozen `SKILL.md` frontmatter, not the full authoring context. Fresh context
keeps Session 2 under budget and prevents drift from stale Slice 1 working state.

## Session 2 — Slice 2: Sync the three hand-maintained skill lists

**Load:** structure.md §Contracts (SkillListEntry), plan.md §Slice 2,
        SKILL.md frontmatter (final name/command/description — values only)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T17 | Modify `.claude/CLAUDE.md` — add SkillListEntry for the new skill | T16 | §2.17 | S | pending |
| T18 | Modify `README.md` — add the same SkillListEntry (matching style) | T16 | §2.18 | S | pending |
| T19 | Modify `docs/qrspi_claude_code_guide.md` — add the same SkillListEntry (matching style) | T16 | §2.19 | S | pending |
| T20 | Run `grep -rl "<name>"` across the three files (all three returned) | T17, T18, T19 | §2.20 | S | pending |
| T21 | Confirm by inspection each entry matches Slice 1 final frontmatter (no drift) | T17, T18, T19 | §2.21 | S | pending |
| T22 | **Verify Slice 2** — checkpoint: all three files, matching style, no drift | T20, T21 | §2.22 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. Slice 2 verified; feature complete and ready for PR.
