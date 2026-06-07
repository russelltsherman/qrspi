# Questions — Create a new agent skill using aws cli

**Ticket:** RUS-20
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the canonical on-disk layout that the agentskills.io standard prescribes (`SKILL.md` plus the optional `references/`, `scripts/`, `assets/` subdirectories), and where in this repo do existing skills place these files so the new aws-cli skill can mirror that convention?
  **Target:** the directory structure of existing skills under `.claude/skills/` and any agentskills.io structure documentation the skill-creator skill references
- Q2: What required frontmatter fields (name, description, and any others) must `SKILL.md` carry for it to be valid, and what format/length constraints apply to each?
  **Target:** the skill-creator skill definition and the frontmatter of existing `SKILL.md` files in the repo

## API Surface

- Q3: What inputs does the Anthropic skill builder (skill-creator) skill expect, and what outputs/files does it produce, so the ticket's "use the Anthropic skill builder skill to generate the skill" step can be executed concretely?
  **Target:** the skill-creator skill definition and its eval loop
- Q4: How is the `description` field in `SKILL.md` used for trigger/discovery, and what phrasing patterns do existing skills use to encode when an agent should invoke them?
  **Target:** the `description` frontmatter of existing skills and the skill-creator guidance on description authoring

## State Management

- Q5: What is the SKILL.md body size budget the acceptance criteria require (under 500 lines / 5000 tokens), and how do existing repo skills split content between `SKILL.md` and `references/` to stay within that budget?
  **Target:** the body length of existing `SKILL.md` files and how each delegates detail to `references/`
- Q6: How should the `references/` material be partitioned across the three required topics (JMESPath patterns, common waiter commands, service-specific cheat sheets), and is there a precedent in existing skills for one reference file per topic versus a combined file?
  **Target:** the `references/` directory of existing skills in `.claude/skills/`

## Edge Cases

- Q7: How does the skill-creator workflow handle a skill that is documentation-only (no `scripts/` needed), and what is the minimal valid skill when the `scripts/` and `assets/` directories are omitted?
  **Target:** the skill-creator skill definition and any existing skills that ship without `scripts/` or `assets/`
- Q8: The ticket says "do not encode AWS account IDs, specific resource names, or region choices" — what existing convention or lint/eval check, if any, verifies a skill avoids embedding environment-specific values, and where would such a check live?
  **Target:** the skill-creator eval harness and any validation under `scripts/` or `evals/`
- Q9: The ticket scopes out full IaC frameworks (Terraform, CDK, Pulumi) while keeping CloudFormation CLI commands in scope — where is the convention for documenting scope boundaries within a `SKILL.md`, and how do existing skills express "in scope / out of scope" guidance?
  **Target:** the body sections of existing `SKILL.md` files that state scope or non-goals

## Testing

- Q10: How is a newly authored skill validated in this repo — what does the skill-creator eval/benchmark loop check, and how is it invoked to confirm the aws-cli skill's frontmatter, body length, and description triggering?
  **Target:** the skill-creator skill's eval loop and `scripts/run_eval.py` / `evals/`
- Q11: What manual end-to-end verification path exists for a documentation skill given that the `evals/` harness is described as a non-functional placeholder, and how have prior skills been confirmed working?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval guidance

## Observability

- Q12: How is the creation or modification of a skill surfaced and tracked in this repo's workflow — what record (PR description, artifact, or status field) signals that the skill was built via the skill-creator skill and meets the acceptance criteria checklist?
  **Target:** the QRSPI artifact persistence path (`scripts/qrspi_persist.py`) and the PR/skill-creator reporting conventions
