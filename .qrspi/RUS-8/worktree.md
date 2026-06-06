# Work Tree — Create a new agent skill for the argocd CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T7 → T8 → T9 (any one reference file → SKILL.md → skill-creator pass → Verify Slice 1; 4 tasks)

> The six `references/*.md` (T1–T6) have no inter-dependencies and may be authored in any
> order / in parallel. T7 (`SKILL.md`) depends on all six existing so its `references/`
> pointers resolve. The whole plan is one create-only vertical slice (structure.md
> §Modified Types: None), so it is one session below the 40% budget — no fresh-context
> boundary is needed mid-slice.

## Session 1

**Load:** plan.md §Slice 1, structure.md §Contracts (the seven `*Contract` definitions),
        structure.md §Types, design §Delta, design §Current State
**Estimated context:** ~30% of window (authoring 7 new markdown files, ~250–350 lines for
        SKILL.md and shorter reference files; no codebase load)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/authentication.md` — H1 `# Authentication & Context`; token vs password auth, `ARGOCD_*` env, `--grpc-web`/`--core`, role tokens, `argocd login`/`context`; bold token-auth default (`ReferenceTitleContract`, `OpinionatedDefaultsContract`) | — | §1.1 | S | pending |
| T2 | Create `references/sync-strategies.md` — H1 `# Sync Strategies`; manual vs auto sync, `--self-heal`/`--auto-prune`, dry-run, waves, hooks, retry; bold manual-sync-for-prod default (`ReferenceTitleContract`, `OpinionatedDefaultsContract`) | — | §1.2 | S | pending |
| T3 | Create `references/rollback-procedures.md` — H1 `# Rollback Procedures`; `app rollback` + auto-disable of auto-sync, `app history`, Git revert follow-up; bold Git-revert default (`ReferenceTitleContract`, `OpinionatedDefaultsContract`) | — | §1.3 | S | pending |
| T4 | Create `references/applicationset-generators.md` — H1 `# ApplicationSet Generators`; Git/Cluster/Matrix/List generators, app-of-apps transition, `preserveResourcesOnDeletion` (`ReferenceTitleContract`) | — | §1.4 | S | pending |
| T5 | Create `references/rbac-configuration.md` — H1 `# RBAC & Projects`; AppProjects, role tokens, `admin settings rbac validate`/`can`, SSO mapping, deny-all default (`ReferenceTitleContract`) | — | §1.5 | S | pending |
| T6 | Create `references/troubleshooting.md` — H1 `# Troubleshooting`; flowchart prose `app get`→`app resources`→events/logs→`terminate-op`, live-vs-git compare, hard refresh (`ReferenceTitleContract`) | — | §1.6 | S | pending |
| T7 | Create `SKILL.md` — five-key frontmatter in order (`FrontmatterContract`), H1 `# Using the Argo CD CLI`, `##` sections in escalation order (`EscalationOrderContract`), root-relative `references/<file>.md` pointers at decision points (`ReferenceCitationContract`), bash-fenced examples, three bold defaults (`OpinionatedDefaultsContract`), ~250–350 lines | T1, T2, T3, T4, T5, T6 | §1.7 | M | pending |
| T8 | Run `skill-creator` authoring/validation pass over `.claude/skills/using-argocd-cli/`; address frontmatter/description findings (external manual step; AC #2, OQ1) | T7 | §1.8 | M | pending |
| T9 | **Verify Slice 1** — run the §1.9 `python3` checkpoint and walk all six acceptance boxes (frontmatter order, pointer resolution, lifecycle coverage, escalation order, length < 500, skill-creator + `/using-argocd-cli` discovery/trigger) | T8 | §1.9 | S | pending |
