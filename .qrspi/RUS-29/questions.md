# Questions — Create a new agent skill called writing dockerfiles

**Ticket:** RUS-29
**Generated:** 2026-05-31T16:02:52Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout of an existing agent skill in this repo (SKILL.md plus any references/, scripts/, assets/ subdirectories), and where do skills physically live?
  **Target:** the directory holding existing skills (e.g., `.claude/skills/` or a `skills/` tree) and a representative existing `SKILL.md`

- Q2: How are reference files under a skill's `references/` directory linked or pointed to from the SKILL.md body in existing skills?
  **Target:** an existing skill's `SKILL.md` and its `references/` directory

## API Surface

- Q3: What exact frontmatter fields are required and permitted in a SKILL.md (name, description, command, argument-hint, allowed-tools, model, claude.tools, etc.), and what are their value formats?
  **Target:** the frontmatter blocks of existing `SKILL.md` files and any `.claude/agents/*.md` definitions

- Q4: Is there a naming convention for the skill directory and the `name:` field (kebab-case, prefix conventions) that "writing-dockerfiles" must conform to?
  **Target:** existing skill directory names and their `name:` frontmatter values

- Q5: What does the Anthropic "skill builder" / skill-creator skill referenced in the ticket actually require as input and produce as output, and is it available in this environment?
  **Target:** the module responsible for skill creation (skill-creator skill definition)

## State Management

- Q6: Are skills registered anywhere (an index, a manifest, settings.json, or a plugin listing) that a new skill must be added to in order to be discoverable, or are they auto-discovered by directory presence?
  **Target:** `.claude/settings.json`, any skills manifest/index file, and the skill discovery mechanism

## Edge Cases

- Q7: What enforces or measures the "SKILL.md body under 500 lines / 5000 tokens" constraint — is there an existing linter, eval, or convention in the repo that checks skill body size?
  **Target:** the eval harness in `evals/` and `scripts/`, and any skill-size validation

- Q8: How do existing skills handle the boundary between concise SKILL.md guidance and detailed `references/` material — what content lives in the body versus what is offloaded to references?
  **Target:** an existing skill that uses `references/` (body vs. reference split)

- Q9: Is there an existing eval/test pattern that verifies a skill triggers correctly on its description and produces expected behavior, which a new skill is expected to satisfy?
  **Target:** the eval harness in `evals/` and `scripts/`

## Testing

- Q10: What testing or validation convention applies to a documentation-only skill (no executable code) in this repo — what would "tested" mean for the writing-dockerfiles skill per project TDD expectations?
  **Target:** `evals/`, `scripts/`, and any existing skill's accompanying test/eval files

- Q11: Are there reusable assets (example Dockerfiles, snippets, scripts) elsewhere in the repo that the skill's `references/` examples could draw on or must stay consistent with?
  **Target:** the repo tree for any existing Docker/container-related files

## Observability

- Q12: How is skill performance or trigger accuracy measured and reported in this repo (eval scores, variance analysis output, logs), so the new skill's quality can be observed after creation?
  **Target:** the eval harness in `evals/` and `scripts/`, and any eval result/report format
