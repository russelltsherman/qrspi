# Questions — Create a new agent skill called using omlx cli

**Ticket:** RUS-24
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout an agent skill must produce in this repo (SKILL.md plus references/, scripts/, assets/) and where do existing skills physically live?
  **Target:** `.claude/skills/` and the directory tree of an existing skill (e.g. `.claude/skills/using-graphite-cli/`)
- Q2: How do existing skills in this repo split content between the top-level SKILL.md body and supporting files under `references/`, and what triggers a reader to load a reference file?
  **Target:** An existing skill's SKILL.md plus its `references/` directory

## API Surface

- Q3: What exact YAML frontmatter fields are required and permitted in a SKILL.md, and what are their value constraints (name pattern, description length, allowed-tools list)?
  **Target:** Frontmatter of existing SKILL.md files under `.claude/skills/` and any skill-authoring guide in the repo
- Q4: What does the skill-creator skill expect as inputs and what does its eval/validation loop check (frontmatter validity, body length limits, description triggering)?
  **Target:** The skill-creator skill definition and its scripts/eval harness

## State Management

- Q5: What naming convention governs a skill's `name` frontmatter field and its containing directory, and how must the ticket's intended name ("using omlx cli") map to a valid slug?
  **Target:** `name` fields and directory names of existing skills under `.claude/skills/`
- Q6: Where are skill description strings tuned for auto-invocation triggering, and is there a documented format or eval for description quality in this repo?
  **Target:** skill-creator description-optimization logic and `evals/`

## Edge Cases

- Q7: What is the enforced or recommended maximum size for a SKILL.md body (the ticket states under 500 lines / 5000 tokens), and where is that limit checked or documented?
  **Target:** skill-authoring guidance or skill-creator validation in the repo
- Q8: How do existing skills handle platform- or environment-specific instructions (e.g. macOS-only, requires specific hardware) so an agent on the wrong platform behaves correctly?
  **Target:** Existing skills that encode environment preconditions in their SKILL.md
- Q9: How do existing skills encode opinionated "prefer X over Y" decision guidance without overstepping into out-of-scope territory?
  **Target:** Existing skills containing decision tables or "when to use / when not to use" sections

## Testing

- Q10: What test or eval harness exists for skills in this repo, and what would a passing validation run for a new skill look like?
  **Target:** `evals/` and `scripts/` eval harness, and any skill-level eval configuration
- Q11: Does the repo provide a way to lint or validate SKILL.md frontmatter and structure before a skill is considered done?
  **Target:** `scripts/` validation tooling and skill-creator's checks

## Observability

- Q12: How does this repo surface skill-authoring failures or eval results (logs, eval output files, console reporting) so the author can confirm the skill meets acceptance criteria?
  **Target:** `evals/` output handling and `scripts/` reporting logic
