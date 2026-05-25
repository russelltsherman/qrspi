# Questions — Create a skill for writing bash scripts
**Ticket:** RUS-5
**Generated:** 2025-05-25T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the agentskills.io standard directory structure for a skill, and does the project already contain any existing skills that follow this pattern (e.g., a `SKILL.md` with frontmatter, `references/`, `scripts/`, `assets/` directories)?
  **Target:** the module responsible for skill directory layout (any existing skill directories in the repo)

- Q2: How does the Anthropic skill builder skill (`skill-creator`) expect input to be provided, and what artifacts does it produce — specifically, does it write `SKILL.md` directly or does it return content for the caller to write?
  **Target:** `.claude/skills/skill-creator/SKILL.md` or equivalent skill-creator definition

- Q3: What frontmatter schema does `SKILL.md` require (fields, types, required vs optional) according to the agentskills.io standard as implemented in this project?
  **Target:** any existing `SKILL.md` files or agentskills.io reference documentation in the repo

## API Surface

- Q4: Where do completed skills get installed or registered so that Claude Code can discover and invoke them — is there a settings file, a directory convention, or a manifest that indexes available skills?
  **Target:** `.claude/settings.json`, `.claude/settings.local.json`, or any skill registration mechanism

- Q5: What is the exact invocation interface the skill-creator skill exposes — what arguments does it accept, and does it have an eval loop that must be run before a skill is considered complete?
  **Target:** the skill-creator skill definition file

- Q6: Does the project enforce a token or line budget for `SKILL.md` files, and if so, where is that constraint defined and how is it validated?
  **Target:** any linting, validation scripts, or CI checks related to skill size

## State Management

- Q7: When a skill references supplementary material in `references/`, how are those files linked or included from the `SKILL.md` body — via relative paths, `@`-includes, or another mechanism?
  **Target:** any existing skill that uses a `references/` directory

- Q8: If the bash-scripts skill needs to exceed the 500-line / 5000-token SKILL.md budget, what is the established pattern for splitting content between the main `SKILL.md` and the `references/` directory?
  **Target:** existing skills with reference material, or agentskills.io documentation in the repo

## Edge Cases

- Q9: The ticket specifies "bash 4+" as the target but notes macOS ships bash 3.2. Are there any existing project scripts or CI environments that run bash 3.2, which would conflict with bash 4+ guidance in the skill?
  **Target:** CI configuration files, Dockerfiles, devcontainer configuration, and any existing `.sh` files

- Q10: The ticket mandates ShellCheck-clean output. Does the project already have ShellCheck configured (e.g., `.shellcheckrc`), and are there existing ShellCheck directives or exclusions that the new skill must be aware of?
  **Target:** `.shellcheckrc`, CI lint configuration, any ShellCheck references in existing scripts

- Q11: The ticket says to use the subcommand dispatcher pattern when a script has 2+ distinct operations. Are there existing bash scripts in the project that use a different pattern (e.g., separate scripts per operation) that would create inconsistency if the skill enforces the dispatcher pattern?
  **Target:** any `.sh` or bash scripts in the repository

## Testing

- Q12: Does the project have BATS-core installed or configured as a test dependency, and is there an existing test harness or directory convention for bash script tests?
  **Target:** `package.json`, `Makefile`, `go.mod`, test directories, or any BATS-related configuration

- Q13: How does the skill-creator's eval loop validate a skill — does it generate test scenarios, invoke the skill against sample prompts, or check structural conformance only?
  **Target:** the skill-creator skill definition and any eval harness in `evals/` or `scripts/`

## Observability

- Q14: Does the project have any existing conventions for how skills report their activation, usage, or failure modes — e.g., structured logs, metrics, or error patterns that the bash-scripts skill must conform to?
  **Target:** existing skill definitions and any observability infrastructure in the repo
