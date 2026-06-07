# Questions — Create new agent skill called writing github actions

**Ticket:** RUS-27
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout an agentskills.io-standard skill must follow in this repo (`SKILL.md` plus `references/`, `scripts/`, `assets/`), and where do existing skills physically live versus their slash-command wrappers?
  **Target:** `.claude/skills/` and `.claude/agents/`
- Q2: How does the skill-creator skill generate a new skill — what inputs does it consume, what files does it scaffold, and where does it write its output?
  **Target:** the skill-creator skill (referenced as "the Anthropic skill builder skill" in the ticket)
- Q3: How is a skill's content split between the `SKILL.md` body and the `references/` directory, and what mechanism loads reference files on demand versus eagerly?
  **Target:** an existing multi-file skill under `.claude/skills/` (e.g. one with a `references/` subdirectory)

## API Surface

- Q4: What frontmatter fields are required and valid in a `SKILL.md` (e.g. name, description, trigger conditions), and what format/constraints does each field carry?
  **Target:** the frontmatter block of existing `SKILL.md` files under `.claude/skills/`
- Q5: What naming convention governs a skill's directory name and its invocation name, and how does that name map to a `/`-slash command?
  **Target:** the module responsible for registering skills as slash commands
- Q6: How is a skill's `description` field written to control auto-invocation/triggering accuracy, and are there length or wording conventions enforced?
  **Target:** existing skill descriptions in `.claude/skills/*/SKILL.md`

## State Management

- Q7: Are there constraints or tooling in this repo for the stated `SKILL.md` size limit (under 500 lines / 5000 tokens), and how is body length currently measured or enforced for existing skills?
  **Target:** the largest existing `SKILL.md` files under `.claude/skills/`
- Q8: When a skill ships `references/`, `scripts/`, and `assets/` subdirectories, what conventions govern relative-path references between `SKILL.md` and those subdirectories?
  **Target:** an existing skill that bundles `references/` or `scripts/`

## Edge Cases

- Q9: How do existing skills that include `scripts/` declare runtime/interpreter and dependencies, and what would a script in this new skill need to remain stdlib-only / dependency-free per repo convention?
  **Target:** `scripts/` directories within existing skills, and `scripts/qrspi_*_test.py` for the stdlib-only convention
- Q10: Does the skill-creator skill provide an eval/benchmark loop, and what is required (eval fixtures, expected outputs, harness wiring) to run it against a newly created skill in this repo?
  **Target:** the skill-creator skill's eval tooling and `evals/` + `scripts/run_eval.py`
- Q11: How do existing skills handle the case where content overlaps another skill's domain — is there a precedent for cross-referencing rather than duplicating guidance (relevant since this skill encodes broad GitHub Actions conventions)?
  **Target:** existing skills with overlapping scope under `.claude/skills/`

## Testing

- Q12: What is the established way to verify a skill in this repo prior to acceptance — does any skill ship automated tests, and how is the placeholder eval harness expected to be used versus manual end-to-end checks?
  **Target:** `evals/`, `scripts/run_eval.py`, and any `_test.py` siblings associated with skills

## Observability

- Q13: How is skill invocation surfaced or logged when a skill triggers (auto or via slash command), so that correct triggering of the new skill can be confirmed during review?
  **Target:** the module responsible for skill invocation/dispatch and its logging
