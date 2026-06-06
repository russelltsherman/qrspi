# Work Tree — Create a new agent skill: using-terraform-cli

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T14

## Session 1

**Load:** structure.md §SkillFrontmatter, structure.md §Contracts, structure.md §Scope, plan.md §Slice 1, design.md §Desired End State, design.md §Decisions
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke global `skill-creator` skill to drive authoring; document the invocation | — | §1.1 | S | pending |
| T2 | Create `references/` directory under the skill | T1 | §1.2 | S | pending |
| T3 | Create SKILL.md with five-field YAML frontmatter (`name: using-terraform-cli`) | T1 | §1.3 | S | pending |
| T4 | Add core-lifecycle body section (init→validate→plan→apply→destroy) | T3 | §1.4 | S | pending |
| T5 | Add state-management section + cite `references/backend-setup.md` | T4 | §1.5 | S | pending |
| T6 | Add version-pinning section | T5 | §1.6 | S | pending |
| T7 | Add import/moved/removed section + cite `references/migration-blocks.md` | T6 | §1.7 | S | pending |
| T8 | Add CI/CD-with-OIDC section + cite `references/cicd-pipelines.md` | T7 | §1.8 | S | pending |
| T9 | Add remaining body sections (secrets/security, workspaces, modules/testing) + scope note | T8 | §1.9 | M | pending |
| T10 | Create `references/backend-setup.md` (S3+DynamoDB canonical + GCS/Azure/HCP) | T2, T5 | §1.10 | M | pending |
| T11 | Create `references/cicd-pipelines.md` (pipeline stages, OIDC, gates, scanning) | T2, T8 | §1.11 | M | pending |
| T12 | Create `references/migration-blocks.md` (import/moved/removed patterns) | T2, T7 | §1.12 | M | pending |
| T13 | Modify `.claude/CLAUDE.md` — add skill to "Available skills" list | T1 | §1.13 | S | pending |
| T14 | **Verify Slice 1** (line budget, frontmatter, citations, ref files, AC coverage, e2e) | T9, T10, T11, T12, T13 | §1.14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. The plan defines a single vertical slice; no further sessions are required.
