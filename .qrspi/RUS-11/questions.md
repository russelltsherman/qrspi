# Questions — Create a new agent skill using devcontainer CLI

**Ticket:** RUS-11
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout the agentskills.io standard expects for a skill, and how do `SKILL.md`, `references/`, `scripts/`, and `assets/` relate to one another?
  **Target:** the skill-creator skill and any existing skills under `.claude/skills/`

- Q2: How is reference material in `references/` surfaced to an agent at runtime — is it loaded eagerly with `SKILL.md` or pulled on demand — and what does that imply for splitting the CLI reference, schema cheatsheet, lifecycle decision tree, and CI/CD examples across files?
  **Target:** the module/skill responsible for skill loading and progressive disclosure

## API Surface

- Q3: What fields are required vs optional in `SKILL.md` frontmatter for the agentskills.io standard, and what constraints (allowed characters, length, naming) apply to the `name` and `description` fields?
  **Target:** the skill-creator skill and existing `SKILL.md` files in `.claude/skills/`

- Q4: What does the skill-creator skill's authoring workflow require as inputs and produce as outputs (scaffolding, eval loop, packaging), and which of its steps are mandatory per the ticket's "Built using the Anthropic skill builder skill" criterion?
  **Target:** the skill-creator skill definition

## State Management

- Q5: Where do new skills live in this repo (`.claude/skills/` vs `.claude/agents/`), and what is the relationship between a skill definition and its slash-command wrapper per the project conventions?
  **Target:** `.claude/skills/` and `.claude/agents/` and project CLAUDE.md conventions

- Q6: How are the `SKILL.md` body size limits (under 500 lines / 5000 tokens) measured and enforced in this repo, and is there an existing check or convention for keeping bodies within budget?
  **Target:** the module responsible for skill validation or any size-check tooling

## Edge Cases

- Q7: How does the standard pattern handle a skill that needs both a concise body and large reference appendices without exceeding the body budget — what is the precedent for what stays in `SKILL.md` vs what moves to `references/`?
  **Target:** existing multi-file skills under `.claude/skills/` (e.g., skill-creator, deep-research)

- Q8: What is the established convention for the `description` triggering field (when-to-use vs when-to-skip phrasing) so the new skill auto-invokes on devcontainer requests without over-triggering on general Docker work that is out of scope?
  **Target:** the skill-creator skill's description-optimization guidance and existing skill descriptions

- Q9: Does this repo's `.devcontainer/devcontainer.json` exist and what patterns does it already use (image vs build, remoteUser, features, lifecycle hooks), so the new skill's opinionated defaults do not contradict the repo's own setup?
  **Target:** `.devcontainer/devcontainer.json`

## Testing

- Q10: What mechanism exists to test or eval a skill in this repo, and is the skill-creator eval loop functional here or is it covered by the "non-functional placeholder" note about `evals/` and `scripts/run_eval.py`?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval loop

- Q11: What format do existing skill evals use for triggering and behavior assertions, so acceptance criteria (six lifecycle hooks covered, Compose patterns, CI/CD patterns, troubleshooting topics) can be verified rather than assumed?
  **Target:** any existing skill eval fixtures or the skill-creator skill

## Observability

- Q12: How does the skill loader report a malformed or oversized skill (frontmatter errors, missing required fields, body over budget) — where would such errors surface so authoring failures are visible?
  **Target:** the module responsible for parsing and loading skills
