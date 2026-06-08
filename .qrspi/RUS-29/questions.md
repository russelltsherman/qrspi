# Questions — Create a new agent skill called writing dockerfiles

**Ticket:** RUS-29
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the canonical on-disk layout the skill-creator skill produces for a new skill (SKILL.md plus the optional `references/`, `scripts/`, `assets/` subdirectories), and where does it place generated skills?
  **Target:** the skill-creator skill (`.claude/skills/skill-creator/` or its SKILL.md) and the skill-creator Skill tool

- Q2: How do existing skills reference their `references/` material from the SKILL.md body — by relative path, by explicit instruction to read, or by some loader convention — so the dockerfile skill's language-specific reference files are discoverable?
  **Target:** an existing skill that uses a `references/` directory (e.g. under `.claude/skills/`)

## API Surface

- Q3: What exact frontmatter fields does the agentskills.io / Anthropic skill standard require in `SKILL.md` (name, description, and any others), and what format/validation does the skill-creator enforce on them?
  **Target:** the skill-creator skill's SKILL.md template and frontmatter validation logic

- Q4: How is a skill's `description` field written in existing skills to control auto-invocation triggering, and what length or phrasing constraints apply?
  **Target:** the `description` frontmatter of existing skills in `.claude/skills/`

## State Management

- Q5: Where should a newly authored skill physically live in this repo (`.claude/skills/<name>/`) and what naming convention applies to the directory versus the skill `name` field (e.g. `writing-dockerfiles` vs "writing dockerfiles")?
  **Target:** the `.claude/skills/` directory and existing skill directory naming

- Q6: Is there an index, manifest, or registration step (e.g. in `.claude/CLAUDE.md` or settings) that must be updated for a new skill to be listed and invokable, or are skills discovered purely by directory presence?
  **Target:** `.claude/CLAUDE.md`, `.claude/settings*.json`, and the skill discovery mechanism

## Edge Cases

- Q7: What does the skill-creator do when a SKILL.md body exceeds the size budget — is the under-500-lines / under-5000-tokens limit from the acceptance criteria enforced anywhere, or only advisory?
  **Target:** the skill-creator skill's size-budgeting / token-counting logic

- Q8: How do existing skills that bundle `scripts/` handle the case where the dockerfile skill ships no executable scripts — is `scripts/` required, optional, or expected to be omitted entirely?
  **Target:** existing skills with and without a `scripts/` directory under `.claude/skills/`

- Q9: Does the skill-creator's eval loop (referenced in the memory directive about always running it) require pre-existing eval fixtures, and what happens for a skill like this one where the `evals/` harness is a non-functional placeholder?
  **Target:** the skill-creator eval loop and `evals/` + `scripts/run_eval.py`

## Testing

- Q10: What mechanism, if any, exists to validate a finished skill (frontmatter validity, body size, reference link integrity) before it is considered complete, and is it manual or scripted?
  **Target:** the skill-creator skill's validation/eval tooling and `scripts/run_eval.py`

- Q11: For documentation-only artifacts like a skill, what does the repo's "a coding task is never complete without tests" convention translate to — eval cases, lint checks, or none?
  **Target:** existing skills in `.claude/skills/` and any sibling test/eval files

## Observability

- Q12: How does the skill-creator surface progress, validation results, or errors during skill generation (console output, written report, eval scores), so the author can confirm each acceptance criterion was met?
  **Target:** the skill-creator skill and its eval-loop output
