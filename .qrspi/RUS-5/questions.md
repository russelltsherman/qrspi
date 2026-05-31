# Questions — writing-bash-scripts agent skill

**Ticket:** RUS-5
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: The skill follows the agentskills.io directory structure with SKILL.md plus optional references/, scripts/, assets/. Where in the `.qrspi/agents/` directory should the `writing-bash-scripts` skill be placed, and what is the exact invocation wrapper convention used to call this skill from other agents?
  **Target:** `.qrspi/agents/` directory and the skill-creator skill at `.qrspi/agents/skill-creator/`

- Q2: The ticket instructs to "use the Anthropic skill builder skill to generate the skill." How does the skill-creator skill produce SKILL.md content — does it scaffold files, invoke a model call, or generate a template? What is the exact input/output contract between the skill-creator and the generated skill directory?
  **Target:** `.qrspi/agents/skill-creator/` directory

- Q3: Existing skills in the project (e.g., `writing-bash-scripts` in the available-skills list) — is this a pre-existing skill that should be updated, or is this ticket asking to create a new one that did not previously exist? How do existing skills reference the `agentskills.io` standard in their frontmatter?
  **Target:** `.qrspi/agents/` directory listing of existing skill definitions

## API Surface

- Q4: The skill-creator skill must produce valid SKILL.md frontmatter following agentskills.io conventions. What are the required frontmatter keys (e.g., `name`, `description`, `version`), and how are optional directories (references/, scripts/, assets/) declared or implied?
  **Target:** Existing SKILL.md files in `.qrspi/agents/` for frontmatter conventions

- Q5: The skill content describes shell conventions (shebang, set -euo pipefail, trap patterns, getopts, subcommand dispatcher). Should these conventions be encoded entirely in the SKILL.md body, or should reference scripts or example files live in a `references/` directory as supplementary material?
  **Target:** SKILL.md body vs. `references/` directory boundary within the new skill

## State Management

- Q6: Does the skill need any persistent state (e.g., a registry of validated shell conventions, a checklist of must-include patterns), or is it purely a static reference document? If state is needed, where is it stored relative to the skill directory?
  **Target:** The skill's own directory structure

- Q7: The ticket specifies conventions like "target bash 4+ (note macOS ships bash 3.2)" and "BSD vs GNU coreutils differences." Should the skill encode environment detection logic, or is it purely a static guidance document that agents read at invocation time?
  **Target:** The skill-creator's understanding of static vs. dynamic skill content

## Edge Cases

- Q8: The skill's scope guidance says "never exceed ~200 lines without strong justification; at that point suggest a different language." Should the skill-enforcing agent validate line counts, or is this a soft heuristic? What happens if a bash script genuinely needs more than 200 lines — does the skill produce a warning, an error, or just a suggestion?
  **Target:** The `writing-bash-scripts` skill's scope validation logic

- Q9: The ticket mentions "include a gotchas section covering common pitfalls (unquoted variables, missing -- in commands, cd without error check)." How should the gotchas section be structured relative to the main conventions — as a separate subsection, as inline notes, or in a dedicated `references/` file?
  **Target:** The SKILL.md body structure of the `writing-bash-scripts` skill

- Q10: The skill should handle the case where `command -v` checks find missing dependencies. Should the skill specify exit codes and error message formats for each possible missing dependency, or just a generic pattern?
  **Target:** The error handling section of the `writing-bash-scripts` skill

## Testing

- Q11: The ticket states "produces ShellCheck-clean output when an agent follows the guidance." How should testability of the skill be measured — by generating example scripts and running them through ShellCheck, or by having the skill-creator's eval harness validate the SKILL.md against an agentskills.io schema?
  **Target:** `evals/` directory and `scripts/` directory for skill validation tooling

- Q12: The skill mentions recommending BATS-core for testable scripts. Should the skill include a BATS test template in a `scripts/` or `references/` directory, or just mention BATS-core by name in the SKILL.md body?
  **Target:** The `writing-bash-scripts` skill's `references/` or `scripts/` directory

## Observability

- Q13: When other agents invoke the `writing-bash-scripts` skill, how is skill usage tracked or logged in the qrspi project? Is there a mechanism to measure how often each skill is triggered, or whether agents follow the skill's guidance (e.g., by scanning generated scripts for ShellCheck violations)?
  **Target:** `evals/` directory and any skill invocation logging in the project

- Q14: The ticket says the SKILL.md body must be under 500 lines / 5000 tokens. Should the skill-creator enforce this limit during generation, or should a post-generation validation step check it? What is the consequence if the generated SKILL.md exceeds this limit?
  **Target:** The skill-creator skill's output validation pipeline

- Q15: Should the skill include a self-documenting mechanism where it lists its own conventions in a machine-readable format (e.g., a JSON schema or YAML checklist) so that downstream tools can verify a generated script complies with the skill's rules?
  **Target:** The `writing-bash-scripts` skill's asset or reference structure
