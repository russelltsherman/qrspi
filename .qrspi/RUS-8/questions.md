# Questions — Create a new agent skill called using argocd cli
**Ticket:** RUS-8
**Generated:** 2026-05-25T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the existing skill-creator skill discover and validate SKILL.md frontmatter fields, and what schema does it enforce for the frontmatter block?
  **Target:** the skill-creator skill definition (SKILL.md or equivalent)

- Q2: What is the agentskills.io standard directory structure, and how do existing skills in this project organize their `SKILL.md`, `references/`, `scripts/`, and `assets/` directories?
  **Target:** existing skill directories under `.claude/skills/` or equivalent skill root

- Q3: How does the skill-creator skill handle the generation of reference material files — does it produce them as separate documents in `references/`, or inline within SKILL.md?
  **Target:** the skill-creator skill and any existing skills with `references/` directories

## API Surface

- Q4: What trigger patterns (description field, keyword matching) do existing skills use to ensure Claude auto-invokes them, and what conventions exist for avoiding trigger collisions between skills that operate on overlapping CLI tooling (e.g., kubectl vs argocd)?
  **Target:** existing SKILL.md files, specifically their `description` and trigger-related fields

- Q5: What is the token/line budget enforcement mechanism for SKILL.md body content, and does the skill-creator skill validate the 500-line / 5000-token acceptance criterion during generation?
  **Target:** the skill-creator skill's validation logic

- Q6: How do existing skills reference environment variables (like `ARGOCD_AUTH_TOKEN`, `ARGOCD_SERVER`) — are these documented inline in the SKILL.md body, or is there a separate configuration or prerequisites section?
  **Target:** existing skills that depend on environment variables or CLI tool availability

## State Management

- Q7: How does the skill-creator eval loop measure skill quality, and what metrics or rubric does it apply to determine whether a generated skill meets acceptance criteria?
  **Target:** the skill-creator skill's eval harness and scoring logic

- Q8: When a skill covers both interactive and CI/CD automation contexts (as this ticket requires), how do existing skills structure conditional guidance — do they use separate sections, decision trees, or contextual headers?
  **Target:** existing multi-context skills (any skill that differentiates between interactive and automated usage)

## Edge Cases

- Q9: How do existing skills handle escalation paths (e.g., simple operation to complex multi-cluster patterns)? Is there a convention for progressive disclosure of advanced topics within SKILL.md versus deferring to reference documents?
  **Target:** existing skills with tiered complexity guidance

- Q10: What happens when the skill-creator generates a skill that exceeds the line/token budget — does it truncate, error, or restructure content into reference files automatically?
  **Target:** the skill-creator skill's output handling for oversized content

- Q11: How do existing skills encode opinionated defaults that vary by environment (e.g., "manual sync for prod, auto sync for dev")? Is there a pattern for environment-conditional guidance that avoids ambiguity for the agent?
  **Target:** existing skills with environment-specific recommendations

## Testing

- Q12: What eval cases exist for the skill-creator skill, and what format do eval inputs/expected outputs follow for validating a newly created skill?
  **Target:** `evals/` directory and skill-creator eval definitions

- Q13: How are skills tested for correct triggering — is there an eval or test harness that verifies a skill activates on expected user prompts and does not activate on unrelated prompts?
  **Target:** eval harness for skill trigger accuracy (evals/ or scripts/)

## Observability

- Q14: Does the project have any mechanism for tracking skill invocation frequency, failure modes, or user overrides after a skill is deployed — and if so, how would a new skill integrate with it?
  **Target:** observability infrastructure, logging hooks, or analytics integration for skills
