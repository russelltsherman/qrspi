# Questions — Create a new agent skill called using graphite cli
**Ticket:** RUS-6
**Generated:** 2026-05-26T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the existing skill-creator skill discover and validate `SKILL.md` frontmatter fields, and what schema does it enforce for the agentskills.io standard pattern?
  **Target:** the skill-creator skill definition (`.claude/skills/skill-creator/`)

- Q2: What directory structure does the project currently use for skills, and where are existing `SKILL.md` files located relative to the project root?
  **Target:** `.claude/skills/` directory tree

- Q3: How does the skill-creator skill's eval loop feed back into `SKILL.md` content — what inputs does it consume and what outputs does it produce during each iteration?
  **Target:** the skill-creator skill and its eval harness

## API Surface

- Q4: What fields and format does the `SKILL.md` frontmatter require (e.g., `name`, `description`, `triggers`, `version`) and are any fields optional versus mandatory?
  **Target:** existing `SKILL.md` files in `.claude/skills/`

- Q5: What is the expected interface between a skill's `references/` directory and the skill runner — are reference files loaded automatically, on-demand, or explicitly referenced from within `SKILL.md`?
  **Target:** the module responsible for skill loading and reference resolution

- Q6: Does the project define any token-budget or line-count enforcement mechanism that validates the "under 500 lines / 5000 tokens" constraint on `SKILL.md` bodies?
  **Target:** skill-creator eval harness or linting configuration

## State Management

- Q7: How does the skill-creator skill manage intermediate state between iterations of its eval loop — does it persist drafts to disk, hold them in memory, or rely on conversation context?
  **Target:** the skill-creator skill definition and any associated scripts

- Q8: When a skill includes a `references/` directory with multiple files, what naming or indexing convention determines load order or lookup keys?
  **Target:** existing skills that contain a `references/` directory

## Edge Cases

- Q9: What happens when a skill's trigger description overlaps with an existing skill's triggers — does the system detect or warn about ambiguity, or does invocation order depend on something else?
  **Target:** the module responsible for skill matching and dispatch

- Q10: If a `SKILL.md` body exceeds the 500-line or 5000-token limit, does the skill-creator's eval loop catch this violation, or is it only enforced manually during review?
  **Target:** skill-creator eval configuration and validation scripts

- Q11: How does the system behave when a skill references commands (e.g., `gt`) that are not installed on the current machine — does skill loading fail, or is the failure deferred to invocation time?
  **Target:** the module responsible for skill execution and command resolution

## Testing

- Q12: What eval harness infrastructure exists for testing skills, and what does a passing eval look like for a skill that wraps an external CLI tool?
  **Target:** `evals/` directory and `scripts/` directory

- Q13: Are there existing eval cases for other CLI-wrapping skills that can serve as a pattern for testing the Graphite CLI skill?
  **Target:** `evals/` directory and existing skill eval definitions

## Observability

- Q14: Does the project emit any structured logs or telemetry when a skill is invoked, and if so, what fields identify the skill, the triggering input, and the outcome?
  **Target:** the module responsible for skill invocation logging or telemetry
