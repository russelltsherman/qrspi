# Questions — Create a new agent skill called using cmux cli

**Ticket:** RUS-10
**Generated:** 2026-05-26T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the existing skill-creator skill generate SKILL.md files, and what template or prompt structure does it use to produce the frontmatter and body sections?
  **Target:** the skill-creator skill definition (SKILL.md or equivalent entry point)

- Q2: What is the agentskills.io standard directory structure, and how do existing skills in this project organize their `SKILL.md`, `references/`, `scripts/`, and `assets/` directories?
  **Target:** existing skill directories under `.claude/skills/`

- Q3: What frontmatter fields are required by the agentskills.io standard for a valid SKILL.md, and what format constraints (YAML, TOML, etc.) apply?
  **Target:** any existing SKILL.md files in the project or skill-creator templates

## API Surface

- Q4: What CLI subcommands and flags does `cmux` expose that the skill must document, and is there a canonical source (man page, `--help` output, or docs) that enumerates them?
  **Target:** the ticket description (no codebase file — this question targets what reference material the skill must encode)

- Q5: How does the skill-creator skill's eval loop validate that a generated skill meets token/line limits (e.g., "under 500 lines / 5000 tokens"), and what tooling measures token count?
  **Target:** the skill-creator skill or its eval harness

- Q6: How do existing skills in this project define their trigger conditions (the description field that tells Claude when to auto-invoke), and what patterns produce reliable triggering?
  **Target:** existing SKILL.md files and their description/trigger metadata

## State Management

- Q7: Where does this project store skill artifacts during creation — are they written directly to `.claude/skills/<name>/` or staged in a temporary location before approval?
  **Target:** the skill-creator skill's file-writing logic

- Q8: How does the skill-creator skill handle `references/` subdirectory content — is reference material generated inline, split from the main SKILL.md, or provided separately?
  **Target:** the skill-creator skill and any existing skills with a `references/` directory

## Edge Cases

- Q9: What happens when a skill's SKILL.md body exceeds the 500-line or 5000-token limit — does the skill-creator skill enforce this with a hard error, a warning, or does it silently truncate?
  **Target:** the skill-creator skill's validation logic

- Q10: How does the project handle platform-specific skills (macOS-only in this case) — is there a convention for documenting platform constraints or conditionally disabling the skill on unsupported systems?
  **Target:** existing skills or project conventions for platform-scoped skills

- Q11: If a skill references external CLI tools that may not be installed (e.g., `cmux`, `brew`), how do existing skills handle the absence of those tools at invocation time?
  **Target:** existing skills that depend on external CLIs (e.g., the using-graphite-cli skill)

## Testing

- Q12: What eval harness exists for testing generated skills, and how are skill evals structured (input scenarios, expected outputs, pass/fail criteria)?
  **Target:** `evals/` directory and `scripts/` directory

- Q13: How does the skill-creator skill's eval loop work end-to-end — what does it measure, how many iterations does it run, and what constitutes a passing result?
  **Target:** the skill-creator skill's eval configuration

## Observability

- Q14: After a skill is created, what feedback or logs does the skill-creator skill produce to confirm successful generation, and how can the user verify the skill is correctly registered and triggerable?
  **Target:** the skill-creator skill's output and any skill registry mechanism in `.claude/settings.json` or equivalent
