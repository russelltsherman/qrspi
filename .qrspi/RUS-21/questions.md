# Questions — Create a new agent skill for using the Codex CLI

**Ticket:** RUS-21
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout a skill occupies in this repo (SKILL.md plus references/, scripts/, assets/), and where are skill source files placed versus their slash-command wrappers?
  **Target:** `.claude/skills/` and `.claude/agents/` directories
- Q2: How does the skill-creator skill take an input description and produce a SKILL.md and supporting files — what files does it read and write during generation?
  **Target:** the skill-creator skill (SKILL.md and its scripts/references)

## API Surface

- Q3: What is the exact required frontmatter schema for a SKILL.md (field names, allowed values, name/description format) that conforms to the agentskills.io standard used here?
  **Target:** the module/template defining SKILL.md frontmatter (skill-creator references or an existing SKILL.md)
- Q4: How is a skill registered so it appears in the available-skills list and can be invoked via slash command or auto-invocation?
  **Target:** the skill registration/loading mechanism (`.claude/skills/` wrappers and any manifest)

## State Management

- Q5: How are reference files under references/ loaded relative to SKILL.md, and what mechanism keeps the SKILL.md body small while deferring detail to references?
  **Target:** an existing multi-file skill (e.g. mcp-builder or claude-api) using a references/ directory
- Q6: What naming and description conventions govern skill trigger matching, and how does the description field affect when the skill auto-invokes?
  **Target:** the skill description/trigger conventions documented in skill-creator

## Edge Cases

- Q7: How does the project enforce or measure the SKILL.md body size limits (under 500 lines / 5000 tokens) called out in the acceptance criteria, and is there tooling that flags overage?
  **Target:** skill-creator eval/lint tooling and any size-check scripts
- Q8: How do existing skills handle content that exceeds the body budget — what is the established pattern for splitting overflow into references/ versus scripts/?
  **Target:** existing skills with references/ directories under `.claude/skills/`
- Q9: What validation exists for malformed or missing frontmatter, and what happens when a SKILL.md fails that validation?
  **Target:** the skill loading/validation path or skill-creator validation scripts

## Testing

- Q10: What eval harness exists for skills in this repo, and what inputs/fixtures does it require to benchmark a newly authored skill?
  **Target:** `evals/` and `scripts/` directories and skill-creator's eval loop
- Q11: How are skill description triggering accuracy and skill performance measured, and what command runs those evals?
  **Target:** the skill-creator eval/benchmark tooling

## Observability

- Q12: How are skill invocations, trigger matches, and eval results surfaced or logged so an author can confirm a new skill triggers and performs as intended?
  **Target:** skill-creator eval output and any logging in `scripts/` or `evals/`
