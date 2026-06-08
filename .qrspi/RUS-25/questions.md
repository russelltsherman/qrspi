# Questions — Create a new agent skill for writing Architecture Decision Records

**Ticket:** RUS-25
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk layout of an existing skill that combines `SKILL.md` with `references/`, `scripts/`, and `assets/` subdirectories, and where do such skills live in this repo?
  **Target:** `.claude/skills/` directory and any existing skill that uses `references/`/`assets/`
- Q2: How are reference files under a skill referenced from the `SKILL.md` body (relative path convention, link format) so the ADR skill can point to its MADR/Nygard/Y-statement reference docs?
  **Target:** an existing multi-file skill's `SKILL.md` that links into `references/`

## API Surface

- Q3: What is the exact required `SKILL.md` frontmatter schema (field names such as name/description, required vs optional fields, formatting constraints) that the agentskills.io standard and this repo enforce?
  **Target:** the module/tooling responsible for skill frontmatter validation (skill-creator skill) and an existing `SKILL.md` frontmatter block
- Q4: How is the Anthropic skill builder (skill-creator) skill invoked, and what inputs and outputs does it produce when generating a new skill?
  **Target:** the skill-creator skill definition

## State Management

- Q5: How does the QRSPI workflow distinguish a skill's slash-command wrapper (in `.claude/skills/`) from its agent definition (in `.claude/agents/`), and which artifacts must be created for a new skill to be discoverable?
  **Target:** `.claude/skills/` and `.claude/agents/` directories
- Q6: Are there existing conventions in the repo for where author-facing template/starter files (like the starter ADR in `assets/`) are stored versus reference documentation, and how is the distinction maintained?
  **Target:** an existing skill containing both `assets/` and `references/`

## Edge Cases

- Q7: What constraints does the skill tooling place on `SKILL.md` body size (the ticket requires under 500 lines / 5000 tokens), and is there a validator or eval that measures this?
  **Target:** the skill-creator skill and any size/lint check in `scripts/`
- Q8: How do existing skills encode multi-state lifecycles or status enumerations (e.g., the QRSPI phase statuses), which the ADR skill must mirror for the `proposed → accepted → deprecated/superseded/rejected` lifecycle?
  **Target:** existing skill or doc that documents a status lifecycle (e.g., QRSPI lifecycle docs)
- Q9: Does the repo already contain a `docs/decisions/`, `docs/adr/`, or `architecture/decisions/` directory or any existing ADRs whose numbering and naming the new skill must remain consistent with?
  **Target:** `docs/` directory tree

## Testing

- Q10: What is the established pattern for testing or evaluating a skill in this repo, given that the `evals/` harness is described as a non-functional placeholder?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator skill's eval loop
- Q11: How are skills currently verified for correct triggering and structure (e.g., description-matching tests, frontmatter checks) that the ADR skill should also satisfy?
  **Target:** the skill-creator skill's measurement/eval capability

## Observability

- Q12: How is a newly added skill surfaced to the agent at runtime (the available-skills listing), and what determines whether the ADR skill appears and auto-invokes correctly?
  **Target:** the mechanism/configuration that lists available skills to the agent
