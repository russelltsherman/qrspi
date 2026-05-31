# Questions — Create a new agent skill using argo workflows cli

**Ticket:** RUS-7
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory layout (SKILL.md plus references/, scripts/, assets/) do existing skills in this repository use, and where on disk are skill directories created relative to the repo root?
  **Target:** the directory or module responsible for housing skill definitions (e.g., a `skills/` or `.claude/skills/` tree)
- Q2: How does the skill-creator skill consume an input description and emit a generated skill — what files does it read as templates and where does it write its output?
  **Target:** the skill-creator skill (`SKILL.md` and any generator scripts under its `scripts/`)

## API Surface

- Q3: What fields are required and optional in the SKILL.md frontmatter (e.g., name, description, version) according to existing skills and any schema the repo enforces?
  **Target:** the SKILL.md frontmatter of existing skills and any frontmatter validation logic
- Q4: What argo CLI command groups and flags appear in existing skill or reference material in this repo, if any, that could be reused or that establish a naming/style precedent?
  **Target:** the module or references responsible for CLI command documentation in existing skills

## State Management

- Q5: How is skill versioning recorded and incremented in this repo — is there a version field or changelog convention applied when a skill is created or modified?
  **Target:** the frontmatter and any version/changelog files of existing skills
- Q6: Where are reference files (references/ directory) linked from within SKILL.md bodies, and what mechanism loads them on demand versus inlining them?
  **Target:** existing skills that use a `references/` directory

## Edge Cases

- Q7: What enforces the SKILL.md body limit (under 500 lines / 5000 tokens), and is there an existing lint, test, or eval that fails when a skill body exceeds that threshold?
  **Target:** the eval harness in `evals/` and scripts in `scripts/`
- Q8: How do existing skills handle content that exceeds the body size budget — what is the established convention for pushing detail into references/ versus keeping it in SKILL.md?
  **Target:** existing skills with a `references/` directory and the skill-creator guidance
- Q9: What naming and collision rules apply to a new skill directory and its `name` frontmatter value, and what happens if a name duplicates an existing skill?
  **Target:** the module responsible for skill discovery/registration and existing skill names

## Testing

- Q10: How does the skill-creator eval loop measure skill performance, and what command or harness runs evals for a single skill?
  **Target:** the eval harness in `evals/` and `scripts/`
- Q11: Are there existing tests or eval fixtures that validate SKILL.md frontmatter and directory structure conformance to the agentskills.io standard?
  **Target:** the validation tests in `evals/` or `scripts/`

## Observability

- Q12: How are skill eval results reported (output format, location of result artifacts, variance/benchmark output), and where would a reviewer look to confirm a new skill passes?
  **Target:** the eval reporting module in `evals/` and `scripts/`
