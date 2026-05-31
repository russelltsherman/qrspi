# Structure Outline — Create a new agent skill using argocd CLI

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This deliverable is a Claude Code `SKILL.md` prompt artifact, not executable code. There are no programmatic types. The "type" analog is the SKILL.md frontmatter shape, defined here as the contract the new skill must conform to:

- `SkillFrontmatter { name: string (kebab-case), description: string (purpose + concrete user phrase + trigger variants), command: string (= "/" + name), argument-hint: string, allowed-tools: string[] }` (ref: design.md §Desired End State, Decision 1/3)

## Modified Types

- None. No existing skill frontmatter or shared schema is changed (there is no schema file in-repo — ref: design.md §Current State).

## Contracts

These are the cross-file interfaces between the SKILL.md body and its `references/` files. The body is the single entry point; each reference is loaded lazily via a one-line imperative pointer (the established `qrspi-work` progressive-disclosure pattern — ref: design.md Decision 2).

- `SKILL.md body → references/authentication.md` — pointer loaded when an auth/login/context step executes. Reference covers: token vs password, env vars (`ARGOCD_AUTH_TOKEN`), `--core`, `--grpc-web`, context management, project-scoped role tokens.
- `SKILL.md body → references/sync-strategies.md` — pointer loaded on diff/sync. Covers manual vs automated, self-heal/auto-prune, sync waves, hooks, retry policies, `--force`/`--prune` cautions.
- `SKILL.md body → references/rollback.md` — pointer loaded on rollback. Covers Git revert vs `argocd app rollback`, history inspection, automated-rollback-on-degraded.
- `SKILL.md body → references/applicationsets.md` — pointer loaded on the simple→multi-cluster escalation path. Covers generators (Git, Cluster, Matrix, List), app-of-apps, `preserveResourcesOnDeletion`.
- `SKILL.md body → references/rbac.md` — pointer loaded on RBAC/permission work. Covers AppProjects, JWT role tokens, `rbac validate`/`can`, SSO mapping, deny-all default.
- `SKILL.md body → references/troubleshooting.md` — pointer loaded on failure/escalation. Covers debugging flowchart, `terminate-op`, hard refresh, manifests live-vs-git, repo connectivity, scoped `kubectl describe`/logs follow-ups.

**Naming contract (OQ1):** directory name == `name` field == command minus leading slash. Recommended value `using-argocd-cli` (design Decision 1). Confirm before authoring — this is the first non-`qrspi-` skill.

**Tooling contract (OQ4):** `allowed-tools` = `Bash(argocd:*)`, `Bash(kubectl:*)`, `Read` (design Decision 3). Confirm kubectl inclusion before authoring.

## Slice 1: Author the `using-argocd-cli` skill (body + references)

**Goal:** A complete, discoverable skill at `.claude/skills/using-argocd-cli/` whose SKILL.md body covers the full argocd lifecycle (auth, create, diff/sync, monitor, rollback, delete) with opinionated-defaults decision tables, a scope-deferral do/don't list, a HARD STOP block, and one-line pointers into all six self-contained reference files. End-to-end testable path: an agent triggered on an argocd request can read the body, follow a lifecycle stage, and load exactly the reference it needs.

**Files touched:**

- ✨ `.claude/skills/using-argocd-cli/SKILL.md` — frontmatter (per Frontmatter contract), lifecycle sections (auth, create, diff/sync, monitor, rollback, delete), interactive-vs-CI/CD guidance blocks, opinionated-defaults decision tables (manual sync for prod, Git revert over imperative rollback, token over password), simple→multi-cluster escalation table, scope-deferral do/don't list, HARD STOP block (`--force`/`--prune`, auth/cluster-access, sync failures), and one-line pointers into each reference.
- ✨ `.claude/skills/using-argocd-cli/references/authentication.md` — see authentication contract.
- ✨ `.claude/skills/using-argocd-cli/references/sync-strategies.md` — see sync-strategies contract.
- ✨ `.claude/skills/using-argocd-cli/references/rollback.md` — see rollback contract.
- ✨ `.claude/skills/using-argocd-cli/references/applicationsets.md` — see applicationsets contract.
- ✨ `.claude/skills/using-argocd-cli/references/rbac.md` — see rbac contract.
- ✨ `.claude/skills/using-argocd-cli/references/troubleshooting.md` — see troubleshooting contract.

**Verification:**

- [ ] Authored via the global `skill-creator` skill (confirm it is invocable first — OQ2; if absent, hand-author to in-repo conventions and flag the criterion as partially met).
- [ ] Directory structure matches `.claude/skills/<name>/SKILL.md` + `references/`; directory name == `name` == command-without-slash (lowercase kebab-case).
- [ ] Frontmatter carries `name`, `description`, `command`, `argument-hint`, `allowed-tools` matching the in-repo skill shape; `allowed-tools` is scoped (`Bash(argocd:*)`, `Bash(kubectl:*)`, `Read`).
- [ ] SKILL.md body is under 500 lines (manual line count; the 5000-token figure is approximate — no in-repo token counter, ref: design Risk Register).
- [ ] Every `references/` file named in the design exists, is self-contained, and is reachable by exactly one one-line pointer from the body (no dangling pointers, no orphan references).
- [ ] Body contains all three guidance formats: ≥1 decision table, ≥1 do/don't list, ≥1 HARD STOP block.
- [ ] Body contains distinct interactive (`argocd login`/`context`) and CI/CD (`ARGOCD_AUTH_TOKEN`/`--core`) guidance blocks.
- [ ] `description` follows the purpose + concrete-phrase + trigger-variants pattern and includes explicit out-of-scope language (ref: design Risk Register).
- [ ] If `skill-creator` is used, run its eval loop per the skill-creator workflow (final validation step of this slice).

**Context cost:** L
**Depends on:** none

## Slice 2 (optional): Add an eval case for the skill

**Goal:** Make the new skill eval-testable for future use by adding ≥1 case to the prompt-quality suite. This is a genuine separate concern from authoring: a different file, different verification, and the design flags it as optional and currently moot (eval execution layer is stubbed). It can be verified independently (the case parses and registers) without re-touching the skill artifact.

**Files touched:**

- ⚠️ `evals/suite.json` — add ≥1 hand-curated case targeting the `using-argocd-cli` skill (ref: design.md §Delta, Q12).
- ⚠️ `scripts/grade.py` — possibly add a new check to the `CHECKS` registry if the case needs a check that does not yet exist (ref: design.md §Delta).
- ✨ fixture file(s) under `evals/` as required by the new case.

**Verification:**

- [ ] Confirm with the human first (OQ3) — the eval execution layer is a stub that returns empty output, so end-to-end scores cannot be produced today; only do this slice if requested.
- [ ] New case parses as valid JSON within `evals/suite.json`.
- [ ] Any new check is registered in `grade.py`'s `CHECKS` registry and is referenced by the new case.
- [ ] The harness loads the case without error (acknowledging execution returns empty output by design — ref: design Risk Register).

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- **`skill-creator` availability (OQ2, design Risk Register):** The acceptance criterion "Built using the Anthropic skill builder skill" depends on the global `skill-creator` skill being invocable in the implementation session. The design states it is NOT present in this repository and could not be read. This cannot be mapped to an in-repo file or verified at structure time; it must be confirmed at the start of Slice 1.
- **Skill name / prefix (OQ1):** The design recommends `using-argocd-cli` but flags it as the first non-`qrspi-` precedent requiring a human decision. The structure assumes this name; if changed, every file path in Slice 1 changes accordingly.
- **`allowed-tools` kubectl scope (OQ4):** Whether `Bash(kubectl:*)` belongs in this skill or should be deferred to a separate skill is an open human decision. The structure assumes inclusion per design Decision 3.
- **5000-token body budget:** No in-repo token counter exists (design §Current State, Risk Register). The "under 5000 tokens" criterion cannot be programmatically verified; only the 500-line count is checkable. Treated as approximate.
- **`grade.py` `CHECKS` registry shape:** The exact mechanism for adding a new check in Slice 2 is inferred from the design's reference to a `CHECKS` registry; the structure phase did not read `scripts/grade.py` directly (reads limited to template + design). Verify the registry shape during planning if Slice 2 is pursued.
- **Reference file content scope:** The specific argocd commands and content within each reference file are drawn from the design's topic descriptions, not from any in-repo argocd material (none exists — design Q10). Command correctness is the author's responsibility during Slice 1 and is not verifiable from repo precedent.
