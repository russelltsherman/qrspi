# Questions — Create a kubectl CLI agent skill

**Ticket:** RUS-15
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an existing skill in this repo lay out the flow from `SKILL.md` body to its `references/`, `scripts/`, and `assets/` subdirectories — what relative-path conventions link the body to reference material?
  **Target:** an existing skill directory under `.claude/skills/` (e.g. `using-graphite-cli`) and its `SKILL.md`
- Q2: What does the Anthropic skill-builder skill produce as output, and where does it write the generated skill files — does it scaffold the directory structure or only the `SKILL.md`?
  **Target:** the skill-creator skill definition (the module responsible for skill generation)

## API Surface

- Q3: What is the exact required frontmatter schema (field names, allowed values, name/description constraints) for a `SKILL.md` in this repo's skills, and is there a validator that enforces it?
  **Target:** frontmatter of existing `.claude/skills/*/SKILL.md` files and any skill-validation script
- Q4: How are skills registered and surfaced to agents (auto-invocation vs. slash-command wrapper) — what file or manifest declares a skill's trigger description and name?
  **Target:** the module responsible for skill registration / the slash-command wrappers under `.claude/skills/`

## State Management

- Q5: Where do skill assets and reference files physically live relative to the worktree, and how is the kubectl skill expected to be persisted given the staging-plus-deterministic-move artifact convention (`/tmp/phase-stage/` → `.qrspi/`)?
  **Target:** `scripts/qrspi_persist.py` and the `.claude/skills/` directory layout
- Q6: Is there an existing CLI-tool agent skill in the repo whose structure (multi-file references, copy-pasteable command patterns) can serve as the structural reference for the kubectl skill?
  **Target:** the `.claude/skills/` directory (e.g. `writing-bash-scripts`, `using-graphite-cli`)

## Edge Cases

- Q7: How do existing skills enforce or document a body-size budget — is the "under 500 lines / 5000 tokens" constraint on `SKILL.md` checked anywhere, and what happens when content exceeds it?
  **Target:** any skill-linting/eval script and the longest existing `SKILL.md`
- Q8: How do existing skills encode prominently-placed safety guardrails (e.g. destructive-operation warnings) within `SKILL.md` — what formatting or section convention signals a guardrail versus normal guidance?
  **Target:** `using-graphite-cli` SKILL.md and any skill that gates destructive operations
- Q9: What is the repo's convention for an in-scope/out-of-scope or "judgment call" section inside a skill, and do any existing skills demonstrate scope boundaries the kubectl skill can mirror?
  **Target:** existing `.claude/skills/*/SKILL.md` bodies

## Testing

- Q10: How are skills verified in this repo given that the `evals/` + `scripts/run_eval.py` harness is documented as a non-functional placeholder — what is the actual accepted verification path for a new skill?
  **Target:** `scripts/run_eval.py`, the `evals/` directory, and the skill-creator eval loop
- Q11: What naming and directory conventions must a new skill directory satisfy to be discovered (directory name vs. frontmatter `name`, location under `.claude/skills/`)?
  **Target:** the `.claude/skills/` directory and skill-discovery logic

## Observability

- Q12: How is a skill's invocation or triggering surfaced/logged — is there any mechanism that records when a skill fires, which would let an author confirm the kubectl skill's description triggers correctly?
  **Target:** the module responsible for skill invocation logging / hooks under `~/.agents/hooks/`
