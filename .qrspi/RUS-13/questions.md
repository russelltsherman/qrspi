# Questions — Create a new agent skill using glab cli

**Ticket:** RUS-13
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the standard agentskills.io directory layout and which files are mandatory versus optional, as established by the existing skills in `.claude/skills/` and `.claude/agents/`?
  **Target:** `.claude/skills/` and `.claude/agents/` directories

- Q2: Where should a newly authored skill physically live in this repo, and what is the naming convention for the skill directory and its `SKILL.md`?
  **Target:** the module/directory responsible for housing skill definitions (`.claude/skills/`)

## API Surface

- Q3: What frontmatter fields does a valid `SKILL.md` require (name, description, and any others), and what format constraints exist on the `description` field used for trigger matching?
  **Target:** the skill-creator skill (SKILL.md authoring rules) and existing `SKILL.md` frontmatter examples

- Q4: What subcommand groups and flags must the glab skill body and `references/` enumerate to satisfy coverage (auth, mr, issue, ci/pipeline, release, changelog, repo, api), and how do existing reference-heavy skills split content between `SKILL.md` and `references/`?
  **Target:** the skill-creator skill and any existing skill with a `references/` directory

## State Management

- Q5: How is authentication state and multi-host configuration represented for glab (`~/.config/glab-cli/config.yml`, `GITLAB_TOKEN`, `--hostname`), and is there an existing repo convention for documenting credential/config handling in a skill?
  **Target:** the module responsible for skill authentication/config guidance (references/ in comparable skills)

- Q6: What invocation/eval mechanism does the skill-creator skill provide for measuring trigger accuracy and skill performance, and what state does it persist between eval runs?
  **Target:** the skill-creator skill and `scripts/run_eval.py` / `evals/`

## Edge Cases

- Q7: How should the skill document non-interactive/scripted use — exit codes, JSON output parsing via `jq`, and `glab ci status --wait` for merge-after-green — and do existing skills establish a pattern for agent-specific scripted guidance?
  **Target:** the module responsible for agent-specific scripted patterns (references/ error-handling section)

- Q8: How are self-hosted GitLab instances (`--hostname gitlab.company.com`) versus gitlab.com handled, and what conflicts arise when multiple authenticated hosts exist in `config.yml`?
  **Target:** the module responsible for authentication flows in the skill references

- Q9: What is the documented behavior when an MR already exists on the current branch, when a release tag does not yet exist (`--ref`), or when a pipeline is failing at merge time — and how should the skill encode these judgment-call branches?
  **Target:** the module responsible for MR and CI workflow patterns in the skill body

## Testing

- Q10: What constitutes a passing verification for a skill in this repo (the SKILL.md body under 500 lines / 5000 tokens, valid frontmatter, eval harness status), and which checks are real versus placeholder?
  **Target:** `scripts/run_eval.py`, `evals/`, and the project skill-authoring conventions in `.claude/CLAUDE.md`

- Q11: How can token/line count of `SKILL.md` be measured against the 500-line / 5000-token acceptance threshold using existing repo tooling or scripts?
  **Target:** the module/scripts responsible for skill size or token measurement

## Observability

- Q12: How do existing skills surface command failures and errors to the agent (exit-code handling, error-message conventions), and what does the skill-creator skill recommend documenting for observable failure modes in a CLI skill?
  **Target:** the skill-creator skill and references/ error-handling sections of comparable skills
