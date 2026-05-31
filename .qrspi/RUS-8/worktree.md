# Work Tree — Create a new agent skill using argocd CLI

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T7 → T13 → T14 → T15 → T16 → T22

> Notes:
> - All paths assume the recommended skill name `using-argocd-cli` (OQ1). If the human picks a different name in T1, every path below changes accordingly.
> - The deliverable is a `SKILL.md` prompt artifact plus `references/` markdown — not executable code. Verification is structural (directory shape, frontmatter fields, line count, pointer reachability); no linter/validator/token-counter exists in-repo.
> - Slice 2 (Session 3) is **optional** and gated on human confirmation (OQ3). Do not begin it unless confirmed.

## Session 1 — Slice 1: scaffold + SKILL.md frontmatter and body

**Load:** plan.md §Slice 1 (Setup + Core Logic SKILL.md body, steps 1–15), structure.md §New Types (SkillFrontmatter), structure.md §Contracts (body→reference pointers, Tooling), design.md §Decisions 1–4 + §Risk Register rows 2/5
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Pre-flight: resolve OQ1 (name `using-argocd-cli`), OQ2 (skill-creator availability), OQ4 (`Bash(kubectl:*)` scope) with human; record resolved name | — | §1 | S | pending |
| T2 | Create `.claude/skills/using-argocd-cli/` and `.../references/` directories (agentskills.io shape) | T1 | §2 | S | pending |
| T3 | Create `SKILL.md` with frontmatter only (name, description, command, argument-hint, allowed-tools) | T2 | §3 | M | pending |
| T4 | Add body section "When to use / out of scope" | T3 | §4 | S | pending |
| T5 | Add body section "Authentication" (interactive vs CI/CD blocks + pointer) | T3 | §5 | M | pending |
| T6 | Add body section "Create application" | T3 | §6 | S | pending |
| T7 | Add body section "Diff & sync" (decision table + pointer) | T3 | §7 | M | pending |
| T8 | Add body section "Monitor" | T3 | §8 | S | pending |
| T9 | Add body section "Rollback" (do/don't + pointer) | T3 | §9 | S | pending |
| T10 | Add body section "Delete" (cascade/finalizer caution) | T3 | §10 | S | pending |
| T11 | Add body section "Escalation: simple → multi-cluster" (decision table + pointer) | T3 | §11 | M | pending |
| T12 | Add body section "RBAC & permissions" (pointer) | T3 | §12 | S | pending |
| T13 | Add body section "Troubleshooting" (pointer) | T3 | §13 | S | pending |
| T14 | Add "HARD STOP" block (forbidden-without-confirmation actions) | T3 | §14 | S | pending |
| T15 | Add "Defaults (do/don't)" list (manual sync, git revert, token auth) | T3 | §15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body complete (~15 sections). Fresh context before authoring the six self-contained reference files, which each carry distinct domain detail and would inflate the body-authoring session past 40%.

## Session 2 — Slice 1: reference files + structural verification

**Load:** plan.md §Slice 1 (Core Logic references/ + Tests/Structural verification, steps 16–28), structure.md §Contracts (body→reference pointer mapping), design.md §Decision 2 (pointer pattern), impl-log.md §Slice 1 (SKILL.md pointer wording — to match references to pointers exactly)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Create `references/authentication.md` (self-contained; reachable by T5 pointer) | T5 | §16 | M | pending |
| T17 | Create `references/sync-strategies.md` (self-contained; reachable by T7 pointer) | T7 | §17 | M | pending |
| T18 | Create `references/rollback.md` (self-contained; reachable by T9 pointer) | T9 | §18 | M | pending |
| T19 | Create `references/applicationsets.md` (self-contained; reachable by T11 pointer) | T11 | §19 | M | pending |
| T20 | Create `references/rbac.md` (self-contained; reachable by T12 pointer) | T12 | §20 | M | pending |
| T21 | Create `references/troubleshooting.md` (self-contained; reachable by T13 pointer) | T13 | §21 | M | pending |
| T22 | Verify file shape: `test -f SKILL.md && ls references/` (6 files present) | T16, T17, T18, T19, T20, T21 | §22 | S | pending |
| T23 | Verify body length: `wc -l SKILL.md` < 500 lines | T22 | §23 | S | pending |
| T24 | Verify pointers: `grep -c 'references/'` == 6 (no dangling/orphan) | T22 | §24 | S | pending |
| T25 | Verify guidance formats: ≥1 decision table, ≥1 do/don't list, ≥1 HARD STOP block | T22 | §25 | S | pending |
| T26 | Manual review: frontmatter + auth blocks vs existing skill (e.g. `qrspi-work`) | T22 | §26 | S | pending |
| T27 | If skill-creator used (per T1/OQ2): run its eval loop; else note criterion partially met | T22 | §27 | S | pending |
| T28 | **Verify Slice 1** checkpoint: shape + 6 refs + <500 lines + frontmatter + formats + auth blocks + description pattern | T23, T24, T25, T26, T27 | §28 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Slice 2 is optional (gated on OQ3) and touches a different area of the codebase (`evals/suite.json`, `scripts/grade.py`) requiring fresh inspection of unverified file shapes — clean context avoids carrying SKILL-authoring detail into eval work.

## Session 3 (optional) — Slice 2: add an eval case

**Load:** plan.md §Slice 2 (steps 29–31), plan.md §Rollback Notes (steps 29–30), structure.md §Slice 2 + §Unverified Assumptions, design.md §Risk Register row 4 (eval stub returns empty output)
**Estimated context:** ~20% of window

> Only execute if the human confirms (OQ3). The eval execution layer is a stub returning empty output, so end-to-end scores cannot be produced today — this slice only makes the case parse and register for future use.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T29 | Inspect existing case shape, then modify `evals/suite.json`: add ≥1 case targeting `using-argocd-cli` (+ any fixture) | T28 | §29 | M | pending |
| T30 | Modify `scripts/grade.py` `CHECKS` registry only if a new check is needed; create fixtures if required | T29 | §30 | M | pending |
| T31 | **Verify Slice 2** checkpoint: OQ3 confirmed; case parses as valid JSON; new check registered+referenced; harness loads case without error | T29, T30 | §31 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of work tree. Slice 2 is the final slice; on completion proceed to the PR phase.
