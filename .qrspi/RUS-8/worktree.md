# Work Tree — Create a new agent skill using-argocd-cli

**Plan basis:** plan.md @ 2026-05-27T13:00:00Z
**Generated:** 2026-05-27T14:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1
**Estimated context:** 25%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `.claude/skills/using-argocd-cli/` directory — top-level skill directory following the agentskills.io pattern and the `references/` structure from structure.md Contract types. | — | §1.1 | S | pending |
| T2 | Invoke `skill-creator` to generate `.claude/skills/using-argocd-cli/SKILL.md` with frontmatter (name=using-argocd-cli, command=argocd, allowed-tools=Read,Write,Edit,Bash,Glob,Grep) and body sections covering Activation, Role, Workflow, Quick Reference, Application Lifecycle, Auth, Opinionated Defaults, Safety. Constraint: under 500 lines. | T1 | §1.2 | M | pending |
| T3 | Create `references/cli-output.md` — map each major subcommand group (app, repo, cluster, account, project, secret, context) to supported output flags and describe `PrintResource()` rendering. | T1 | §1.3 | M | pending |
| T4 | Create `references/sync-model.md` — document sync waves, resource hooks, sync phases, and sync strategies (manual vs auto, self-heal, prune). | T1 | §1.4 | M | pending |
| T5 | Create `references/auth-rbac.md` — cover authentication flows (ARGOCD_AUTH_TOKEN, ARGOCD_OPTS, argocd login, argocd context), project-scoped role tokens, and RBAC escalation path. | T1 | §1.5 | M | pending |
| T6 | Create `references/troubleshooting.md` — provide diagnostic commands, error patterns (optimistic lock, TLS/self-signed cert, SSO redirect), and retry guidance. | T1 | §1.6 | M | pending |
| T7 | Modify `.claude/CLAUDE.md` — append `using-argocd-cli` to the available skills list after the QRSPI skills block. | T2,T3,T4,T5,T6 | §1.7 | S | pending |
| T8 | **Verify Slice 1** — Run all 5 verification checks: line count under 500, frontmatter valid YAML with 5 fields, references/ has all 4 files non-empty, CLAUDE.md lists skill, grep confirms Argo CD content. | T7 | §1.8-§1.9 | S | pending |
