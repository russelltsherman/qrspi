# Questions — Create a new agent skill for writing Product Requirements Documents

**Ticket:** RUS-26
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does the skill-creator skill expect (skill name, description, target directory) and what files does it emit when generating a new skill?
  **Target:** the skill-creator skill at `.claude/skills/` (or the Anthropic skill builder referenced in the ticket)
- Q2: Where do existing skills in this repo place their generated SKILL.md and supporting directories, and what is the on-disk layout (SKILL.md + references/ + scripts/ + assets/) the new PRD skill must match?
  **Target:** `.claude/skills/` directory and an existing example skill's directory tree

## API Surface

- Q3: What frontmatter fields and format does the agentskills.io standard require in SKILL.md (name, description, and any others), and how do existing repo skills populate them?
  **Target:** the frontmatter of an existing `SKILL.md` (e.g., `.claude/skills/*/SKILL.md`)
- Q4: How is a skill's `description` field written so the skill triggers correctly, and what wording conventions do existing skills in this repo use for their trigger descriptions?
  **Target:** the `description` frontmatter across existing skills in `.claude/skills/`
- Q5: How does the slash-command wrapper relate to the skill definition, and does a SKILL.md-only skill need a separate wrapper in this repo's convention?
  **Target:** the wrapper files in `.claude/skills/` vs agent definitions in `.claude/agents/`

## State Management

- Q6: What constitutes the "default lean one-pager" versus the "expanded multi-section" PRD format, and how would the skill encode both so the agent selects between them rather than hardcoding one?
  **Target:** the module responsible for the PRD template content (SKILL.md body and/or `references/`)
- Q7: Which content belongs in the SKILL.md body versus the `references/` directory, given the 500-line / 5000-token cap on the body?
  **Target:** the SKILL.md body and `references/` split for the new skill

## Edge Cases

- Q8: How should the skill behave when the user's problem statement lacks supporting evidence — what clarifying-question behavior enforces problem-first validation before solution specification?
  **Target:** the module responsible for problem-statement validation guidance in SKILL.md
- Q9: How is the mandatory non-goals section enforced, and what happens when a generated PRD would omit it?
  **Target:** the non-goals enforcement guidance in the SKILL.md body
- Q10: How does the skill distinguish outcome-oriented goals from output-oriented ones, and what guidance catches a goal stated as an output ("build onboarding wizard")?
  **Target:** the goals/non-goals section guidance in SKILL.md

## Testing

- Q11: How is a SKILL.md authoring task verified in this repo — does skill-creator provide an eval loop, and what is the status of the `evals/` + `scripts/run_eval.py` harness?
  **Target:** `scripts/run_eval.py` and the `evals/` directory, plus any eval support in skill-creator
- Q12: What checks confirm the SKILL.md body stays under 500 lines / 5000 tokens and that frontmatter is valid against the agentskills.io standard?
  **Target:** any frontmatter/size validation tooling, or the verification approach for `.claude/skills/*/SKILL.md`

## Observability

- Q13: What metadata or status markers (document status Draft/In Review/Approved, version, changelog) should generated PRDs carry, and how would the skill instruct the agent to populate and update them so PRD state is traceable across iterations?
  **Target:** the metadata/changelog guidance in the SKILL.md PRD template
