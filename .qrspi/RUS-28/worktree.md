# Work Tree — Create a new agent skill: writing GitLab pipelines

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T20 → T21 → T22 (11 tasks)

## Session 1 — Slice 1: SKILL.md skeleton + reference stubs

**Load:** structure.md §Types (SkillFrontmatter), structure.md §Contracts (flat allowed-tools, Reference-link contract), plan.md §Slice 1, reference shape from `.claude/skills/qrspi-ticket/SKILL.md`
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/rules.md` stub (H1 + scope line) | — | §1 | S | pending |
| T2 | Create `references/includes-extends.md` stub | — | §2 | S | pending |
| T3 | Create `references/cache-artifacts.md` stub | — | §3 | S | pending |
| T4 | Create `references/environments.md` stub | — | §4 | S | pending |
| T5 | Create `references/security.md` stub | — | §5 | S | pending |
| T6 | Create `references/architecture.md` stub | — | §6 | S | pending |
| T7 | Write SKILL.md YAML frontmatter (flat shape, name=dir, trigger description, allowed-tools, OQ1/OQ3 defaults) | — | §7 | S | pending |
| T8 | Append `## Purpose & when to use` section | T7 | §8 | S | pending |
| T9 | Append `## Opinionated defaults` section | T8 | §9 | S | pending |
| T10 | Append `## Performance & optimization` section | T9 | §10 | S | pending |
| T11 | Append `## Anti-patterns → alternatives` section | T10 | §11 | S | pending |
| T12 | Append `## See references/` index (six resolving relative links) | T11, T1, T2, T3, T4, T5, T6 | §12 | S | pending |
| T13 | **Verify Slice 1** — frontmatter parses, name matches dir, flat allowed-tools, links resolve, ≤500 lines, four inline sections present | T12 | §13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (skeleton + stubs verified). Reference content fill is high-volume Markdown that would bloat context; start fresh for Slice 2 carrying only the verified contracts and the Slice-1 link/budget result.

## Session 2 — Slice 2: Reference content fill + final cross-checks

**Load:** structure.md §Contracts (Reference-link contract, standalone-H1 requirement), plan.md §Slice 2, design §Desired End State (ticket-concern → file mapping), impl-log.md §Slice 1 (verified link/budget result only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Fill `references/rules.md` (rules:, workflow:rules, changes, CI vars, terminal when) | T13 | §14 | L | pending |
| T15 | Fill `references/includes-extends.md` (include kinds, extends vs anchors, !reference, Catalog GA 17.0 note) | T13 | §15 | L | pending |
| T16 | Fill `references/cache-artifacts.md` (cache keys/policy, artifacts expire_in/reports/when) | T13 | §16 | L | pending |
| T17 | Fill `references/environments.md` (static/dynamic envs, on_stop, review apps, scoped vars, gates) | T13 | §17 | L | pending |
| T18 | Fill `references/security.md` (SAST/dep/container/secret templates, DAST, reports, policies) | T13 | §18 | L | pending |
| T19 | Fill `references/architecture.md` (worked examples: minimal, mature, parent-child + multi-project) | T13 | §19 | L | pending |
| T20 | **Verify Slice 2** — each ref standalone H1, no stubs remain, design concerns mapped, version notes present | T14, T15, T16, T17, T18, T19 | §20 | S | pending |
| T21 | **Checkpoint (manual)** — re-run Slice-1 link + budget check post-fill | T20 | §21 | S | pending |
| T22 | **Checkpoint (manual)** — cross-check vs ticket acceptance criteria; confirm OQ1/OQ3/OQ4 resolved or accepted | T21 | §22 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Feature complete — all slices verified. No further sessions; proceed to PR phase.
