# Questions — Create a new agent skill using argocd cli

**Ticket:** RUS-8
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where are agent skills stored in this repo, and what is the on-disk layout of an existing skill (SKILL.md plus references/, scripts/, assets/) that the new argocd skill must mirror?
  **Target:** the directory holding existing agent skills (e.g., `.claude/skills/` or `skills/`)
- Q2: How does the skill-creator skill consume an input description and emit a SKILL.md plus reference files — what is its expected input format and output directory convention?
  **Target:** the skill-creator skill (SKILL.md and any scaffolding scripts it invokes)

## API Surface

- Q3: What exact frontmatter fields (name, description, and any others) does a valid SKILL.md require in this repo, and what are the format/length constraints on each?
  **Target:** the module or template defining SKILL.md frontmatter schema (skill-creator references)
- Q4: What naming convention is enforced for skill directories and the `name` field — does an existing skill demonstrate the kebab-case / prefix pattern the argocd skill should follow?
  **Target:** existing skill directories and skill-creator validation rules
- Q5: How do existing skills reference their `references/` files from the SKILL.md body (relative paths, link syntax, progressive-disclosure pattern)?
  **Target:** an existing multi-file skill's SKILL.md body

## State Management

- Q6: Is there an eval harness or metadata registry that tracks skills, and must a newly created skill be registered there to be discoverable/triggerable?
  **Target:** `evals/` and `scripts/` (skill eval harness, any skill index/registry)
- Q7: How is a skill's `description` used for trigger matching, and what existing examples show the pattern for writing a triggering description?
  **Target:** skill-creator description-optimization guidance and existing skill descriptions

## Edge Cases

- Q8: What enforces the SKILL.md body limit (under 500 lines / 5000 tokens), and is there tooling to measure token count so reference material can be split out correctly?
  **Target:** skill-creator validation/measurement scripts
- Q9: How do existing skills handle content that exceeds the body budget — what is the established split point between SKILL.md and `references/` files?
  **Target:** an existing skill that uses a `references/` directory
- Q10: Are there existing CLI-wrapper or kubectl/Helm-adjacent skills whose scope boundaries (in-scope vs defer-to-other-skill) demonstrate how this skill should declare its out-of-scope deferrals?
  **Target:** existing infrastructure/CLI-oriented skills in the skills directory
- Q11: What format do existing skills use to encode opinionated defaults and judgment-call guidance (decision tables, flowcharts, do/don't lists) that the argocd skill's escalation paths should follow?
  **Target:** existing skills containing decision guidance or troubleshooting flows

## Testing

- Q12: How are skills evaluated in this repo — what does the eval harness expect (eval cases, scoring, variance analysis) and what artifacts must accompany a new skill to be testable?
  **Target:** `evals/` and `scripts/` skill eval harness
- Q13: Is there a validation command or linter that checks SKILL.md frontmatter and directory structure, and how is it invoked?
  **Target:** skill-creator validation tooling and `scripts/`

## Observability

- Q14: How does skill trigger/invocation get logged or surfaced (hooks, harness logging) so the argocd skill's auto-invocation behavior can be verified after creation?
  **Target:** the harness hooks/logging config (`.claude/settings.json`, PreToolUse/skill hooks)
