# Questions — Create a new agent skill called using graphite cli
**Ticket:** RUS-6
**Generated:** 2026-05-26
**Status:** draft

## Data Flow
- Q1: What is the complete file structure and directory layout of each existing skill under `.claude/skills/`, including any `references/`, `scripts/`, or `assets/` subdirectories that exist?
  **Target:** `.claude/skills/`
- Q2: What frontmatter fields does each existing `SKILL.md` contain, and which fields are mandatory versus optional per the agentskills.io standard?
  **Target:** `.claude/skills/*/SKILL.md` frontmatter blocks
- Q3: How does the CLAUDE.md project config register skills and enable auto-invocation, and what mechanism maps a command (e.g., `/qrspi-research`) to a specific skill directory?
  **Target:** `.claude/CLAUDE.md`

## API Surface
- Q4: What is the minimum set of frontmatter fields (name, description, command, argument-hint, allowed-tools) and which must be present for an agent skill to load successfully?
  **Target:** `.claude/skills/*/SKILL.md` files
- Q5: How are the `allowed-tools` values scoped -- are they workspace-wide or per-skill, and what happens when a skill references a tool that is not listed?
  **Target:** `.claude/skills/*/SKILL.md` and CLAUDE.md configuration

## State Management
- Q6: What scope does the `$ARGUMENTS` variable have -- is it passed per-invocation from CLAUDE.md, cached across calls, or parsed from the command string by the harness?
  **Target:** `.claude/skills/*/SKILL.md` files that use `$ARGUMENTS`
- Q7: Are there any environment variables, config files, or session state that skills can read at runtime, and how is skill isolation enforced between parallel invocations?
  **Target:** CLAUDE.md and skill configuration

## Edge Cases
- Q8: What happens when two skills define the same command prefix (e.g., `/gt` vs `/gtx`) -- how does the auto-invocation resolver disambiguate?
  **Target:** CLAUDE.md skill registration logic
- Q9: If a skill references files outside its own directory (e.g., `.qrspi/<ticket-id>/`), what happens when that target path does not exist yet -- does the skill fail silently, produce an error, or create the path?
  **Target:** Skills that read from `.qrspi/<ticket-id>/`
- Q10: The ticket specifies SKILL.md body under 500 lines / 5000 tokens -- is this enforced by the harness or is it a human-review gate? What happens to a skill that exceeds this limit?
  **Target:** CLAUDE.md or any skill-validation logic

## Testing
- Q11: Is there an eval harness or testing mechanism for skills (e.g., `evals/` directory), and has any existing skill been evaluated with a benchmark or regression test suite?
  **Target:** `evals/` and `scripts/` directories
- Q12: Are there integration tests that validate a skill actually loads and executes its instructions when invoked with a command like `/qrspi-implement`?
  **Target:** `evals/`, `scripts/`, or any test harness

## Observability
- Q13: When a skill fails to load (e.g., bad frontmatter, missing SKILL.md, syntax error in allowed-tools), what does the agent see in the console -- a silent skip, an error message, or a warning?
  **Target:** CLAUDE.md harness behavior
