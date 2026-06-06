# Implementation Plan — Create a new agent skill using the devcontainer CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

> Content-authoring feature. Every step is one file + one action. No runtime
> code, so "Current/After signatures" apply only where an existing file would
> change — none do (design §Delta: no modifications). Steps cite the exact
> structure.md Contracts and Decisions they satisfy.

## Slice 1: Reference files (CLI, schema, lifecycle, CI/CD)

### Setup

1. ✨ Create `.claude/skills/devcontainer-cli/references/` directory — establishes the `references/` subdirectory (the only one of the four agentskills.io subdirs with in-repo precedent; structure.md Slice 1, design §Current State Q1). Created implicitly by the first file write below; no standalone action required if the editor auto-creates parent dirs.

### Core Logic

2. ✨ Create `.claude/skills/devcontainer-cli/references/cli-commands.md` — full `devcontainer` CLI reference satisfying contract `references/cli-commands.md`. MUST cover commands `up`, `exec`, `build`, `read-configuration`, `run-user-commands` and flags `--workspace-folder`, `--frozen-lockfile`, `--remove-existing-container` (structure.md Contracts; design §Delta).

3. ✨ Create `.claude/skills/devcontainer-cli/references/devcontainer-json-schema.md` — schema cheatsheet satisfying contract `references/devcontainer-json-schema.md`. MUST cover `image` vs `build`, `remoteUser`, `forwardPorts`, `customizations`, `mounts`, `features`, and the Compose keys `dockerComposeFile`, `service`, `workspaceFolder`, `shutdownAction` (structure.md Contracts; design §Delta).

4. ✨ Create `.claude/skills/devcontainer-cli/references/lifecycle-decision-tree.md` — lifecycle reference satisfying contract `references/lifecycle-decision-tree.md`. MUST enumerate all six hooks `initializeCommand`, `onCreateCommand`, `updateContentCommand`, `postCreateCommand`, `postStartCommand`, `postAttachCommand` with when-to-use guidance, execution order, object/parallel syntax, and the skip-on-failure + idempotency rule (structure.md Contracts; design §Desired End State, Q9).

5. ✨ Create `.claude/skills/devcontainer-cli/references/cicd-workflows.md` — CI/CD reference satisfying contract `references/cicd-workflows.md`. MUST cover the `devcontainers/ci` GitHub Action, pre-build-and-push, registry cache (`--cache-from`), and reusing the CI image as the local `image` (structure.md Contracts; design §Delta).

### Tests

6. No automated test file — there is no SKILL.md validator or eval harness in-repo (design §Current State Q6/Q10/Q12, OQ4). Verification is by inspection in the checkpoint below.

### Verify Slice 1

7. **Checkpoint:** run
   `D=.claude/skills/devcontainer-cli/references; for f in cli-commands devcontainer-json-schema lifecycle-decision-tree cicd-workflows; do test -s "$D/$f.md" && echo "OK $f" || echo "MISSING $f"; done; grep -c -E "initializeCommand|onCreateCommand|updateContentCommand|postCreateCommand|postStartCommand|postAttachCommand" "$D/lifecycle-decision-tree.md"`
   - [ ] All four `references/*.md` files exist and are non-empty.
   - [ ] `lifecycle-decision-tree.md` names all six hooks and states the skip-on-failure rule (grep each hook name; expect 6 distinct matches).
   - [ ] `cli-commands.md` covers `up`, `exec`, `build`, `read-configuration`, `run-user-commands` and the three named flags (`grep` each).
   - [ ] `devcontainer-json-schema.md` covers `image` vs `build`, `remoteUser`, and the four Compose keys (`grep` each).
   - [ ] `cicd-workflows.md` references `devcontainers/ci` and registry cache (`grep`).

---

## Slice 2: SKILL.md body, frontmatter, and citations (authored via skill-creator)

### Setup

8. ✨ Invoke the global `skill-creator` skill to author the `devcontainer-cli` skill (acceptance criterion "Built using the Anthropic skill builder skill"; design Decision 1, OQ1). Record the invocation. This is an authoring action, not a file write; its output feeds steps 9–13.

9. ✨ Create `.claude/skills/devcontainer-cli/SKILL.md` frontmatter — a `---`-delimited YAML block with the five repo-convention keys `name`, `description`, `command`, `argument-hint`, `allowed-tools` (structure.md New Types `SkillFrontmatter`; design Decision 1). Set `name: devcontainer-cli` (== directory name). Reconcile with skill-creator output: prefer repo keys, keep any extra standard keys it emits (design OQ1). Choose an `argument-hint` placeholder appropriate to a no-argument guidance skill (design OQ3).

### Core Logic

10. ⚠️ Edit `.claude/skills/devcontainer-cli/SKILL.md` `description` field — set the two-part "what it does" + "Use when…/Trigger on…" trigger phrasing plus the short negative "do NOT use for general Docker / Kubernetes / Codespaces" clause (structure.md New Types `description`; design Decision 4).
    - **Current:** placeholder/skill-creator-emitted `description` value from step 9.
    - **After:** positive devcontainer trigger phrases + the negative-scope clause.

11. ✨ Write the `.claude/skills/devcontainer-cli/SKILL.md` body — concise guidance satisfying contract `SKILL.md body content`: install + primary workflow; opinionated defaults (non-root user, lockfile committed, named volumes for deps) framed as general-project advice WITH the explicit "this repo's hardened build-based devcontainer is a deliberate exception" caveat; a lifecycle summary; a Compose summary; a troubleshooting section covering permissions, cache invalidation, volume ownership, lifecycle failures, slow builds (structure.md Contracts; design §Desired End State, Decision 3, Risk register). Keep body ≤ 500 lines / ~5000 tokens — push detail into references.

12. ⚠️ Edit `.claude/skills/devcontainer-cli/SKILL.md` body — add a relative-path citation to each of the four `references/*.md` files at its decision point, satisfying contract `SKILL.md body → references/*` (no orphan references; structure.md Contracts; design Decision 3, Risk: dead reference, Q2).
    - **Current:** body from step 11 with reference content inlined or uncited.
    - **After:** body cites `references/cli-commands.md`, `references/devcontainer-json-schema.md`, `references/lifecycle-decision-tree.md`, `references/cicd-workflows.md` each by relative path where used.

### Tests

13. No automated test file — manual inspection only (design OQ4). Covered by the checkpoint below.

### Verify Slice 2

14. **Checkpoint:** run
    `S=.claude/skills/devcontainer-cli/SKILL.md; wc -l "$S"; for f in cli-commands devcontainer-json-schema lifecycle-decision-tree cicd-workflows; do grep -q "references/$f.md" "$S" && echo "CITED $f" || echo "ORPHAN $f"; done; grep -niE "do NOT use|named volume|deliberate exception|troubleshoot|compose" "$S"`
    - [ ] Frontmatter is valid YAML with the five keys; `name: devcontainer-cli` equals the directory name.
    - [ ] `description` carries the two-part trigger phrasing plus the negative "do NOT use for general Docker/Kubernetes/Codespaces" clause.
    - [ ] Body cites all four `references/*.md` files by relative path — no orphan (expect 4 CITED).
    - [ ] Body states the opinionated defaults AND the explicit "this repo's build-based hardened devcontainer is a deliberate exception" caveat.
    - [ ] Body includes a Compose summary and a troubleshooting section covering permissions, cache invalidation, volume ownership, lifecycle failures, slow builds.
    - [ ] Body ≤ 500 lines (`wc -l`) and within the ~5000-token budget (manual estimate).
    - [ ] `skill-creator` was invoked at authoring time (records OQ1 reconciliation).

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations: this feature only adds new files under `.claude/skills/devcontainer-cli/` and modifies nothing existing (design §Delta: "No modifications to existing files").
- Step 2–5, 9–12: to roll back, delete the `.claude/skills/devcontainer-cli/` directory in its entirety. No other path is touched, so removal fully reverts the feature.
