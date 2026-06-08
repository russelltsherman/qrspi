# Questions — Create an agent skill for the Argo Workflows CLI

**Ticket:** RUS-7
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an existing SKILL.md reference and link to its `references/`, `scripts/`, and `assets/` subdirectories, and how are those auxiliary files loaded relative to the SKILL.md body?
  **Target:** an existing skill directory under `.claude/skills/` (e.g. the using-graphite-cli skill) and the module responsible for skill discovery/loading

- Q2: What does the skill-creator skill take as input and what artifacts/files does it emit when generating a new skill?
  **Target:** the skill-creator skill definition and its `SKILL.md` / supporting scripts

## API Surface

- Q3: What is the exact required frontmatter schema for a `SKILL.md` (field names, required vs optional, allowed values) as used by skills in this repo?
  **Target:** the frontmatter blocks of existing `SKILL.md` files under `.claude/skills/` and any frontmatter validator

- Q4: How are slash-command wrappers in `.claude/skills/` related to agent definitions in `.claude/agents/`, and which file types must coexist for a skill to be invocable?
  **Target:** `.claude/agents/` and `.claude/skills/` directories

## State Management

- Q5: Where on disk must the new Argo skill directory live to be auto-discovered, and what naming convention (directory name vs. frontmatter `name`) is enforced?
  **Target:** the module/config responsible for enumerating available skills

- Q6: Is there an index, manifest, or registry file that must be updated when a new skill is added, or is skill availability derived purely from directory presence?
  **Target:** the skill registration mechanism (config or loader)

## Edge Cases

- Q7: What is the enforced or conventional limit on SKILL.md body size (the ticket cites under 500 lines / 5000 tokens) — is this validated anywhere, or only a convention?
  **Target:** any skill linter/validator or documented convention in skill-creator

- Q8: How do existing skills handle content that exceeds the body-size budget — what is the established pattern for splitting detail into `references/` files?
  **Target:** existing multi-file skills under `.claude/skills/` (those with `references/`)

- Q9: How are skills that wrap external CLIs (like the `argo` binary) expected to behave when the CLI is absent or a command fails — is there a precedent for prerequisite/availability checks?
  **Target:** existing CLI-wrapping skills (e.g. using-graphite-cli, writing-bash-scripts)

## Testing

- Q10: How are skills verified in this repo — is there an eval harness, and what is its current functional status?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval loop

- Q11: What lint or structural checks (if any) run against a `SKILL.md` and its directory layout before the skill is considered valid?
  **Target:** any skill-validation script or CI step

## Observability

- Q12: How is a skill's invocation/triggering surfaced — what makes the `description` field effective for auto-invocation, and is there logging or any signal for whether a skill triggered?
  **Target:** the module responsible for skill triggering/description matching
