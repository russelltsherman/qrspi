# Questions — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the exact on-disk directory layout of an existing skill (SKILL.md plus the optional `references/`, `scripts/`, `assets/` subdirectories), and where do skills physically live in this repo?
  **Target:** `.claude/skills/` and any existing skill directories under it
- Q2: How does a skill's content get loaded and surfaced to an agent at invocation time — is the SKILL.md body read whole, and are `references/` files loaded lazily or eagerly?
  **Target:** the module or harness responsible for skill discovery and loading

## API Surface

- Q3: What fields are required in the SKILL.md YAML frontmatter (e.g. name, description, and any others), and what are their format/length constraints?
  **Target:** SKILL.md frontmatter of existing skills; the skill-creator skill definition
- Q4: How is a skill exposed as a slash command, and is a separate wrapper file required (the project notes "slash-command wrappers live in `.claude/skills/`")?
  **Target:** `.claude/skills/` wrappers and `.claude/agents/` definitions
- Q5: What naming convention governs the skill's directory name and frontmatter `name` (e.g. `using-graphite-cli` vs `using graphite cli`), and how must it match the ticket's intended invocation?
  **Target:** existing skill directory names under `.claude/skills/`

## State Management

- Q6: Does the project already contain a graphite-related skill, memory note, or convention (the global memory references "All git actions use the using-graphite-cli skill") that this skill must align with or supersede?
  **Target:** `~/.agents/memory/feedback_git_delegation.md` and existing `.claude/skills/` entries
- Q7: What governs the SKILL.md size limit referenced in acceptance criteria (under 500 lines / 5000 tokens) — is it enforced anywhere, or purely a convention to follow?
  **Target:** the skill-creator skill and any skill-size validation in the harness

## Edge Cases

- Q8: How do existing skills encode hard rules versus soft guidance (the ticket requires the single-commit-per-branch convention as a "hard rule")?
  **Target:** body structure of existing skills under `.claude/skills/`
- Q9: How do existing skills handle "never do X" warnings such as forbidding raw `git rebase`/`git commit --amend` on tracked branches — formatting, placement, and emphasis?
  **Target:** existing skills that contain prohibition/anti-pattern guidance
- Q10: Are there existing references in the repo to `gt continue`, `gt sync`, or Graphite workflow steps that this skill must stay consistent with?
  **Target:** repo-wide search of `.claude/` and `docs/` for Graphite CLI usage

## Testing

- Q11: How is a skill validated or evaluated in this repo — does the skill-creator eval loop or `scripts/run_eval.py` apply, and is that harness functional or a placeholder?
  **Target:** `scripts/run_eval.py`, `evals/`, and the skill-creator skill's eval tooling
- Q12: What does the skill-creator skill require as inputs/process steps, since the ticket mandates the skill be built using it?
  **Target:** the skill-creator skill definition

## Observability

- Q13: How is a newly created skill registered or made discoverable to the agent runtime (does it auto-appear, require a manifest update, or a restart), so its presence can be confirmed after creation?
  **Target:** the skill discovery/registration mechanism in the harness
