# PR: RUS-5 — Add writing-bash-scripts agent skill

## Summary

This PR adds a new `writing-bash-scripts` agent skill that provides Claude Code
with comprehensive guidance for producing robust, portable, ShellCheck-clean bash
scripts. The skill follows the agentskills.io directory structure with a concise
SKILL.md body (273 lines, well under the 500-line limit) and four topic-split
reference files covering conventions, patterns, gotchas, and a canonical template
script. Reviewers should focus on the QRSPI planning artifacts committed to the
repo (the skill files themselves live at `~/.agents/skills/writing-bash-scripts/`,
which is user-global and outside version control). The template script passes
ShellCheck with zero warnings (shellcheck v0.11.0).

**Important:** The primary deliverable (the skill itself) lives at
`~/.agents/skills/writing-bash-scripts/` on the developer's machine, outside this
repository. The git diff contains only the QRSPI planning artifacts that document
the design, structure, plan, and implementation log for the skill.

---

## Acceptance Criteria Mapping

| Criterion | Implementation File(s) | Verification |
|-----------|----------------------|--------------|
| Skill follows agentskills.io directory structure with valid SKILL.md frontmatter | `~/.agents/skills/writing-bash-scripts/SKILL.md` | Frontmatter contains `name`, `description`, `command` fields; `references/` subdirectory exists with 4 files |
| Built using the Anthropic skill builder skill | `~/.agents/skills/writing-bash-scripts/SKILL.md` | Skill-creator skill was invoked during authoring (see impl-log.md) |
| SKILL.md body under 500 lines / 5000 tokens | `~/.agents/skills/writing-bash-scripts/SKILL.md` | `wc -l SKILL.md` = 273 lines (under 500 limit) |
| Detailed reference material in references/ directory if needed | `references/conventions.md`, `references/patterns.md`, `references/gotchas.md`, `references/template.sh` | All 4 files exist; total 914 lines of reference material |
| Produces ShellCheck-clean output when an agent follows the guidance | `references/template.sh` + all code examples | `shellcheck references/template.sh` exits 0 with zero warnings |

---

## Changes by Slice

### Slice 1: Author complete skill (SKILL.md + all references)

#### Skill files (user-global, outside repo)

| File | Change Type | Lines |
|------|------------|-------|
| `~/.agents/skills/writing-bash-scripts/SKILL.md` | new | 273 |
| `~/.agents/skills/writing-bash-scripts/references/template.sh` | new | 104 |
| `~/.agents/skills/writing-bash-scripts/references/conventions.md` | new | 247 |
| `~/.agents/skills/writing-bash-scripts/references/patterns.md` | new | 243 |
| `~/.agents/skills/writing-bash-scripts/references/gotchas.md` | new | 320 |

#### QRSPI artifacts (in-repo, tracked by git)

| File | Change Type | Lines Added |
|------|------------|-------------|
| `.qrspi/RUS-5/questions.md` | new | 52 |
| `.qrspi/RUS-5/research.md` | new | 467 |
| `.qrspi/RUS-5/design.md` | new | 143 |
| `.qrspi/RUS-5/structure.md` | new | 58 |
| `.qrspi/RUS-5/plan.md` | new | 197 |
| `.qrspi/RUS-5/worktree.md` | new | 89 |
| `.qrspi/RUS-5/impl-log.md` | new | 14 |

**Total in-repo:** 7 files, 1020 lines added

---

## Testing Summary

- [x] `shellcheck references/template.sh` -- exit 0, zero warnings (shellcheck v0.11.0)
- [x] `wc -l SKILL.md` -- 273 lines (under 500 limit)
- [x] Frontmatter validation -- `name`, `description`, `command` fields all present
- [x] Reference pointer count -- `grep -c 'references/' SKILL.md` = 5 (exceeds minimum of 4)
- [x] All reference files exist -- `conventions.md`, `patterns.md`, `gotchas.md`, `template.sh` confirmed
- [x] Skill discovery -- Claude Code auto-discovered the skill (confirmed by system reminder listing `writing-bash-scripts` in available skills during implementation session)

---

## Deviations from Structure

| Deviation | Description | Impact |
|-----------|-------------|--------|
| SKILL.md body length | 273 lines vs. target of 150-200 lines | Low -- well under 500-line hard limit. Extra length from inline code examples that provide immediate value for simple scripts without requiring reference file reads. Reasonable tradeoff for usability. |

No other deviations from `structure.md` contracts.

---

## Risks & Rollback

Updated risk register from `design.md` with implementation findings:

| Risk | Design Assessment | Implementation Outcome |
|------|-------------------|----------------------|
| SKILL.md exceeds 500-line limit | High likelihood / Medium impact | **Mitigated.** 273 lines -- over the 150-200 target but well under the 500-line hard limit. Progressive disclosure works as designed. |
| Agent ignores reference file pointers | Medium likelihood / Medium impact | **Mitigated by design.** SKILL.md contains 5 conditional Read instructions with clear trigger conditions (e.g., "If writing a multi-command script..."). Effectiveness depends on agent behavior at runtime -- no automated enforcement possible. |
| Template script becomes stale relative to prose | Low likelihood / Low impact | **Accepted.** Template is 104 lines, self-contained. Header comment cross-references SKILL.md. |
| Frontmatter `command` field fails validation | Medium likelihood / Low impact | **Accepted.** `quick_validate.py` would reject `command` but that validator is not in CI and Claude Code discovery works independently. Confirmed by live skill discovery. |
| ShellCheck compliance unverifiable without CI | Medium likelihood / Medium impact | **Partially mitigated.** `template.sh` verified clean with shellcheck v0.11.0. No CI enforcement exists. shellcheck was installed to user-local npm prefix (`/home/vscode/.local/node_modules/.bin/shellcheck`). |

### Rollback procedure

All skill files are net-new with no modifications to existing files. Full rollback:

```bash
rm -rf ~/.agents/skills/writing-bash-scripts/
```

No database migrations, config changes, or destructive operations involved.

---

## Open Items

| Item | Type | Notes |
|------|------|-------|
| CI enforcement of ShellCheck | Tech debt | No pre-commit hook or CI pipeline runs shellcheck on scripts. Enforcement is manual. |
| `quick_validate.py` allow-list | Tech debt | The validator's hardcoded allow-list does not include `command` or `argument-hint` fields used by project skills. Out of scope for this ticket. |
| Retroactive application to existing scripts | Deferred | `run_loop.sh` and `.devcontainer/config/post-start.sh` exist in the project but were not refactored under this skill. Forward-looking only per design decision. |
| Eval harness integration | Deferred | The project eval harness has orchestration infrastructure but agent execution is stubbed. Skill effectiveness cannot be measured until evals are functional. |
| Skill files not in version control | Architectural | Skill lives at `~/.agents/skills/` (user-global). Not tracked by any repository. Consider a dotfiles repo or backup strategy for user-global skills. |
