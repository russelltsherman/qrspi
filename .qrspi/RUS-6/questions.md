# Questions — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the existing on-disk layout of the `using-graphite-cli` skill, and what files (SKILL.md, references/, scripts/, assets/) already exist versus need to be created?
  **Target:** The directory containing the `using-graphite-cli` skill (e.g., `.claude/skills/using-graphite-cli/` or wherever skills are stored in this repo)
- Q2: How does the skill-creator skill ingest source material and emit a finished skill, and what inputs does it expect to produce SKILL.md plus the references/ directory?
  **Target:** The skill-creator skill definition and its supporting scripts

## API Surface

- Q3: What frontmatter fields and value constraints does the agentskills.io / Anthropic skill standard require in SKILL.md (name, description, and any others), and how are they validated in this repo?
  **Target:** Existing SKILL.md files in the repo and any skill frontmatter schema or validation script
- Q4: What is the canonical directory structure (`SKILL.md` + optional `references/`, `scripts/`, `assets/`) the standard pattern expects, and how do other skills in this repo organize these subdirectories?
  **Target:** The skills directory and the skill-creator reference material

## State Management

- Q5: Where is the skill description text consumed for trigger matching, and what existing description format do comparable skills in this repo use?
  **Target:** The module or loader responsible for skill discovery and trigger-description matching
- Q6: How are `references/` files referenced from within SKILL.md (relative paths, link syntax, progressive-disclosure pattern), based on existing multi-file skills?
  **Target:** Existing skills that include a `references/` directory

## Edge Cases

- Q7: What is the measured token count and line count of comparable SKILL.md files in this repo, so the new SKILL.md can stay under the 500-line / 5000-token acceptance criterion?
  **Target:** Existing SKILL.md files and any token-counting or size-check tooling in `scripts/`
- Q8: How does the repo's tooling or convention handle the boundary between content that belongs in SKILL.md versus content that must move to `references/` (e.g., full command reference, edge cases)?
  **Target:** The skill-creator reference material and existing skills with split content
- Q9: Are there existing validation, lint, or eval checks that would fail if SKILL.md frontmatter is malformed or if required directory entries are missing?
  **Target:** The eval harness in `evals/` and `scripts/`

## Testing

- Q10: What eval or test pattern does this repo use to verify a skill triggers correctly and behaves as intended, and where would a test for the `using-graphite-cli` skill live?
  **Target:** The eval harness in `evals/` and `scripts/`
- Q11: How does skill-creator's eval loop measure skill performance and trigger accuracy, and what artifacts does it produce?
  **Target:** The skill-creator skill's eval-loop component

## Observability

- Q12: What logging, output, or reporting does the skill-creator process emit during generation, and where can its results be inspected to confirm the skill was built correctly?
  **Target:** The skill-creator skill and any log/report output location it writes to
