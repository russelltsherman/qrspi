# Questions — Create a new agent skill using Codex CLI

**Ticket:** RUS-21
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory structure of an existing agent skill in this repo, and where do `SKILL.md`, `references/`, `scripts/`, and `assets/` sit relative to one another?
  **Target:** the directory holding existing skills (e.g. `.qrspi/agents/` or a skills directory)
- Q2: How does the skill-creator skill consume its inputs and where does it write the generated skill output (target path, naming convention)?
  **Target:** the skill-creator skill definition and its SKILL.md

## API Surface

- Q3: What exact frontmatter fields and value formats does the agentskills.io standard require in `SKILL.md` (name, description, and any others), as evidenced by existing skills in this repo?
  **Target:** the frontmatter block of one or more existing `SKILL.md` files
- Q4: What is the established naming convention for skill names and directories in this repo, and what would the canonical name for the Codex CLI skill be?
  **Target:** the skills directory and existing skill name slugs

## State Management

- Q5: How is the skill-creator's eval loop invoked and where are its eval artifacts, harness, and pass/fail thresholds stored?
  **Target:** the skill-creator skill and `evals/` / `scripts/` directories
- Q6: Where are the size/length constraints (SKILL.md under 500 lines / 5000 tokens, content offloaded to `references/`) enforced or measured, if anywhere, in the existing tooling?
  **Target:** the skill-creator skill and any token/line-count validation in `scripts/`

## Edge Cases

- Q7: How do existing skills in this repo split content between `SKILL.md` body and `references/` files, and at what point is material moved out of the body?
  **Target:** an existing skill that uses a `references/` directory
- Q8: Are there existing skills documenting an external CLI tool (approval modes, sandbox modes, config files) that establish a pattern for encoding tool-specific conventions, and how do they structure that material?
  **Target:** the skills directory (search for CLI/tool-wrapper skills)
- Q9: Does any existing skill or repo convention dictate how platform-specific behavior (e.g. macOS vs. Linux) is documented within a single skill?
  **Target:** existing skills and any authoring guidelines in skill-creator references

## Testing

- Q10: What does the skill-creator eval harness measure for a generated skill (description triggering accuracy, body length, structural validity), and what command runs it?
  **Target:** the skill-creator skill's eval harness in `evals/` and `scripts/`
- Q11: Are there fixtures, example prompts, or golden outputs used to validate skills, and what format do they take?
  **Target:** `evals/` and any test fixtures referenced by skill-creator

## Observability

- Q12: How are skill eval results reported and surfaced (output format, location, variance/benchmark reporting), and where would a reviewer look to confirm the new skill passed?
  **Target:** the skill-creator eval reporting path in `evals/` / `scripts/`
