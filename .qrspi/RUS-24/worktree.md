# Work Tree — Create a new agent skill using the omlx CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T15 → T17 → T18 → T19 → T20 (15 tasks)

## Session 1 — Author the `using-omlx-cli` skill (Slice 1)

**Load:** structure.md §Types (SkillFrontmatter, ReferenceFile), structure.md §Contracts (C1–C7),
        plan.md §Slice 1, design.md §Desired End State, design.md Decision 3
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` to scaffold `.claude/skills/using-omlx-cli/` (C7; OQ1) | — | §1.1 | M | pending |
| T2 | Create `.claude/skills/using-omlx-cli/references/` directory | T1 | §1.2 | S | pending |
| T3 | Create SKILL.md with YAML frontmatter in order `name → description → command → argument-hint → allowed-tools` (C2, C1) | T2 | §1.3 | S | pending |
| T4 | Set `description` with "Use when…" trigger phrases (Apple Silicon, local LLM, omlx) | T3 | §1.4 | S | pending |
| T5 | Add lifecycle overview section → `references/serve-flags.md` pointer (C4) | T4 | §1.5 | S | pending |
| T6 | Add memory-tier model-size summary (16/24/32/64 GB) → `references/memory-tiers.md` (C4) | T5 | §1.6 | S | pending |
| T7 | Add two-tier KV-cache summary → `references/memory-tiers.md` (C4) | T6 | §1.7 | S | pending |
| T8 | Add OpenAI-compatible API + MCP + agent-launch summary → `references/serve-flags.md` | T7 | §1.8 | S | pending |
| T9 | Add oMLX-vs-Ollama-vs-LM-Studio decision-guidance section | T8 | §1.9 | S | pending |
| T10 | Add troubleshooting index → `references/troubleshooting.md` (C4) | T9 | §1.10 | S | pending |
| T11 | Create `references/serve-flags.md` (flags, lifecycle, cache, API, MCP, launch) | T8 | §1.11 | M | pending |
| T12 | Create `references/memory-tiers.md` (per-tier model table + KV-cache tuning) | T7 | §1.12 | M | pending |
| T13 | Create `references/troubleshooting.md` (OOM loop, memory pressure, instability, model-not-showing) | T10 | §1.13 | M | pending |
| T14 | Check: frontmatter parses, field order correct (C2) | T3 | §1.14 | S | pending |
| T15 | Check: SKILL.md body < 500 lines / < 5000 tokens (C3) | T10 | §1.15 | S | pending |
| T16 | Check: every `references/` link resolves, no dead links (C4) | T11, T12, T13 | §1.16 | S | pending |
| T17 | **Verify Slice 1** (all files exist, identity, triggers, budget, links, no agent file, C1–C7) | T14, T15, T16 | §1.17 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (skill authored + structurally verified). Slice 2 is an optional, isolated documentation edit gated on OQ3; a fresh context drops the bulky SKILL.md/references authoring detail and loads only the catalog-edit scope.

## Session 2 — (Optional) Register skill in human-facing catalog (Slice 2)

**Load:** plan.md §Slice 2, structure.md §Contracts (catalog entry), design.md §Delta (OQ3),
        impl-log.md §Slice 1 (notes only — confirm skill name/description)
**Estimated context:** ~10% of window

> Gated on OQ3 — skip entirely if the reviewer decides unvalidated docs should not be touched.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T18 | Append `/using-omlx-cli` entry to `.claude/CLAUDE.md` "Available skills" list (doc-only; existing entries untouched) | T17 | §2.18 | S | pending |
| T19 | Check: `grep` shows exactly one new `using-omlx-cli` line in skills list | T18 | §2.19 | S | pending |
| T20 | **Verify Slice 2** (entry present + accurate; pure doc edit, no behavior change) | T19 | §2.20 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. Work tree complete; hand off to PR phase.
