# Work Tree — Create a new agent skill called writing gitlab pipelines

**Plan basis:** plan.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 (Verify Slice 1) → T8 → T9 → T10 (Verify Slice 2)

## Session 1 — Slice 1: SKILL.md (frontmatter + dispatcher body)

**Load:** structure.md §New Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill dir + SKILL.md frontmatter (`name`, `command`, `argument-hint`, `allowed-tools`) | — | §1.1–1.2 | S | pending |
| T2 | Write `description` with explicit GitLab/.gitlab-ci.yml trigger phrases | T1 | §1.3 | S | pending |
| T3 | Write body: scope, structure, rules-over-only/except (opinionated format) | T2 | §1.4–1.6 | M | pending |
| T4 | Write body: DRY, artifacts/cache, services | T3 | §1.7–1.9 | M | pending |
| T5 | Write body: environments/review apps, multi-project, security, variables/secrets | T4 | §1.10–1.13 | M | pending |
| T6 | Write body: performance, anti-patterns table, Reference-material index | T5 | §1.14–1.16 | M | pending |
| T7 | **Verify Slice 1** — frontmatter parse, name==dir, trigger phrases, <500 lines, 10 concerns, 6 references named, opinionated format present | T6 | §1.17–1.20 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (the SKILL.md body) is complete and independently verifiable. Slice 2 writes six reference files — a fresh context loads only the Slice 2 plan + the completed body's reference index, keeping context under budget.

## Session 2 — Slice 2: references/ (six concern files)

**Load:** structure.md §Contracts (body→reference link, concern coverage), plan.md §Slice 2, SKILL.md §Reference material (the index naming each file), impl-log.md §Slice 1 (notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Create `references/rules.md`, `references/includes-extends.md`, `references/caching.md` | T7 | §2.21–2.23 | L | pending |
| T9 | Create `references/environments.md`, `references/security-scanning.md`, `references/architecture.md` | T8 | §2.24–2.26 | L | pending |
| T10 | **Verify Slice 2** — link/orphan check, per-file topic coverage, version annotations, full concern+criteria coverage | T9 | §2.27–2.28 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of implementation. After Slice 2 verification, the orchestrator runs the PR phase.

## Notes

- All tasks are additive file creation under one new directory; no task modifies existing files, so there is no cross-task contention or restack hazard within the deliverable.
- T8 and T9 are split only to keep each session's writing load under the 40% context budget (six substantial reference files); they share no testability boundary and could merge if context allows.
