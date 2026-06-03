# Questions — Create a new agent skill using cmux CLI

**Ticket:** RUS-10
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What does the Anthropic skill builder (skill-creator) skill produce as output, and where does it write generated `SKILL.md`, `references/`, `scripts/`, and `assets/` files?
  **Target:** the skill-creator skill definition and its scaffolding scripts
- Q2: What is the canonical on-disk location and directory layout for installed skills in this repo (e.g., `.claude/skills/`), and how does a new skill's directory get named relative to its skill identifier?
  **Target:** the `.claude/skills/` directory and existing skill subdirectories

## API Surface

- Q3: What is the exact required `SKILL.md` frontmatter schema (field names, allowed values, required vs. optional) that the agentskills.io standard / skill-creator enforces?
  **Target:** the skill-creator templates and any frontmatter validation in skill-creator scripts
- Q4: What invocation interface does the skill-creator skill expose (arguments, sub-commands, or eval-loop entry points) for creating a new skill versus modifying an existing one?
  **Target:** the skill-creator skill definition (SKILL.md and its scripts/)

## State Management

- Q5: How are skills registered or discovered so they become available via `/` invocation or auto-invocation after the files are written — is there an index, manifest, or generated listing that must be updated?
  **Target:** the module/config responsible for skill discovery and the available-skills listing
- Q6: How do existing skills structure and reference auxiliary `references/` files from the main `SKILL.md` body so the agent loads them on demand rather than upfront?
  **Target:** existing multi-file skills under `.claude/skills/` that use a `references/` directory

## Edge Cases

- Q7: What enforces or measures the "SKILL.md body under 500 lines / 5000 tokens" acceptance constraint — is there a linter, token counter, or eval check, and what happens when it is exceeded?
  **Target:** skill-creator validation/eval scripts and any token-budget tooling
- Q8: How is a skill's `description` field optimized for trigger accuracy, and is there an eval/benchmark step (variance analysis) that must pass before a skill is considered shippable?
  **Target:** the skill-creator eval loop and description-optimization tooling
- Q9: What are the documented constraints or escaping rules for content within `SKILL.md` (e.g., handling of code fences, keyboard-shortcut notation like `Cmd+N`, OSC escape sequences) that could break frontmatter parsing or rendering?
  **Target:** the SKILL.md parser/loader and skill-creator template examples

## Testing

- Q10: How are skills tested or evaluated in this repo, and what does the skill-creator eval harness require as inputs (test prompts, expected behaviors) to validate a new skill?
  **Target:** the skill-creator eval harness and any `evals/` fixtures for skills
- Q11: Is the `evals/` + `scripts/run_eval.py` harness functional for skill testing, or must skill verification rely on the skill-creator's own eval loop and manual checks?
  **Target:** `scripts/run_eval.py` and the `evals/` directory

## Observability

- Q12: How does the skill-creator surface results, warnings, and failures during skill generation and eval (logs, console output, written report files), so the author can confirm acceptance criteria were met?
  **Target:** the skill-creator scripts' output/logging behavior
