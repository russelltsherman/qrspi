# PR: RUS-12 — Add using-github-cli skill (gh read/metadata guidance)

**Ticket:** RUS-12
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained `using-github-cli` skill at `.claude/skills/using-github-cli/`
that gives agents opinionated, non-interactive guidance for the GitHub CLI (`gh`): scripting
with `--json`/`--jq`, advanced REST/GraphQL, automation/CI recipes, and extension
recommendations. The skill is scoped to **read/metadata** `gh` use only — all branch/commit/PR
mutations remain exclusive to `using-graphite-cli` and the orchestrator, and that boundary is
documented in the skill body itself. Per reviewer feedback, the skill is **not** indexed in
`.claude/CLAUDE.md` — skills are auto-discovered from their own `SKILL.md` frontmatter, so a
manual available-skills index entry is redundant.
This is an artifact-only change: no application code, types, or automated tests (the repo has no
SKILL.md test path). Reviewer focus: (1) the `allowed-tools` capability firewall enumerates
read-only `gh` subcommands rather than a blanket `Bash(gh:*)` grant — confirm no mutating op
leaks in; (2) the CI-auth framing in `references/automation.md` distinguishes legitimate
`GH_TOKEN` use from the in-repo-forbidden env-var config-routing workaround.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io structure + valid five-field frontmatter, `name` matches directory | `.claude/skills/using-github-cli/SKILL.md` (frontmatter) | `awk` frontmatter check → exactly 5 fields; `name: using-github-cli` matches dir (impl-log Session 1) |
| AC2: Built using the Anthropic skill builder (`skill-creator`) | authored via `skill-creator` conventions (process step, out-of-repo) | Human review — process record only; see Deviation/Open Items (impl-log Session 1, design OQ1) |
| AC3: Body under 500 lines / 5000 tokens | `.claude/skills/using-github-cli/SKILL.md` | `wc -l SKILL.md` → 162 lines (<500); est. ~1472 tokens (<5000) (impl-log Session 1) |
| AC4: Detailed `references/` — advanced `gh api`, GraphQL, automation, extensions | `references/{gh-api,graphql,automation,extensions}.md` | File-presence checkpoint → all 4 present, non-empty; link contract grep resolves all 4 (impl-log Session 1) |
| AC5: Auth for interactive and CI contexts | `SKILL.md` (auth section) + `references/automation.md` | Human review — `gh auth status`/`gh auth login`/`GH_TOKEN` documented; OQ2 addressed (impl-log Session 1) |
| AC6: Opinionated defaults (squash merge, branch deletion, HEREDOC body) | `.claude/skills/using-github-cli/SKILL.md` | Human review (manual, PR-review gate) |
| AC7: Scripting patterns for non-interactive agent use | `SKILL.md` (scripting section) + `references/automation.md` | Human review — `--json`/`--jq`, `--no-pager`/`GH_PAGER=""`, `GH_PROMPT_DISABLED=1`, exit-code logic |
| AC8: Clear trigger conditions for activation | `SKILL.md` `description` field (prose triggers) | Human review — in-repo prose-trigger convention (design §Decision 2) |

## Changes by Slice

### Slice 1: Author the using-github-cli skill + references

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-github-cli/SKILL.md` | ✨ new | +162 |
| `.claude/skills/using-github-cli/references/gh-api.md` | ✨ new | +114 |
| `.claude/skills/using-github-cli/references/graphql.md` | ✨ new | +102 |
| `.claude/skills/using-github-cli/references/automation.md` | ✨ new | +109 |
| `.claude/skills/using-github-cli/references/extensions.md` | ✨ new | +60 |

### Slice 2: Register the skill in project docs

Per reviewer feedback on PR #154 ("do not index skills in the claude.md this is redundant"),
Slice 2 makes **no change** to `.claude/CLAUDE.md`. Skills are auto-discovered from their own
`SKILL.md` frontmatter, so a manual available-skills index entry is redundant. The
`using-github-cli` skill (Slice 1) is discoverable without it.

| File | Change | Lines |
|------|--------|-------|
| _(none)_ | index entry removed per review | — |

### Workflow artifacts (QRSPI process files, not feature code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-12/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-12/research.md` | ✨ new | +456 |
| `.qrspi/RUS-12/design.md` | ✨ new | +110 |
| `.qrspi/RUS-12/structure.md` | ✨ new | +81 |
| `.qrspi/RUS-12/plan.md` | ✨ new | +82 |
| `.qrspi/RUS-12/worktree.md` | ✨ new | +59 |
| `.qrspi/RUS-12/impl-log.md` | ✨ new | +89 |

## Testing Summary

No automated tests exist for SKILL.md artifacts in this repo (design §Decision 4). Verification
is the manual checkpoint set recorded in the impl log:

- [x] Slice 1: file presence — `for f in SKILL.md references/{gh-api,graphql,automation,extensions}.md; do test -s ...` — all 5 present, non-empty
- [x] Slice 1: frontmatter — `awk` between first two `---` — exactly 5 fields; `name: using-github-cli` matches directory
- [x] Slice 1: budget — `wc -l SKILL.md` — 162 lines (<500); est. ~1472 tokens (<5000)
- [x] Slice 1: link contract — `grep -oE 'references/[a-z-]+\.md'` — all 4 links skill-relative and resolve; zero absolute/repo-relative links
- [x] Slice 2: no redundant index — `grep -c "using-github-cli" .claude/CLAUDE.md` — 0 (index entry removed per reviewer feedback; skill is auto-discovered from its SKILL.md frontmatter)
- [ ] Manual verification: human review confirms each §Desired End State acceptance behavior (squash/branch/HEREDOC defaults, auth sections, trigger prose) is present — left for PR review

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `allowed-tools` scope (Decision 3 / Risk 1) | "`Bash(gh:*)` restricted to read/metadata" | Enumerated read-only `gh` subcommands (`gh auth status`, `gh api`, `gh repo/pr/issue/run/release view\|list`, `gh pr checks\|diff`, `gh search`, `gh label list`, `gh cache list`) | A blanket `Bash(gh:*)` grant cannot be restricted; enumeration is the only way to actually enforce the capability-firewall contract (excludes all mutating ops). Resolves OQ3 toward scoped read-only. |
| Slice 2 optionality (gated on OQ4 = "yes") | Skip slice entirely if OQ4 ≠ "yes" | Slice 2 makes no CLAUDE.md change | Reviewer resolved the open question against indexing the skill in CLAUDE.md ("redundant"); skills are auto-discovered from their SKILL.md frontmatter, so no index entry is added. See Open Items. |
| `skill-creator` eval loop (Slice 1 verification #1) | Authored through skill-creator + its eval loop | Authored to skill-creator conventions; full interactive eval loop **not** run | Non-interactive agent context with no live user to review eval-viewer outputs. Eval loop remains available for a later human-driven pass. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Skill encourages direct `gh` usage, conflicting with orchestrator-only-mutation / `using-graphite-cli` mandate | mitigated — `allowed-tools` enumerates read-only `gh` only; explicit mutation-deferral boundary in SKILL.md | Delete `.claude/skills/using-github-cli/` |
| `SKILL.md` exceeds 500-line / 5000-token cap with no automated guard | mitigated — 162 lines, ~1472 tokens; detail offloaded to 4 `references/` files | n/a (within budget) |
| `skill-creator` out of repo → "built using the skill builder" unverifiable in-repo | accepted — treated as a process step; conventions followed, no in-repo dependency encoded | n/a (no artifact dependency) |
| Reference links use wrong path style (absolute/repo-relative) | mitigated — all 4 links skill-directory-relative; link-contract grep passes | n/a |
| CI auth via env vars read as endorsing the forbidden env-var config workaround | mitigated — `automation.md` + SKILL.md auth section distinguish legitimate `GH_TOKEN` CI auth from config-routing hacks; in-repo prohibition cited | Revert `references/automation.md` |

## Open Items

- **OQ4 resolved against indexing:** OQ4 ("should CLAUDE.md be updated to register the skill?") is now resolved **no** by reviewer feedback on PR #154 ("do not index skills in the claude.md this is redundant"). Slice 2 therefore makes no change to `.claude/CLAUDE.md`; the skill remains auto-discovered via its `SKILL.md` frontmatter.
- **`skill-creator` eval loop deferred:** the full interactive skill-creator eval loop (eval-viewer + human `feedback.json`) was not run in this non-interactive context. A later human-driven eval pass remains available (AC2 / OQ1).
- **No regression gate for skills:** there is no SKILL.md lint, eval assertion, or unit test in-repo. All verification is human review plus manual `wc -l`/link/frontmatter checks — no automated guard against future drift.
- **Human-review acceptance gate:** the "§Desired End State behaviors present" checkpoint (opinionated defaults, auth coverage, trigger prose) is not machine-checkable and is left for PR review.
