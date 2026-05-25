# Worktree — Create a new agent skill called using argocd cli

**Plan basis:** plan.md @ 2026-05-25
**Generated:** 2026-05-25
**Status:** draft

## Critical Path

T1 → T2 → T3..T8 (parallel) → T9 → T10 → T11

Tasks T3–T8 (reference files) can run in parallel since they are independent, but T2 (SKILL.md) must complete first because it defines the conditional pointers that reference files must satisfy. T9 (evals) depends on knowing the exact skill name and file paths established in T1–T2. T10 (validation) depends on all content files. T11 (skill-creator eval loop) depends on T10 passing.

---

## Session 1: Skill skeleton and main SKILL.md

**Load manifest:**
- `structure.md` — Contracts section
- `plan.md` — Steps 1–2
- `design.md` — Desired End State, Decisions 1–6

**Estimated context:** ~15%

### Tasks

| ID  | Description | Depends On | Plan Step | Cost | Status |
|-----|-------------|------------|-----------|------|--------|
| T1  | Create directory `.claude/skills/using-argocd-cli/references/` | — | 1 | S | pending |
| T2  | Create `.claude/skills/using-argocd-cli/SKILL.md` with YAML frontmatter (`name`, `description`, `command`, `argument-hint`), body sections (prerequisites, core lifecycle, opinionated defaults with reasoning, interactive workflow, CI/CD delta, escalation path, conditional Read pointers to all six reference files). Target 350–450 lines, hard cap 500. | T1 | 2 | L | pending |

---

### SESSION BOUNDARY

**Reason:** SKILL.md is the largest single artifact (L cost, 350–450 lines of dense technical content). Completing it before reference files ensures the conditional pointer contracts are established, and keeps context clean for the next batch of medium-cost writes.

---

## Session 2: Reference files (batch 1 — auth, sync, rollback)

**Load manifest:**
- `structure.md` — Contracts section (`references/*.md` contract only)
- `plan.md` — Steps 3–5
- `.claude/skills/using-argocd-cli/SKILL.md` — conditional pointer sections only (to verify alignment)

**Estimated context:** ~20%

### Tasks

| ID  | Description | Depends On | Plan Step | Cost | Status |
|-----|-------------|------------|-----------|------|--------|
| T3  | Create `references/authentication.md` — token auth, login flow, context management, core mode, grpc-web, project-scoped tokens, admin password change. Self-contained with purpose header, under 300 lines. | T2 | 3 | M | pending |
| T4  | Create `references/sync-strategies.md` — manual vs automated sync, self-heal, auto-prune, dry-run workflow, sync waves, resource hooks, force sync safety, apply-out-of-sync-only. Self-contained with purpose header, under 300 lines. | T2 | 4 | M | pending |
| T5  | Create `references/rollback-procedures.md` — Git revert as primary path with reasoning, emergency rollback, post-rollback Git reconciliation, deployment history inspection. Self-contained with purpose header, under 300 lines. | T2 | 5 | M | pending |

---

### SESSION BOUNDARY

**Reason:** Three reference files at M cost each bring estimated context to ~20%. Splitting references into two batches of three keeps each session well under the 40% ceiling and avoids quality degradation from context pressure on technical prose.

---

## Session 3: Reference files (batch 2 — appsets, RBAC, troubleshooting)

**Load manifest:**
- `structure.md` — Contracts section (`references/*.md` contract only)
- `plan.md` — Steps 6–8
- `.claude/skills/using-argocd-cli/SKILL.md` — conditional pointer sections only (to verify alignment)

**Estimated context:** ~20%

### Tasks

| ID  | Description | Depends On | Plan Step | Cost | Status |
|-----|-------------|------------|-----------|------|--------|
| T6  | Create `references/applicationsets.md` — generator types (Git, Cluster, Matrix, List), preserveResourcesOnDeletion, transition criteria (>20 apps or >3 clusters), CLI commands. Self-contained with purpose header, under 300 lines. | T2 | 6 | M | pending |
| T7  | Create `references/rbac-configuration.md` — AppProject isolation, project-scoped roles with JWT, deny-all default, production sync restrictions, role binding examples. Self-contained with purpose header, under 300 lines. | T2 | 7 | M | pending |
| T8  | Create `references/troubleshooting.md` — diagnostic flowchart from `argocd app get`, branching by symptom to dry-run, terminate-op, resource inspection, log streaming, manifest comparison, hard-refresh. Self-contained with purpose header, under 300 lines. | T2 | 8 | M | pending |

---

### SESSION BOUNDARY

**Reason:** All content files complete. Next session switches from content authoring to eval authoring and validation — a different cognitive mode. Clean context avoids cross-contamination between prose writing and structured JSON + shell validation.

---

## Session 4: Eval file, validation, and skill-creator eval loop

**Load manifest:**
- `structure.md` — Contracts section (`evals/argocd-evals.json` contract only)
- `plan.md` — Steps 9–23
- `.claude/skills/using-argocd-cli/SKILL.md` — frontmatter only (for skill_name alignment)

**Estimated context:** ~25%

### Tasks

| ID  | Description | Depends On | Plan Step | Cost | Status |
|-----|-------------|------------|-----------|------|--------|
| T9  | Create `evals/argocd-evals.json` — at least 5 should-trigger queries (sync, rollback, app creation, health check, diff) and at least 3 should-not-trigger queries (kubectl, helm, flux). Realistic user prompts, skill-creator eval format. | T2 | 9 | M | pending |
| T10 | Run all validation checks (plan steps 10–22): SKILL.md line count < 500, frontmatter fields present, reference pointers >= 6, each reference file under 300 lines with purpose header, eval JSON valid, eval count >= 8 with required fields, opinionated defaults present, CI/CD section exists, escalation path present, exactly 6 reference files, checkpoint script. Fix any failures. | T3, T4, T5, T6, T7, T8, T9 | 10–22 | M | pending |
| T11 | Invoke skill-creator eval loop to validate trigger accuracy and overall skill quality. | T10 | 23 | M | pending |

---

## Task Dependency Graph

```
T1 ─→ T2 ─┬→ T3 ─┐
           ├→ T4 ─┤
           ├→ T5 ─┤
           ├→ T6 ─┤
           ├→ T7 ─┤
           ├→ T8 ─┤
           └→ T9 ─┴→ T10 ─→ T11
```

## Summary

- **Total tasks:** 11
- **Total sessions:** 4
- **Critical path length:** 5 (T1 → T2 → T3..T8 → T10 → T11)
- **Max parallelism:** 7 (T3–T9 can all run concurrently, but grouped into sessions of 3 for context budget)
