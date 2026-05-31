# Structure Outline — Create a new agent skill called using argocd cli

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This ticket produces Markdown documents only; no code types are introduced.

- `SKILL.md frontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }` — declarative metadata required by the Claude Code runtime, matching the repo's existing five-field shape (ref: design.md §Pattern Decisions Decision 1).

## Modified Types

None. No existing files are modified.

## Contracts

The skill exposes one contract to the runtime and one to the user:

- `using-argocd-cli SKILL.md frontmatter` — must include `name: using-argocd-cli`, a description string whose first 80 characters trigger on argocd / Argo CD / GitOps / sync-and-rollback work, and `allowed-tools: Bash(argocd:*), Read` (ref: design.md §Decision 3).
- `references/<topic>.md` files — each is self-contained Markdown the SKILL.md body explicitly directs the agent to read on demand (ref: design.md §Decision 2). Inbound link from SKILL.md is the only contract; no schema.

There are no cross-slice interfaces because all files ship together as a single deliverable.

## Slice 1: Author the using-argocd-cli skill

**Goal:** Ship the complete `using-argocd-cli` skill — SKILL.md plus six reference files — that satisfies every acceptance criterion in the ticket. After this slice, an agent can be invoked on an argocd task and receive opinionated, lifecycle-complete guidance.

**Files touched:**

- ✨ `.claude/skills/using-argocd-cli/SKILL.md` — main skill body. Frontmatter (5 fields per repo convention), opinionated defaults summary, lifecycle overview (create → sync → monitor → rollback → delete), explicit "load reference X for topic Y" pointers, escalation guidance from single-app to app-of-apps to ApplicationSets to multi-cluster, interactive vs CI/CD context guidance. Hard cap: under 500 lines / 5000 tokens.
- ✨ `.claude/skills/using-argocd-cli/references/authentication.md` — token vs username/password, `ARGOCD_AUTH_TOKEN`, `ARGOCD_SERVER`, `ARGOCD_OPTS`, `--grpc-web`, `--core`, `argocd login`, `argocd context`, project-scoped role tokens via `argocd proj role create-token`, default admin password rotation.
- ✨ `.claude/skills/using-argocd-cli/references/sync-strategies.md` — manual vs automated sync, `--self-heal`/`--auto-prune` pairing, sync waves via `argocd.argoproj.io/sync-wave`, resource hooks (`PreSync`/`Sync`/`PostSync`/`SyncFail`), `--dry-run`, `--force`/`--prune` cautions, retry policies (staging vs prod backoff), `--apply-out-of-sync-only`.
- ✨ `.claude/skills/using-argocd-cli/references/rollback-procedures.md` — Git revert preferred; `argocd app rollback` for emergencies; automated-sync auto-disable behaviour after imperative rollback; `argocd app history` for picking the target revision; follow-up Git revert to restore GitOps consistency; PostSync hook for automated rollback on degraded health.
- ✨ `.claude/skills/using-argocd-cli/references/applicationset-generators.md` — Git, Cluster, Matrix, List generators; when to use each; DRY templating; `preserveResourcesOnDeletion: true` for production ApplicationSets; the >20-application or >3-cluster threshold for transitioning from app-of-apps.
- ✨ `.claude/skills/using-argocd-cli/references/rbac-configuration.md` — AppProjects scoping (source repos, destination clusters/namespaces, resource kinds); `argocd admin settings rbac validate` and `argocd admin settings rbac can` for testing; SSO group mapping; deny-by-default posture; explicit "never grant `applications, sync, *, */*`" warning.
- ✨ `.claude/skills/using-argocd-cli/references/troubleshooting.md` — flowchart starting at `argocd app get`; `--dry-run` previews; `argocd app terminate-op` for stuck syncs; resource health investigation with `argocd app resources` plus deferral to `kubectl describe`; `argocd app logs`; manifest diff (`--source live` vs `--source git`); `--hard-refresh`; `argocd repo list`/`argocd repo get` for repo connectivity.

**Verification:**

- [ ] `find .claude/skills/using-argocd-cli -type f` lists exactly 7 files: SKILL.md and six references.
- [ ] `wc -l .claude/skills/using-argocd-cli/SKILL.md` reports ≤ 500.
- [ ] Token count of SKILL.md body (estimated by `wc -w` * 1.3) is < 5000.
- [ ] `head -10 .claude/skills/using-argocd-cli/SKILL.md` shows valid frontmatter with all five fields and `name: using-argocd-cli`.
- [ ] SKILL.md body contains explicit "read references/<topic>.md" pointers for all six topic files.
- [ ] SKILL.md body contains an opinionated-defaults section that encodes: manual sync for prod, Git revert over imperative rollback, token auth over password.
- [ ] SKILL.md body covers the full lifecycle (create / sync / monitor / rollback / delete) by name.
- [ ] SKILL.md body contains separate guidance blocks for interactive developer use and CI/CD automation.
- [ ] SKILL.md body documents the >20-application or >3-cluster threshold for ApplicationSets.
- [ ] skill-creator skill validates the structure with no errors (manual invocation during implementation).
- [ ] Spot-check: invoking the skill on a representative prompt ("how do I roll back app foo to last week's revision?") produces guidance consistent with the references.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **skill-creator scope.** design.md §OQ3 flags that invoking skill-creator inside the worktree must write only inside the worktree path. If skill-creator insists on writing to `~/.claude/skills/`, implementation must stop and report (HARD STOP per project convention). The assumption that skill-creator can be pointed at an arbitrary path needs verification in the first action of Slice 1.
- **frontmatter shape compatibility.** design.md §Decision 1 assumes the repo's five-field frontmatter is compatible with the agentskills.io standard skill-creator expects. If skill-creator demands additional fields (e.g., `version`, `model`, `license`), the implementation must reconcile before declaring the slice done.
- **`command:` declaration.** design.md §OQ1 leaves it open whether the skill needs a `/<name>` slash command. Implementation will default to declaring `command: /using-argocd-cli` to match every other skill in the repo and to allow explicit invocation, unless skill-creator's validation rejects it.
- **Bash tool restriction syntax.** design.md §Decision 3 assumes `Bash(argocd:*)` is valid syntax matching the `Bash(pwd:*)` precedent. If the runtime rejects glob-prefixed restrictions for argocd, fall back to `Bash` with an explicit usage warning in the body.
- **Token / line counting.** The 500-line / 5000-token ceiling is enforced informally; no project tooling measures tokens. The verification step uses `wc -w * 1.3` as a rough approximation. If precise tokenization matters, this needs a follow-up.
