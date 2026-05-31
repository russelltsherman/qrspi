# Implementation Plan — Create a new agent skill using argocd CLI

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 31

> Note: This deliverable is a Claude Code `SKILL.md` prompt artifact plus `references/` markdown, not executable code. "Atomic step = one file, one action" applies to authoring each markdown file and section. Verification is structural (directory shape, frontmatter fields, line count, pointer/reference reachability) since the repo has no frontmatter linter, structure validator, or token counter (ref: design Risk Register, structure §Unverified Assumptions). All file paths assume the recommended name `using-argocd-cli` (OQ1); if the human picks a different name, every path below changes accordingly.

## Slice 1: Author the `using-argocd-cli` skill (body + references)

### Setup

1. **Pre-flight (OQ1, OQ2, OQ4):** Confirm with the human three open decisions before authoring: (a) skill name `using-argocd-cli` (OQ1); (b) whether the global `skill-creator` skill is invocable and required (OQ2) — if absent, hand-author to in-repo conventions and flag the "built using skill builder" criterion as partially met; (c) `allowed-tools` includes scoped `Bash(kubectl:*)` (OQ4). Record the resolved name; it is the basis for every path below.

2. ✨ Create directory `.claude/skills/using-argocd-cli/` and `.claude/skills/using-argocd-cli/references/` — establishes the `agentskills.io` directory shape: `name == directory == command-without-slash` (ref: structure Naming contract; design Decision 1).

### Core Logic — SKILL.md body

3. ✨ Create `.claude/skills/using-argocd-cli/SKILL.md` with frontmatter only — fields per the `SkillFrontmatter` contract (ref: structure §New Types):
   - `name: using-argocd-cli` (kebab-case, == directory)
   - `description:` purpose + concrete user phrase + trigger variants + explicit out-of-scope language (ref: design Risk Register row 5; structure verify item 7)
   - `command: /using-argocd-cli`
   - `argument-hint:` (e.g. `<app-name or natural-language argocd request>`)
   - `allowed-tools: Bash(argocd:*), Bash(kubectl:*), Read` (ref: structure Tooling contract; design Decision 3 — adjust per OQ4 resolution)

4. ✨ Add body section "When to use / out of scope" to `SKILL.md` — reinforces the trigger surface and states what this skill does NOT cover (non-argocd k8s automation), per design Risk Register row 5.

5. ✨ Add body section "Authentication" to `SKILL.md` — distinct interactive block (`argocd login` / `argocd context`) vs CI/CD block (`ARGOCD_AUTH_TOKEN` / `--core`); ends with a one-line pointer: `Read references/authentication.md for token vs password, --grpc-web, and project-scoped role tokens.` (ref: structure body→authentication contract; design Decision 2 pointer pattern).

6. ✨ Add body section "Create application" to `SKILL.md` — opinionated create flow (declarative manifest preferred); covers the create lifecycle stage (ref: design §Desired End State "Full lifecycle").

7. ✨ Add body section "Diff & sync" to `SKILL.md` — decision table for manual-sync-for-prod vs automated; one-line pointer: `Read references/sync-strategies.md for self-heal, sync waves, hooks, retry, and --force/--prune cautions.` (ref: structure body→sync-strategies contract).

8. ✨ Add body section "Monitor" to `SKILL.md` — app health/status inspection commands; covers the monitor lifecycle stage (ref: design §Desired End State "Full lifecycle").

9. ✨ Add body section "Rollback" to `SKILL.md` — do/don't list encoding "Git revert over imperative rollback" default; one-line pointer: `Read references/rollback.md for git revert vs argocd app rollback, history inspection, and auto-rollback-on-degraded.` (ref: structure body→rollback contract; design Decision 4).

10. ✨ Add body section "Delete" to `SKILL.md` — safe delete flow with cascade/finalizer caution; covers the delete lifecycle stage (ref: design §Desired End State "Full lifecycle").

11. ✨ Add body section "Escalation: simple → multi-cluster" to `SKILL.md` — decision table routing app-of-apps vs ApplicationSets (>20 apps or >3 clusters); one-line pointer: `Read references/applicationsets.md for generators (Git/Cluster/Matrix/List), app-of-apps, and preserveResourcesOnDeletion.` (ref: structure body→applicationsets contract; design §Desired End State escalation).

12. ✨ Add body section "RBAC & permissions" to `SKILL.md` — one-line pointer: `Read references/rbac.md for AppProjects, JWT role tokens, rbac validate/can, SSO mapping, and the deny-all default.` (ref: structure body→rbac contract).

13. ✨ Add body section "Troubleshooting" to `SKILL.md` — one-line pointer: `Read references/troubleshooting.md for the debugging flowchart, terminate-op, hard refresh, live-vs-git manifests, repo connectivity, and scoped kubectl describe/logs follow-ups.` (ref: structure body→troubleshooting contract).

14. ✨ Add "HARD STOP" block to `SKILL.md` — bold escalation block listing explicitly forbidden-without-confirmation actions: jumping to `--force` / `--prune`, auth/cluster-access failures, and sync failures (ref: design Decision 4; structure verify item 6; repo HARD STOP format from research Q11).

15. ✨ Add "Defaults (do / don't)" do/don't list to `SKILL.md` — encodes the three opinionated defaults as a numbered do/don't list: manual sync for prod, Git revert over imperative rollback, token auth over password (ref: design Decision 4; structure verify item 6).

### Core Logic — references/

16. ✨ Create `.claude/skills/using-argocd-cli/references/authentication.md` — self-contained: token vs password, env vars (`ARGOCD_AUTH_TOKEN`), `--core`, `--grpc-web`, context management, project-scoped role tokens (ref: structure body→authentication contract). Reachable by exactly the pointer from step 5.

17. ✨ Create `.claude/skills/using-argocd-cli/references/sync-strategies.md` — self-contained: manual vs automated, self-heal/auto-prune, sync waves, hooks, retry policies, `--force`/`--prune` cautions (ref: structure body→sync-strategies contract). Reachable by exactly the pointer from step 7.

18. ✨ Create `.claude/skills/using-argocd-cli/references/rollback.md` — self-contained: Git revert vs `argocd app rollback`, history inspection, automated-rollback-on-degraded (ref: structure body→rollback contract). Reachable by exactly the pointer from step 9.

19. ✨ Create `.claude/skills/using-argocd-cli/references/applicationsets.md` — self-contained: generators (Git, Cluster, Matrix, List), app-of-apps, `preserveResourcesOnDeletion` (ref: structure body→applicationsets contract). Reachable by exactly the pointer from step 11.

20. ✨ Create `.claude/skills/using-argocd-cli/references/rbac.md` — self-contained: AppProjects, JWT role tokens, `rbac validate`/`can`, SSO mapping, deny-all default (ref: structure body→rbac contract). Reachable by exactly the pointer from step 12.

21. ✨ Create `.claude/skills/using-argocd-cli/references/troubleshooting.md` — self-contained: debugging flowchart, `terminate-op`, hard refresh, manifests live-vs-git, repo connectivity, scoped `kubectl describe` / logs follow-ups (ref: structure body→troubleshooting contract). Reachable by exactly the pointer from step 13.

### Tests / Structural verification

22. Run: `test -f .claude/skills/using-argocd-cli/SKILL.md && ls .claude/skills/using-argocd-cli/references/`
    - **Expected:** SKILL.md exists; all six reference files listed (`authentication.md`, `sync-strategies.md`, `rollback.md`, `applicationsets.md`, `rbac.md`, `troubleshooting.md`).

23. Run: `wc -l .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** body under 500 lines (manual count; 5000-token figure is approximate — no in-repo token counter, ref: structure verify item 4 / design Risk Register row 2).

24. Run: `grep -c 'references/' .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** exactly 6 one-line pointers, one per reference file — no dangling pointers, no orphan references (ref: structure verify item 5).

25. Run: `grep -iE 'HARD STOP|do.?n.?t|don.t' .claude/skills/using-argocd-cli/SKILL.md` and visually confirm ≥1 markdown decision table (`|---|`)
    - **Expected:** all three guidance formats present — ≥1 decision table, ≥1 do/don't list, ≥1 HARD STOP block (ref: structure verify item 6).

26. **Manual review** of `SKILL.md` frontmatter and the interactive-vs-CI/CD auth blocks against an existing skill (e.g. `qrspi-work`'s SKILL.md) — confirm field shape matches in-repo convention and both auth contexts are distinct (ref: structure verify items 3, 8). No automated linter exists (design Q13).

27. **If `skill-creator` was used (per step 1 / OQ2):** run its eval loop per the skill-creator workflow as the final authoring validation (ref: structure verify item 9). If hand-authored, skip and note the criterion as partially met.

### Verify Slice 1

28. **Checkpoint:** `test -f .claude/skills/using-argocd-cli/SKILL.md && [ "$(ls .claude/skills/using-argocd-cli/references/ | wc -l)" -eq 6 ] && [ "$(wc -l < .claude/skills/using-argocd-cli/SKILL.md)" -lt 500 ]`
    - [ ] Directory shape `.claude/skills/<name>/SKILL.md` + `references/`; name == directory == command-without-slash.
    - [ ] Frontmatter carries `name`, `description`, `command`, `argument-hint`, `allowed-tools`; `allowed-tools` scoped to `Bash(argocd:*)`, `Bash(kubectl:*)`, `Read`.
    - [ ] SKILL.md body under 500 lines.
    - [ ] All six reference files exist, are self-contained, each reachable by exactly one pointer (no dangling/orphan).
    - [ ] Body has ≥1 decision table, ≥1 do/don't list, ≥1 HARD STOP block.
    - [ ] Body has distinct interactive and CI/CD auth blocks.
    - [ ] `description` follows purpose + concrete-phrase + trigger-variants + out-of-scope pattern.
    - [ ] (If `skill-creator` used) eval loop run; else criterion flagged partially met.

---

## Slice 2 (optional): Add an eval case for the skill

> Only execute this slice if the human confirms (OQ3). The eval execution layer is a stub that returns empty output, so end-to-end scores cannot be produced today — this slice only makes the case parse and register for future use (ref: structure §Slice 2 verify item 1; design Q12).

### Setup

29. ⚠️ Modify `evals/suite.json` — add ≥1 hand-curated case targeting the `using-argocd-cli` skill.
    - **Current:** suite.json contains existing cases only (no `using-argocd-cli` case).
    - **After:** suite.json contains a new valid-JSON case referencing the new skill and any required fixture. Verify the existing case shape before editing — the structure phase did not read `evals/suite.json` directly (ref: structure §Unverified Assumptions).

### Core Logic

30. ⚠️ Modify `scripts/grade.py` — add a new check to the `CHECKS` registry only if the new case needs a check that does not yet exist.
    - **Current:** `CHECKS` registry holds existing checks (exact shape unverified — must inspect `scripts/grade.py` first; ref: structure §Unverified Assumptions).
    - **After:** new check registered in `CHECKS` and referenced by the case from step 29. Skip this step if an existing check suffices.
    - Also create any fixture file(s) under `evals/` required by the new case (✨ new file, if needed).

### Verify Slice 2

31. **Checkpoint:** `python -c "import json; json.load(open('evals/suite.json'))"` then run the harness loader against the new case.
    - [ ] Confirmed with human first (OQ3).
    - [ ] New case parses as valid JSON within `evals/suite.json`.
    - [ ] Any new check registered in `grade.py`'s `CHECKS` registry and referenced by the case.
    - [ ] Harness loads the case without error (execution returns empty output by design — ref: design Risk Register row 4).

---

## Rollback Notes

- **Step 2 (create directories) / Steps 3–21 (create files):** Authoring is additive and isolated to a new `.claude/skills/using-argocd-cli/` directory; rollback = `rm -rf .claude/skills/using-argocd-cli/`. No existing skill, registry, or shared schema is touched (ref: structure §Modified Types: none).
- **Step 29 (`evals/suite.json`):** Modifies an existing tracked file. Rollback = `git checkout -- evals/suite.json` to restore the prior case set. Back up / diff before editing since this is shared eval state.
- **Step 30 (`scripts/grade.py`):** Modifies an existing tracked file. Rollback = `git checkout -- scripts/grade.py`. Removing a registered check that other cases reference would break those cases — only add, never remove existing checks.
