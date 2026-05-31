# Work Tree — Create a new agent skill: writing Architecture Decision Records

**Plan basis:** plan.md @ 2026-05-31T16:39:00Z
**Generated:** 2026-05-31T16:42:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T14 → T21 → T22

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1, ticket conventions (MADR section list, status lifecycle, numbering rules)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke skill-creator to scaffold `.claude/skills/<name>/` with references/ + assets/ | — | §1 | M | pending |
| T2 | Confirm SKILL.md scaffold + valid `name`/`description` frontmatter, no name collision | T1 | §2 | S | pending |
| T3 | Write trigger-tuned `description` (capability + Use when/Trigger on + negative scope) | T2 | §3 | S | pending |
| T4 | Body: "When to write an ADR" (architecturally-significant test) | T2 | §4 | S | pending |
| T5 | Body: "Default format: MADR 4.0" (required + optional sections, pointer to reference) | T2 | §5 | S | pending |
| T6 | Body: "Choosing a format" option/recommendation table (MADR/Nygard/Y-statement) | T2 | §6 | S | pending |
| T7 | Body: "Numbering, naming, location" (+ adr-tools/log4brains compatibility) | T2 | §7 | S | pending |
| T8 | Body: "Status lifecycle" (+ immutability after accepted) | T2 | §8 | S | pending |
| T9 | Body: "Creating an ADR" (copy asset, compute NNNN, write, index) | T2 | §9 | S | pending |
| T10 | Body: "Superseding an ADR" (bidirectional links) | T2 | §10 | S | pending |
| T11 | Body: "Deprecating an ADR" | T2 | §11 | S | pending |
| T12 | Body: "Maintaining the index" (pointer to index template) | T2 | §12 | S | pending |
| T13 | Body: "Writing style & level of detail" (+ supersede-vs-amend) | T2 | §13 | S | pending |
| T14 | Trim/verify body under 500 lines / ~5000 tokens; offload overflow to references | T3,T4,T5,T6,T7,T8,T9,T10,T11,T12,T13 | §14 | M | pending |
| T15 | Create `references/madr-4.0.md` (full template + per-section guidance) | T2 | §15 | M | pending |
| T16 | Create `references/nygard.md` | T2 | §16 | S | pending |
| T17 | Create `references/y-statements.md` | T2 | §17 | S | pending |
| T18 | Create `references/examples.md` (2+ examples + supersede pair) | T2 | §18 | M | pending |
| T19 | Create `assets/adr-template.md` (MADR starter, angle-bracket placeholders) | T2 | §19 | S | pending |
| T20 | Create `assets/index-README-template.md` (index starter) | T2 | §20 | S | pending |
| T21 | Run skill-creator validation / eval loop; address findings | T14,T15,T16,T17,T18,T19,T20 | §21 | M | pending |
| T22 | **Verify Slice 1** — structural checkpoint (frontmatter, size, files, coverage, conventions, eval) | T21 | §22 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Single cohesive slice; the entire skill is authored and validated in one session. No further sessions — the deliverable is complete when T22 passes. Estimated context stays well under 40% because the work is bounded to one skill directory and its reference/asset files, with no broad codebase exploration.
