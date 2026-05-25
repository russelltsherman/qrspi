# PR Summary — RUS-8

**PR Title:** RUS-8: Add using-argocd-cli agent skill with references and evals

## Summary

This PR adds a new `using-argocd-cli` agent skill to `.claude/skills/` that provides opinionated guidance for managing ArgoCD applications via the `argocd` CLI. The skill covers the full application lifecycle (create, sync, monitor, rollback, delete) with production-safety defaults, progressive disclosure from single-app to multi-cluster patterns, and context-aware guidance for interactive vs CI/CD workflows. Six reference files provide deep-dive material on authentication, sync strategies, rollback procedures, ApplicationSets, RBAC configuration, and troubleshooting. An eval set validates trigger accuracy with 11 test cases. Reviewer focus: verify the trigger description discriminates ArgoCD from kubectl/helm/flux, and check that SKILL.md conditional pointers to reference files are clear enough for selective loading.

## Acceptance Criteria Mapping

| # | Criterion | Implementation File | Test / Verification |
|---|-----------|-------------------|---------------------|
| AC1 | Skill follows agentskills.io directory structure with valid SKILL.md frontmatter | `.claude/skills/using-argocd-cli/SKILL.md` (lines 1-5: frontmatter with `name`, `description`, `command`, `argument-hint`) | impl-log.md: frontmatter check passed; 4/4 fields present |
| AC2 | Built using the Anthropic skill builder skill | `.claude/skills/using-argocd-cli/SKILL.md` (authored per skill-creator contracts) | impl-log.md: skill-creator eval loop skipped (cannot invoke `claude -p` recursively); content follows skill-creator patterns |
| AC3 | SKILL.md body under 500 lines / 5000 tokens | `.claude/skills/using-argocd-cli/SKILL.md` (379 lines) | impl-log.md: line count check passed (379 lines, target 350-450) |
| AC4 | Detailed reference material in `references/` directory | `references/authentication.md`, `references/sync-strategies.md`, `references/rollback-procedures.md`, `references/applicationsets.md`, `references/rbac-configuration.md`, `references/troubleshooting.md` | impl-log.md: 6 reference files verified, all under 300 lines (except troubleshooting.md at 319 with TOC per contract) |
| AC5 | Covers full application lifecycle: create, sync, monitor, rollback, delete | `.claude/skills/using-argocd-cli/SKILL.md` — "Core Application Lifecycle" section (steps 1-7) | impl-log.md: reference count check passed (6+ pointers) |
| AC6 | Encodes opinionated defaults (manual sync for prod, Git revert over rollback, token auth) | `.claude/skills/using-argocd-cli/SKILL.md` — "Opinionated Defaults Summary" table | impl-log.md: opinionated defaults check passed (4+ mentions) |
| AC7 | Includes guidance for both interactive and CI/CD contexts | `.claude/skills/using-argocd-cli/SKILL.md` — "Interactive Workflow" + "CI/CD Delta" sections | impl-log.md: CI/CD section check passed |
| AC8 | Provides escalation path from simple to complex patterns | `.claude/skills/using-argocd-cli/SKILL.md` — "Scaling Up" section (single-app -> app-of-apps -> ApplicationSets -> multi-cluster) | impl-log.md: escalation path check passed |

## Changes by Slice

### Slice 1: Author complete skill (SKILL.md + all references + eval file)

| File | Change Type | Lines |
|------|-------------|-------|
| `.claude/skills/using-argocd-cli/SKILL.md` | added | +379 |
| `.claude/skills/using-argocd-cli/references/authentication.md` | added | +178 |
| `.claude/skills/using-argocd-cli/references/sync-strategies.md` | added | +229 |
| `.claude/skills/using-argocd-cli/references/rollback-procedures.md` | added | +210 |
| `.claude/skills/using-argocd-cli/references/applicationsets.md` | added | +296 |
| `.claude/skills/using-argocd-cli/references/rbac-configuration.md` | added | +261 |
| `.claude/skills/using-argocd-cli/references/troubleshooting.md` | added | +319 |
| `evals/argocd-evals.json` | added | +136 |
| `.qrspi/RUS-8/design.md` | added | +135 |
| `.qrspi/RUS-8/impl-log.md` | added | +9 |
| `.qrspi/RUS-8/plan.md` | added | +126 |
| `.qrspi/RUS-8/questions.md` | added | +58 |
| `.qrspi/RUS-8/research.md` | added | +595 |
| `.qrspi/RUS-8/structure.md` | added | +67 |
| `.qrspi/RUS-8/worktree.md` | added | +125 |
| `.devcontainer/config/post-start.sh` | modified | +1 / -1 |

**Total: 16 files changed, +3124 / -1**

## Testing Summary

- [x] SKILL.md frontmatter contains all 4 required fields (`name`, `description`, `command`, `argument-hint`)
- [x] SKILL.md body is 379 lines (under 500-line cap, within 350-450 target)
- [x] SKILL.md body contains 6+ conditional Read pointers to reference files
- [x] 6 reference files present in `references/` directory
- [x] All reference files under 300 lines except `troubleshooting.md` (319 lines, includes TOC per contract allowance)
- [x] Each reference file has a purpose header
- [x] `evals/argocd-evals.json` is valid JSON
- [x] 11 evals total (7 should-trigger, 4 should-not-trigger) — exceeds minimum of 8
- [x] Should-not-trigger queries cover kubectl, helm install, flux, and k8s manifest authoring
- [x] Opinionated defaults stated with reasoning (not bare rules)
- [x] CI/CD section describes deltas from interactive default
- [x] Escalation path flows: single-app -> app-of-apps -> ApplicationSets -> multi-cluster
- [ ] Skill-creator eval loop — **not run** (requires `claude -p` which cannot be invoked recursively from within Claude Code)

## Deviations from Structure

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `troubleshooting.md` is 319 lines (exceeds 300-line soft limit) | Diagnostic flowchart requires branching coverage; includes TOC as specified by the contract for files over 300 lines | None — contract allows exceeding 300 if TOC is included |
| 4 should-not-trigger evals instead of minimum 3 | Added k8s manifest authoring as 4th discriminator for better trigger boundary coverage | Positive — more thorough trigger discrimination testing |
| Skill-creator eval loop (plan step 23) not executed | Cannot invoke `claude -p` recursively from within the running Claude Code session | AC2 partially met — skill content follows skill-creator patterns but trigger accuracy not machine-validated |
| `.devcontainer/config/post-start.sh` modified | Egress restriction `exit 0` line was commented out (unrelated infrastructure change already on branch) | No impact on skill deliverables |

## Risks & Rollback

| Risk | Design Likelihood | Design Impact | Implementation Finding |
|------|-------------------|---------------|----------------------|
| Trigger collision with kubectl/helm/flux prompts | Medium | Medium | Mitigated: description explicitly lists "Do NOT trigger for: kubectl commands, helm install/upgrade, flux operations, ArgoCD server installation, or general Kubernetes manifest authoring." 4 should-not-trigger evals cover these boundaries. Residual risk: untested with other skills loaded simultaneously. |
| SKILL.md body exceeds 500-line budget | High | Low | Resolved: final SKILL.md is 379 lines, well within budget. Aggressive offloading to 6 reference files kept the body lean. |
| Reference file pointers insufficiently directive | Medium | High | Mitigated: each pointer in SKILL.md includes both a conditional trigger ("When the user needs...") and the exact filename. Quality depends on Claude's adherence to conditional Read instructions — not testable in isolation. |
| Eval set misses edge-case trigger failures | Medium | Low | Partially mitigated: 11 evals (7 trigger, 4 non-trigger) with realistic prompts. Cross-skill collision testing remains a known gap — no mechanism exists in the project to test multiple skills simultaneously. |

**Rollback procedure:** Delete `.claude/skills/using-argocd-cli/` directory and `evals/argocd-evals.json`. No database migrations, config changes, or destructive operations. All files are net-new.

## Open Items

| Item | Type | Follow-up |
|------|------|-----------|
| Run skill-creator eval loop for trigger accuracy validation | Deferred from AC2 | Requires manual invocation of `claude -p` outside of a running Claude Code session |
| Cross-skill trigger collision testing | Tech debt | No infrastructure exists for testing multiple skills simultaneously; future risk if kubectl/helm skills are added |
| `command` and `argument-hint` frontmatter fields fail `quick_validate.py` | Known inconsistency | All 10 existing project skills have this same issue (design.md OQ1); batch-fix when validator is updated |
| `compatibility` field not used for `argocd` CLI dependency | Design decision | No existing skill uses this field; can be added later if convention is established (design.md OQ3) |
| `.devcontainer/config/post-start.sh` change on branch | Unrelated | Infrastructure change that comments out the egress bypass `exit 0`; should be reviewed separately or split to its own PR |
