# Questions — Create a new agent skill called using claude cli
**Ticket:** RUS-9
**Generated:** 2026-05-26T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the exact directory structure and frontmatter schema that the agentskills.io standard requires for a `SKILL.md` file, and how do existing skills in this project conform to or deviate from that standard?
  **Target:** existing `SKILL.md` files in the project (e.g., `.claude/skills/*/SKILL.md`)

- Q2: How does the skill-creator skill (referenced in the project's available skills) generate skill artifacts, and what inputs/outputs does its build pipeline expect?
  **Target:** the module responsible for the `skill-creator` skill

- Q3: What is the current layout of `.claude/agents/` in this project, and how are custom subagent definitions structured (frontmatter fields, file naming, referencing from other skills)?
  **Target:** `.claude/agents/` directory

## API Surface

- Q4: What existing skills in this project reference Claude CLI flags or modes, and what flag documentation do they already encode that this new skill must avoid duplicating or contradicting?
  **Target:** all `SKILL.md` files under `.claude/skills/`

- Q5: How does the `references/` directory convention work in existing skills in this project — what file formats are used, how are references linked from the main `SKILL.md`, and are there size or naming constraints?
  **Target:** `references/` directories in existing skills

- Q6: What is the expected YAML frontmatter schema for `SKILL.md` files — which fields are required vs optional, and what values does the skill triggering/matching system use to determine when a skill fires?
  **Target:** the module or configuration responsible for skill discovery and triggering

## State Management

- Q7: How does the project manage skill versioning and updates — is there a registry, manifest, or index file that tracks available skills and must be updated when a new skill is added?
  **Target:** the module responsible for skill registration or discovery (e.g., settings files, manifest, or index)

- Q8: When a skill is split across a main `SKILL.md` body and `references/` files, how does the runtime load and assemble these — does it concatenate them, lazy-load on demand, or inject them as context only when specific triggers match?
  **Target:** the module responsible for skill loading at runtime

## Edge Cases

- Q9: The ticket specifies "SKILL.md body under 500 lines / 5000 tokens" — how are tokens counted for enforcement purposes, and what happens if a skill exceeds this limit (build error, runtime truncation, silent overflow)?
  **Target:** the module responsible for skill validation or token counting

- Q10: The ticket marks Agent Teams as experimental and requires noting this clearly. Are there existing patterns in the project for marking experimental features in skill documentation, and how do agents handle experimental-status warnings at invocation time?
  **Target:** existing skills or documentation that reference experimental features

- Q11: The ticket includes both `--bare` mode (which skips auto-discovery of skills) and MCP integration requiring explicit `--mcp-config` in bare mode. How do existing skills handle documenting mutually exclusive or mode-dependent flag combinations without creating contradictory guidance?
  **Target:** existing `SKILL.md` files that document CLI flags with conditional behavior

## Testing

- Q12: What test infrastructure exists for validating skills — are there eval harnesses, linting rules, or CI checks that run against `SKILL.md` files (e.g., frontmatter validation, token count checks, broken link detection)?
  **Target:** `evals/` directory and `scripts/` directory

- Q13: How are existing skills tested for triggering accuracy — is there an eval dataset or benchmark that measures whether the skill fires on the correct user prompts and avoids false positives?
  **Target:** the eval harness referenced in the project conventions (`evals/` and `scripts/`)

## Observability

- Q14: What logging, metrics, or telemetry does the skill runtime emit when a skill is matched and loaded — and how would we verify during development that the new skill triggers correctly on Claude CLI-related prompts?
  **Target:** the module responsible for skill matching/triggering and any associated logging configuration
