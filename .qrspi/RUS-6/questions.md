# Questions — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory does the Anthropic skill builder skill emit generated skill files into, and how does that path map to where this project expects skills to live?
  **Target:** the skill-creator (Anthropic skill builder) skill and its generation/output logic
- Q2: How does a skill's `SKILL.md` reference and load its `references/`, `scripts/`, and `assets/` sub-resources at runtime, and what path resolution rules apply?
  **Target:** an existing skill in `.claude/skills/` that uses a `references/` directory

## API Surface

- Q3: What fields are required versus optional in `SKILL.md` frontmatter, and what are the constraints on the `name` and `description` fields?
  **Target:** the skill frontmatter schema/spec as used by existing skills in `.claude/skills/`
- Q4: How is a skill registered so it becomes invocable as a slash command (e.g. `/using-graphite-cli`) versus auto-invoked, and is any wrapper file required beyond `SKILL.md`?
  **Target:** the module responsible for skill discovery/registration; existing skill wrappers in `.claude/skills/`

## State Management

- Q5: Where is the repo-level Graphite trunk configuration persisted (`.git/`) versus the global user config (`~/.config/graphite/`), and which of these does an agent need to read or verify before operating?
  **Target:** the references material describing Graphite initialization and configuration
- Q6: What is the canonical naming convention for the skill directory and the `name` frontmatter value, and does this repo already contain a using-graphite-cli skill or related git-delegation skill that this would conflict with or replace?
  **Target:** `.claude/skills/` directory contents

## Edge Cases

- Q7: When a branch ends up with more than one commit, what failure mode does the ticket's "single commit per branch" rule guard against, and how should the skill instruct an agent to detect and recover that state?
  **Target:** the references material covering the single-commit-per-branch convention
- Q8: During a restack conflict, what exact sequence distinguishes correct recovery (`gt continue`) from the forbidden path (`git rebase --continue`), and how should the skill instruct the agent to verify the stack is fully propagated afterward?
  **Target:** the references material covering restacking and conflict resolution
- Q9: What does the skill instruct an agent to do when raw `git branch` or `git rebase` commands have already been run on a Graphite-tracked branch and metadata has drifted?
  **Target:** the references material covering git/Graphite mixing warnings

## Testing

- Q10: How are skills evaluated for correctness in this repo, and what eval format does the harness expect for a newly authored skill?
  **Target:** the eval harness in `evals/` and `scripts/`
- Q11: What measurable checks correspond to the acceptance criteria (SKILL.md under 500 lines / 5000 tokens, valid frontmatter, `references/` present), and is there an existing lint or validation step that enforces them?
  **Target:** the skill validation/lint tooling and the skill-creator eval loop

## Observability

- Q12: How does an agent surface or log which Graphite command it ran and the resulting stack state (e.g. `gt log short`) so the outcome is auditable, and does the skill prescribe any output the agent must report back?
  **Target:** the references material covering stack navigation/visualization (`gt log short`)
