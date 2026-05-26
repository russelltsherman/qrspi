# Design — using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-26
**Phase:** Design
**Status:** draft

## 1. Current State

The project has 10 agent skills under `.claude/skills/`, all following a consistent single-file pattern: one `SKILL.md` per skill directory with YAML frontmatter (name, description, command, argument-hint, allowed-tools) (ref: Q1), (ref: Q2).

No skill currently uses subdirectories (references/, scripts/, assets/) — the only exception is `qrspi-work` which has a `references/` folder with one markdown file (ref: Q1).

Existing skills are QRSPi-phase-specific (design, implement, plan, pr, questions, research, structure, ticket, work, worktree), each with its own slash-command trigger and scoped `allowed-tools` list (ref: Q3), (ref: Q5).

The eval harness exists in `evals/` and `scripts/` but has never been executed; `results/` contains only `.gitkeep` (ref: Q11).

A `using-graphite-cli` skill does not yet exist. The Graphite CLI is referenced externally (via personal git workflow) but has no encoded knowledge in the agent system.

Frontmatter validation is not enforced by the codebase; the eval harness reads SKILL.md files as raw text (ref: Q4).

The ticket specifies SKILL.md body under 500 lines / 5000 tokens — this is a human-review gate, not enforced programmatically (ref: Q10).

The Anthropic skill builder skill (`skill-creator`) is available for generating new skills.

## 2. Desired End State

**DS1:** A new skill directory `.claude/skills/using-graphite-cli/` exists with a valid `SKILL.md` that loads successfully in the Claude Code harness.

**DS2:** The SKILL.md contains frontmatter with all five standard fields: name (`using-graphite cli`), description, command (`/using-graphite-cli`), argument-hint (`<command>`), and allowed-tools (Bash with gt-specific globs).

**DS3:** The CLAUDE.md "Available skills" list is updated to include the new skill, following the existing convention of listing skills with slash-command and short description.

**DS4:** The skill body encodes the single-commit-per-branch convention as a hard rule: use `gt create` (not `git branch`) and `gt modify --all` (not `git commit --amend`).

**DS5:** The skill covers the complete Create -> Submit -> Modify -> Sync workflow loop with concrete command examples for each phase.

**DS6:** The skill documents conflict resolution using `gt continue` and explicitly warns against `git rebase --continue` on Graphite-tracked branches.

**DS7:** The skill includes stack navigation commands (`gt bu`, `gt bd`, `gt stack top`, `gt log short`) and directionality conventions (downstack = toward trunk, upstack = away from trunk).

**DS8:** Submit flag defaults are documented (`--no-edit --publish`) for automated agent use, along with shorthand equivalents.

**DS9:** Reference material in `references/` covers the full Graphite CLI command reference and edge cases.

**DS10:** The skill warns against mixing raw git commands (branch creation, rebase) with Graphite-tracked branches.

## 3. Delta

### New files

- `.claude/skills/using-graphite-cli/SKILL.md` — primary skill definition
- `.claude/skills/using-graphite-cli/references/cli-reference.md` — comprehensive command reference (new pattern — no existing skill has a references/ directory with substantive content)

### Modified files

- `.claude/CLAUDE.md` — add `using-graphite-cli` to the "Available skills" list

### New queries / references

- The skill must be registered in CLAUDE.md for discoverability (ref: Q3)
- The skill will follow the agentskills.io directory structure (SKILL.md + references/)

### Size constraints

- SKILL.md body: under 500 lines, under 5000 tokens (ref: Q10)
- Estimated SKILL.md body: ~150-200 lines
- Estimated references/cli-reference.md: ~100-150 lines

## 4. Pattern Decisions

### Decision 1: Directory structure — SKILL.md only vs SKILL.md + references/

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| SKILL.md only | Simpler, matches 9 of 10 existing skills | Body may exceed 500-line limit with full command coverage | |
| SKILL.md + references/cli-reference.md | Keeps body concise; reference material is complete | New pattern for this project (only qrspi-work has references/ but with only 64 lines) | **Recommended.** The ticket explicitly requires "detailed reference material in references/ directory covering full command reference and edge cases." The CLI surface is large enough that cramming it all into the body would risk the 500-line limit. |

### Decision 2: allowed-tools scoping — Bash vs Bash(gt:*)

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Bare `Bash` | No risk of missing command globs; matches qrspi-implement and qrspi-work | Less defensive; any bash command available | |
| `Bash(gt:*), Bash(git status:*)` | Restricts to only known-allowed commands; follows the pattern in qrspi-research, qrspi-design | Risk of missing a legitimate command; `gt` has many subcommands and flags | **Recommended: `Bash(gt:*), Bash(git status:*)`** — follow the existing restrictive pattern seen in most skills. The skill instructions themselves should guard against disallowed commands. We can always relax if a needed command is missing. |

### Decision 3: Command name — `/using-graphite-cli` vs `/gt`

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| `/using-graphite-cli` | Consistent with existing naming convention (all skills use descriptive names, not abbreviations); avoids collision with other potential `/gt*` skills | Longer, more verbose to type | **Recommended.** All 10 existing skills use descriptive names (`qrspi-design`, `qrspi-work`, etc.), not abbreviations. The command name should match the skill directory name per the naming convention (ref: Q3). |

### Decision 4: Description field quoting

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Quoted (double quotes) | Handles commas and special characters safely | Inconsistent with 9 of 10 existing skills | |
| Unquoted | Consistent with 9 of 10 existing skills; simpler | May need quoting if description contains commas | **Unquoted**, unless the description naturally contains characters that require it. Follow the majority pattern (ref: Q2). |

### Decision 5: New pattern for reference directory

The `references/` directory is a **new pattern** for this project's skill conventions. Only `qrspi-work` has a `references/` folder, and it contains a single 64-line markdown file about review cascades. The `cli-reference.md` in this skill is anticipated to be substantially larger (~100-150 lines) and serve as a comprehensive command catalog. This is the most significant deviation from existing conventions and may warrant discussion if the project scales to more CLI-based skills.

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SKILL.md body exceeds 500 lines or 5000 tokens | Medium | The skill fails the human-review gate; must be rewritten | Place the bulk of command details in `references/cli-reference.md`; keep SKILL.md body focused on workflow and conventions |
| `allowed-tools` is too restrictive and blocks legitimate `gt` subcommands | Medium | Agent cannot execute commands needed for the workflow | Start with `Bash(gt:*)` glob, add `Bash(git status:*)` and any other needed git commands; be prepared to relax if gaps are found |
| CLI reference becomes stale as Graphite CLI evolves | Low | Agent follows outdated commands | Note in the reference file that it is a snapshot; add a maintenance TODO |
| Collision with future `/gt`-named skills | Low | Two skills compete for the same command prefix | Use `using-graphite-cli` (not `/gt`) to avoid collision; note in CLAUDE.md that the command is unique |
| The skill-creator skill produces non-standard output | Low | Generated skill does not match project conventions | Review generated SKILL.md against the 10 existing skills before committing; hand-edit if needed |

## 6. Open Questions

- **Q1:** Should the skill be triggerable without arguments (no argument-hint) since it is a reference skill, or should it expect a command argument (e.g., `/using-graphite-cli submit`)? The existing skills all use argument-hint.
- **Q2:** The ticket says "Use the Anthropic skill builder skill to generate the skill" — should the design document specify the exact invocation pattern for the skill-creator, or is that implementation detail?
- **Q3:** Should the `references/cli-reference.md` be included in the skill's `allowed-tools` scope (e.g., `Read` is needed for the agent to load it)? All existing skills that have references/ files include `Read` in their allowed-tools.
- **Q4:** The ticket mentions "warns against mixing raw git branch/rebase commands" — should the skill also include the rescue procedure (how to recover if someone already broke a stack with raw git commands)?
- **Q5:** Is there an existing pattern for skills that are purely informational/reference (no artifacts to produce) versus skills that produce artifacts? The `using-graphite-cli` skill is reference-only — it does not create `.qrspi/` artifacts like the QRSPI-phase skills. How does this affect its `allowed-tools` (probably just `Bash` and `Read`)?
