# Work Tree — Create a new agent skill for writing Product Requirements Documents

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 (14 tasks, fully linear single-file authoring chain)

## Session 1 — Author the writing-prds skill files

**Load:** structure.md §Types (`PrdHeader`, `PrdSection`, `SmartMetric`, `UserStory`, `SkillFrontmatter`), structure.md §Contracts (`SKILL.md frontmatter`, `body → references/prd-template.md`, `clarifyThrottle`, `formatSelection`, `requiredSectionGate`), plan.md §Slice 1 (steps 1–11)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/prd-template.md` empty scaffold | — | §1 | S | pending |
| T2 | Add PRD metadata-header block per `PrdHeader` (source/timestamp/Status) | T1 | §2 | S | pending |
| T3 | Add lean six-section skeleton per `PrdSection` | T2 | §3 | S | pending |
| T4 | Append expanded sections (Personas, Technical Considerations, Dependencies, Launch Plan) | T3 | §4 | S | pending |
| T5 | Add SMART metrics table format per `SmartMetric` | T4 | §5 | S | pending |
| T6 | Add user-story + Given/When/Then block per `UserStory` | T5 | §6 | S | pending |
| T7 | Create `SKILL.md` with YAML frontmatter per `SkillFrontmatter` + contract | T6 | §7 | M | pending |
| T8 | Add problem-first conversation body section per `clarifyThrottle` (≤2-question throttle) | T7 | §8 | S | pending |
| T9 | Add reference-by-path body section linking `references/prd-template.md` | T8 | §9 | S | pending |
| T10 | Add lean-vs-expanded body section per `formatSelection` | T9 | §10 | S | pending |
| T11 | Add required-section checklist + solution-blind self-review gate per `requiredSectionGate` | T10 | §11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All authoring complete. Verification — especially the `skill-creator` eval loop (T14) — is a distinct activity that loads the skill-creator skill and runs an interactive e2e; a fresh context keeps that under budget and isolates eval feedback from the authoring chain.

## Session 2 — Verify Slice 1

**Load:** plan.md §Verify Slice 1 (steps 12–14), plan.md §Blocking Open Questions (OQ1), structure.md §Contracts (`SkillFrontmatter`), impl-log.md §Slice 1 (notes only)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Checkpoint: both files exist; dir name `writing-prds` == frontmatter `name` | T11 | §12 | S | pending |
| T13 | Checkpoint: body references template by relative path (resolves); `allowed-tools: Read, Write` present | T12 | §13 | S | pending |
| T14 | **Verify Slice 1** — invoke `skill-creator` eval loop + manual e2e (clarify throttle, all core sections, lean+expanded, SMART table, user story, header, trigger firing, ≤500-line self-check) | T13 | §14 | L | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 is the only slice; feature authoring + verification complete. No further session — proceed to PR phase.

## Notes

- Single-slice plan: all 11 authoring tasks (T1–T11) operate on exactly two new files under `.claude/skills/writing-prds/`, so the critical path is a strict linear chain with no parallelizable branches.
- Carry the Blocking Open Questions into Session 2: **OQ1** affects whether the `skill-creator` invocation in T14 is a hard gate; **OQ2/OQ3** could add Modify steps to Session 1 (T2 for a `version`/changelog field; a new task to register the skill in `.claude/CLAUDE.md`). Confirm before/at implementation.
