# Questions — Create a new agent skill called writing bash scripts
**Ticket:** RUS-5
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## Data Flow
- Q1: What is the directory structure, file naming conventions, and frontmatter schema that the existing skill definitions follow in this project?
  **Target:** `.qrspi/agents/` or `.claude/skills/` directory
- Q2: What content and structure do the existing skill `SKILL.md` files contain, and what tokens/lines do they typically use?
  **Target:** Existing `SKILL.md` files in the project
- Q3: What does the `skill-creator` skill produce when invoked, and how does its output differ from a hand-written skill?
  **Target:** `skill-creator` skill definition and any generated outputs

## API Surface
- Q4: What is the `agentskills.io` standard pattern for agent skill directory structure, and what fields are required in SKILL.md frontmatter?
  **Target:** External `agentskills.io` specification or documentation
- Q5: What parameters, invocation syntax, and output format does the `skill-creator` skill accept?
  **Target:** `skill-creator` skill definition and usage examples

## State Management
- Q6: Where are generated skill artifacts stored and how are they discovered or loaded by the agent harness at runtime?
  **Target:** Project skill configuration, `.claude/settings.json`, or harness code
- Q7: Are skills scoped per-worktree, per-user, or workspace-wide, and does this affect where the new skill file is placed?
  **Target:** Project skill configuration and worktree setup code

## Edge Cases
- Q8: When a skill's guidance conflicts with an existing project convention (e.g., the project may have its own bash style), which takes precedence — the skill or the project convention?
  **Target:** Existing project conventions and any skill override mechanisms
- Q9: How should the skill handle bash 3.2 (macOS default) versus bash 4+ feature requests — does it produce conditional code, or does it document the incompatibility and refuse to generate it?
  **Target:** The portability conventions the skill encodes and any bash version detection logic
- Q10: What happens when the generated script exceeds the ~200 line threshold the skill mentions — does the skill truncate, warn, or suggest switching languages mid-output?
  **Target:** The skill's own enforcement logic for line-count limits

## Testing
- Q11: How are existing skills tested in this project — are there eval harnesses, regression tests, or human-review checklists for skill quality?
  **Target:** `evals/` directory, `scripts/` directory, or CI configuration
- Q12: What ShellCheck versions and rule sets are configured in this project, and are there any intentional exceptions?
  **Target:** ShellCheck configuration, `.shellcheckrc`, or CI linting scripts

## Observability
- Q13: How is skill usage tracked or measured in this project — is there telemetry, usage logging, or a way to determine which skills are invoked most frequently?
  **Target:** Project telemetry, usage analytics, or agent invocation logging
