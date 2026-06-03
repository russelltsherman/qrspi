# Questions — Create a new agent skill: using helm cli

**Ticket:** RUS-14
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the Anthropic skill builder skill (skill-creator) consume an initial description and produce a SKILL.md plus supporting directories, and what inputs does it require to run?
  **Target:** the skill-creator skill definition and its referenced builder scripts

- Q2: What is the canonical on-disk layout for an agentskills.io-style skill in this repo (SKILL.md + references/ + scripts/ + assets/), and where do new skills get placed?
  **Target:** existing skill directories under `.claude/skills/` and `.claude/agents/`

## API Surface

- Q3: What exact frontmatter fields and value formats are required and accepted in a valid SKILL.md (name, description, triggers, allowed-tools, etc.)?
  **Target:** the SKILL.md frontmatter spec used by skill-creator and an existing SKILL.md example

- Q4: How is a skill's `description`/trigger phrasing structured so the harness auto-invokes it correctly, and what conventions does skill-creator enforce for triggering accuracy?
  **Target:** the skill-creator skill and its description-optimization guidance

- Q5: How are `references/`, `scripts/`, and `assets/` files referenced from within SKILL.md so the agent loads them on demand rather than inline?
  **Target:** an existing multi-file skill and its SKILL.md cross-references

## State Management

- Q6: What process does skill-creator define for its eval loop, and where are eval cases and results stored when iterating on a new skill?
  **Target:** the skill-creator eval workflow and `evals/` directory

- Q7: How is the SKILL.md body size constraint (under 500 lines / 5000 tokens) measured and validated, and what existing skills sit near that boundary?
  **Target:** the module responsible for skill size/token validation and existing SKILL.md files

## Edge Cases

- Q8: How do existing skills delineate in-scope vs out-of-scope material (e.g., deferring related topics to separate skills) within SKILL.md so scope boundaries like kubectl/kustomize, Helmfile, and GitOps reconcilers are expressed consistently?
  **Target:** scope/boundary sections of existing skill SKILL.md files

- Q9: How do existing skills handle version-specific guidance where defaults differ across tool versions (analogous to Helm 3 vs Helm 4 behavior), and is there a convention for noting compatibility caveats?
  **Target:** existing skills that encode version- or environment-dependent behavior

- Q10: When skill-creator generates a skill, how are failure cases surfaced if required frontmatter is missing or the directory structure is invalid?
  **Target:** the skill-creator validation step and any structure-check script

## Testing

- Q11: How are skills verified in this repo given the eval harness is a non-functional placeholder, and what manual or unit-test path confirms a new skill is well-formed?
  **Target:** `scripts/run_eval.py`, the `evals/` placeholder, and skill-creator's eval guidance

## Observability

- Q12: How does the harness report which skill was invoked and whether its trigger matched, so authors can confirm the new helm skill activates on the intended requests?
  **Target:** the module responsible for skill invocation/trigger logging
