# Structure Outline — Create a new agent skill called using github cli

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This is a content/docs deliverable — no programmatic types are introduced. The only "type-like" surface is the SKILL.md frontmatter schema, which is fixed by Claude Code and not invented here:

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: comma-separated-list }` — pre-existing schema (ref: design.md §Delta, research Q1).
- `EvalCase { id: string, name: string, phase: string, prompt: string, context: object, assertions: Assertion[] }` — pre-existing schema in `evals/suite.json` and `evals/graphite-evals.json` (ref: research Q10).
- `Assertion { type: "programmatic", check: string, weight: number }` — pre-existing schema (ref: research Q10).

## Modified Types

None.

## Contracts

This is a docs-only deliverable; no functions or APIs are created. The contracts are the structural rules that downstream evals enforce:

- `SKILL.md` MUST have frontmatter with all five required keys (`name`, `description`, `command`, `argument-hint`, `allowed-tools`).
- `SKILL.md` body MUST be ≤ 500 lines (ref: design.md §Desired End State).
- `references/` MUST contain four named files: `gh-api.md`, `graphql.md`, `automation.md`, `extensions.md`.
- `evals/gh-evals.json` MUST be a valid JSON object containing at least one `case` with at least one programmatic assertion.
- `SKILL.md` MUST contain top-level sections (level-2 headings) covering: Authentication, PR Workflows, Code Review, Issue Management, Releases & Versioning, GitHub Actions, API Queries, Repository Management, Scripting & Automation, Boundary with git/graphite, Defaults, Hard Stop on Auth Errors.

## Slice 1: Author the SKILL.md and references

**Goal:** A reviewer can `cat .claude/skills/using-github-cli/SKILL.md` and the four reference files and confirm: frontmatter is valid; body ≤ 500 lines; trigger description is high-recall; all required sections present; HEREDOC and `--json`/`--jq` patterns documented; auth hard-stop documented; reference files are populated with non-placeholder content.
**Files touched:**

- ✨ `.claude/skills/using-github-cli/SKILL.md` — main skill body. Frontmatter, role statement, Authentication, PR Workflows, Code Review, Issue Management, Releases, Actions, API Queries, Repo Management, Scripting & Automation, Boundary with git/graphite, Defaults, Hard Stop. Cross-links to `references/`.
- ✨ `.claude/skills/using-github-cli/references/gh-api.md` — advanced `gh api` patterns: REST CRUD, `--paginate`, `--jq`, `--cache`, custom headers, batch mutations.
- ✨ `.claude/skills/using-github-cli/references/graphql.md` — GraphQL examples: PR with reviews + checks + commits; cross-repo queries; pagination.
- ✨ `.claude/skills/using-github-cli/references/automation.md` — non-interactive recipes: CI auth via `GH_TOKEN`, `GH_PROMPT_DISABLED=1`, `--no-pager`, exit-code-driven scripts, `gh status` dashboards, alias definitions.
- ✨ `.claude/skills/using-github-cli/references/extensions.md` — recommended extensions and the "prefer built-in" rule.

**Verification:**

- [ ] `head -10 .claude/skills/using-github-cli/SKILL.md` shows valid YAML frontmatter with the five required keys.
- [ ] `wc -l .claude/skills/using-github-cli/SKILL.md` returns ≤ 500.
- [ ] `grep -c '^## ' .claude/skills/using-github-cli/SKILL.md` returns ≥ 12 (matches the contract section list).
- [ ] Each of the four reference files exists and is non-empty: `[ -s .claude/skills/using-github-cli/references/gh-api.md ]` (etc.).
- [ ] `grep -q '\-\-json' .claude/skills/using-github-cli/SKILL.md && grep -q '\-\-jq' .claude/skills/using-github-cli/SKILL.md` — the `--json`/`--jq` opinion is encoded.
- [ ] `grep -q 'gh auth status' .claude/skills/using-github-cli/SKILL.md` — the auth preflight is documented.
- [ ] `grep -qi 'HARD STOP\|hard-stop' .claude/skills/using-github-cli/SKILL.md` — the auth hard-stop rule is documented.
- [ ] `grep -q 'GH_TOKEN' .claude/skills/using-github-cli/SKILL.md` — CI auth context is covered.
- [ ] `grep -qi 'squash' .claude/skills/using-github-cli/SKILL.md` — the squash-merge default is documented.
- [ ] `grep -q "HEREDOC\|cat <<'EOF'" .claude/skills/using-github-cli/SKILL.md` — HEREDOC formatting opinion is documented.

**Context cost:** M
**Depends on:** none

## Slice 2: Add eval coverage

**Goal:** A reviewer can run the eval harness (or inspect `evals/gh-evals.json`) and see the new skill is graded by the same convention as `evals/graphite-evals.json` — at minimum, structural assertions that catch regressions (file existence, frontmatter validity, required sections).
**Files touched:**

- ✨ `evals/gh-evals.json` — eval suite with one or more cases asserting: SKILL.md exists; frontmatter has all required keys; line count ≤ 500; reference files present; required sections present.

**Verification:**

- [ ] `python3 -c "import json; json.load(open('evals/gh-evals.json'))"` succeeds (valid JSON).
- [ ] `python3 -c "import json; d=json.load(open('evals/gh-evals.json')); assert len(d['cases']) >= 1; assert all(len(c['assertions']) >= 1 for c in d['cases'])"` succeeds.
- [ ] The eval file references the new skill's path at least once: `grep -q 'using-github-cli' evals/gh-evals.json`.

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- The global "Anthropic skill builder skill" (referenced in the ticket's Process step 1) cannot be observed from inside this repo (research Q6 confirmed it is not local). The implementation will not invoke that plugin; it will hand-author the skill following the agentskills.io standard. If a reviewer wants the plugin used instead, the slice plan will need to be revised.
- The 500-line / 5000-token cap from the ticket is interpreted strictly per the SKILL.md body. The frontmatter and reference files are excluded from that count. Reviewer should confirm.
- `evals/gh-evals.json` is being added under the convention demonstrated by `evals/graphite-evals.json`. The convention has not been documented in writing anywhere in the repo; reviewer should confirm this is the right home for the file (vs. a future generic skill-eval harness).
- The slice ordering assumes a single human reviewer in a single review cycle. If the project switches to per-reference-file review, slice 1 should fan out into one slice per reference file.
