# Work Tree — Create a new agent skill: using helm cli

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T13 (8 tasks)

> Single vertical slice. The artifact is a self-contained documentation/prompt
> skill (markdown only, no executable code), so all 13 tasks fit one session
> well under the 40% budget. SKILL.md body sections (T3–T7) are sequential
> because they edit the same file; the five `references/*.md` files (T8–T12) fan
> out off the body sections that name them. T13 (verification) joins all leaves.

## Session 1

**Load:** structure.md §Types (SkillDirectory, SkillFrontmatter, ReferenceFile),
        structure.md §Contracts (Frontmatter, Triggering, Reference-loading,
        Scope-boundary, Size-budget, Version-caveat), structure.md §Verification,
        plan.md §Slice 1, design §Desired End State + §Risk Register
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Begin authoring pass via `skill-creator` + eval loop, scoped to `.claude/skills/using-helm-cli/` (self-contained archetype only) | — | §1 | S | pending |
| T2 | Write SKILL.md five-field frontmatter; `name == using-helm-cli == dir name`; action + "Use when" description with literal helm trigger phrases | T1 | §2 | M | pending |
| T3 | Add release-lifecycle body (install/upgrade/rollback/uninstall/status) with security defaults `--atomic`/`--wait`/`--verify` + explicit namespaces | T2 | §3 | M | pending |
| T4 | Add values/overrides + chart-authoring body; backtick-name `references/values-patterns.md` | T3 | §4 | M | pending |
| T5 | Add repo/registry, hooks, testing body; backtick-name `references/oci-workflow.md`, `references/hook-lifecycle.md`, `references/testing-strategies.md` | T4 | §5 | M | pending |
| T6 | Add troubleshooting decision tree + Helm 4 body with `Helm 3:` caveats; backtick-name `references/helm4-migration.md` | T5 | §6 | M | pending |
| T7 | Add out-of-scope body naming-and-deferring kubectl/kustomize, Helmfile, GitOps reconcilers | T6 | §7 | S | pending |
| T8 | Create `references/values-patterns.md` (layered values, `-f` ordering, deep-merge vs array-replace, schema, secrets deferral) | T4 | §8 | M | pending |
| T9 | Create `references/hook-lifecycle.md` (hook weights, delete policies, pre/post phases, hook Job limits) | T5 | §9 | M | pending |
| T10 | Create `references/oci-workflow.md` (OCI push/pull, classic repo, signing/verification) | T5 | §10 | M | pending |
| T11 | Create `references/testing-strategies.md` (`helm test`, helm-unittest, lint, policy template, schema validation) | T5 | §11 | M | pending |
| T12 | Create `references/helm4-migration.md` (SSA default, readiness annotations, post-renderer plugins, Helm 3 notes) | T6 | §12 | M | pending |
| T13 | **Verify Slice 1** — run checkpoint `wc -l` + `ls references/`; confirm frontmatter, size budget, all five references named & present, out-of-scope, triggering, acceptance checklist, no sibling agents/scripts/assets | T7, T8, T9, T10, T11, T12 | §13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Only slice in the plan; no further sessions.
