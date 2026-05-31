# Work Tree — Create a new agent skill using Codex CLI

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T0 → T1 → T2 → T3 → T4 → T7 → T8 → T9 → T10 → T13 → T14 → T15

> **BLOCKING PRECONDITION (plan §BLOCKING PRECONDITION, structure OQ1):** the skill
> `<name>` (candidate `codex-cli`) is undecided. Resolve before T1; substitute identically
> across directory name, frontmatter `name`, and frontmatter `command` (three-way identity).
>
> **AUTHORING NOTE (plan §AUTHORING NOTE):** Codex CLI factual content is external/unverified
> in-repo. Source accurate, current Codex CLI facts at authoring time. Per MEMORY (skill-creator
> directive), invoke the global skill-creator skill during authoring and record the invocation
> (OQ2 attestation).

## Session 1 — Slice 1: Reference material (`references/`)

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1,
        plan.md §BLOCKING PRECONDITION, plan.md §AUTHORING NOTE
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T0 | Resolve `<name>` (blocking precondition); create `.claude/skills/<name>/references/` (+ parent) | — | §1 | S | pending |
| T1 | Write `references/sandbox-and-platform.md` — 3 sandbox modes + macOS Seatbelt (incl. `network_access` bug) + Linux Bubblewrap+Landlock | T0 | §2 | L | pending |
| T2 | Write `references/config-toml.md` — config locations, key sections, `[profiles.<name>]`, `model_instructions_file`, project-root detection | T0 | §3 | M | pending |
| T3 | Write `references/multi-agent.md` — MCP server mode, Agents SDK, subagents, worktree parallelism | T0 | §4 | M | pending |
| T4 | Test: `ls references/` shows exactly the 3 verbatim filenames | T1, T2, T3 | §5 | S | pending |
| T5 | Test: `grep` for `seatbelt`, `bubblewrap`, `network_access` in sandbox-and-platform.md | T1 | §6 | S | pending |
| T6 | **Verify Slice 1** — checkpoint: all 3 files, required coverage, markdown lint clean | T4, T5 | §7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (references) complete and independently valid. Fresh context for Slice 2
so the SKILL.md authoring session loads only the reference filenames/contracts it must bind to,
keeping context under 40% and avoiding carry-over of long-form reference prose.

## Session 2 — Slice 2: `SKILL.md` body + integration + validation

**Load:** structure.md §New Types (SkillFrontmatter), structure.md §Contracts, structure.md §Slice 2,
        plan.md §Slice 2, impl-log.md §Slice 1 (reference filenames + resolved `<name>` only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Create `SKILL.md` frontmatter only — exact 5-field `SkillFrontmatter`; `name`=dir=`command` (three-way identity) | T6 | §8 | M | pending |
| T8 | Append SKILL.md body sections — overview, approval-mode table, `codex exec` patterns, AGENTS.md hierarchy, limitations/workarounds, pipe examples | T7 | §9 | L | pending |
| T9 | Add on-demand `Read references/<file>.md` load pointers — one per Slice 1 file, verbatim paths | T8 | §10 | M | pending |
| T10 | Test: `grep -c "Read references/"` ≥ 3 | T9 | §11 | S | pending |
| T11 | Test: each pointed-to reference file exists AND is referenced (no `MISSING`) | T9 | §12 | S | pending |
| T12 | Test: body under 500 lines; hand-check token estimate < 5000 | T9 | §13 | S | pending |
| T13 | **Verify Slice 2** — frontmatter shape (5 fields) + three-way identity | T10, T11, T12 | §14 | S | pending |
| T14 | **Verify Slice 2** — body completeness, cross-slice pointer binding, skill-creator attestation (OQ2) | T13 | §15 | S | pending |
| T15 | **Verify Slice 2** — confirm skill loads/lists without frontmatter-loader error (manual) | T14 | §16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of plan. All slices implemented and verified; no further session required.

## Rollback Notes

Net-new only (no migrations/config/destructive ops). To reverse Slice 1: delete
`.claude/skills/<name>/references/` (+ parent if no SKILL.md yet). To reverse Slice 2:
delete `.claude/skills/<name>/SKILL.md` (Slice 1 stays valid). Full rollback:
`rm -rf .claude/skills/<name>/`.
