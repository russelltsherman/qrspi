# Questions — Create a new agent skill called writing Product Requirements Documents

**Ticket:** RUS-26
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory layout does an existing skill use for `SKILL.md` plus supporting `references/`, `scripts/`, and `assets/`, and where in the repo do skill source files live versus where they are installed/discovered?
  **Target:** `.claude/skills/` directory and any existing skill (e.g. `.claude/skills/qrspi-questions/SKILL.md`)
- Q2: How does the skill builder skill consume input and emit a finished skill — what files does it create, and where does it write them?
  **Target:** the skill-creator skill definition (the "Anthropic skill builder skill" referenced by the ticket)

## API Surface

- Q3: What fields are required and optional in `SKILL.md` frontmatter (name, description, command, argument-hint, allowed-tools, model, etc.), and what are the formatting/length constraints on the `description` field?
  **Target:** frontmatter of existing `SKILL.md` files under `.claude/skills/`
- Q4: How is a skill invoked — what naming convention maps a skill to its `/command` trigger, and how is the skill name expected to read for a PRD-writing skill?
  **Target:** the `command` and `name` frontmatter keys across existing `.claude/skills/*/SKILL.md`

## State Management

- Q5: What is the established convention for splitting content between the `SKILL.md` body and `references/` files, and what triggers content being moved into a reference file versus kept inline?
  **Target:** the module/skill responsible for skill authoring guidance (skill-creator references) and any existing skill using `references/`
- Q6: How are templates and example output stored and referenced by existing skills (inline fenced blocks vs separate `assets/` or `references/` files), so a PRD template can follow the same pattern?
  **Target:** existing skills under `.claude/skills/` that ship a template or example artifact

## Edge Cases

- Q7: What is the documented hard ceiling on `SKILL.md` size (the ticket states under 500 lines / 5000 tokens), and how is that limit enforced or verified for existing skills?
  **Target:** skill-creator guidance and the SKILL.md files of existing skills (line/token counts)
- Q8: How do existing skills encode a "must ask clarifying questions when evidence is missing" gate, so the PRD skill can require problem validation before solution specification?
  **Target:** any existing skill that conditionally prompts the user before proceeding (e.g. qrspi-ticket guided conversation)
- Q9: How do existing skills express "opinionated defaults with flexible overrides" — i.e. a default mode plus an expanded/alternate mode — within a single SKILL.md?
  **Target:** existing skills that offer a default-vs-expanded behavior path under `.claude/skills/`

## Testing

- Q10: What eval/test harness exists for skills in this repo, what format do skill eval cases take, and how is a skill's behavior scored?
  **Target:** the `evals/` and `scripts/` directories referenced by project conventions
- Q11: How is the skill builder skill's own eval loop invoked, and is running it a required gate before a skill is considered complete?
  **Target:** the skill-creator skill's eval/benchmark tooling and `scripts/`

## Observability

- Q12: How does the repo verify a newly authored skill is well-formed and discoverable (lint, frontmatter validation, registration step), and what signals indicate a skill is correctly installed?
  **Target:** the module/tooling responsible for skill validation/registration (scripts under `scripts/` or skill-creator checks)
