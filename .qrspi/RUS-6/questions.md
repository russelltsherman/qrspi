# Questions — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-31T10:25:00Z
**Status:** draft

## Data Flow

- Q1: What is the canonical on-disk layout an agent skill must follow in this repo, including the relationship between a skill's `SKILL.md`, `references/`, `scripts/`, and `assets/` subdirectories, and where do skill source files live?
  **Target:** the module responsible for skill discovery and loading (e.g., `~/.claude/skills/` or `.claude/skills/` within this repo, plus any existing skill examples under `.claude/skills/`)

- Q2: How does an existing skill in this repo encode its frontmatter (name, description, allowed-tools, model, etc.), and what fields are required vs optional for the agentskills.io standard?
  **Target:** existing skills under `.claude/skills/` such as `qrspi-work/SKILL.md` and any examples already authored using the skill-builder

## API Surface

- Q3: What flags, subcommands, and option signatures does the project already invoke on `gt` (Graphite CLI), and where in the codebase are those invocations centralized (e.g., the qrspi-work orchestrator, planning skills, implement skill)?
  **Target:** the module responsible for orchestrating git/graphite operations (e.g., `.claude/skills/qrspi-work/SKILL.md`, any `gt`-touching skills, helper scripts under `scripts/`)

- Q4: Does the repo already define a tool-allowlist or restricted-tools convention for skills that mostly read instructions vs ones that execute commands, and what does that look like in frontmatter?
  **Target:** the frontmatter blocks of existing skills under `.claude/skills/` and any docs that describe agent tool restrictions

## State Management

- Q5: How is "trunk branch" detection and configuration persisted by Graphite in this project (e.g., `.git/config`, `~/.config/graphite/`), and how does that interact with the worktree-based workflow in `.worktrees/<ticket-id>/`?
  **Target:** the module responsible for worktree setup (qrspi-work skill, any helper scripts) and any docs that describe `gt repo init`, `gt repo trunk`

- Q6: What does the existing `using-graphite-cli` reference imply about state we already assume — for example, is `gt` expected to be pre-authenticated, or is there onboarding text covering `gt auth login`?
  **Target:** any existing skill/doc referencing the graphite CLI (e.g., the memory file `~/.agents/memory/feedback_git_delegation.md`, qrspi-work skill), and the global AGENTS.md memory index

## Edge Cases

- Q7: What does the project currently do when a `gt` command fails inside a sub-agent or orchestrator (conflict, missing trunk, untracked branch, broken stack), and how should the new skill instruct agents to recover without escalating with raw `git` commands?
  **Target:** the qrspi-work orchestrator's error-handling section and any existing references to `gt continue` / `gt restack`

- Q8: How are multi-commit branches prevented or detected today, and is there an existing automated check that the new skill should reference (precommit, CI, lint, or just convention)?
  **Target:** any pre-commit config, CI workflow files under `.github/workflows/`, scripts under `scripts/`, and the orchestrator's branch/commit conventions

- Q9: When a worktree has the same branch already checked out elsewhere, what is the established recovery path, and how should the skill describe that to an agent encountering the failure mode?
  **Target:** the qrspi-work skill's "Worktree Management" / "Stale worktree recovery" sections and any helper scripts

## Testing

- Q10: What evaluation harness exists for skills in this repo (under `evals/` and `scripts/`), and what interface must a new skill expose so it can be benchmarked the same way as existing ones?
  **Target:** the directories `evals/` and `scripts/` and any README/skill docs that describe how to add eval tasks

- Q11: Is there a reference example of a "skill built with the skill-builder" already in the repo that demonstrates the expected references/scripts/assets layout, and what conventions does it set (file naming, length budgets, callout style)?
  **Target:** the module responsible for skill creation patterns — specifically the skill-creator/skill-builder skill definition and any previously-built skills (e.g., qrspi-* skills)

## Observability

- Q12: When a `gt` invocation fails or behaves unexpectedly, what information should the skill instruct agents to capture (stderr, `gt log short` output, current branch state), and where does that information get surfaced today (orchestrator logs, Linear comments, PR descriptions)?
  **Target:** the qrspi-work orchestrator's logging/print conventions and any Linear comment helpers (e.g., usages of `mcp__linear-russelltsherman__save_comment` in skills)

## Scope and Conventions

- Q13: Does the repo already enforce a SKILL.md length budget (the ticket says under 500 lines / 5000 tokens) via a check or only by convention, and where are long-form details expected to live (e.g., `references/full-command-reference.md`)?
  **Target:** existing skills' SKILL.md sizes and any lint/check scripts under `scripts/`

- Q14: What naming convention does the repo use for skill directories and the `name` frontmatter field — kebab-case, snake_case, or something else — and does "using-graphite-cli" already match a pattern in use?
  **Target:** the directory layout under `.claude/skills/` and the frontmatter of every skill defined there
