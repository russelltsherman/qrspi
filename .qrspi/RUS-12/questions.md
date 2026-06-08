# Questions — Create a new agent skill: using GitHub CLI

**Ticket:** RUS-12
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout of an existing skill in this repo, and where do skill definitions live versus their slash-command wrappers?
  **Target:** `.claude/skills/` and `.claude/agents/` directories

- Q2: How does a SKILL.md reference its supporting material (`references/`, `scripts/`, `assets/`), and what path conventions do existing skills use for those links?
  **Target:** the `using-graphite-cli` skill directory and any other skill with a `references/` subdirectory

## API Surface

- Q3: What frontmatter fields are present in existing SKILL.md files (e.g. name, description, trigger conditions), and which are required versus optional?
  **Target:** the SKILL.md frontmatter of `skill-creator` and `using-graphite-cli`

- Q4: What is the exact invocation contract for the Anthropic skill builder skill referenced in the ticket — what inputs it expects and what outputs it produces?
  **Target:** the `skill-creator` skill definition

- Q5: How are skill `description` fields phrased to encode trigger conditions, and what format do existing skills use to signal "TRIGGER when / SKIP when"?
  **Target:** the description fields of `claude-api` and `using-graphite-cli` skills

## State Management

- Q6: Is there an existing convention or precedent for a skill that wraps a CLI tool (auth state, environment variables, non-interactive mode), and how does it document those stateful concerns?
  **Target:** the `using-graphite-cli` skill (the closest existing CLI-wrapping skill)

## Edge Cases

- Q7: How do existing skills document non-interactive / CI execution contexts and environment-variable-driven configuration, given the ticket requires both interactive and CI auth coverage?
  **Target:** the body of `using-graphite-cli` SKILL.md and any references covering automation

- Q8: Does this project already mandate a git/GitHub workflow (the using-graphite-cli skill and CLAUDE.md git-delegation rule) that could conflict with a skill encouraging direct `gh` usage, and how is that boundary expressed?
  **Target:** `.claude/CLAUDE.md` git delegation conventions and the `using-graphite-cli` skill scope section

- Q9: What enforces the SKILL.md body size limit (under 500 lines / 5000 tokens) cited in the acceptance criteria — is there a lint, eval, or documented check?
  **Target:** the module or script responsible for skill validation, and `scripts/run_eval.py` / `evals/`

## Testing

- Q10: How are skills validated or evaluated in this repo, and is the eval harness functional or a placeholder for skill-level checks?
  **Target:** `scripts/run_eval.py`, the `evals/` directory, and project MEMORY.md note on the eval harness

- Q11: What testing precedent exists for non-code artifacts (skills, templates) versus the stdlib `_test.py` unit tests used for the resolver/persist scripts?
  **Target:** `scripts/qrspi_*_test.py` and any test coverage referencing `.claude/skills/`

## Observability

- Q12: How does the skill-creator workflow surface and report skill performance, triggering accuracy, or eval results, so the new skill's quality is observable after creation?
  **Target:** the `skill-creator` skill's eval/benchmark capability and its output reporting
