# Questions — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Generated:** 2026-05-30T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the skill-creator skill (available as the `skill-creator` skill) structure its output? The ticket says to use it but the `writing-bash-scripts` skill already exists in the available skills list — was it already created, or does the ticket describe work that remains?
  **Target:** `.qrspi/agents/skill-creator` skill definition, or the `writing-bash-scripts` skill already present in the system prompt

- Q2: The ticket references the "agentskills.io standard pattern" — what is the exact directory schema expected (frontmatter fields, file conventions)? Is there a canonical reference for agentskills.io that the SKILL.md frontmatter must match?
  **Target:** External agentskills.io specification or any existing SKILL.md files in the repo that already follow this pattern

- Q3: Where in the project directory tree should this new skill's SKILL.md and any `references/`, `scripts/`, or `assets/` subdirectories be placed? The CLAUDE.md notes that agent prompt definitions live in `.qrspi/agents/` and skills are invoked via `/` slash commands — does this new skill need a corresponding slash command wrapper or does it register purely via its skill invocation mechanism?
  **Target:** `.qrspi/agents/` directory structure, existing skill SKILL.md files for structural reference

## API Surface

- Q4: The `writing-bash-scripts` skill already appears in the available skills list. Is this ticket about refining an existing skill, or about creating a separate new skill with a different name/trigger that supersedes it?
  **Target:** Existing `writing-bash-scripts` skill definition in the skill registry or available skills list

## State Management

- Q5: The skill-creator skill is available in the available skills list. What input contract (description, conventions, scope) does it expect, and does it produce output in a format that can be directly saved as a SKILL.md? Or does it produce structured guidance that still needs manual assembly?
  **Target:** `skill-creator` skill definition file

## Edge Cases

- Q6: The ticket says to target bash 4+ but calls out macOS ships bash 3.2. Does the skill need to encode fallback patterns for bash 3.2 features (e.g., no associative arrays, no `mapfile`), or is the decision to exclude macOS support acceptable? This is a judgment call outside the ticket's stated conventions.
  **Target:** The `writing-bash-scripts` SKILL.md body and any bash portability reference material

- Q7: The ticket says "never exceed ~200 lines without strong justification" and "at that point suggest a different language." Who makes this judgment — the skill, or the agent using the skill? Does the skill need to encode a checklist for when to exit bash and switch to Python/Go, or is this advisory only?
  **Target:** The `writing-bash-scripts` SKILL.md body, specifically the scope guidance section

- Q8: The acceptance criteria mention "ShellCheck-clean output when an agent follows the guidance." How is this evaluated — is there an automated check (a script in `references/` or `scripts/` that runs ShellCheck on generated output), or is this a manual review gate?
  **Target:** Any existing eval or test harness in `evals/` or `scripts/` directories

## Testing

- Q9: The ticket recommends BATS-core for testable scripts. Should the `writing-bash-scripts` skill include a BATS template or scaffolding script as part of its `scripts/` or `references/` directory, or does it only reference BATS as a recommendation?
  **Target:** The `writing-bash-scripts` skill's `scripts/` or `references/` directory (if they exist)

- Q10: The ticket says the skill body must be under 500 lines / 5000 tokens. Is there an existing mechanism to enforce or verify this constraint, or is it a manual review criterion?
  **Target:** The skill-creator skill's output validation logic or manual review process

## Observability

- Q11: The skill includes conventions for `log()`, `info()`, `warn()`, `die()` helpers inside generated scripts. Does the qrspi system itself need to intercept or log when this skill is used (e.g., to measure how often agents invoke it, or to track whether scripts it generates produce expected output), or is observability scoped only to the scripts the skill helps create?
  **Target:** The qrspi skill invocation system or any eval/monitoring infrastructure
