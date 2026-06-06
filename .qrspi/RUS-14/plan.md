# Implementation Plan — Create a new agent skill: using helm cli

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 13

> Note: this ticket produces a documentation/prompt artifact (a self-contained
> agent skill), not executable code. Steps create markdown files and verify them
> against the structure contracts. There are no function signatures; "actions"
> are authoring actions and "verification" is manual review + `wc -l`, since no
> automated validator exists (ref: structure §Contracts, design Risk Register).

## Slice 1: Author the `using-helm-cli` self-contained skill

### Setup

1. ✨ Begin the authoring pass through the `skill-creator` skill (invoke `skill-creator` and its eval loop), scoped to a new self-contained skill directory `.claude/skills/using-helm-cli/`. All file-authoring steps below run inside this pass; validate output against the ten in-repo SKILL.md examples (ref: structure Verification, design Risk #1). Self-contained archetype only — do NOT create a sibling `.claude/agents/using-helm-cli.md`, `scripts/`, or `assets/` (ref: SkillDirectory type, design §Delta).

### Core Logic

2. ✨ Create `.claude/skills/using-helm-cli/SKILL.md` frontmatter — exactly the five-field YAML block delimited by `---`: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (SkillFrontmatter type). Set `name: using-helm-cli` equal to the directory name (Frontmatter contract). Write `description` in the action + explicit "Use when" structure, enumerating literal helm trigger phrases e.g. "deploy with helm", "helm upgrade", "rollback a release", "helm install/uninstall/status" (Triggering contract; design OQ3 — choose concrete phrasings).

3. ✨ Add the release-lifecycle body sections to `.claude/skills/using-helm-cli/SKILL.md` — install, upgrade, rollback, uninstall, status, each carrying the security-first mandatory defaults `--atomic`, `--wait`, `--verify`, and explicit namespaces (ref: design §Desired End State).

4. ✨ Add the values/overrides and chart-authoring body sections to `.claude/skills/using-helm-cli/SKILL.md` — naming, versioning, schema validation, library charts; name `references/values-patterns.md` by backtick path here (ref: design §Desired End State; Reference-loading contract).

5. ✨ Add the repo/registry, hooks, and testing body sections to `.claude/skills/using-helm-cli/SKILL.md` — OCI + classic repo workflows, hook lifecycle, testing; name `references/oci-workflow.md`, `references/hook-lifecycle.md`, and `references/testing-strategies.md` by backtick path here (Reference-loading contract).

6. ✨ Add the troubleshooting decision tree and Helm 4 awareness body sections to `.claude/skills/using-helm-cli/SKILL.md` — diagnostic sequence for common failure modes; opinionated toward Helm 4 defaults with inline caveats prefixed `Helm 3:`; name `references/helm4-migration.md` by backtick path here (Version-caveat convention; Decision 4).

7. ✨ Add the explicit out-of-scope section to `.claude/skills/using-helm-cli/SKILL.md` — name kubectl/kustomize, Helmfile, and GitOps reconcilers and defer each to its owning skill/phase using the repo's name-and-defer convention (Scope-boundary contract; Decision 3).

8. ✨ Create `.claude/skills/using-helm-cli/references/values-patterns.md` (ReferenceFile) — layered values hierarchy, `-f` ordering, deep-merge vs array-replace, `values.schema.json`, secrets deferral.

9. ✨ Create `.claude/skills/using-helm-cli/references/hook-lifecycle.md` (ReferenceFile) — hook weights, delete policies, pre/post lifecycle phases, hook Job resource limits.

10. ✨ Create `.claude/skills/using-helm-cli/references/oci-workflow.md` (ReferenceFile) — OCI push/pull, classic-repo workflow, signing/verification (cosign + provenance).

11. ✨ Create `.claude/skills/using-helm-cli/references/testing-strategies.md` (ReferenceFile) — `helm test`, helm-unittest, lint, template-against-policy, schema validation.

12. ✨ Create `.claude/skills/using-helm-cli/references/helm4-migration.md` (ReferenceFile) — Server-Side Apply default, readiness annotations, post-renderer plugins, Helm 3 compatibility notes.

### Verify Slice 1

13. **Checkpoint:** `wc -l .claude/skills/using-helm-cli/SKILL.md && ls .claude/skills/using-helm-cli/references/`
    - [ ] Authoring/validation pass completed through `skill-creator` and its eval loop over the whole directory (ref: structure Verification, design Risk #1).
    - [ ] `SKILL.md` frontmatter contains exactly the five fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) inside `---`; `name == using-helm-cli == directory name` (manual review).
    - [ ] `wc -l` confirms SKILL.md body under 500 lines; spot-check token budget under ~5000 (Size-budget contract — manual, no tokenizer available).
    - [ ] All five `references/*.md` files exist (`values-patterns`, `hook-lifecycle`, `oci-workflow`, `testing-strategies`, `helm4-migration`) and each is named by a backtick-quoted relative path in SKILL.md; no orphaned or dangling references (Reference-loading contract).
    - [ ] Out-of-scope section names kubectl/kustomize, Helmfile, and GitOps reconcilers and defers each to its owner (Scope-boundary contract).
    - [ ] `description` uses the action + "Use when" structure with literal helm trigger phrases (Triggering contract).
    - [ ] All five release operations, the security defaults (`--atomic`/`--wait`/`--verify`/explicit namespaces), both repo workflows, and the troubleshooting decision tree are present in the body (acceptance-criterion checklist).
    - [ ] No sibling `.claude/agents/using-helm-cli.md`, `scripts/`, or `assets/` was created (self-contained archetype, Decision 1).

---

## Rollback Notes

- This slice is purely additive — no existing files are modified and no DB/config/destructive ops occur (structure §Modified Types: None).
- Steps 2–12: to reverse, delete the directory `.claude/skills/using-helm-cli/` (`rm -rf .claude/skills/using-helm-cli`). No registry, agents file, or script references it, so removal leaves no dangling pointers (ref: design §Delta).
