# Questions — Create a new agent skill: writing Architecture Decision Records

**Ticket:** RUS-25
**Generated:** 2026-05-31T16:27:56Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk layout of an existing agent skill in this repo (the `SKILL.md` plus any `references/`, `scripts/`, `assets/` subdirectories), and where do skills live relative to the repo root?
  **Target:** the directory holding skill definitions (e.g., `.claude/skills/`)
- Q2: How is skill content split between the `SKILL.md` body and supporting `references/` files in existing skills — what triggers an agent to load a reference file versus reading inline body content?
  **Target:** an existing multi-file skill such as `.claude/skills/skill-creator/` or `.claude/skills/qrspi-work/`

## API Surface

- Q3: What frontmatter fields does a valid `SKILL.md` declare in this repo (e.g., `name`, `description`, `command`, `argument-hint`, `allowed-tools`), and which are required versus optional?
  **Target:** frontmatter of existing `SKILL.md` files under `.claude/skills/`
- Q4: How is the skill-creator skill invoked and what is its directory structure, since the ticket requires the skill be "built using the Anthropic skill builder skill"?
  **Target:** the module responsible for skill creation (`.claude/skills/skill-creator/`)

## State Management

- Q5: Does this repo have an existing `docs/decisions/`, `docs/adr/`, or `architecture/decisions/` directory, or any pre-existing ADRs that the new skill must be consistent with?
  **Target:** repo-root `docs/` tree and any ADR directories
- Q6: How do existing skills encode "default + alternatives" guidance (a primary recommended path plus fallbacks), which the ADR skill needs for MADR-as-default with Nygard/Y-statement alternatives?
  **Target:** body structure of an existing skill that recommends a default approach

## Edge Cases

- Q7: What is the maximum size/line/token budget enforced or conventionally observed for a `SKILL.md` body in this repo, given the acceptance criterion of "under 500 lines / 5000 tokens"?
  **Target:** the largest existing `SKILL.md` bodies and any skill-creator guidance on size limits
- Q8: How do existing skills reference and copy `assets/` template files (the mechanism by which an agent copies a starter file), which the ADR skill needs for its starter ADR template?
  **Target:** any skill that ships an `assets/` directory with copyable templates
- Q9: Are skill names in this repo constrained to a naming convention (kebab-case, prefix, uniqueness), and is there a name collision for an ADR skill?
  **Target:** the set of skill directory names and any naming guidance in skill-creator

## Testing

- Q10: Does the repo provide an eval or validation harness for skills (the ticket mentions `evals/` and `scripts/`), and what would validate the new ADR skill's correctness?
  **Target:** the eval harness in `evals/` and `scripts/`

## Observability

- Q11: How is a skill's `description` field used for trigger/discovery, and what makes a description effective at auto-invocation — so the ADR skill triggers on relevant requests but not unrelated ones?
  **Target:** skill-creator guidance on description writing and existing skill `description` fields
