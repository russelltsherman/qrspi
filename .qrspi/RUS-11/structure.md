# Structure Outline — Create a new agent skill using the devcontainer CLI

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> This is a content-authoring feature (a guidance skill made of Markdown +
> YAML frontmatter), not application code. There are no runtime types or
> function signatures. "New Types" below captures the SKILL.md frontmatter
> schema as a structural contract, and "Contracts" captures the body↔reference
> citation interfaces and the required-content contract each reference must satisfy.

## New Types

- `SkillFrontmatter { name: string (lowercase kebab, == directory name == "devcontainer-cli"), description: string (two-part "what it does" + "Use when…/Trigger on…" with a short negative "do NOT use for general Docker/K8s/Codespaces" clause), command: string, argument-hint: string, allowed-tools: string }` — the five-key YAML block all ten existing skills share (ref: design.md §Decision 1, Q3).

## Modified Types

- None. The design specifies no modifications to existing files (ref: design.md §Delta).

## Contracts

These are authoring-time interfaces, not code APIs. Each is verifiable by inspection.

- `references/cli-commands.md` — full `devcontainer` CLI reference covering `up`, `exec`, `build`, `read-configuration`, `run-user-commands`, and flags `--workspace-folder`, `--frozen-lockfile`, `--remove-existing-container` (ref: design.md §Delta).
- `references/devcontainer-json-schema.md` — schema cheatsheet covering `image` vs `build`, `remoteUser`, `forwardPorts`, `customizations`, `mounts`, `features`, Compose keys (`dockerComposeFile`, `service`, `workspaceFolder`, `shutdownAction`) (ref: design.md §Delta, §Desired End State).
- `references/lifecycle-decision-tree.md` — all six hooks (`initializeCommand`, `onCreateCommand`, `updateContentCommand`, `postCreateCommand`, `postStartCommand`, `postAttachCommand`) with when-to-use guidance, execution order, object/parallel syntax, and the skip-on-failure + idempotency rule (ref: design.md §Desired End State, Q9).
- `references/cicd-workflows.md` — `devcontainers/ci` GitHub Action usage, pre-build-and-push, registry cache (`--cache-from`), CI image reuse as the local `image` (ref: design.md §Delta).
- `SKILL.md body → references/*` — every one of the four reference files MUST be cited by relative path from the body at its decision point; no orphan references (ref: design.md §Decision 3, Risk: dead reference, Q2).
- `SKILL.md body content` — must contain: install + primary workflow, opinionated defaults (non-root user, lockfile committed, named volumes for deps) framed as general-project advice with an explicit "this repo's hardened build-based devcontainer is a deliberate exception" caveat, lifecycle summary, Compose summary, troubleshooting (permissions, cache invalidation, volume ownership, lifecycle failures, slow builds); body ≤ 500 lines / ~5000 tokens (ref: design.md §Desired End State, §Decision 3, Risk register).

## Slice 1: Reference files (CLI, schema, lifecycle, CI/CD)

**Goal:** Produce the four `references/*.md` lookup documents, each self-contained and independently verifiable for required content coverage — the bounded material the body will later cite. This is the forward dependency (the body cannot cite files that do not yet exist).
**Files touched:**

- ✨ `.claude/skills/devcontainer-cli/references/cli-commands.md` — full devcontainer CLI command + flag reference.
- ✨ `.claude/skills/devcontainer-cli/references/devcontainer-json-schema.md` — devcontainer.json schema cheatsheet incl. Compose keys.
- ✨ `.claude/skills/devcontainer-cli/references/lifecycle-decision-tree.md` — all six lifecycle hooks with when-to-use, order, syntax, skip-on-failure rule.
- ✨ `.claude/skills/devcontainer-cli/references/cicd-workflows.md` — GitHub Actions `devcontainers/ci` integration + registry cache.

**Verification:**
- [ ] All four files exist under `references/` and are non-empty.
- [ ] `lifecycle-decision-tree.md` enumerates all six hooks (`initializeCommand`, `onCreateCommand`, `updateContentCommand`, `postCreateCommand`, `postStartCommand`, `postAttachCommand`) with selection guidance and the skip-on-failure rule (`grep` each hook name).
- [ ] `cli-commands.md` covers `up`, `exec`, `build`, `read-configuration`, `run-user-commands` and the three named flags.
- [ ] `devcontainer-json-schema.md` covers `image` vs `build`, `remoteUser`, and the Compose keys (`dockerComposeFile`, `service`, `workspaceFolder`, `shutdownAction`).
- [ ] `cicd-workflows.md` references the `devcontainers/ci` action and registry cache.

**Context cost:** M
**Depends on:** none

## Slice 2: SKILL.md body, frontmatter, and citations (authored via skill-creator)

**Goal:** Author the skill entry point: valid five-key frontmatter, concise body (workflow + opinionated defaults + repo-exception caveat + lifecycle/Compose summaries + troubleshooting), and a relative-path citation to each of the four Slice 1 references — delivering a complete, loadable `devcontainer-cli` skill. Per Decision 2 this is a self-contained content skill, so no agent file is created. Authored by invoking the global `skill-creator` skill (acceptance criterion); reconcile its emitted frontmatter with the repo five-key convention, preferring the repo keys while keeping any extra standard keys (ref: design.md §Decision 1, OQ1).
**Files touched:**

- ✨ `.claude/skills/devcontainer-cli/SKILL.md` — frontmatter + concise body + four reference pointers.

**Verification:**
- [ ] Frontmatter is valid YAML with the five keys; `name: devcontainer-cli` equals the directory name.
- [ ] `description` carries the two-part trigger phrasing plus the short negative "do NOT use for general Docker/Kubernetes/Codespaces" clause (ref: Decision 4).
- [ ] Body cites all four `references/*.md` files by relative path — no orphan reference (`grep` each filename in SKILL.md).
- [ ] Body states the opinionated defaults (non-root user, lockfile committed, named volumes) AND the explicit "this repo's build-based hardened devcontainer is a deliberate exception" caveat.
- [ ] Body includes a Compose summary and a troubleshooting section covering permissions, cache invalidation, volume ownership, lifecycle failures, slow builds.
- [ ] Body ≤ 500 lines (`wc -l`) and within the ~5000-token budget (manual estimate).
- [ ] `skill-creator` was invoked at authoring time (records OQ1 reconciliation).

**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

These are design Open Questions / claims that cannot be mapped to concrete, in-repo verifiable code and need human attention before planning.

- **OQ1 — skill-creator authorship & frontmatter precedence.** The "Built using the Anthropic skill builder skill" criterion depends on the global, out-of-repo `skill-creator` skill; the design cannot verify it ran, and if skill-creator emits a frontmatter shape differing from the repo's five-key convention, which wins is unresolved. Structure assumes "prefer repo keys, keep extra standard keys" — needs confirmation (ref: design.md OQ1, Decision 1).
- **OQ2 — opinionated-defaults vs repo reality.** Whether the skill's general defaults (prefer `image`, use `features`, named volumes) should be stated even though this repo's own devcontainer deliberately does the opposite, and how prominent the "exception" caveat must be, is a judgment call left open (ref: design.md OQ2, Risk register row 1).
- **OQ3 — `argument-hint` for a no-argument guidance skill.** A guidance skill takes no positional ticket argument, so the value/placeholder for the mandatory `argument-hint` key is undecided (ref: design.md OQ3).
- **OQ4 — verification method.** With the eval harness a non-functional placeholder and no SKILL.md validator/size-check tooling in-repo, all acceptance verification is manual inspection (`wc -l`, `grep`, section presence). Whether manual review is acceptable as the sole gate is unconfirmed (ref: design.md OQ4, Q6/Q10/Q12).
- **NEW PATTERN — negative trigger clause.** Decision 4 introduces a negative "do NOT use for…" description clause with no in-repo precedent (all ten skills scope by positive specificity only); its real-world triggering behavior is unverifiable here (ref: design.md Decision 4).
