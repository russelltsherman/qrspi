# Questions — Create a new agent skill named using git worktrees

**Ticket:** RUS-30
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What directory does the agentskills.io standard require for a skill, and what files/subdirectories (SKILL.md, references/, scripts/, assets/) appear in existing skills in this repo?
  **Target:** existing skill directories under `.claude/skills/` (e.g., `.claude/skills/qrspi-work/`)
- Q2: How do existing skills in this repo split content between `SKILL.md` and `references/` files — what lives in the body versus what is deferred to references?
  **Target:** `.claude/skills/*/SKILL.md` and any `.claude/skills/*/references/` directories

## API Surface

- Q3: What exact frontmatter fields does a valid `SKILL.md` use in this repo (name, description, command, argument-hint, allowed-tools, model), and which are required?
  **Target:** frontmatter of existing `.claude/skills/*/SKILL.md` and `.claude/agents/*.md`
- Q4: What is the established naming convention for skill `name` and `command` fields, and how would a "using git worktrees" skill be named to match?
  **Target:** `name`/`command` fields across `.claude/skills/*/SKILL.md`
- Q5: How are `scripts/` referenced and invoked from within an existing skill — relative path conventions, executability, shebang style?
  **Target:** any `.claude/skills/*/scripts/` directory and references to them in SKILL.md bodies

## State Management

- Q6: Is there a skill-builder skill available in this repo or environment (the "Anthropic skill builder skill" the ticket mandates), and what does it expect as input/output?
  **Target:** `.claude/skills/skill-creator/` or equivalent skill-authoring skill
- Q7: Where should the new skill physically live in this repo's tree, and does the repo distinguish project-local skills from global ones?
  **Target:** `.claude/skills/` layout and `.claude/CLAUDE.md` conventions

## Edge Cases

- Q8: Does this repo itself use the bare-repo worktree pattern, or the `.worktrees/<ticket-id>/` linked-worktree pattern, and would the skill's recommended layout conflict with the repo's own QRSPI worktree convention?
  **Target:** `.claude/CLAUDE.md` worktree section and `.gitignore` entries for `.worktrees/`
- Q9: What is the SKILL.md body size budget enforced by the acceptance criteria (under 500 lines / 5000 tokens), and how do existing skills measure against it as a reference point?
  **Target:** line/token counts of existing `.claude/skills/*/SKILL.md`
- Q10: How should the skill describe submodule and shared-stash gotchas without overstepping scope guidance (no general branching strategy, no IDE-specific detail)?
  **Target:** the ticket's Scope Guidance section as encoded in skill body vs references split

## Testing

- Q11: Does this repo have an eval harness for skills (`evals/`, `scripts/`) that a new skill must conform to, and what shape do skill evals take?
  **Target:** `evals/` directory and `scripts/` at repo root
- Q12: How is the bare-repo bootstrap script expected to be validated — is there a ShellCheck/lint convention scripts must pass in this repo?
  **Target:** existing `.claude/skills/*/scripts/*.sh` and any lint config (`.shellcheckrc`, CI workflow)

## Observability

- Q13: How does an agent verify a skill is well-formed and triggers correctly in this repo (description-triggering, eval pass/fail signals) — what feedback surfaces tell the author the skill works?
  **Target:** `evals/` harness output conventions and `skill-creator` eval loop if present
