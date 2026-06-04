# Questions — Create a new agent skill: writing GitLab pipelines

**Ticket:** RUS-28
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where do existing agent skills physically live in this repo, and what is the on-disk layout of a single skill (SKILL.md plus any references/, scripts/, assets/ subdirectories)?
  **Target:** `.claude/skills/` directory and the module responsible for skill storage

- Q2: How is a skill's content surfaced to an agent at invocation time — is the full SKILL.md body loaded, or only the frontmatter description until triggered, and where is that loading defined?
  **Target:** the module responsible for loading/registering skills (skill loader)

## API Surface

- Q3: What exact frontmatter fields does a SKILL.md require and which are optional, according to the agentskills.io / skill-creator convention already used in this repo?
  **Target:** the `skill-creator` skill definition and an existing `.claude/skills/*/SKILL.md` frontmatter block

- Q4: What is the Anthropic "skill builder" skill referenced in the ticket — is it the `skill-creator` skill present in this environment, and what inputs/invocation does it expect?
  **Target:** the `skill-creator` skill and its SKILL.md

- Q5: How are slash-command wrappers wired to skills in this repo, and would a new "writing GitLab pipelines" skill need a wrapper or only a SKILL.md?
  **Target:** `.claude/skills/` wrappers vs `.claude/agents/` definitions

## State Management

- Q6: Is there a naming convention or registry that skill directory names must conform to (e.g., kebab-case, prefix), and where is that constraint enforced or documented?
  **Target:** the module responsible for skill discovery / naming conventions

## Edge Cases

- Q7: What is enforced when a SKILL.md exceeds the body size limits the ticket cites (under 500 lines / 5000 tokens) — is there validation tooling, or is it convention only?
  **Target:** `skill-creator` skill eval/validation tooling, if any

- Q8: How do existing skills handle reference material that would otherwise bloat SKILL.md — what is the established pattern for splitting content into `references/` and how are those files referenced from the body?
  **Target:** an existing skill that uses a `references/` directory

- Q9: Are there existing skills with `scripts/` or `assets/` subdirectories, and what conventions (shebang, permissions, language) do those scripts follow that a new skill must match?
  **Target:** existing `.claude/skills/*/scripts/` directories

## Testing

- Q10: How are skills validated or eval-tested in this repo — does `skill-creator` provide an eval loop, and is there a `scripts/run_eval.py` or `evals/` harness that applies to skills?
  **Target:** `scripts/run_eval.py` and the `evals/` directory

- Q11: What does the skill-creator eval loop measure for a skill's description (triggering accuracy), and what format must eval cases take?
  **Target:** the `skill-creator` skill eval components

## Observability

- Q12: How is skill invocation or triggering observable during a session — is there logging, a hook, or a transcript signal that confirms a skill was loaded and used?
  **Target:** the module responsible for skill invocation logging / hooks (e.g., `~/.agents/hooks/`)
