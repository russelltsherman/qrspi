# Work Tree — Create a new agent skill using aws cli

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T4 → T5 → T6 → T7 → T8 → T9 → T12 → T13 → T14

> Single-slice feature (plan Slice 1). Tasks T1–T14 map 1:1 to plan steps §1–§14.
> T1–T3 (single-topic references) are mutually independent and feed the body-authoring
> tasks that link them (T6←T1, T7←T2, T8←T3). The SKILL.md body (T4–T9) is a strictly
> sequential same-file chain. Validation T10/T11 branch off T9; the verify chain
> T12→T13→T14 gates the slice and re-joins T10 and T11.

## Session 1 — Single-topic references

**Load:** plan.md §Slice 1 Setup (steps 1–3), structure.md §Contracts (Topic-partition,
        Content-hygiene), design.md §Delta (waiter timeout exit-code-255 note)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/jmespath.md` — `--query` JMESPath reference (placeholders only) | — | §1 | M | pending |
| T2 | Create `references/waiters.md` — built-in waiter reference incl. timeout note | — | §2 | M | pending |
| T3 | Create `references/services.md` — per-service cheat sheets (S3/EC2/ECS/Lambda/IAM/CFN) | — | §3 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** References complete. Authoring SKILL.md is a distinct, sequential same-file
task with a different load manifest (Frontmatter/Body/Budget contracts); fresh context
keeps the authoring session focused and under budget.

## Session 2 — Author SKILL.md (frontmatter + body)

**Load:** plan.md §Slice 1 Core Logic (steps 4–9), structure.md §Contracts (Frontmatter,
        Reference-link, Body-coverage, Budget, Security-as-imperatives), design.md
        §Desired End State, design.md §Current State Q4, impl-log.md §References (notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T4 | SKILL.md frontmatter — five `SkillFrontmatter` fields (resolve A1/A2 first) | — | §4 | S | pending |
| T5 | Body — Authentication & Profiles section | T4 | §5 | S | pending |
| T6 | Body — Env/Config, Output Formatting & Filtering, Pagination; link `jmespath.md` | T5, T1 | §6 | M | pending |
| T7 | Body — Waiters section; link `waiters.md` | T6, T2 | §7 | S | pending |
| T8 | Body — per-service sections (S3/EC2/ECS/Lambda/IAM/CFN); link `services.md` | T7, T3 | §8 | M | pending |
| T9 | Body — Error Handling & Scripting, Security imperatives, `## Scope` | T8 | §9 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Authoring complete. Validation/verify uses tooling (skill-creator,
content/link/hygiene checks) and the slice checkpoint gates rather than authoring
contracts; a fresh context separates "write" from "verify".

## Session 3 — Validation & Verify Slice 1

**Load:** plan.md §Slice 1 Tests (steps 10–11), plan.md §Verify Slice 1 (steps 12–14),
        structure.md §Contracts (Frontmatter, Reference-link, Body-coverage, Budget,
        Content-hygiene), impl-log.md §Slice 1 authoring (notes only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Invoke skill-creator against the skill (or hand-author + note A3 substitution) | T9 | §10 | M | pending |
| T11 | Content-and-link check (five fields, links resolve, hygiene grep) | T9 | §11 | S | pending |
| T12 | Checkpoint — all four files exist | T9 | §12 | S | pending |
| T13 | Checkpoint — Frontmatter contract + Reference-link contract resolve | T12 | §13 | S | pending |
| T14 | **Verify Slice 1** — Budget/Body-coverage/Content-hygiene + skill-creator recorded + live trigger | T13, T10, T11 | §14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (the only slice) complete and verified. End of work tree.
