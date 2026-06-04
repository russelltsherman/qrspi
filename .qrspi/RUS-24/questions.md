# Questions — Create a new agent skill using the omlx CLI

**Ticket:** RUS-24
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout an agentskills.io-standard skill must follow in this repo (SKILL.md plus references/, scripts/, assets/), and where do existing skills physically live?
  **Target:** `.claude/skills/` and any existing skill directory (e.g. `.claude/skills/qrspi-questions/`)

- Q2: What frontmatter fields, ordering, and value formats are required and validated for a SKILL.md, and what is the maximum length of the description field?
  **Target:** the skill-creator skill (`skill-creator`) and its SKILL.md template/reference material

## API Surface

- Q3: How is the skill builder ("Anthropic skill builder skill") invoked in this environment, and what inputs/arguments does it expect to scaffold a new skill?
  **Target:** the `skill-creator` skill definition

- Q4: What naming convention governs the skill identifier (folder name and frontmatter `name`), and is there a constraint preventing a name like "using-omlx-cli" from colliding with existing skills?
  **Target:** the module responsible for skill name validation in `skill-creator` and the `.claude/skills/` listing

## State Management

- Q5: Where does the skill-creator place generated skill files (target directory), and does it write to a staging path or directly into `.claude/skills/`?
  **Target:** the `skill-creator` skill's file-output logic

- Q6: How are optional companion directories (references/, scripts/, assets/) registered or referenced from SKILL.md so the agent loads them on demand rather than inlining their content?
  **Target:** the SKILL.md body conventions documented in `skill-creator`

## Edge Cases

- Q7: What enforcement or guidance exists for keeping the SKILL.md body under 500 lines / 5000 tokens, and what is the prescribed pattern for overflowing detailed material into references/?
  **Target:** the `skill-creator` token/line budget guidance

- Q8: Is there an evaluation/benchmark mechanism for a new skill (the skill-creator eval loop), and what does it require as input to run against a draft skill?
  **Target:** the `skill-creator` eval/benchmark component and `scripts/run_eval.py`

- Q9: How does the skill-creator handle modifying or regenerating an already-existing skill directory versus creating a net-new one (overwrite, merge, or refuse)?
  **Target:** the `skill-creator` create-vs-edit code path

## Testing

- Q10: What is the documented method for verifying a skill triggers correctly (description triggering accuracy) and for measuring its performance/variance in this repo?
  **Target:** the `skill-creator` eval harness and any `evals/` fixtures

## Observability

- Q11: How does the skill-creator surface validation failures (invalid frontmatter, oversized body, naming collisions) back to the author, and where are those errors reported?
  **Target:** the `skill-creator` validation/reporting output path
