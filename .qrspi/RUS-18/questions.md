# Questions — Create a new agent skill: using terraform cli

**Ticket:** RUS-18
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory layout an agentskills.io skill is expected to occupy in this repo, and where do new skills get created relative to `.claude/skills/` and any agent definitions in `.claude/agents/`?
  **Target:** `.claude/skills/` and `.claude/agents/`
- Q2: How does an existing skill split content between the top-level `SKILL.md` body and the `references/`, `scripts/`, and `assets/` subdirectories, and how does the body point an agent to the reference files?
  **Target:** an existing multi-file skill under `.claude/skills/` (e.g. a skill that already uses a `references/` directory)

## API Surface

- Q3: What exact frontmatter fields and value formats does a valid `SKILL.md` require in this repo (name, description, and any others), and what are the naming/length constraints on each?
  **Target:** the frontmatter block of existing `SKILL.md` files under `.claude/skills/`
- Q4: How is the Anthropic skill-builder/skill-creator skill invoked, and what inputs and output structure does it produce that the ticket's "built using the Anthropic skill builder skill" criterion depends on?
  **Target:** the module responsible for skill creation (the `skill-creator` skill)
- Q5: How is a skill's `description` field written so the harness auto-triggers it on relevant user requests, and what triggering/anti-triggering conventions do existing skills follow?
  **Target:** the `description` frontmatter across existing skills in `.claude/skills/`

## State Management

- Q6: How are skill artifacts versioned, committed, and reviewed in this repo — do skills live on the default branch directly, or do they flow through the QRSPI PR-gated lifecycle and worktree at `.worktrees/<id>/`?
  **Target:** `.claude/CLAUDE.md` lifecycle section and the worktree convention

## Edge Cases

- Q7: What is the enforced or conventional ceiling on `SKILL.md` size in this repo, and how does it compare to the ticket's "under 500 lines / 5000 tokens" requirement — is there tooling that measures it?
  **Target:** existing `SKILL.md` files and any size/lint checks under `scripts/`
- Q8: How do existing skills that ship runnable helpers handle the `scripts/` directory (language, shebang, executable bit, test siblings), and which conventions would a Terraform skill's optional scripts need to follow?
  **Target:** the `scripts/` directory of existing skills and `scripts/qrspi_*_test.py` conventions
- Q9: Are there existing infrastructure/CLI-oriented skills in this repo whose scope overlaps with Terraform CLI guidance, that could cause triggering collisions or duplicated conventions?
  **Target:** all skill `description` fields under `.claude/skills/`

## Testing

- Q10: What is the established way to verify a skill in this repo given that "the `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder" — what does the skill-creator eval loop actually run, and what counts as a passing skill?
  **Target:** `scripts/run_eval.py`, the `evals/` directory, and the `skill-creator` skill's eval loop
- Q11: What conventions govern reference files in `references/` (file naming, headings, cross-linking from `SKILL.md`) that the ticket's backend-setup/CI-CD/migration reference documents must match?
  **Target:** the `references/` directory of an existing multi-file skill

## Observability

- Q12: How would an agent or operator confirm a newly added skill is registered and discoverable by the harness (appears in the available-skills list) after it is written — what surfaces the skill name and description?
  **Target:** the skill registration/discovery mechanism that lists skills to the agent
