# Questions — Create a writing-bash-scripts agent skill

**Ticket:** RUS-5
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where does the skill-creator skill store generated skills on disk — under `.claude/skills/`, `.qrspi/skills/`, or another directory?
  **Target:** the skill-creator skill's output logic

- Q2: How does the agentskills.io directory structure map to qrspi's existing skill layout — are `references/`, `scripts/`, and `assets/` subdirectories under a single `writing-bash-scripts/` directory, or spread across the workspace?
  **Target:** the skill-creator skill and the `.claude/skills/` directory

## API Surface

- Q3: What SKILL.md frontmatter fields are required by the skill-creator skill versus optional, and does the qrspi workflow expect any additional fields beyond agentskills.io?
  **Target:** the skill-creator skill's SKILL.md specification

- Q4: How are skill invocation triggers defined — via the `/` slash command prefix, auto-invoke conditions in the system prompt, or both?
  **Target:** existing skills in `.claude/skills/` or `.agents/skills/`

## State Management

- Q5: Does the skill-creator skill maintain any persistent state (e.g., a registry of all skills, version tracking, or eval history), and if so, where is it stored?
  **Target:** the skill-creator skill's storage backend

## Edge Cases

- Q6: When a bash script skill is invoked, how should the agent distinguish between writing a new script from scratch versus editing an existing one — does the skill guidance need to encode discovery logic, or is that always the agent's responsibility?
  **Target:** the writing-bash-scripts skill's SKILL.md body

- Q7: The ticket calls out bash 3.2 on macOS versus bash 4+ features like associative arrays — should the skill include a conditional detection mechanism (e.g., `bash --version` check at skill invocation time), or is the documentation note sufficient?
  **Target:** the writing-bash-scripts skill's references or SKILL.md body

## Testing

- Q8: The ticket requires ShellCheck-clean output — should the skill itself invoke ShellCheck as a post-generation verification step, or is that a manual gate the agent performs?
  **Target:** the writing-bash-scripts skill's SKILL.md guidance

- Q9: How should the skill's correctness be evaluated — does the eval harness look at generated scripts passing ShellCheck, functional test results, or both?
  **Target:** the `evals/` directory and `scripts/` eval harness

## Observability

- Q10: When the skill-creator skill runs, what logging or output does it produce that would help debug a failed skill generation — and should the writing-bash-scripts skill add its own instrumentation?
  **Target:** the skill-creator skill's execution output
