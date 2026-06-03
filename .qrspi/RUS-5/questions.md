# Questions — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an existing skill in this repo flow from `SKILL.md` frontmatter through to invocation — what fields in the frontmatter (name, description, triggers) are consumed and where?
  **Target:** existing `SKILL.md` files under `.claude/skills/` and the skill-loading mechanism

- Q2: Where are agent skills stored and discovered in this repo, and what is the on-disk directory layout for a single skill (SKILL.md plus optional `references/`, `scripts/`, `assets/`)?
  **Target:** `.claude/skills/` directory tree

## API Surface

- Q3: What exact `SKILL.md` frontmatter schema do existing skills use (required vs optional keys, value formats), and does it match the agentskills.io standard pattern referenced in the ticket?
  **Target:** frontmatter blocks of existing skills in `.claude/skills/`

- Q4: What capabilities does the Anthropic skill-builder / skill-creator skill expose that this ticket requires using to generate the new skill?
  **Target:** the skill-creator skill definition and its eval loop

## State Management

- Q5: How does the project distinguish between a skill's slash-command wrapper and its underlying agent definition, and where does each live for an existing skill?
  **Target:** `.claude/skills/` (wrappers) and `.claude/agents/` (definitions)

- Q6: Is there an index, registry, or manifest that must be updated when a new skill is added, or are skills discovered purely by directory presence?
  **Target:** the module/config responsible for skill discovery

## Edge Cases

- Q7: What is the enforced or conventional size limit for a `SKILL.md` body (the ticket cites under 500 lines / 5000 tokens) and how do existing skills handle overflow into `references/`?
  **Target:** existing skills that use a `references/` directory

- Q8: How do existing skills that bundle executable helpers under `scripts/` reference and invoke those scripts, and what conventions (permissions, shebang) do they follow?
  **Target:** `scripts/` subdirectories of existing skills

- Q9: What does an existing skill's `description` field look like that governs auto-invocation triggering, and what level of specificity is needed to avoid false triggers for a broad topic like "bash scripts"?
  **Target:** description fields of existing skills in `.claude/skills/`

## Testing

- Q10: How are skills verified or evaluated in this repo — is there an eval harness, and what is its current functional status?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval loop

- Q11: Is ShellCheck available in this environment, and how would the acceptance criterion "produces ShellCheck-clean output" be checked against sample scripts the skill guidance generates?
  **Target:** the toolchain/dev environment configuration

## Observability

- Q12: How can it be confirmed that a newly added skill is registered and discoverable by the agent (what surface lists available skills), so the new bash skill's presence and triggering can be verified?
  **Target:** the skill-listing surface and any logging emitted on skill load
