# Implementation Plan — Create a new agent skill using glab cli

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 18

> Note: This ticket produces Markdown skill content, not executable code. Steps
> create new Markdown files; there are no runtime signatures. Each step honors
> the structure contracts: `dir == name == command-minus-slash`, the references
> split rule, eight-subcommand coverage, non-interactive + JSON-parsed CLI use,
> and the RecognizedState-vs-HardStopBlock distinction. Authoring runs through
> the global `skill-creator` skill per design Decision 4.

## Slice 1: Author the glab-cli skill (body + four references) via skill-creator

### Setup

1. Invoke the `skill-creator` skill to scaffold a new skill named `glab-cli`. This drives the create-skill flow and produces the `.claude/skills/glab-cli/` directory with a starter `SKILL.md`. Honors design Decision 4 (author via skill-creator).
   - **Note:** If skill-creator cannot run or verify in this environment (Unverified Assumption OQ3), stop and report; do not silently hand-author and skip the tool.

2. ✨ Create directory `.claude/skills/glab-cli/references/` — holds the four cohesive-topic reference files (contract: `body links every references/*.md`).

### Core Logic — SKILL.md body

3. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — write the frontmatter block.
   - **Current:** skill-creator starter frontmatter
   - **After:** five-field `SkillFrontmatter` — `name: glab-cli`, `command: /glab-cli`, quoted `description` enumerating glab/GitLab trigger phrases only (avoid collision with existing skill triggers), `argument-hint`, `allowed-tools` (frontmatter contract; `dir == name == command-minus-slash`).

4. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — add the Overview section summarizing scope: glab CLI guidance for agents, gitlab.com + self-hosted, non-interactive scripted use.

5. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — add the Authentication summary section (condensed; deep detail in references/authentication.md) and link to `references/authentication.md`.

6. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — add the condensed eight-subcommand-group section (auth, mr, issue, ci/pipeline, release, changelog, repo, api) and link to `references/commands.md` (contract: `command coverage = {…}`).

7. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — add the opinionated Workflow Patterns section: merge-after-green via `--when-pipeline-succeeds` / `glab ci status --wait`, stacked MRs, fork-based contributions; link to `references/ci-scripting.md`.

8. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — add the RecognizedState section: named judgment-call branches with deterministic recovery (existing MR on branch, missing release tag → `--ref`, failing pipeline at merge), kept textually distinct from infra failures (contract: `judgment calls = RecognizedState`).

9. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — add the agent/scripted-use rules: non-interactive flag on every invocation, JSON parsed via `glab … -F`/`jq`, multi-step flows folded into one `{"ok": …}` envelope (contract: `every CLI invocation is non-interactive + JSON-parsed`); link to `references/error-handling.md`.

10. ⚠️ Modify `.claude/skills/glab-cli/SKILL.md` — append the verbatim `HardStopBlock` (stop, print exact failing command + output, no workarounds) for auth/config/tooling failures (contract: `infra failures = HardStopBlock`).

### Core Logic — reference files

11. ✨ Create `.claude/skills/glab-cli/references/commands.md` — full subcommand/flag reference enumerating all eight groups: auth, mr, issue, ci/pipeline, release, changelog, repo, api. Source syntax from official glab docs at authoring time (Unverified Assumption: greenfield content, human spot-check required).

12. ✨ Create `.claude/skills/glab-cli/references/authentication.md` — `glab auth login` (OAuth vs PAT), `GITLAB_TOKEN` for CI, `--hostname` self-hosted, multi-host `config.yml`, conflict handling encoded as named states.
    - **Note:** Self-hosted/multi-host default (require explicit `--hostname` vs infer from remote) is undecided (Unverified Assumption OQ4); document explicit `--hostname` guidance and flag the open choice rather than inventing a precedent.

13. ✨ Create `.claude/skills/glab-cli/references/ci-scripting.md` — merge-after-green, `glab ci status --wait`, JSON parsing via `jq`, exit-code handling, single-envelope scripting pattern.

14. ✨ Create `.claude/skills/glab-cli/references/error-handling.md` — exit codes, recognized-state vs HARD-STOP distinction, verbatim error propagation.

### Tests

15. Run the skill-creator eval loop against the authored `glab-cli` skill (per design Decision 4).
    - **Expected:** skill validates as well-formed; auto-invocation `description` does not collide with existing skill triggers.
    - **Note:** The `evals/` harness is a non-functional placeholder and not a gate; the skill-creator eval loop is the authoring-time check, not the repo eval harness.

### Verify Slice 1

16. **Checkpoint:** `python3 - <<'PY'` frontmatter assertion (or manual inspection) confirming `name`/`command`/dir all equal `glab-cli`, `description` is quoted, `argument-hint` and `allowed-tools` present.
    - [ ] `name: glab-cli`, `command: /glab-cli`, directory `glab-cli/` all identical kebab-case
    - [ ] `description` quoted; `argument-hint` and `allowed-tools` present

17. **Checkpoint:** `wc -l .claude/skills/glab-cli/SKILL.md && ls .claude/skills/glab-cli/references/`
    - [ ] SKILL.md body within the ~500-line soft budget (deep detail pushed to references/; soft check only — no repo token/line gate, Unverified Assumption OQ1)
    - [ ] All four reference files exist (commands.md, authentication.md, ci-scripting.md, error-handling.md), each one cohesive topic
    - [ ] Body links every one of the four reference files

18. **Checkpoint:** `grep -n "ci/pipeline\|changelog\|release\|api\|issue\|repo\|auth\|mr" .claude/skills/glab-cli/references/commands.md` plus human spot-check.
    - [ ] commands.md enumerates all eight subcommand groups (auth, mr, issue, ci/pipeline, release, changelog, repo, api)
    - [ ] Body contains the verbatim HARD STOP block and a distinct RecognizedState section
    - [ ] Human spot-check of glab command/flag accuracy (greenfield content; no in-repo facts to verify against)

---

## Rollback Notes

- Steps 1–14 (all additive file creation): a new skill is purely additive (structure §Modified Types: None). To reverse, `rm -rf .claude/skills/glab-cli/`. No existing files are modified, so no restore of prior content is needed.
- Step 1 (skill-creator scaffold): if the tool created files outside `.claude/skills/glab-cli/`, remove only those; the directory delete above covers the in-scope output.
- No DB migrations, config changes, or destructive operations are involved.
