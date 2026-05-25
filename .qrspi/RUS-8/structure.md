# Structure Outline — Create a new agent skill called using argocd cli

**Design basis:** design.md @ 2026-05-25T23:00:00Z
**Generated:** 2026-05-25
**Status:** draft

## New Types

None. This is a content-only skill (Markdown prose and JSON eval definitions). No application types are introduced.

## Modified Types

None. No existing project code is modified.

## Contracts

- `SKILL.md frontmatter` — must contain `name: using-argocd-cli`, `description: <trigger string max 1024 chars>`, `command: using-argocd-cli`, `argument-hint: <hint>` (following project convention per Decision 3)
- `SKILL.md body → references/` pointer contract — body must include explicit conditional Read instructions for each of the six reference files (e.g., "When the user asks about sync strategies, read `references/sync-strategies.md`") so the consuming agent knows when to load detail
- `SKILL.md body` — must stay under 500 lines (target 350-450 per design)
- `references/*.md` — each file must be self-contained with a brief purpose header; files over 300 lines must include a table of contents (per skill-creator guidance)
- `evals/argocd-evals.json` — must follow the skill-creator eval format: `{ "skill_name": "using-argocd-cli", "evals": [{ "id", "prompt", "expected_output", "files", "assertions" }] }`; must include both `should_trigger: true` and `should_trigger: false` queries for trigger accuracy testing

## Slice 1: Author complete skill (SKILL.md + all references + eval file)

**Goal:** Deliver a fully functional `using-argocd-cli` skill at `.claude/skills/using-argocd-cli/` with valid frontmatter, body under 500 lines, six topic-split reference files, and a trigger-accuracy eval set — invocable via `/using-argocd-cli` and auto-triggered on ArgoCD CLI usage requests. Run skill-creator eval loop to validate trigger accuracy and skill quality.

**Files touched:**

- ✨ `.claude/skills/using-argocd-cli/SKILL.md` — Main skill definition: YAML frontmatter (`name`, `description`, `command`, `argument-hint`), prerequisites and authentication overview, core application lifecycle (create → get → diff → sync → monitor → rollback → delete), opinionated defaults with reasoning (manual sync for prod, Git revert over rollback, token auth, dry-run before sync), interactive vs CI/CD context sections (default interactive, CI/CD as delta), conditional pointers to all six reference files. Target 350-450 lines.
- ✨ `.claude/skills/using-argocd-cli/references/authentication.md` — Token-based auth, login flow, context management, core mode for headless environments, grpc-web for restricted networks, project-scoped role tokens, initial admin password change.
- ✨ `.claude/skills/using-argocd-cli/references/sync-strategies.md` — Manual vs automated sync, self-heal, auto-prune, dry-run workflow, sync waves and ordering, resource hooks (PreSync/Sync/PostSync/SyncFail), force sync and prune safety, apply-out-of-sync-only optimization.
- ✨ `.claude/skills/using-argocd-cli/references/rollback-procedures.md` — Git revert as primary rollback path with reasoning, emergency rollback with `argocd app rollback`, post-rollback Git reconciliation, deployment history inspection via `argocd app history`.
- ✨ `.claude/skills/using-argocd-cli/references/applicationsets.md` — Generator types (Git, Cluster, Matrix, List), preserveResourcesOnDeletion for production safety, transition criteria from app-of-apps to ApplicationSets (>20 apps or >3 clusters), CLI commands for listing and managing ApplicationSets.
- ✨ `.claude/skills/using-argocd-cli/references/rbac-configuration.md` — AppProject isolation, project-scoped roles with JWT tokens, deny-all default policy, production sync permission restrictions, role binding examples.
- ✨ `.claude/skills/using-argocd-cli/references/troubleshooting.md` — Diagnostic flowchart starting from `argocd app get`, branching by symptom to dry-run, terminate-op, resource inspection, log streaming, manifest comparison, hard-refresh.
- ✨ `evals/argocd-evals.json` — Trigger accuracy eval set: should-trigger queries (ArgoCD-specific operations) and should-not-trigger queries (kubectl, helm, flux, server installation). Follows skill-creator eval format.

**Verification:**

- [ ] `SKILL.md` has valid frontmatter with `name`, `description`, `command`, and `argument-hint` fields
- [ ] `SKILL.md` body is under 500 lines
- [ ] `SKILL.md` body contains conditional pointers to each of the six reference files with clear trigger conditions
- [ ] Each reference file has a purpose header and stays under 300 lines (or includes TOC if over)
- [ ] `evals/argocd-evals.json` is valid JSON matching the skill-creator eval schema
- [ ] Eval set includes at least 5 should-trigger and 3 should-not-trigger queries
- [ ] Should-not-trigger queries cover kubectl, helm, and flux to test trigger discrimination
- [ ] Opinionated defaults are stated with reasoning (not bare rules)
- [ ] CI/CD section describes deltas from the interactive default (not a parallel workflow)
- [ ] Escalation path flows: single-app → app-of-apps → ApplicationSets → multi-cluster, with advanced topics deferred to references
- [ ] Invoke skill-creator eval loop to validate trigger accuracy and overall skill quality

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

1. **`command` and `argument-hint` frontmatter fields work at runtime** — Decision 3 in design.md chose these fields for consistency with existing project skills, despite `quick_validate.py` rejecting them. We assume Claude Code's skill discovery mechanism (not `quick_validate.py`) is what matters. Cannot verify without testing.

2. **Six reference files do not degrade skill loading performance** — No existing project skill has more than one reference file (Q2). The design justifies six based on the ArgoCD CLI surface area and AC4 requirements. Whether Claude efficiently loads only the relevant file per query depends on the quality of SKILL.md pointers — there is no mechanism to test selective loading in isolation.

3. **Trigger description discriminates ArgoCD from kubectl/helm** — The eval set will test trigger accuracy, but cross-skill collision testing is a known gap (Q13). If other Kubernetes-related skills are added later, the trigger description may need retuning.

4. **ArgoCD CLI command syntax is stable across 2.x versions** — The skill will document ArgoCD CLI commands without pinning a version. If ArgoCD 3.x introduces breaking CLI changes, the skill content would need updating. The `compatibility` field could note this but was deemed unnecessary per current project convention (Q6).

5. **Skill-creator eval loop is runnable in this environment** — AC2 requires using the skill-creator's eval loop. This depends on `claude -p` CLI availability and subagent support (Q13). If the eval loop cannot run, trigger validation falls back to manual review of the eval set.
