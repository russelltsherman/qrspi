# Structure Outline — Create a new agent skill for the argocd CLI

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

This is a prose/knowledge-skill deliverable — no code types or runtime data structures.
The structural "types" are document contracts (frontmatter schema + file conventions):

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the repo's five-key YAML block, keys in that exact order. `name` == directory name,
  `command` == `/` + `name`, `description` quoted (contains colons), `allowed-tools: Bash` (minimized).
- `ReferenceFile { h1Title: string (self-titled), body: markdown }`
  — each `references/<topic>.md` opens with a self-titled H1, no frontmatter.

## Modified Types

- None. No existing file is modified (ref: design.md §Delta). Skill discovery is directory-convention only, so no manifest/index/registry edit.

## Contracts

These are the cross-file conventions every file in the new skill directory must honor.
They are not function signatures (no code), but they are the load-bearing interfaces.

- `FrontmatterContract` — `SKILL.md` carries exactly the five keys in order; `name` == `using-argocd-cli` == directory; `command` == `/using-argocd-cli`; `description` quoted with explicit "Use when…/Trigger on…" clause naming argocd/GitOps phrases; `allowed-tools: Bash`.
- `ReferenceCitationContract` — body sections cite references skill-root-relative as `references/<file>.md` (no leading `./`, no absolute path), each pointer placed at the decision point of its body section (the `qrspi-work` precedent).
- `ReferenceTitleContract` — each of the six `references/*.md` files begins with a self-titled H1 matching its topic.
- `EscalationOrderContract` — body `##` sections are ordered simple → complex: Authentication & Context → Application Lifecycle → Sync Strategies → Health Monitoring → Rollbacks → App-of-Apps → ApplicationSets → RBAC & Projects → Multi-Cluster → Troubleshooting.
- `OpinionatedDefaultsContract` — the three defaults (manual sync for prod, Git revert over `app rollback`, token auth over password) appear as `**bold**` rules in both body and the relevant reference, and are mutually consistent across files.

## Slice 1: Author the `using-argocd-cli` skill (SKILL.md + six references)

**Goal:** A complete, auto-discoverable, self-contained skill at `.claude/skills/using-argocd-cli/` that triggers on argocd/GitOps prompts, walks the full create→sync→monitor→rollback→delete lifecycle in the body, and offloads deep per-topic material to six on-demand `references/` files — validated as the final step through the external `skill-creator` skill.

**Why one slice:** All seven files are one cohesive, mutually dependent unit. The body sections directly cite the reference files (`ReferenceCitationContract`), so SKILL.md and `references/` are a main file plus the support files it depends on — there is no genuine testability boundary between them (the skill is verified as a whole: discoverable, triggers, references load on demand). Splitting would violate the "don't separate a main file from its references" rule. Seven files < 10. The `skill-creator` validation is the closing step of this same slice, not a separate slice.

**Files touched:**

- ✨ `.claude/skills/using-argocd-cli/SKILL.md` — five-key frontmatter; H1 `# Using the Argo CD CLI`; topical `##` sections in escalation order with bash-fenced `argocd` examples; each deep section ends with a skill-root-relative pointer into `references/`; the three opinionated defaults as `**bold**` rules; ~250–350 lines (discipline only).
- ✨ `.claude/skills/using-argocd-cli/references/authentication.md` — token vs password, `ARGOCD_SERVER`/`ARGOCD_AUTH_TOKEN`/`ARGOCD_OPTS`, `--grpc-web`, `--core`, project-scoped role tokens, interactive `login`/`context`; contrasts interactive-developer vs CI/CD-automation auth.
- ✨ `.claude/skills/using-argocd-cli/references/sync-strategies.md` — manual vs automated, `--self-heal`/`--auto-prune`, `--dry-run`, sync waves, hooks, `--force`/`--prune` cautions, retry policies, `--apply-out-of-sync-only`.
- ✨ `.claude/skills/using-argocd-cli/references/rollback-procedures.md` — Git revert preference, `argocd app rollback` emergency use + auto-disable of automated sync, `app history`, follow-up revert.
- ✨ `.claude/skills/using-argocd-cli/references/applicationset-generators.md` — Git/Cluster/Matrix/List generators, app-of-apps→ApplicationSet transition thresholds, `preserveResourcesOnDeletion`.
- ✨ `.claude/skills/using-argocd-cli/references/rbac-configuration.md` — AppProjects, project-scoped role tokens, `admin settings rbac validate`/`can`, SSO group mapping, deny-all default.
- ✨ `.claude/skills/using-argocd-cli/references/troubleshooting.md` — flowchart prose: `app get` → `app resources` → events/logs → `terminate-op`, manifest live-vs-git compare, hard refresh, repo connectivity.

**Verification:**

- [ ] `SKILL.md` frontmatter satisfies `FrontmatterContract`: five keys in order, `name`/`command`/directory all `using-argocd-cli`, `description` quoted with a "Use when…/Trigger on…" clause naming argocd/GitOps phrases, `allowed-tools: Bash` (visual diff against an existing skill's frontmatter, e.g. `qrspi-work`).
- [ ] Every `references/` pointer in the body resolves to a real file and is skill-root-relative with no `./` and no absolute path (`ReferenceCitationContract`); all six reference files exist and each opens with a self-titled H1 (`ReferenceTitleContract`).
- [ ] Body covers the full lifecycle (create, sync, monitor, rollback, delete) with bash-fenced `argocd` examples and presents the three opinionated defaults as `**bold**` rules consistent with their reference files (`OpinionatedDefaultsContract`).
- [ ] Body `##` sections appear in the escalation order (`EscalationOrderContract`).
- [ ] Manual length check: `SKILL.md` body counted before submit, targeting < 500 lines (no checker exists — discipline gate; see Unverified Assumptions).
- [ ] Final authoring/validation pass run through the external `skill-creator` skill and its eval loop (AC #2); manual end-to-end check that `/using-argocd-cli` is discovered and triggers.

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

These are claims from design.md that could not be mapped to a concrete, in-repo verifiable type, file, or interface, and need human attention before planning:

- **AC #2 — "Built using the Anthropic skill-builder skill" (design OQ1, Risk row 2).** The `skill-creator` skill lives outside `REPO_ROOT` and cannot be inspected or vendored here. Whether the skill *must* be authored through `skill-creator` to be accepted, or a hand-authored convention-conforming skill suffices, is unresolved. Treated as a manual process step in Slice 1's final verification, not a code deliverable — confirm acceptance criteria with the reviewer.
- **500-line / 5000-token budget (design OQ2, Risk row 1).** No checker, validator, or token-budget mechanism exists in the repo, and `qrspi-work/SKILL.md` (565 lines) already exceeds it. Whether this is a hard gate measured manually at review, or an aspirational target, is unconfirmed. Slice 1 treats it as a discipline-only target.
- **Helper scripts / assets scope (design OQ3).** Design Decision 3 commits to prose + bash-fenced examples only (no per-skill `scripts/`/`assets/`), but the ticket's intent on executable helpers is unconfirmed. If reviewers expect runnable helpers, that is new scope (and a new per-skill `scripts/` pattern) not covered by this structure.
- **Reference content accuracy.** The six references encode opinionated argocd operational knowledge (sync waves, generator transition thresholds, RBAC defaults, rollback semantics). Correctness of this domain content is not verifiable against the codebase — it requires a reviewer with Argo CD expertise.
