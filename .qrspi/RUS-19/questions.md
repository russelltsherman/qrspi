# Questions — Create a new agent skill for the atmos CLI

**Ticket:** RUS-19
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the required `SKILL.md` frontmatter schema (field names, order, allowed values) that existing skills in this repo use, and does it match the agentskills.io standard the ticket references?
  **Target:** `.claude/skills/*/SKILL.md` frontmatter and the skill-creator skill (`skill-creator`)
- Q2: How does the skill-builder/skill-creator skill expect content to be split between the `SKILL.md` body and the `references/`, `scripts/`, and `assets/` subdirectories, and how is reference material loaded on demand?
  **Target:** the skill-creator skill definition and any `references/` examples it ships

## API Surface

- Q3: What is the canonical on-disk directory layout for a skill in this repo (where the skill directory lives, naming of `SKILL.md`, `references/`, `scripts/`, `assets/`), and where must the new atmos skill be created?
  **Target:** `.claude/skills/` directory and existing skill folders
- Q4: What naming convention and `name`/`description` triggering pattern do existing skills use, and what does the skill-creator skill recommend for the new atmos skill's description to control auto-invocation?
  **Target:** existing `SKILL.md` `description` fields and the skill-creator triggering guidance

## State Management

- Q5: Does the skill-creator skill enforce or measure the SKILL.md body limits (under 500 lines / 5000 tokens) named in the acceptance criteria, and what mechanism reports those counts?
  **Target:** the skill-creator skill and its eval/measurement tooling
- Q6: How are `references/` files referenced from within `SKILL.md` (relative paths, link format, progressive disclosure markers) so an agent knows when to load the stack-YAML-schema, vendoring, workflow, CLI, and troubleshooting reference docs?
  **Target:** existing skills that ship `references/` and the skill-creator authoring rules

## Edge Cases

- Q7: What does the skill-creator eval loop require before a skill is considered shippable (per the global memory rule to never ship a SKILL.md ad-hoc), and what failure modes does that loop check for?
  **Target:** the skill-creator skill's eval workflow
- Q8: Are there existing skills in this repo that contain executable `scripts/` or `assets/`, and what conventions (shebang, ShellCheck cleanliness, permissions) must any scripts bundled with the atmos skill follow?
  **Target:** `.claude/skills/*/scripts/` and the writing-bash-scripts skill
- Q9: Does the repo place any constraint on whether a new skill must also have a matching slash-command wrapper, and where would such a wrapper for the atmos skill live versus the skill definition itself?
  **Target:** `.claude/agents/` and `.claude/skills/` (per the "Codebase conventions" note that agents and wrappers are split)

## Testing

- Q10: How are skills validated or tested in this repo today (eval harness, unit tests, manual runs), and which of those mechanisms is real versus placeholder for verifying the atmos skill?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval capability
- Q11: What concrete acceptance-criteria checks from the ticket (frontmatter validity, line/token budget, presence of the five named reference docs) can be verified mechanically, and what tooling in the repo performs that check?
  **Target:** the skill-creator measurement tooling and any skill-linting present in the repo

## Observability

- Q12: When a skill fails to trigger or under-performs, what signal does the skill-creator eval/benchmark surface (scores, variance, triggering accuracy), and where is that output recorded so the atmos skill's quality can be observed?
  **Target:** the skill-creator skill's benchmark/variance-analysis output
