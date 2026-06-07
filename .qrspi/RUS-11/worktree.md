# Work Tree — Create a new agent skill using the devcontainer CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T6 → T7 → T8 → T9 → T10 → T11 → T12 (9 tasks)

## Session 1 — Slice 1: Reference files

**Load:** structure.md §Contracts (references/* contracts), plan.md §Slice 1, design §Delta
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/` directory (auto-created by first file write) | — | §1 | S | pending |
| T2 | Author `references/cli-commands.md` (up/exec/build/read-configuration/run-user-commands + 3 flags) | T1 | §2 | M | pending |
| T3 | Author `references/devcontainer-json-schema.md` (image vs build, remoteUser, Compose keys) | T1 | §3 | M | pending |
| T4 | Author `references/lifecycle-decision-tree.md` (6 hooks, order, skip-on-failure/idempotency) | T1 | §4 | M | pending |
| T5 | Author `references/cicd-workflows.md` (devcontainers/ci, pre-build, registry cache) | T1 | §5 | M | pending |
| T6 | **Verify Slice 1** (4 ref files non-empty; 6 hooks; named commands/flags/keys present) | T2, T3, T4, T5 | §7 | S | pending |

> §6 has no automated test (no validator/eval harness in-repo); verification is the §7 checkpoint (T6).

--- SESSION BOUNDARY ---
**Reason:** Slice 1 reference content complete and verified. Slice 2 authors SKILL.md via the skill-creator skill (a distinct authoring workflow with large context cost); start fresh so the four reference files are loaded as notes/contracts only, not full inline content.

## Session 2 — Slice 2: SKILL.md body, frontmatter, citations

**Load:** structure.md §New Types (SkillFrontmatter, description), structure.md §Contracts (SKILL.md body, body→references), plan.md §Slice 2, design Decisions 1/3/4 + Risk register, impl-log.md §Slice 1 (notes only — reference filenames/paths)
**Estimated context:** ~30% of window (skill-creator invocation adds overhead)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Invoke global `skill-creator` to author the `devcontainer-cli` skill; record invocation | T6 | §8 | M | pending |
| T8 | Create SKILL.md frontmatter (5 repo keys; `name: devcontainer-cli`; reconcile skill-creator output) | T7 | §9 | S | pending |
| T9 | Set `description` (two-part trigger + negative Docker/K8s/Codespaces scope clause) | T8 | §10 | S | pending |
| T10 | Write SKILL.md body (workflow, opinionated defaults + exception caveat, lifecycle/Compose/troubleshooting; ≤500 lines) | T9 | §11 | L | pending |
| T11 | Add relative-path citations to all four `references/*.md` at their decision points (no orphans) | T10, T2, T3, T4, T5 | §12 | S | pending |
| T12 | **Verify Slice 2** (valid YAML 5 keys; description clauses; 4 CITED; defaults+caveat; Compose+troubleshooting; ≤500 lines; skill-creator recorded) | T11 | §14 | S | pending |

> §13 has no automated test (manual inspection only); covered by the §14 checkpoint (T12).

--- SESSION BOUNDARY ---
**Reason:** Feature complete after T12. No further sessions; subsequent work (PR prep) is a separate phase.

## Rollback Notes

- Additive only: feature creates new files under `.claude/skills/devcontainer-cli/` and modifies nothing existing (design §Delta).
- To roll back any/all tasks, delete the `.claude/skills/devcontainer-cli/` directory in its entirety; no other path is touched.
