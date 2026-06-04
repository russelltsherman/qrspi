# Questions — Create a new agent skill: using git worktrees

**Ticket:** RUS-30
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk directory structure of an existing skill in this repo (SKILL.md plus any references/, scripts/, assets/ subdirectories), and where do new skills get placed?
  **Target:** `.claude/skills/` and the existing `qrspi-*` skill directories

- Q2: How does the bare-repo bootstrap script's expected inputs and outputs flow — what arguments does a comparable existing bootstrap/setup script in this repo take, and where does it write output?
  **Target:** the `scripts/` directory and existing self-locating scripts (`scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`)

## API Surface

- Q3: What does the Anthropic skill-builder skill require as inputs, and what artifacts does it emit (SKILL.md, references, scripts)?
  **Target:** the skill-creator / skill-builder skill referenced in the available skills list

- Q4: What is the exact required SKILL.md frontmatter schema (required fields, name format, description format/length) per the agentskills.io standard as encoded in existing skills here?
  **Target:** the frontmatter blocks of existing `.claude/skills/*/SKILL.md` files

## State Management

- Q5: What naming convention do existing skills in this repo use for the skill name field and directory name (e.g. lowercase-hyphen), and does the new "using git worktrees" skill name need to match a directory slug?
  **Target:** the `name` frontmatter field and directory names across `.claude/skills/`

- Q6: How does this repo itself already use worktrees (the `.worktrees/<ticket-id>/` convention), and does that established pattern conflict with or differ from the bare-repo pattern the ticket asks the skill to recommend?
  **Target:** the worktree conventions documented in `.claude/CLAUDE.md` and the `using-graphite-cli` skill

## Edge Cases

- Q7: How do existing skills in this repo keep SKILL.md bodies short and offload detail (the under-500-line / under-5000-token constraint) — are large bodies split into `references/` files, and what is the splitting pattern?
  **Target:** existing `.claude/skills/*/SKILL.md` files and any sibling `references/` directories

- Q8: What conventions does this repo already follow for bash scripts (shellcheck cleanliness, shebang, error handling) that the bare-repo bootstrap script in `scripts/` must conform to?
  **Target:** the `writing-bash-scripts` skill and any existing `.sh` files in the repo

- Q9: For the submodule and shared-stash gotchas the skill must warn about, is there any existing repo guidance or script behavior that already touches git submodules or stash that the skill should stay consistent with?
  **Target:** the module responsible for git operations guidance (`using-graphite-cli` skill, `scripts/` git-touching scripts)

## Testing

- Q10: How are skills verified in this repo — does the skill-creator skill provide an eval loop, and what is the status of the `evals/` + `scripts/run_eval.py` harness for validating a new skill?
  **Target:** `scripts/run_eval.py`, the `evals/` directory, and the skill-creator eval tooling

- Q11: What test pattern do existing repo scripts follow (the stdlib-only `_test.py` siblings), and would the bare-repo bootstrap shell script need a comparable test?
  **Target:** the `scripts/qrspi_*_test.py` files

## Observability

- Q12: How do existing skills and scripts in this repo surface errors and progress to the user (logging, echoed status, error-surfacing conventions), so the bare-repo bootstrap script reports its create/configure/first-worktree steps consistently?
  **Target:** existing `scripts/*.py` output/error-handling and the bash-script error-surfacing conventions
