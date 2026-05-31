# Questions — Create a new agent skill called using github cli

**Ticket:** RUS-12
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How do existing skills in this repository structure their `SKILL.md` frontmatter (name, description, command, argument-hint, allowed-tools, model), and what fields are required versus optional?
  **Target:** `.claude/skills/*/SKILL.md` files in the repo, especially those following the agentskills.io standard.

- Q2: What is the canonical directory layout that other skills in this repo use for `references/`, `scripts/`, and `assets/` subdirectories?
  **Target:** Any existing skill in `.claude/skills/` that uses reference material (e.g., `qrspi-work`, `verify`, `code-review`).

## API Surface

- Q3: Which `gh` CLI subcommands are already used elsewhere in this repo (workflows, scripts, other skills, CLAUDE.md guidance), and what conventions are already established for invoking them?
  **Target:** The full repo — grep for `gh ` invocations across `.claude/`, `.qrspi/`, `scripts/`, and root-level config.

- Q4: Does this repo already have any documented pattern for shell snippets in skills (e.g., HEREDOC commit bodies, `--json`/`--jq` parsing), and where is that pattern codified?
  **Target:** `.claude/skills/using-graphite-cli/SKILL.md` and the using-graphite-cli skill's `references/` directory; CLAUDE.md instructions.

## State Management

- Q5: Where does the qrspi workflow currently document its trigger conditions (the YAML `description` field) and how do other skills format that description string to maximize triggering accuracy?
  **Target:** The `description:` frontmatter field across `.claude/skills/*/SKILL.md` files.

- Q6: How does this repo's skill-creator skill expect new skills to be authored and evaluated — what is its end-to-end flow, and what evals harness exists?
  **Target:** The skill-creator skill definition and the `evals/` and `scripts/` directories referenced in CLAUDE.md.

## Edge Cases

- Q7: What is the established convention for skills that wrap external CLIs (like the using-graphite-cli skill) regarding tool lockdown, allowed bash patterns, and forbidding raw invocations of the underlying tool outside the skill?
  **Target:** `.claude/skills/using-graphite-cli/SKILL.md`.

- Q8: How do existing skills handle the case where the wrapped CLI is unauthenticated or misconfigured (e.g., expired tokens, missing config) — is there a documented "hard stop" pattern?
  **Target:** `.claude/skills/using-graphite-cli/SKILL.md` and the global MEMORY.md error-surfacing entry.

- Q9: How do existing skills handle non-interactive / CI versus interactive developer-workstation contexts when the underlying CLI behaves differently between them?
  **Target:** The using-graphite-cli skill and any CI-related shell scripts in `scripts/`.

## Testing

- Q10: What test conventions, if any, exist for skill content in this repo (the evals harness mentioned in `.claude/CLAUDE.md`), and what does the eval contract look like for a new skill?
  **Target:** `evals/` directory and `scripts/` directory.

- Q11: Are there any sample skill evals that exercise an external-CLI wrapping skill (graphite, gh, etc.) that can serve as a template for evaluating this new skill?
  **Target:** `evals/` directory.

## Observability

- Q12: Where in the repo are skill versions, changelogs, or commit conventions for skill modifications documented, so that this new skill follows the same revision-tracking pattern?
  **Target:** Recent git log for `.claude/skills/`, the qrspi `revision-log.md` template, and any CHANGELOG files.

- Q13: How do existing skills surface errors and progress (verbose progress logs, structured output, etc.) so that the new gh-cli skill follows the same observability pattern?
  **Target:** `.claude/skills/qrspi-work/SKILL.md` and the using-graphite-cli skill — both wrap CLIs and likely model the observability convention.
