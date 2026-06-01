# Questions — Create a new agent skill using gemini cli

**Ticket:** RUS-22
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout of an existing skill in this repo (SKILL.md plus references/, scripts/, assets/), and where are skills physically located?
  **Target:** `.claude/skills/` and the module responsible for skill storage

- Q2: How does the skill-creator skill ingest input and emit its output skill files, and what intermediate artifacts does it produce?
  **Target:** the skill-creator skill directory and its SKILL.md

## API Surface

- Q3: What fields are required versus optional in the YAML frontmatter of a SKILL.md in this repo, and what constraints exist on the `description` field?
  **Target:** existing SKILL.md frontmatter across `.claude/skills/`

- Q4: How is a skill invoked in this environment (slash-command wrapper versus auto-invocation), and where is the wrapper-to-agent mapping defined?
  **Target:** `.claude/skills/` wrappers and `.claude/agents/` definitions

- Q5: What naming convention is enforced for skill names (directory name, frontmatter `name`, and slash-command identifier)?
  **Target:** the module responsible for skill registration

## State Management

- Q6: Where does skill-creator persist its working state during a multi-step skill build, and is any eval/iteration loop state retained between runs?
  **Target:** the skill-creator skill and `evals/` harness

## Edge Cases

- Q7: What is the enforced size limit on a SKILL.md body, and how is the 500-line / 5000-token threshold from the acceptance criteria measured or validated in this repo?
  **Target:** the module or script responsible for skill validation

- Q8: How are existing skills structured when content exceeds the SKILL.md budget — what triggers content moving into `references/` versus staying inline?
  **Target:** existing skills with `references/` directories under `.claude/skills/`

- Q9: How do existing skills handle deprecation or version-transition notices in their body content?
  **Target:** existing SKILL.md files referencing tool versions or migrations

## Testing

- Q10: How does the eval harness assess a skill's description-triggering accuracy and body quality, and what command runs it?
  **Target:** `evals/` and `scripts/` eval harness

- Q11: What validation exists for SKILL.md frontmatter correctness, and is it run manually or in CI?
  **Target:** the module responsible for skill validation and any CI config

## Observability

- Q12: What logging, scoring output, or run reports does the skill-creator eval loop emit so a reviewer can inspect skill performance after a build?
  **Target:** the skill-creator eval loop and `evals/` output artifacts
