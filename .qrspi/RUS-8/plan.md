# Implementation Plan — Create a new agent skill called using argocd cli

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 23

## Slice 1: Author the using-argocd-cli skill

### Setup

1. Verify skill-creator availability and scope. From the worktree root, confirm the global skill-creator skill is visible in this session's skill list (it appears in the available-skills system reminder). Confirm it will accept a target output directory inside the worktree — if it cannot be pointed at the worktree, HARD STOP per project convention and document in impl-log. (ref: structure.md §Unverified Assumptions)
2. Verify no existing directory at `.claude/skills/using-argocd-cli/`. If one exists, HARD STOP and report — do not overwrite.
3. ✨ Create `.claude/skills/using-argocd-cli/` directory.
4. ✨ Create `.claude/skills/using-argocd-cli/references/` directory.

### Core Logic — SKILL.md

5. ✨ Invoke the skill-creator skill (Skill tool with `skill: "skill-creator"`) to scaffold the SKILL.md frontmatter and body skeleton. Pass the skill name (`using-argocd-cli`), the ticket's authoritative description, and the target path `.claude/skills/using-argocd-cli/SKILL.md`. If skill-creator writes files outside the worktree, HARD STOP. (ref: structure.md §Unverified Assumptions, design.md §Decision 1)
6. ✨ Edit `.claude/skills/using-argocd-cli/SKILL.md` frontmatter so it contains exactly five fields matching the repo convention plus any fields skill-creator requires. Required values:
   - **After:** `name: using-argocd-cli`
   - **After:** `description:` — single-paragraph description (~70-150 words) that triggers on argocd CLI, Argo CD, GitOps deployment, sync, rollback, ApplicationSet, app-of-apps, RBAC, multi-cluster work. Mention the skill is opinionated (manual sync for prod, Git revert over imperative rollback, token auth).
   - **After:** `command: /using-argocd-cli`
   - **After:** `argument-hint: <argocd task>`
   - **After:** `allowed-tools: Bash(argocd:*), Read`
7. ✨ Write the SKILL.md body. Required sections, in order:
   - "## When to use" — short triggers list.
   - "## Opinionated defaults" — bulleted summary: manual sync for prod, automated sync only with `--self-heal` + `--auto-prune`, declarative Application manifests over imperative `argocd app create`, token auth via `ARGOCD_AUTH_TOKEN`, project-scoped role tokens for CI/CD, Git revert preferred over `argocd app rollback`, deny-by-default RBAC.
   - "## Lifecycle at a glance" — five subsections: Create, Sync, Monitor, Rollback, Delete. Each lists 2-4 essential commands and points to the relevant reference file.
   - "## Interactive developer use" — `argocd login`, `argocd context`, environment variables, when to use `--grpc-web`.
   - "## CI/CD automation" — token auth, Core mode (`--core`), project-scoped roles, avoiding admin tokens, retry policies appropriate to environment.
   - "## Escalation: single app → app-of-apps → ApplicationSets → multi-cluster" — short prose with the >20-application or >3-cluster threshold for transitioning to ApplicationSets explicitly stated.
   - "## References" — bullet list pointing each topic to its `references/<topic>.md` with one-line summary.
   - "## When to defer" — explicit list of out-of-scope work (ArgoCD server install/upgrade → Helm/kustomize skills; Kubernetes resource authoring → kubectl/Helm skills; CI pipeline config → CI-specific skills).
8. ✨ Sanity check the SKILL.md body length immediately after writing: run `wc -l .claude/skills/using-argocd-cli/SKILL.md`. If > 500, trim until it fits, moving overflow into the appropriate reference file. (ref: structure.md §Slice 1 Verification)

### Core Logic — references

9. ✨ Create `.claude/skills/using-argocd-cli/references/authentication.md`. Cover (in order): token vs username/password (token wins for automation), `ARGOCD_SERVER`/`ARGOCD_AUTH_TOKEN`/`ARGOCD_OPTS` env vars, `--grpc-web` flag for ingress/load-balancers without HTTP/2, `--core` mode for in-cluster automation, `argocd login <server>` and `argocd context` for interactive multi-instance work, project-scoped role tokens via `argocd proj role create-token <project> <role>`, mandatory default-admin-password rotation. Include the explicit warning: "never grant `applications, sync, *, */*`".
10. ✨ Create `.claude/skills/using-argocd-cli/references/sync-strategies.md`. Cover: manual sync default for production; automated sync paired with `--self-heal` and `--auto-prune`; `--dry-run` previews; sync waves via the `argocd.argoproj.io/sync-wave` annotation (negatives first for namespaces/CRDs, 0 for infrastructure, positives for apps); resource hooks (`PreSync`, `Sync`, `PostSync`, `SyncFail`); `--force` and `--prune` cautions including the "never combine in production without explicit confirmation" rule; retry policies (staging aggressive 1×5s, prod conservative 5×30s exponential); `--apply-out-of-sync-only` for partial syncs.
11. ✨ Create `.claude/skills/using-argocd-cli/references/rollback-procedures.md`. Cover: Git revert as the preferred path (keeps Git as single source of truth); `argocd app rollback <app>` for emergencies only; the auto-disable-of-automated-sync behaviour after imperative rollback; using `argocd app history <app>` to pick the target revision; mandatory follow-up Git revert after imperative rollback to restore GitOps consistency; PostSync hook for automated rollback on degraded health.
12. ✨ Create `.claude/skills/using-argocd-cli/references/applicationset-generators.md`. Cover: app-of-apps pattern (single root Application pointing to a directory of Application manifests; centralised lifecycle for related apps); when to transition to ApplicationSets (>20 applications or >3 clusters); Git generator (per-directory apps in a monorepo); Cluster generator (same app across many clusters); Matrix generator (combinatorial e.g. Git × Cluster); List generator (explicit control); DRY templating; `preserveResourcesOnDeletion: true` for production ApplicationSets.
13. ✨ Create `.claude/skills/using-argocd-cli/references/rbac-configuration.md`. Cover: AppProjects to isolate teams (restrict source repos, destination clusters/namespaces, allowed resource kinds); project-scoped JWT role tokens via `argocd proj role create-token`; validating policies with `argocd admin settings rbac validate`; testing with `argocd admin settings rbac can <role> <action> <resource>`; SSO group → role mapping for scale; deny-by-default with incremental grants; explicit warning never to grant `applications, sync, *, */*` in production.
14. ✨ Create `.claude/skills/using-argocd-cli/references/troubleshooting.md`. Cover: a flowchart-style top-down sequence starting at `argocd app get <app>`; `argocd app sync <app> --dry-run` for previewing changes; `argocd app terminate-op <app>` for stuck syncs; `argocd app resources <app>` plus follow-up `kubectl describe`; `argocd app logs <app>` for container logs; manifest diff with `--source live` vs `--source git`; `argocd app get <app> --hard-refresh` for stale caches; `argocd repo list` and `argocd repo get <url>` for repo connectivity.

### Validation

15. Run skill-creator validation pass on the completed skill if the skill exposes a validation step (e.g., its eval mode). If skill-creator only scaffolds and does not validate post-hoc, skip and rely on the manual checks below. Document the outcome in impl-log.
16. Manual smoke prompt: as a thought experiment, write into impl-log how the skill would direct the agent for two test prompts: "How do I roll back app foo to last week's revision?" and "How should I set up an ApplicationSet for 30 microservices across staging and prod clusters?". Confirm the SKILL.md body plus the relevant reference files give a coherent answer. If either gap is found, add a fix step.

### Verify Slice 1

17. **Checkpoint:** `find .claude/skills/using-argocd-cli -type f | sort`
    - [ ] Output lists exactly 7 files: `SKILL.md`, `references/authentication.md`, `references/sync-strategies.md`, `references/rollback-procedures.md`, `references/applicationset-generators.md`, `references/rbac-configuration.md`, `references/troubleshooting.md`.
18. **Checkpoint:** `wc -l .claude/skills/using-argocd-cli/SKILL.md`
    - [ ] Reports a number ≤ 500.
19. **Checkpoint:** `head -10 .claude/skills/using-argocd-cli/SKILL.md`
    - [ ] Shows valid YAML frontmatter with `name: using-argocd-cli`, `command: /using-argocd-cli`, and `allowed-tools` starting with `Bash(argocd:*)`.
20. **Checkpoint:** `grep -c "references/" .claude/skills/using-argocd-cli/SKILL.md`
    - [ ] Reports at least 6 (one pointer per reference file).
21. **Checkpoint:** `grep -i "manual sync.*prod\|prod.*manual sync" .claude/skills/using-argocd-cli/SKILL.md` AND `grep -i "git revert" .claude/skills/using-argocd-cli/SKILL.md` AND `grep -i "ARGOCD_AUTH_TOKEN\|token.*auth" .claude/skills/using-argocd-cli/SKILL.md`
    - [ ] All three return at least one match — confirms the opinionated defaults are encoded.
22. **Checkpoint:** `grep -E "20|twenty" .claude/skills/using-argocd-cli/SKILL.md && grep -E "3|three" .claude/skills/using-argocd-cli/SKILL.md`
    - [ ] Both grep — confirms the >20-application / >3-cluster ApplicationSets threshold is documented.
23. **Checkpoint:** Cross-read SKILL.md and confirm it explicitly covers create, sync, monitor, rollback, delete by name.
    - [ ] All five lifecycle phases referenced in the body.

---

## Rollback Notes

- Steps 3–14 (file creation): If the slice must be reverted, `git restore --staged .claude/skills/using-argocd-cli/ && rm -rf .claude/skills/using-argocd-cli/` returns the worktree to a clean state. No upstream files are touched, so rollback is purely local.
- Step 5 (skill-creator invocation): If skill-creator writes outside the worktree (which would trigger HARD STOP), the implementation must report and exit. Any state skill-creator left in `~/.claude/` must be reported to Russell — do not attempt to clean it up automatically (project HARD STOP rule).
