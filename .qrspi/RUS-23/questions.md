# Questions — Create a new agent skill using the Crossplane CLI

**Ticket:** RUS-23
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory layout and file set does an existing skill produce (SKILL.md plus references/, scripts/, assets/), and where does this repo place skill source so a new Crossplane skill matches the established location?
  **Target:** `.claude/skills/` and the directory structure of an existing skill (e.g., `.claude/skills/qrspi-questions/`)
- Q2: How does the skill-creator skill ingest source material and emit the generated SKILL.md plus reference files — what inputs does it expect and what output paths does it write to?
  **Target:** the `skill-creator` skill (SKILL.md and any generation scripts under its directory)

## API Surface

- Q3: What exact fields are required in SKILL.md frontmatter (name, description, and any others) for it to be considered valid per the agentskills.io pattern this repo follows?
  **Target:** the frontmatter block of existing `SKILL.md` files in `.claude/skills/`
- Q4: What are the description-field conventions used by existing skills (length, trigger phrasing, "use when" structure) that the new skill's triggering description must conform to?
  **Target:** the `description` frontmatter field across skills in `.claude/skills/`
- Q5: Does the skill-creator skill provide an eval/benchmark sub-capability, and what command or entry point invokes it for measuring skill triggering and performance?
  **Target:** the `skill-creator` skill definition and its referenced eval tooling

## State Management

- Q6: How are reference documents under a skill's `references/` directory linked or referenced from SKILL.md so an agent loads them on demand rather than inline?
  **Target:** the SKILL.md body and `references/` of an existing multi-file skill

## Edge Cases

- Q7: What mechanism enforces the SKILL.md body size limit (under 500 lines / 5000 tokens), and how do existing large skills split content between the body and `references/` to stay within it?
  **Target:** existing skills in `.claude/skills/` and any skill-creator size guidance
- Q8: How do existing skills express version-dependent or branching guidance (analogous to Crossplane v1 vs v2), and is there an established pattern for "default to X unless the environment indicates Y" judgment calls?
  **Target:** the body of existing skills that encode conditional/version guidance
- Q9: When the skill-creator skill is asked to create a skill whose name collides with an existing one, how does it behave, and what naming constraints apply to the skill directory and frontmatter `name`?
  **Target:** the `skill-creator` skill and the naming pattern of directories under `.claude/skills/`

## Testing

- Q10: What eval or verification harness exists for skills in this repo, and is it functional or a placeholder, so the acceptance criteria can be validated?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval loop
- Q11: How are skill triggering accuracy and description quality measured (variance analysis, benchmarks), and what command produces those metrics?
  **Target:** the `skill-creator` skill's benchmarking/eval functionality

## Observability

- Q12: How does the skill-creator skill surface progress, validation results, or errors during generation (e.g., frontmatter validation failures, size-limit violations), so a creator can confirm the produced skill passes its checks?
  **Target:** the `skill-creator` skill's generation and validation output
