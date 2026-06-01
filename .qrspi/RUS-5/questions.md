# Questions — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout the Anthropic skill builder produces for a new skill (SKILL.md plus which of `references/`, `scripts/`, `assets/`), and where in this repo are generated skills placed?
  **Target:** the skill-creator/skill-builder skill and the module responsible for skill scaffolding output paths
- Q2: How does an authored skill split content between the SKILL.md body and `references/` files — what is the loading/inclusion mechanism that pulls reference material in when the body points to it?
  **Target:** the skill-builder skill and existing skills with `references/` directories in `.claude/skills/`

## API Surface

- Q3: What fields are required in SKILL.md frontmatter for a valid agentskills.io-pattern skill, and what are their format/length constraints (e.g., name, description)?
  **Target:** the skill-builder skill frontmatter spec and existing SKILL.md files in this repo
- Q4: How is a skill registered so it appears in the available-skills list and triggers via `/` or auto-invocation — what governs the `description` used for trigger matching?
  **Target:** the module responsible for skill discovery/registration and the skill-builder description-optimization step

## State Management

- Q5: Does the skill builder include an eval/benchmark step, and what artifacts or state (eval cases, scores, variance reports) does it create and persist alongside the skill?
  **Target:** the skill-creator eval/benchmark component and the `evals/` and `scripts/` directories
- Q6: What conventions in this repo govern skill versioning or naming collisions — how is the skill name `writing-bash-scripts` validated against existing skills?
  **Target:** the module responsible for skill name validation and the existing `.claude/skills/` listing

## Edge Cases

- Q7: How is the SKILL.md body size limit (under 500 lines / 5000 tokens) measured and enforced — is there a check that fails when the body exceeds it, and how are tokens counted?
  **Target:** the skill-builder validation/lint step responsible for body size
- Q8: What mechanism, if any, verifies the "ShellCheck-clean output" acceptance criterion — is ShellCheck available in this environment, and how would the skill's guidance be exercised to confirm output passes with zero warnings?
  **Target:** the module/tooling responsible for ShellCheck availability and skill acceptance verification
- Q9: How does the skill builder handle the case where optional directories (`references/`, `scripts/`, `assets/`) are not needed — does it create empty directories, omit them, or leave placeholders?
  **Target:** the skill-builder scaffolding step for optional directories

## Testing

- Q10: What test or eval harness exists for validating a skill's behavior in this repo, and what is the expected format of skill eval cases?
  **Target:** the eval harness in `evals/` and `scripts/`
- Q11: How are the BATS-core and `BASH_SOURCE` testing recommendations the skill encodes themselves validated — is there existing tooling in the repo that runs bash tests the skill's guidance should align with?
  **Target:** the module responsible for running bash/shell tests in this repo

## Observability

- Q12: How does the skill-builder report success, failures, and warnings during skill generation (e.g., frontmatter validation errors, size-limit violations) — where does that diagnostic output surface?
  **Target:** the skill-builder logging/reporting component
