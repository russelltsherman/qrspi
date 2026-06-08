# Questions — Create a new agent skill using obsidian cli

**Ticket:** RUS-17
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the directory layout the agentskills.io / Anthropic skill-builder pattern produces (SKILL.md plus references/, scripts/, assets/), and where in this repo are existing skills stored that the new Obsidian skill must sit alongside?
  **Target:** the skill-creator skill and `.claude/skills/`

- Q2: How does the skill-creator skill expect the new skill to be scaffolded and invoked (inputs, generated files, output location), so the build can be driven through it as the acceptance criteria require?
  **Target:** the skill-creator skill definition

## API Surface

- Q3: What fields, format, and length constraints does the SKILL.md frontmatter require (name, description, and any other keys), and what triggers the "body under 500 lines / 5000 tokens" limit named in the acceptance criteria?
  **Target:** the SKILL.md frontmatter convention used by existing skills in `.claude/skills/`

- Q4: How do existing skills in this repo split content between the SKILL.md body and a `references/` directory, so the Obsidian CLI command reference, URI protocol, and Dataview syntax can be placed correctly?
  **Target:** an existing multi-file skill under `.claude/skills/` that uses references/

## State Management

- Q5: How are skills registered and discovered so a newly added skill becomes available (directory naming, manifest, or auto-discovery), and is any index or config update needed when adding the Obsidian skill?
  **Target:** the module responsible for skill registration/discovery (`.claude/skills/` layout and any index)

- Q6: What naming convention governs skill directory and skill `name` values in this repo, and what must the Obsidian skill be named to remain consistent?
  **Target:** existing skill directories under `.claude/skills/`

## Edge Cases

- Q7: How do existing skills document error-handling and failure-mode guidance, so the Obsidian skill can encode the required cases (Obsidian not running, malformed YAML frontmatter, link collisions) in a consistent style?
  **Target:** an existing skill that includes error-handling guidance

- Q8: How do existing skills express "prefer tool X over fallback Y" decision guidance, so the CLI-vs-URI-vs-filesystem and idempotency guidance in this ticket can follow the same pattern?
  **Target:** an existing skill encoding tool-preference / fallback guidance

- Q9: Do any skills in this repo include runnable scripts or assets, and how are file permissions, shebangs, and invocation paths handled, in case the Obsidian skill needs a `scripts/` directory?
  **Target:** the `scripts/` or `assets/` directory of an existing skill, if present

## Testing

- Q10: How is a skill verified or evaluated in this repo (the skill-creator eval loop and the `evals/` + `scripts/run_eval.py` harness), and which of these is functional versus placeholder for validating the Obsidian skill?
  **Target:** `scripts/run_eval.py`, `evals/`, and the skill-creator eval loop

## Observability

- Q11: How does a skill's `description` field surface the skill for triggering/auto-invocation, and what wording pattern do existing skill descriptions use so the Obsidian skill is discoverable when an agent works with vaults and notes?
  **Target:** the `description` frontmatter of existing skills in `.claude/skills/`
