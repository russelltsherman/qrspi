# Structure Outline — Create a new agent skill: using helm cli

**Design basis:** design.md @ 2026-06-03T13:10:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: this ticket produces a documentation/prompt artifact (a self-contained
> agent skill), not executable code. "Types" below are the structural shapes the
> skill must conform to; "Contracts" are the cross-file conventions that must
> hold between SKILL.md and its references/. There are no function signatures.

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the five-field YAML block delimited by `---`, proven across the ten in-repo skills (ref: design §Desired End State, Q3). `name` MUST equal the directory name `using-helm-cli`.
- `SkillDirectory { SKILL.md: SkillFile, references/: ReferenceFile[] }`
  — self-contained archetype (Decision 1): no sibling `.claude/agents/<name>.md`, no `scripts/` or `assets/` (ref: design §Delta).
- `ReferenceFile { path: string (backtick-named in SKILL.md prose), body: markdown }`
  — depth content loaded on demand, mirroring `qrspi-work/references/` precedent (ref: Q5).

## Modified Types

- None. Skills are additive; no central registry, agents file, or script references them (ref: design §Delta, Q2).

## Contracts

- **Frontmatter contract** — `SKILL.md` opens with exactly the five fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) inside `---` delimiters; `name == "using-helm-cli" == directory name` (ref: Q2, Q3).
- **Reference-loading contract** — every file under `references/` is named by a backtick-quoted relative path in SKILL.md prose and is read on demand, never inlined (ref: Q5). The five reference paths are fixed: `references/values-patterns.md`, `references/hook-lifecycle.md`, `references/oci-workflow.md`, `references/testing-strategies.md`, `references/helm4-migration.md`.
- **Size-budget contract** — SKILL.md body stays under 500 lines / 5000 tokens, enforced manually via `wc -l` + review since no checker exists; depth is offloaded to references/ (ref: Q7, Decision 2).
- **Triggering contract** — `description` follows the action + explicit "Use when" structure with literal helm trigger phrases enumerated, mirroring qrspi-work (ref: Q4, Risk #4).
- **Scope-boundary contract** — a dedicated out-of-scope section names each excluded topic (kubectl/kustomize, Helmfile, GitOps reconcilers) and the owning skill/phase, using the repo's name-and-defer convention (ref: Q8, Decision 3).
- **Version-caveat convention (NEW PATTERN)** — opinionated toward Helm 4 defaults; inline caveats prefixed `Helm 3:`; deep migration content isolated in `references/helm4-migration.md` (ref: Q9, Decision 4).

## Slice 1: Author the `using-helm-cli` self-contained skill

**Goal:** A complete, validated self-contained skill directory `.claude/skills/using-helm-cli/` — SKILL.md plus its five reference files — that loads, triggers correctly, stays under budget, and satisfies every acceptance criterion as one cohesive authoring pass through skill-creator. This is the testable end-to-end path: the skill is discoverable and usable by the agent.

**Files touched:**

- ✨ `.claude/skills/using-helm-cli/SKILL.md` — five-field frontmatter; body sections for full release lifecycle (install/upgrade/rollback/uninstall/status), security-first defaults (`--atomic`, `--wait`, `--verify`, explicit namespaces), values/overrides, chart authoring, repo/registry (OCI + classic), hooks, testing, troubleshooting decision tree, Helm 4 awareness with inline `Helm 3:` caveats, and an explicit out-of-scope section; names all five reference paths in backtick prose. Kept under 500 lines / 5000 tokens.
- ✨ `.claude/skills/using-helm-cli/references/values-patterns.md` — layered values hierarchy, `-f` ordering, deep-merge vs array-replace, `values.schema.json`, secrets deferral.
- ✨ `.claude/skills/using-helm-cli/references/hook-lifecycle.md` — hook weights, delete policies, pre/post lifecycle phases, hook Job resource limits.
- ✨ `.claude/skills/using-helm-cli/references/oci-workflow.md` — OCI push/pull, classic-repo workflow, signing/verification (cosign + provenance).
- ✨ `.claude/skills/using-helm-cli/references/testing-strategies.md` — `helm test`, helm-unittest, lint, template-against-policy, schema validation.
- ✨ `.claude/skills/using-helm-cli/references/helm4-migration.md` — Server-Side Apply default, readiness annotations, post-renderer plugins, Helm 3 compatibility notes.

**Verification:**

- [ ] Authoring/validation pass runs through the `skill-creator` skill and its eval loop over the whole directory (ref: Q1, Q11, Risk #1).
- [ ] `SKILL.md` frontmatter contains exactly the five fields inside `---`; frontmatter `name` equals directory name `using-helm-cli` (manual review — ref: Q3).
- [ ] `wc -l .claude/skills/using-helm-cli/SKILL.md` confirms body under 500 lines; spot-check token budget under 5000 (ref: Q7).
- [ ] Every one of the five `references/*.md` files exists and is named by a backtick-quoted relative path in SKILL.md; no orphaned or dangling references (ref: Q5).
- [ ] Out-of-scope section names kubectl/kustomize, Helmfile, and GitOps reconcilers and defers each to its owner (ref: Q8).
- [ ] `description` uses the action + "Use when" structure with literal helm trigger phrases (ref: Q4).
- [ ] All five release operations, the security defaults, both repo workflows, and the troubleshooting decision tree are present in the body (acceptance-criterion checklist — ref: design §Desired End State).

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

- **skill-creator behavior is unobservable from the repo.** The design treats skill-creator as the authoring/validation pass, but its inputs, eval loop, validation rules, and trigger logging live outside REPO_ROOT and were not readable (ref: Q1, Q6, Q10, Q12, Risk #1). The slice cannot guarantee what skill-creator enforces; output must be validated against the ten in-repo SKILL.md examples regardless.
- **No automated validator exists** for frontmatter, structure, or the 500-line/5000-token budget (ref: Q7, Q10). All "Verification" checks above are manual; there is no concrete linter/checker file to invoke.
- **Token budget cannot be measured precisely in-repo.** "Under 5000 tokens" has no tokenizer tool available; it is approximated via `wc -l` and review (ref: Q7).
- **Triggering accuracy is unverifiable in-repo.** Whether the `description` under- or over-matches depends on the external harness UI, which is not testable here (ref: Q12, Risk #4, OQ3).
- **Open questions unresolved by the design** (carried forward for human attention before/during planning): OQ1 — vendor skill-creator into the repo or stay dependent on the global skill; OQ2 — whether to establish `scripts/`/`assets/` conventions now (design defers to references/-only); OQ3 — exact literal trigger phrases for the `description`.
- **NEW PATTERN, no precedent:** the Helm 3 vs Helm 4 version-caveat convention (Decision 4) has no in-repo example to mirror (ref: Q9); its concrete shape is established by this skill itself rather than mapped to an existing file.
