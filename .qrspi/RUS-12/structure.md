# Structure Outline — Create a new agent skill: using GitHub CLI

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> This is a documentation/skill-authoring feature, not application code. The
> "types" and "contracts" below are the structural conventions a `SKILL.md`
> and its `references/` must satisfy (frontmatter shape, link contract, tool
> scope). There are no runtime types, function signatures, or tests.

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the five-field convention every in-repo `SKILL.md` carries (ref: design §Decision 2). `name` == directory name == `command` stem. `description` embeds the trigger prose ("Use when…"). `argument-hint` may be empty/optional-topic for this no-argument knowledge skill.
- `ReferenceSet { gh-api.md, graphql.md, automation.md, extensions.md }`
  — the four detail files under `references/`, each cited from `SKILL.md` by a skill-directory-relative path (ref: design §Delta, §Decision 1).

## Modified Types

- none (no code types are added or changed; ref: design §Delta — "No DB/query changes", "no new tests").

## Contracts

These are the cross-slice/structural interfaces the artifact must honor:

- `frontmatter.name == "using-github-cli" == directoryName == command-stem` — registration contract (ref: design §Decision 2).
- `allowed-tools ⊇ {read tools, Bash(gh:*) scoped to read/metadata}` AND excludes all mutating git/PR operations — capability firewall; mutations defer to the orchestration layer / `using-graphite-cli` (ref: design §Decision 3, Risk 1). Pending OQ3.
- `SKILL.md → references/<file>.md` links use skill-directory-relative paths only (not absolute or repo-relative) — matches `qrspi-work/references/` precedent (ref: design Risk 4).
- `SKILL.md` body length < 500 lines and < 5000 tokens — manual budget (no automated gate; ref: design §Decision 4, Risk 2). Detail offloaded into `ReferenceSet`.
- CI auth guidance frames `GH_TOKEN` as a legitimate external-context auth pattern, explicitly distinguished from the in-repo-forbidden env-var config-routing workaround (ref: design Risk 5). Pending OQ2.

## Slice 1: Author the `using-github-cli` skill + references

**Goal:** A complete, self-contained, consultable skill exists at `.claude/skills/using-github-cli/` — valid five-field frontmatter, body under the 500-line/5000-token cap, and four `references/` files covering advanced `gh api`, GraphQL, automation/CI, and extensions — authored via the global `skill-creator` (ref: design §Desired End State, §Decision 1). End-to-end testable: an agent can load the skill and follow each reference link to working content.
**Files touched:**

- ✨ `.claude/skills/using-github-cli/SKILL.md` — self-contained skill body: frontmatter (Type `SkillFrontmatter`), trigger prose, opinionated defaults (squash merge, branch deletion, HEREDOC body), non-interactive scripting section (`--json`+`--jq`, `--no-pager`/`GH_PAGER=""`, `GH_PROMPT_DISABLED=1`, exit-code logic), and an explicit "defer mutations to the orchestration layer" boundary section (ref: design §Desired End State, Risk 1).
- ✨ `.claude/skills/using-github-cli/references/gh-api.md` — advanced `gh api` REST patterns (pagination, `--jq`, `-X` mutations, `--cache`, `--header`).
- ✨ `.claude/skills/using-github-cli/references/graphql.md` — GraphQL query examples for multi-resource joins.
- ✨ `.claude/skills/using-github-cli/references/automation.md` — non-interactive/CI recipes, scripting patterns, env vars (`GH_TOKEN` framed per the CI-auth contract).
- ✨ `.claude/skills/using-github-cli/references/extensions.md` — extension and alias recommendations.

**Verification:**
- [ ] Authored through the `skill-creator` skill (and its eval loop) — never hand-shipped ad-hoc (ref: design OQ1; user directive on skill-creator).
- [ ] `SKILL.md` frontmatter has exactly the five fields; `name` matches directory `using-github-cli` (manual check / skill-creator validation).
- [ ] `wc -l .claude/skills/using-github-cli/SKILL.md` < 500 and token budget < 5000 (manual; no automated gate, ref: design §Decision 4).
- [ ] Every `references/*.md` link in `SKILL.md` is skill-relative and resolves to an existing file (manual link check).
- [ ] `allowed-tools` is scoped to `gh` read/metadata + read tools and documents the mutation-deferral boundary (ref: Risk 1).
- [ ] Human review confirms each acceptance-criteria behavior from §Desired End State is present.

**Context cost:** L
**Depends on:** none

## Slice 2: Register the skill in project docs (optional, pending OQ4)

**Goal:** `.claude/CLAUDE.md` lists `using-github-cli` in the available-skills section and clarifies its boundary with the git-delegation / `using-graphite-cli` mandate, so the skill is discoverable and its scope is unambiguous (ref: design §Delta, OQ4). Independently verifiable: the skill name appears in the doc and the boundary note is present.
**Files touched:**

- ⚠️ `.claude/CLAUDE.md` (and/or the worktree copy) — add `using-github-cli` to the available-skills list; add a one-line boundary note distinguishing read/metadata `gh` use from orchestrator-only mutations (ref: design §Decision 3, Risk 1).

**Verification:**
- [ ] OQ4 resolved "yes" before doing this slice; if "no", skip the slice entirely.
- [ ] `using-github-cli` appears in the available-skills list in `.claude/CLAUDE.md`.
- [ ] The boundary note references the `using-graphite-cli` / orchestrator-only-mutation mandate.
- [ ] Human review.

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

These are design claims that could not be mapped to concrete, in-repo verifiable code/files and need human attention before planning:

- **OQ1 / "built using the skill builder":** The `skill-creator` (Anthropic builder) is out of repo (ref: design Risk 3, OQ1). Whether the implementer invokes it in-harness and treats its output as the artifact, or hand-authors to its conventions — and how "built using the skill builder" is evidenced — is unresolved. The user directive mandates using `skill-creator`, but its in-harness invocation contract cannot be documented from in-repo evidence.
- **OQ2 / CI auth depth:** Whether `GH_TOKEN` in CI is an accepted exception to the in-repo env-var-config prohibition, or must be framed only as an external-context pattern, is unresolved (ref: design Risk 5). Affects the `automation.md` content and the CI-auth contract above.
- **OQ3 / `allowed-tools` scope:** Whether the skill is advisory-only or may actually run `gh` (read/metadata) is unresolved (ref: design §Decision 3, Risk 1). The capability-firewall contract above assumes scoped-actionable (Option A); if advisory-only is chosen, the `allowed-tools` contract and the Slice 1 boundary section change.
- **OQ4 / CLAUDE.md update:** Whether to register the skill in `.claude/CLAUDE.md` at all is unresolved (ref: design OQ4). Slice 2 is gated entirely on this.
- **No automated verification exists** for any of this work: no SKILL.md lint, eval assertion, or unit test path exists in-repo (ref: design §Decision 4, Risk 2). All verification is human review plus manual `wc -l`/link/frontmatter checks — there is no regression gate.
