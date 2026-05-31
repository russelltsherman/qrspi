# Questions — Create a new agent skill called writing gitlab pipelines

**Ticket:** RUS-28
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an existing skill's SKILL.md flow from frontmatter to body to `references/` files — what content lives in the body versus what is deferred to reference files?
  **Target:** an existing reference skill in `.claude/skills/` (e.g., `using-graphite-cli`, `writing-bash-scripts`) and its `references/` directory
- Q2: Where do skill source files physically live in this repo, and is there a distinction between project-local skills (`.claude/skills/`) and the agent-skills standard layout the ticket references?
  **Target:** `.claude/skills/` directory tree and any skill-authoring tooling

## API Surface

- Q3: What is the exact required SKILL.md frontmatter schema (field names, required vs optional, `name`/`description`/`allowed-tools`/`command`/`argument-hint`) as used by skills already in this repo?
  **Target:** frontmatter of multiple existing SKILL.md files under `.claude/skills/`
- Q4: What does the skill-creator skill expect as inputs and what directory structure / files does it produce, and does it include an eval loop the ticket implies ("Anthropic skill builder skill")?
  **Target:** the `skill-creator` skill definition and its scripts/templates
- Q5: What naming convention is used for skill directory names and the `name` field (kebab-case, verb-first), and is there a uniqueness/collision constraint with existing skill names?
  **Target:** the set of existing skill directory names under `.claude/skills/`

## State Management

- Q6: Are there constraints on SKILL.md body length or token budget enforced anywhere (lint, eval, CI), given the acceptance criterion of under 500 lines / 5000 tokens?
  **Target:** any skill linting/validation in `scripts/`, `evals/`, or skill-creator tooling
- Q7: How are `references/`, `scripts/`, and `assets/` subdirectories referenced from the SKILL.md body in existing skills (relative paths, naming) so an agent loads them on demand?
  **Target:** body text of an existing skill that uses a `references/` directory

## Edge Cases

- Q8: How do existing skills encode opinionated "prefer X over deprecated Y" guidance and anti-pattern callouts (the ticket requires "rules over only/except" style guidance) — is there an established format for do/don't or anti-pattern sections?
  **Target:** body of skills that give opinionated guidance (e.g., `writing-bash-scripts`)
- Q9: How do existing skills handle version-gated or environment-specific behavior (the ticket needs SaaS vs self-managed and "GA since GitLab 17.0" notes) — is there a convention for noting version/applicability caveats?
  **Target:** any skill that documents version- or environment-conditional guidance
- Q10: What is the convention for splitting a large topic across multiple `references/` files versus one large file, given the ticket lists six distinct reference topics?
  **Target:** the `references/` directory of the largest existing skill

## Testing

- Q11: What does the eval harness in `evals/` and `scripts/` measure for a skill, and is there an existing pattern (eval fixtures, scoring, variance analysis) a new skill is expected to ship with?
  **Target:** `evals/` directory and `scripts/` eval runner
- Q12: Is there an existing test or validation that a SKILL.md's frontmatter is parseable / description triggers correctly, that this new skill would need to pass?
  **Target:** skill-creator eval tooling and any frontmatter validation in `scripts/`

## Observability

- Q13: How is skill triggering accuracy observed/measured in this repo (the `description` field drives auto-invocation), and is there a documented way to benchmark or log whether a skill's description triggers on intended prompts?
  **Target:** skill-creator's description-optimization / eval components and `evals/`
