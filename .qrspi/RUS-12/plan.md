# Implementation Plan — Create a new agent skill: using GitHub CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 17

> Documentation/skill-authoring feature. No runtime types, signatures, or automated
> tests exist. "Tests" steps are manual checks (frontmatter, line/token budget, link
> resolution). All authoring goes through the global `skill-creator` skill per the user
> directive and design OQ1.

## Slice 1: Author the `using-github-cli` skill + references

### Setup

1. ⚙️ Invoke the global `skill-creator` skill (and its eval loop) to scaffold/author the new skill — never hand-ship ad-hoc (ref: structure Verification §Slice 1; design OQ1; user directive). All files in this slice are produced/validated through `skill-creator`.
2. ✨ Create `.claude/skills/using-github-cli/SKILL.md` — frontmatter only first: the five fields of Type `SkillFrontmatter` (`name`, `description`, `command`, `argument-hint`, `allowed-tools`). Set `name: using-github-cli` and `command` stem to match the directory (registration contract, ref: structure Contracts). `argument-hint` empty/optional-topic (no-argument knowledge skill).
3. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — set the `description` field to embed trigger prose ("Use when…") matching the in-repo prose-trigger convention (ref: design §Decision 2).
   - **Current:** `description:` empty/placeholder
   - **After:** `description:` contains one-string trigger prose per Decision 2
4. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — set `allowed-tools` scoped to read tools + `Bash(gh:*)` restricted to read/metadata, excluding all mutating git/PR operations (capability-firewall contract, ref: structure Contracts; design §Decision 3, Risk 1). Pending OQ3 — if advisory-only is chosen, narrow to read-only.
   - **Current:** `allowed-tools:` empty/placeholder
   - **After:** `allowed-tools:` = read tools + scoped `Bash(gh:*)` read/metadata

### Core Logic

5. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — add the opinionated-defaults section: squash merge, branch deletion after merge, HEREDOC for PR/issue body (ref: design §Desired End State).
6. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — add the non-interactive scripting section: `--json`+`--jq`, `--no-pager`/`GH_PAGER=""`, `GH_PROMPT_DISABLED=1`, and exit-code logic (ref: design §Desired End State; Q6/Q7).
7. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — add the auth section: `gh auth status` verification, interactive `gh auth login`, and `GH_TOKEN`/CI framed as a legitimate external-context auth pattern, explicitly distinguished from the in-repo-forbidden env-var config-routing workaround (CI-auth contract, ref: structure Contracts; design Risk 5). Pending OQ2.
8. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — add the "defer mutations to the orchestration layer" boundary section pointing mutating git/PR operations to the orchestrator / `using-graphite-cli` (ref: structure Contracts; design Risk 1).
9. ⚠️ Modify `.claude/skills/using-github-cli/SKILL.md` — add the four `references/*.md` links using skill-directory-relative paths only (link contract, ref: structure Contracts; design Risk 4).
   - **Current:** body has no reference links
   - **After:** body links `references/gh-api.md`, `references/graphql.md`, `references/automation.md`, `references/extensions.md` via skill-relative paths
10. ✨ Create `.claude/skills/using-github-cli/references/gh-api.md` — advanced `gh api` REST patterns: pagination, `--jq`, `-X` mutations, `--cache`, `--header` (ref: structure §Slice 1 Files; Type `ReferenceSet`).
11. ✨ Create `.claude/skills/using-github-cli/references/graphql.md` — GraphQL query examples for multi-resource joins (ref: structure §Slice 1 Files).
12. ✨ Create `.claude/skills/using-github-cli/references/automation.md` — non-interactive/CI recipes, scripting patterns, env vars (`GH_TOKEN` framed per the CI-auth contract) (ref: structure §Slice 1 Files; design Risk 5).
13. ✨ Create `.claude/skills/using-github-cli/references/extensions.md` — extension and alias recommendations (ref: structure §Slice 1 Files).

### Tests

14. Manual frontmatter + budget check — confirm exactly the five frontmatter fields, `name` == directory `using-github-cli`, and body within budget.
    - Run: `awk '/^---$/{c++;next} c==1' .claude/skills/using-github-cli/SKILL.md` (inspect frontmatter) and `wc -l .claude/skills/using-github-cli/SKILL.md`
    - **Expected:** five fields present; `name: using-github-cli`; `wc -l` < 500 and est. token budget < 5000 (ref: structure Contracts; design §Decision 4).

### Verify Slice 1

15. **Checkpoint:** `for f in SKILL.md references/gh-api.md references/graphql.md references/automation.md references/extensions.md; do test -s ".claude/skills/using-github-cli/$f" && echo "OK $f" || echo "MISSING $f"; done; wc -l .claude/skills/using-github-cli/SKILL.md`
    - [ ] Authored through `skill-creator` (and its eval loop), not hand-shipped (design OQ1; user directive).
    - [ ] All five files exist and are non-empty.
    - [ ] Frontmatter has exactly five fields; `name` matches directory `using-github-cli`.
    - [ ] `wc -l SKILL.md` < 500 and token budget < 5000 (manual; no automated gate).
    - [ ] Every `references/*.md` link in `SKILL.md` is skill-relative and resolves to an existing file.
    - [ ] `allowed-tools` scoped to `gh` read/metadata + read tools; mutation-deferral boundary documented (Risk 1).
    - [ ] Human review confirms each §Desired End State acceptance behavior is present.

---

## Slice 2: Register the skill in project docs (optional, pending OQ4)

> Entire slice is gated on OQ4 resolving "yes". If "no", skip steps 16–17.

### Core Logic

16. ⚠️ Modify `.claude/CLAUDE.md` (and the worktree copy `.worktrees/RUS-12/.claude/CLAUDE.md` if applicable) — add `using-github-cli` to the available-skills list and add a one-line boundary note distinguishing read/metadata `gh` use from orchestrator-only mutations / `using-graphite-cli` (ref: structure §Slice 2; design §Decision 3, Risk 1, OQ4).
    - **Current:** available-skills list has no `using-github-cli` entry
    - **After:** list includes `using-github-cli` plus the one-line boundary note

### Verify Slice 2

17. **Checkpoint:** `grep -n "using-github-cli" .claude/CLAUDE.md && grep -n "using-graphite-cli" .claude/CLAUDE.md`
    - [ ] OQ4 resolved "yes" before doing this slice (else skipped entirely).
    - [ ] `using-github-cli` appears in the available-skills list in `.claude/CLAUDE.md`.
    - [ ] The boundary note references the `using-graphite-cli` / orchestrator-only-mutation mandate.
    - [ ] Human review.

---

## Rollback Notes

- Step 2 / Slice 1: to reverse, delete the directory `.claude/skills/using-github-cli/` in its entirety (removes `SKILL.md` and all `references/`). No registration side effects until Slice 2.
- Step 16 / Slice 2: config/doc change. To reverse, remove the `using-github-cli` list entry and boundary note from `.claude/CLAUDE.md` (and the worktree copy). No data migration; purely textual.
