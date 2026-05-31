# Design — Create a new agent skill called using github cli

**Ticket:** RUS-12
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

The repository has ten skills under `.claude/skills/`, all of them QRSPI-workflow specific (ref: Q1). Only the `qrspi-work` skill includes a `references/` subdirectory; every other skill is a lone `SKILL.md` (ref: Q2). The repo already invokes `gh` from inside `qrspi-work` — six call patterns covering `gh repo view`, `gh pr list`, `gh pr view`, `gh pr edit`, and `gh api repos/.../pulls/.../comments`, all using `--json` + `--jq` and HEREDOC bodies (ref: Q3). The devcontainer installs the `gh` binary and bind-mounts the host's `~/.config/gh` read-only, so authentication is inherited at container start (ref: Q3, Q9). The repository contains no documented pattern for `gh issue`, `gh release`, `gh run`, `gh workflow`, or any non-PR `gh` surface (ref: Q3). Skill frontmatter follows a fixed schema: `name`, `description`, `command`, `argument-hint`, `allowed-tools` — `model` is reserved for the agent layer and does NOT appear in skills (ref: Q1). The `qrspi-work` skill is the canonical example of error-surfacing: a "HARD STOP" section forbids workarounds and mandates printing the verbatim error before exiting (ref: Q8). There is a Python-driven eval harness at `evals/` plus `scripts/`, but its assertions are tightly coupled to QRSPI phase outputs (ref: Q10). A separate `evals/graphite-evals.json` file demonstrates the convention that external-CLI wrapping skills get their own eval file (ref: Q11). No `skill-creator` skill exists locally; the one referenced in the ticket is a global plugin outside this project (ref: Q6).

## Desired End State

Acceptance criteria mapped to system behavior:

- **Skill follows agentskills.io directory structure with valid SKILL.md frontmatter** → A new directory `.claude/skills/using-github-cli/` exists containing `SKILL.md` (frontmatter matches the existing repo schema: `name`, `description`, `command`, `argument-hint`, `allowed-tools`) and a `references/` subdirectory with the four detailed reference files listed below.
- **Built using the Anthropic skill builder skill** → The authoring process for this new skill will be carried out via the global skill-creator plugin (a global skill, not in-repo). The deliverable is the resulting files committed to this repo; no in-repo wrapper for skill-creator is added (research found none).
- **SKILL.md body under 500 lines / 5000 tokens** → The body of `SKILL.md` is under 500 lines; detailed material moves to `references/`.
- **Detailed reference material in `references/` covering: advanced `gh api` patterns, GraphQL query examples, automation recipes, and extension recommendations** → Four reference files exist: `references/gh-api.md`, `references/graphql.md`, `references/automation.md`, `references/extensions.md`.
- **Covers authentication for both interactive and CI contexts** → `SKILL.md` includes an "Authentication" section that documents `gh auth status` checks, `GH_TOKEN` for CI/automation, and `gh auth login`/`gh auth switch` for workstations.
- **Encodes opinionated defaults (squash merge, branch deletion, HEREDOC body formatting)** → `SKILL.md` contains a "Defaults" section explicitly stating: squash merge with `--delete-branch` as default, HEREDOC for multi-line bodies, `--json`+`--jq` for parsing, `--no-pager`/`GH_PAGER=""` in non-interactive contexts.
- **Includes scripting patterns for non-interactive agent use** → A dedicated section "Scripting & automation" lives in `SKILL.md` (one-screen summary) with the deep recipes in `references/automation.md`.
- **Provides clear trigger conditions for skill activation** → The `description:` frontmatter follows the repo's high-recall pattern (cf. `qrspi-work` Q5) — enumerating literal user utterances ("create a PR", "list issues", "review PR #X", "run a workflow", "merge with squash") and naming `gh`/GitHub CLI explicitly.

## Delta

New files:

- `.claude/skills/using-github-cli/SKILL.md` — main skill body (~250–400 lines).
- `.claude/skills/using-github-cli/references/gh-api.md` — advanced `gh api` patterns (REST, pagination, mutations, headers, `--cache`).
- `.claude/skills/using-github-cli/references/graphql.md` — GraphQL query examples joining multiple resources.
- `.claude/skills/using-github-cli/references/automation.md` — non-interactive recipes (CI auth, `gh status`, alias setup, exit-code-driven scripts).
- `.claude/skills/using-github-cli/references/extensions.md` — recommended extensions (`gh-dash`, `gh-poi`, etc.) and the "prefer built-in" rule.
- `evals/gh-evals.json` — eval suite for the new skill (parallels `evals/graphite-evals.json`). Programmatic assertions limited to file existence, section presence, frontmatter validity, and reference-file completeness.

No modifications to existing files are required. `.claude/CLAUDE.md` does not list non-QRSPI skills in its "Available skills" block, so no update is needed there (the new skill is auto-discovered via its frontmatter).

## Pattern Decisions

### Decision 1: Skill structure (single file vs. SKILL.md + references)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single `SKILL.md` with everything inline | One file to load; simpler diff | Violates the ticket's 500-line / 5000-token cap; harder to navigate; no precedent in repo for inlining this much detail |
| B | `SKILL.md` + `references/` subdirectory | Mirrors the only existing precedent (`qrspi-work`); fits the ticket's explicit `references/` requirement; lets `SKILL.md` stay scan-able | Two-level discovery — agents must remember to read `references/` when needed |

**Recommendation:** Option B
**Rationale:** The ticket explicitly requires reference material under `references/`. The `qrspi-work` precedent demonstrates the pattern in this codebase (ref: Q2). Option A is disqualified by the line cap.
**NEW PATTERN?** No — directly follows `qrspi-work`.

### Decision 2: How rigorously to scope `allowed-tools`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bare `Bash` (like `qrspi-work`) | Matches dominant precedent; lets the skill use `gh`, `jq`, `git` interleaved | No bounded scope; `gh extension install` could mutate the user's environment if invoked |
| B | Fine-grained `Bash(gh:*)` (like `qrspi-design`'s `Bash(pwd:*)`) | Bounds shell calls to the wrapped CLI | Excludes `jq`, `cat`, `grep` which are needed alongside `gh`; precedent is thin — only one fine-grained example in the repo and it does not wrap a CLI in the same sense |
| C | `Bash`, `Read`, `Glob`, `Grep`, `Write` | Matches `qrspi-ticket` shape (ref: Q1) — covers reading repo files, writing PR bodies/templates, searching for context | Slightly broader than strictly needed for `gh`-only operations |

**Recommendation:** Option C
**Rationale:** A general-purpose `gh` skill is invoked in many contexts (PR creation, issue triage, automation). It needs to read repo files (e.g., a PR template), write commit/PR bodies, and search the repo. Option C matches the dominant repo precedent (ref: Q3) without overreaching. Option B's fine-grained scope is unproven for multi-binary workflows.
**NEW PATTERN?** No — same shape as `qrspi-ticket` minus the Linear MCP tools.

### Decision 3: Where to draw the authentication hard-stop line

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Document the `gh auth status` preflight as a recommendation only | Less rigid; works when caller already knows auth is fine | Lets an unauthenticated `gh` call cascade — the failure manifests later, deeper, and is harder to attribute |
| B | Mandate `gh auth status` as the first command, exit on failure with verbatim error (modeled on `qrspi-work`'s HARD STOP) | Surfaces config/auth errors at the boundary; aligns with the repo's hard-stop pattern (ref: Q8); matches the global `feedback_error_surfacing` memory rule | One extra command per skill invocation; can be skipped in trivial read-only contexts |

**Recommendation:** Option B
**Rationale:** The repo already enforces "stop on infrastructure errors" (ref: Q8). Inheriting that pattern for `gh auth status` is consistent and matches user MEMORY.md directives on error surfacing. The cost (one extra call) is negligible.
**NEW PATTERN?** No — direct application of the `qrspi-work` HARD STOP section to a new CLI surface.

### Decision 4: Eval coverage scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | No eval file — skill is a docs deliverable | Lowest effort; skill content is mostly prose | Violates the convention demonstrated by `evals/graphite-evals.json` (ref: Q11); regressions go undetected |
| B | Structural eval — `evals/gh-evals.json` checks file existence, frontmatter validity, required sections, and reference-file presence | Cheap; deterministic; matches the QRSPI assertion grammar (ref: Q10) | Does not exercise the skill's actual `gh` behavior |
| C | Behavioral eval — spin up `gh` in a sandbox and exercise commands | Highest realism | Requires fixture repositories, mock `gh` server, or sandboxed network — out of scope for this ticket |

**Recommendation:** Option B
**Rationale:** Behavioral evals for `gh` need infrastructure that does not exist in this repo (ref: Q10, Q11). Structural assertions are sufficient to catch missing reference files, malformed frontmatter, or accidental deletion. Mirrors the apparent purpose of `evals/graphite-evals.json`.
**NEW PATTERN?** No — parallels `graphite-evals.json`.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gh` and `git` overlap (e.g., creating PRs vs. pushing branches). Skill could give conflicting guidance to the using-graphite-cli skill. | medium | medium | Add a "Boundary with git/graphite" section to `SKILL.md` that defers branch/commit operations to Graphite and reserves `gh` for GitHub-side operations (PRs, issues, releases, Actions). |
| Skill body drifts above the 500-line cap as recipes accrete. | medium | medium | Keep `SKILL.md` to high-signal patterns; route depth to `references/`. CI / eval can include a line-count assertion. |
| Description-field triggering competes with existing skills (e.g., user says "create PR" and Claude picks the wrong skill). | low | medium | Name the skill `using-github-cli` (parallel to `using-graphite-cli`) and have the description prefix concrete `gh` verbs and the literal string `gh` to disambiguate. |
| Authentication assumption (host bind-mount) breaks outside the devcontainer. | medium | high | The skill's first instruction is `gh auth status` with a HARD STOP on failure (ref: Q8). The reference file `gh-api.md` documents `GH_TOKEN` for CI contexts. |
| Reference files become stale relative to upstream `gh` CLI releases. | medium | low | Cite `gh help <command>` as the canonical authority in each reference file; date-stamp the frontmatter. |
| The eval harness can't grade skill prose meaningfully — only structural assertions. | low | low | Accept structural-only assertions for this ticket; defer behavioral evals to a future ticket if/when sandboxed `gh` execution is set up. |

## Open Questions

- OQ1: Should `evals/gh-evals.json` be added in this ticket's deliverable, or deferred? The ticket's acceptance criteria do not explicitly require eval coverage, but the codebase convention (ref: Q11) suggests parallel eval files for external-CLI skills. Default in this design is to include the file with structural assertions.
- OQ2: Should the global skill-creator plugin be invoked as part of the implementation (per the ticket "Process" step 1), or is hand-authoring while following the agentskills.io structure acceptable? The plugin is not present in this repo; the implementation will need a human decision before slice 1 starts.
- OQ3: Are there team or org-specific GitHub conventions (e.g., default reviewer groups, merge style enforced by branch protection) that should be encoded as opinionated defaults? Default in this design is to encode the conventions from the ticket body verbatim and let the reviewer flag any local overrides.
