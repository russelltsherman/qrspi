# Questions — Create a new agent skill for using the Gemini CLI

**Ticket:** RUS-22
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory structure and file layout do existing skills in this repository follow, and where would a new skill's `SKILL.md`, `references/`, `scripts/`, and `assets/` be placed?
  **Target:** the skills directory (e.g., `.claude/skills/` or the module responsible for skill registration)
- Q2: How does the skill-builder skill referenced in the ticket consume an input description and produce a `SKILL.md` plus supporting files?
  **Target:** the skill-creator skill definition and its supporting scripts

## API Surface

- Q3: What fields are required in `SKILL.md` YAML frontmatter (name, description, and any others) for a skill to be valid and discoverable in this repository?
  **Target:** an existing `SKILL.md` frontmatter and the skill loader/registry
- Q4: What naming, description, and triggering conventions do existing skill descriptions use so the new Gemini CLI skill is routed correctly?
  **Target:** the `description` frontmatter of existing skills (e.g., using-graphite-cli, workflow-creator)

## State Management

- Q5: How do existing skills that wrap external CLIs separate the body of `SKILL.md` from detailed reference material placed in `references/`?
  **Target:** an existing CLI-wrapping skill and its `references/` directory
- Q6: What conventions exist for keeping a `SKILL.md` body under the 500-line / 5000-token budget while linking out to deeper reference files?
  **Target:** existing skills' `SKILL.md` bodies and reference file structure

## Edge Cases

- Q7: Where in the codebase or skill conventions is the handling of deprecation/migration notices (such as the June 2026 Gemini-to-Antigravity transition) documented, so the timeline note is encoded consistently?
  **Target:** existing skills that document version-specific or deprecation caveats
- Q8: What patterns exist for documenting destructive or autonomous operations (analogous to `--yolo`/sandbox) so risk guidance is surfaced rather than buried?
  **Target:** existing skills covering approval or permission models
- Q9: How do existing skills document conflicting precedence rules (analogous to Gemini's CLI args > env vars > project settings > global settings hierarchy)?
  **Target:** existing skill references covering configuration hierarchies

## Testing

- Q10: What eval or verification harness exists for skills in this repository, and what would be required to validate the new skill's triggering and content?
  **Target:** `evals/` and `scripts/` directories
- Q11: How are skill description/triggering accuracy and `SKILL.md` correctness currently measured for existing skills?
  **Target:** the skill-creator eval loop and any benchmark scripts under `evals/`

## Observability

- Q12: How is skill invocation, triggering, or activation recorded or surfaced in this repository so the new skill's usage can be observed after it ships?
  **Target:** the module responsible for skill loading, logging, or invocation tracking
