# Questions — Create a new agent skill for the argocd CLI

**Ticket:** RUS-8
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an existing SKILL.md in this repo reference and load its supporting material at runtime (e.g., relative paths into `references/`, `scripts/`, `assets/`), and what path conventions do those references use?
  **Target:** the `.claude/skills/` directory and any existing SKILL.md files plus their `references/` siblings

- Q2: How does the skill-creator skill expect inputs and where does it emit the generated skill directory (target path, naming, frontmatter scaffolding)?
  **Target:** the skill-creator skill definition (the module responsible for generating new skills)

## API Surface

- Q3: What is the exact required frontmatter schema for a SKILL.md in this repo (required keys such as name/description, allowed values, naming format), and is there a validator that enforces it?
  **Target:** existing SKILL.md frontmatter across `.claude/skills/` and any skill-validation script

- Q4: What invocation surface do skills expose here — slash-command wrappers vs. agent definitions — and which file(s) must exist for the new skill to be discoverable/triggerable?
  **Target:** `.claude/agents/` and `.claude/skills/` wrapper files

## State Management

- Q5: Where do skill artifacts physically live relative to the worktree/repo root, and how is the new skill directory expected to be registered or auto-discovered (no manifest vs. an index file)?
  **Target:** the module/convention responsible for skill discovery and registration in this repo

## Edge Cases

- Q6: Is there an enforced line/token budget mechanism for SKILL.md bodies (the acceptance criteria require under 500 lines / 5000 tokens), and where would such a limit be checked or measured?
  **Target:** any skill linting/size-check script or documented convention for SKILL.md length

- Q7: How do existing skills in this repo handle the split between the SKILL.md body and `references/` content — what determines what belongs inline vs. in a reference file, and are there examples of multi-reference skills to model the argocd reference set after?
  **Target:** existing multi-file skills under `.claude/skills/` with `references/` directories

- Q8: How are `scripts/` and `assets/` subdirectories within a skill expected to be structured, named, and made executable (if at all), for cases where the argocd skill ships helper scripts?
  **Target:** existing skills that include `scripts/` or `assets/` subdirectories

## Testing

- Q9: How are skills verified in this repo — is there an eval harness, unit-test pattern, or manual checklist used to confirm a SKILL.md is valid and triggers correctly?
  **Target:** `evals/`, `scripts/run_eval.py`, and the skill-creator eval loop

- Q10: What naming, formatting, and Markdown conventions do existing SKILL.md files follow (heading structure, section ordering, code-fence style) that the new argocd skill must match?
  **Target:** existing SKILL.md files under `.claude/skills/`

## Observability

- Q11: How is skill triggering/selection surfaced or logged when an agent chooses a skill (what signal indicates the description field is correctly scoped), and where is that triggering behavior measured?
  **Target:** the skill-creator description-optimization/triggering-accuracy tooling
