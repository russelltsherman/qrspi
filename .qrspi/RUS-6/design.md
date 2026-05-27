# Design — using graphite cli skill

**Ticket:** RUS-6
**Research basis:** direct `gt --help` and `gt <cmd> --help` exploration (questions.md and research.md not yet generated for this ticket)
**Generated:** 2026-05-27
**Status:** draft

## Current State

- The Graphite CLI (`gt`) is installed at `/usr/bin/gt` and supports stacked PR workflows on GitHub. It has a rich command surface covering initialization, branch creation, modification, stacking, navigation, submission, and merging. (ref: GT1)
- The project already uses `gt` commands extensively within the qrspi-work SKILL.md: `gt create`, `gt modify`, `gt submit`, `gt sync`, `gt checkout`, `gt log short`, `gt move`, `gt delete`, `gt merge`, and `gt track`. All `gt` calls use `--no-interactive`. (ref: GT2)
- A `using-graphite-cli` skill directory exists at `/workspaces/qrspi/.claude/skills/using-graphite-cli/` but is empty (no SKILL.md or reference files). (ref: GT3)
- Existing skills follow a convention: YAML frontmatter (name, description, command, argument-hint, allowed-tools) followed by Markdown sections with clear headings, prose instructions, and inline code blocks for shell commands. (ref: GT4)
- The project has 10 skills in `.claude/skills/`: qrspi-ticket, qrspi-questions, qrspi-research, qrspi-design, qrspi-structure, qrspi-plan, qrspi-implement, qrspi-worktree, qrspi-work, qrspi-pr. The `using-graphite-cli` skill is listed as an available skill in the system prompt. (ref: GT5)
- There is no centralized reference for `gt` CLI patterns. Each skill that uses `gt` inline-embeds the commands it needs, leading to duplication and potential drift. (ref: GT6)

## Desired End State

- **AC - Initialization:** The skill documents the correct `gt init` and `gt auth` workflows. Agents know to use `gt init` for repository initialization and `gt auth --token` for authentication, and that `gt init` requires no flags. (ref: AC1)
- **AC - Core Workflow:** The skill codifies the standard create-modify-submit loop: `gt create` (with `--no-interactive`), `gt modify` (with `-c` for new commits, `--no-interactive`), and `gt submit` (with `--no-edit` and `--no-interactive`). (ref: AC2)
- **AC - Branch Navigation:** The skill documents `gt checkout` (with `--no-interactive`), `gt up`, `gt down`, `gt bottom`, `gt top`, and `gt trunk` for stack traversal. Agents know when to use each command. (ref: AC3)
- **AC - Single Commit Per Branch:** The skill encodes the project convention that planning uses one commit (created with `gt modify -c`) and subsequent phases amend it (with `gt modify` no `-c`). (ref: AC4)
- **AC - Restacking:** The skill explains that `gt modify` automatically restacks descendants, and that `gt sync` can restack all branches when needed. It covers when to use each. (ref: AC5)
- **AC - Submitting PRs:** The skill distinguishes `gt submit` (current branch plus downstack) from `gt submit --stack` (entire stack). It documents `--no-edit`, `--no-interactive`, and other flags. (ref: AC6)
- **AC - Downstack/Upstack Operations:** The skill covers `gt move --onto` for re-parenting, `gt delete --force` for branch removal, and their `--downstack`/`--upstack` flags. (ref: AC7)
- **AC - Merging Stacks:** The skill documents `gt merge --confirm` for merging the full stack, and `gt delete --force` for cleanup afterward. (ref: AC8)
- **AC - Integration with GitHub:** The skill explains that `gt submit` handles the GitHub PR creation/update workflow automatically. Agents should use `gh` for read-only GitHub operations (review comments, PR views) and `gt` for stack state changes. (ref: AC9)
- **AC - Scope Guidance:** The skill provides guidance on when to use `gt` vs. `gh` vs. raw `git`. `gt` for stack-aware operations, `gh` for GitHub API interactions, raw `git` only for worktree management. (ref: AC10)
- **AC - Acceptance Criteria Met:** All acceptance criteria from the ticket are addressable and testable through the skill's content. (ref: AC11)

## Delta

**New files:**
- `/workspaces/qrspi/.claude/skills/using-graphite-cli/SKILL.md` — the primary skill file, containing YAML frontmatter and all reference sections.

**No files modified.** This skill does not alter existing code or configurations.

**Content structure of SKILL.md:**
- Frontmatter: name, description, allowed-tools (Bash for gt/git/gh, Read, Edit, Write)
- Section: "Graphite CLI Primer" — core concepts (stack, trunk, downstack, upstack)
- Section: "Initialization" — `gt init`, `gt auth`
- Section: "Core Workflow" — create, modify, submit loop
- Section: "Branch Navigation" — checkout, up, down, bottom, top, trunk
- Section: "Single Commit Per Branch" — planning commit convention
- Section: "Restacking" — automatic vs. explicit restack
- Section: "Submitting PRs" — narrow vs. stack submit
- Section: "Downstack/Upstack Operations" — move, delete with flags
- Section: "Merging Stacks" — merge, cleanup
- Section: "Integration with GitHub" — gt vs gh division of labor
- Section: "Scope Guidance" — when to use each tool

## Pattern Decisions

### Decision 1: Skill format — single SKILL.md vs. multi-file with references/

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single SKILL.md (recommended) | Simple, self-contained, follows existing qrspi skill pattern, no dependency on external file references | Could become large; ~150-200 lines |
| B | SKILL.md + references/gt-reference.md | Main skill stays lean; full command reference in separate file | Adds file resolution complexity for agents; deviates from existing skill convention; agents may miss the reference file |

**Recommendation:** Option A — single SKILL.md.

**Rationale:** All existing qrspi skills use a single SKILL.md file. Agents already have the skill loaded into context when invoked. Adding a second file creates a file-resolution step that doesn't exist in any other skill. The `gt` CLI has ~20 commands; a single file of 150-200 lines is well within context budget.

**NEW PATTERN?** No — follows the single-file SKILL.md pattern established by all 10 existing qrspi skills.

### Decision 2: Inline code blocks vs. prose descriptions for commands

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline code blocks with full commands (recommended) | Copy-pasteable, shows exact flags (`--no-interactive`), matches existing qrspi skill convention (see qrspi-work) | Slightly longer file |
| B | Prose descriptions of commands | Shorter file | Agents may omit required flags; harder to verify correctness |

**Recommendation:** Option A — inline code blocks.

**Rationale:** The qrspi-work SKILL.md uses inline code blocks for all `gt` commands, and this pattern is established across all project skills. Agents benefit from exact, copy-pasteable commands rather than paraphrased descriptions. This reduces the chance of agents omitting critical flags like `--no-interactive`.

**NEW PATTERN?** No — follows inline code block convention from qrspi-work and other skills.

### Decision 3: Allowed tools in frontmatter — Bash restriction scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bash + Read only | Minimal surface; `gt` commands don't need Read | May need Read to verify stack state |
| B | Bash + Read + Edit | Matches existing skill pattern (qrspi-work uses Bash+Read+Write) | Edit is unlikely to be needed for `gt` usage |
| C | Bash + Read (recommended) | Minimal but sufficient; Read for verifying `gt log` output, Bash for all `gt` commands | Slightly more permissive than necessary for Read |

**Recommendation:** Option C — Bash + Read.

**Rationale:** The `using-graphite-cli` skill guides agents on how to use `gt`. Agents need Bash to run `gt` commands and Read to verify output (e.g., `gt log` output). They do not need to write or edit files for `gt` operations. This is more constrained than the 200-line qrspi-work SKILL.md but appropriate for a reference skill.

**NEW PATTERN?** No — allowed-tools follow the pattern of other skills (Bash + Read + others as needed).

### Decision 4: Skill invocation model — command-driven vs. auto-invoke

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Command-driven with `argument-hint` (recommended) | Matches existing skill format; user invokes `/using-graphite-cli` or system auto-detects via description | Requires explicit mention or matching description |
| B | Pure auto-invoke via description only | Simpler for users; skill fires on any mention of "graphite" or "stacked PR" | May fire too eagerly; harder to control scope |

**Recommendation:** Option A — command-driven.

**Rationale:** The existing `using-graphite-cli` skill in the system prompt already uses command-driven invocation. Keeping it consistent with all other qrspi skills simplifies the mental model. The `command` field is `/using-graphite-cli` with `argument-hint: none`.

**NEW PATTERN?** No — matches command-driven pattern of all existing skills.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gt` CLI command surface changes between versions, making the skill stale | medium | medium | Include `gt --help` as a reference command in the skill; agents should run it to verify flag availability before using obscure flags. Document the version range covered. |
| Skill file grows too large (>300 lines), exceeding context budget | low | medium | Keep the skill target at ~200 lines. Use concise code blocks. If it grows, split into two skills (e.g., core vs. advanced). |
| Agents use `gt` commands that require interactive prompts in automated sessions | medium | high | Always include `--no-interactive` in documented commands. Document which commands have no non-interactive equivalent (e.g., `gt checkout` without branch arg). |
| Agents conflate `gt` (stack operations) with `gh` (GitHub API) or `git` (low-level ops) | low | high | Include a clear "Tool Selection" section in Scope Guidance. Provide decision table: stack-aware = `gt`, GitHub API = `gh`, worktree/trunk = `git`. |
| The skill's "no `-a` flag" staging rule is omitted, causing pollution of staged changes | low | high | Copy the exact staging rule from qrspi-work into the skill. This is a project-wide convention that must be preserved. |

## Open Questions

- OQ1: Should the skill include `gt config` commands for setting defaults (e.g., `--no-interactive` as default), or only documented invocations?
- OQ2: Should the skill cover `gt aliases` setup? The existing qrspi-work SKILL.md uses bare `gt` commands, not aliases, but some users may prefer aliases.
- OQ3: Should the skill reference specific `gt` CLI version(s)? The current installation is at `/usr/bin/gt` but no version is pinned.
