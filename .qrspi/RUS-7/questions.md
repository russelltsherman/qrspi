# Questions — Create a new agent skill called using argo workflows cli
**Ticket:** RUS-7
**Generated:** 2026-05-26T01:15:00Z
**Status:** draft

## Data Flow

- Q1: What is the agentskills.io standard directory structure for a skill, and what files are required vs optional (`SKILL.md`, `references/`, `scripts/`, `assets/`)?
  **Target:** the module or documentation responsible for skill directory layout conventions

- Q2: What frontmatter fields does a valid `SKILL.md` require according to the agentskills.io standard, and what are valid values for each?
  **Target:** existing `SKILL.md` files in the codebase and the skill-creator skill definition

- Q3: How does the Anthropic skill builder skill (`skill-creator`) expect input, and what is the sequence of operations it performs to produce a new skill?
  **Target:** `.claude/skills/skill-creator/SKILL.md` or equivalent skill definition

- Q4: When the ticket says "Detailed reference material in references/ directory if needed," what format and structure do existing skills use for their `references/` content?
  **Target:** `references/` directories in any existing skills

## API Surface

- Q5: What CLI command groups does the `argo` binary expose (submit, list, get, logs, watch, delete, cron, lint, retry, resubmit, stop, terminate, suspend, resume), and are there any additional groups not mentioned in the ticket that a comprehensive skill must cover?
  **Target:** the module responsible for enumerating argo CLI commands (or `argo --help` output)

- Q6: How do existing agent skills in this project structure their SKILL.md body to stay under the 500-line / 5000-token acceptance criterion while still covering a broad CLI surface?
  **Target:** existing `SKILL.md` files and their line/token counts

## State Management

- Q7: How does the skill-creator skill track progress across its generation phases — does it produce intermediate artifacts, require user approval between steps, or run to completion in one pass?
  **Target:** `.claude/skills/skill-creator/SKILL.md`

- Q8: Where in the project are skills registered so that Claude Code can discover and invoke them (e.g., `.claude/settings.json`, a skills index, or directory convention)?
  **Target:** `.claude/settings.json` or the skill discovery mechanism

## Edge Cases

- Q9: What happens when the skill body exceeds the 500-line / 5000-token limit — does the skill-creator enforce this constraint, or must it be validated separately?
  **Target:** the skill-creator skill's validation logic or post-generation checks

- Q10: How does the skill handle the case where `argo` CLI is not installed or not on the PATH in the agent's environment — do existing skills include prerequisite checks or guards?
  **Target:** existing skills that wrap external CLI tools

- Q11: If the skill references both `--dry-run` (client-side) and `--server-dry-run` (server-side), how does it guide the agent when the Argo server is unreachable and server-dry-run fails?
  **Target:** the debugging and validation sections of the skill body

## Testing

- Q12: What eval harness exists in this project for testing skills, and what does a skill eval look like (input prompt, expected behavior, scoring)?
  **Target:** `evals/` and `scripts/` directories

- Q13: How are existing skills tested for correctness — are there snapshot tests of SKILL.md output, integration tests that invoke the skill, or manual checklists?
  **Target:** test files associated with existing skills

## Observability

- Q14: Do existing skills include any observability guidance (logging, metrics, tracing) for the CLI operations they wrap, and if so, what pattern do they follow?
  **Target:** existing `SKILL.md` files that wrap CLI tools

- Q15: What conventions exist for surfacing workflow node status transitions (Pending, Running, Succeeded, Failed, Error, Skipped, Omitted) in agent output so the user can observe progress?
  **Target:** the module responsible for agent output formatting or existing monitoring-related skills
