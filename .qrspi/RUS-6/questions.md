# Questions — Create a new agent skill called using graphite cli
**Ticket:** RUS-6
**Generated:** 2026-05-27T12:30:00Z
**Status:** draft

## Data Flow
- Q1: How does the existing `skill-creator` skill validate that a generated `SKILL.md` conforms to the agentskills.io frontmatter specification?
  **Target:** `evals/` or `scripts/` containing the skill-creator validation logic
- Q2: Where does the `skill-creator` skill write its output, and how does it reference the `references/`, `scripts/`, and `assets/` subdirectories?
  **Target:** `skills/skill-creator/` or the skill definition used by `Skill` tool invocations
- Q3: What is the existing `using-graphite-cli` skill's current `SKILL.md` content, and how does it structure reference material?
  **Target:** The `using-graphite-cli` skill directory (path in the skills registry or `.claude/skills/`)
- Q4: How does the `qrspi-worktree` skill encode its DAG and session state, and could the graphite skill use a similar pattern for tracking stack state?
  **Target:** The `qrspi-worktree` skill definition

## API Surface
- Q5: Which Graphite CLI commands need to be represented in the skill versus left as references, given the agentskills.io convention of embedding core workflow directly in `SKILL.md`?
  **Target:** The Graphite CLI (`gt`) command set and the agentskills.io specification
- Q6: How does the skill distinguish between commands an agent should invoke directly (e.g., `gt create`) and commands that are prohibitions (e.g., `git rebase` on tracked branches)?
  **Target:** The `SKILL.md` body structure and any existing prohibition patterns in other skills

## State Management
- Q7: Where does Graphite store its repo-level config (trunk branch, remote) inside `.git/`, and what file names are used?
  **Target:** Graphite CLI's `.git/` config files or docs on its configuration format
- Q8: What files exist in `~/.config/graphite/` and what is the schema of the user-level config?
  **Target:** `~/.config/graphite/` directory

## Edge Cases
- Q9: When an agent runs `gt modify --all` and multiple descendants have uncommitted changes, what does Graphite do and what does the skill need to warn the agent about?
  **Target:** Graphite CLI behavior documentation or source code handling stacked branches with dirty working trees
- Q10: What happens when `gt sync` encounters a branch that was merged remotely but the local Graphite metadata does not reflect that merge?
  **Target:** Graphite CLI `gt sync` implementation or error handling around stale metadata

## Testing
- Q11: Does the project have an eval harness or test script for validating generated skills, and what assertions does it make on `SKILL.md`?
  **Target:** `evals/` directory and any test scripts in `scripts/`
- Q12: How should the generated skill's correctness be verified — by running the `skill-creator` eval, by manual review, or through some other mechanism?
  **Target:** The eval harness and how other skills were validated

## Observability
- Q13: How does the Linear MCP server currently interact with Graphite PRs (via `list_diffs`, `get_diff`, `get_diff_threads`), and does the agent skill need to mirror or replace any of those capabilities?
  **Target:** The Linear MCP tool definitions and the Graphite CLI diff commands
