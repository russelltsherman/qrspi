# Questions — Create a new agent skill called writing bash scripts
**Ticket:** RUS-5
**Generated:** 2026-05-25T00:00:00Z
**Status:** draft

## Data Flow
- Q1: How does the skill-creator skill discover and validate the `SKILL.md` frontmatter schema — what file defines the required fields and their types?
  **Target:** the skill-creator skill definition (SKILL.md or equivalent)

- Q2: What is the directory structure the skill-creator produces on disk, and which module enforces the `SKILL.md` + optional `references/`, `scripts/`, `assets/` layout?
  **Target:** the skill-creator skill and any template or scaffolding logic it invokes

- Q3: Where are existing agent skills stored in this repository (or referenced externally), and what naming convention do their directories follow?
  **Target:** project root or `.claude/skills/` or equivalent skills directory

## API Surface
- Q4: What frontmatter fields does the agentskills.io standard require in a `SKILL.md`, and is there a local schema or validation script that checks conformance?
  **Target:** any schema file, linter config, or validation script related to skill definitions

- Q5: How does the skill-creator skill accept input parameters (e.g., skill name, description, conventions) — through interactive prompts, a structured input file, or CLI arguments?
  **Target:** the skill-creator skill's invocation interface

- Q6: What is the mechanism for a skill's `references/` directory to be loaded into agent context — does the runtime read all files in that directory, or must they be explicitly referenced in `SKILL.md`?
  **Target:** the module responsible for skill context injection at runtime

## State Management
- Q7: After the skill-creator generates a skill, where is the resulting artifact persisted, and is there a registry or index file that must be updated to activate the new skill?
  **Target:** the module responsible for skill registration and discovery

- Q8: Does the skill-creator maintain any intermediate state (drafts, revision history) during multi-turn skill authoring, and if so, where is that state stored?
  **Target:** the skill-creator skill's internal state management

## Edge Cases
- Q9: What happens if a generated `SKILL.md` exceeds the 500-line / 5000-token limit stated in acceptance criteria — is there an existing enforcement mechanism or lint rule?
  **Target:** any validation, pre-commit hook, or CI check related to skill size limits

- Q10: How does the system handle a skill whose `references/` directory contains files that conflict with or duplicate guidance already present in `SKILL.md` body?
  **Target:** the module responsible for skill content assembly and deduplication

- Q11: If the skill-creator is invoked for a skill name that already exists, what conflict resolution behavior applies — overwrite, error, or interactive prompt?
  **Target:** the skill-creator skill's file-write logic

## Testing
- Q12: What existing test infrastructure (if any) validates that a generated skill produces correct output when used by an agent — are there eval harnesses, snapshot tests, or BATS-style integration tests?
  **Target:** `evals/` directory and any test scripts related to skill quality

- Q13: Is there an existing mechanism to verify that code samples embedded in a skill's `SKILL.md` or `references/` pass ShellCheck (or equivalent linting) as part of CI?
  **Target:** CI configuration files and any lint scripts in `scripts/`

## Observability
- Q14: When an agent invokes a skill at runtime, what logging or telemetry captures whether the skill was triggered, how much context it consumed, and whether the agent followed its guidance?
  **Target:** the module responsible for skill invocation logging or metrics collection
