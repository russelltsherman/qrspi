# Questions — Create a new agent skill called using argocd cli

**Ticket:** RUS-8
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How are existing agent skills in this repository structured on disk — what directories, frontmatter fields, and required files constitute a valid skill?
  **Target:** the directory or module responsible for agent skill definitions (e.g., `.claude/skills/`, `.claude/agents/`, or a comparable location), plus any existing `SKILL.md` files

- Q2: What naming convention is used for skill directories, SKILL.md frontmatter `name` fields, and command/argument-hint fields in the existing skills?
  **Target:** existing skills under `.claude/skills/` (e.g., qrspi-work, qrspi-questions, deep-research) — examine their frontmatter

- Q3: Where do `references/`, `scripts/`, and `assets/` subdirectories live for skills that already use them, and what conventions govern their contents?
  **Target:** any existing skill in the repo that uses references/ or scripts/ subdirectories (search `.claude/skills/*/references/`)

## API Surface

- Q4: What frontmatter fields are required vs optional in SKILL.md files in this repo, and how do they correspond to the agentskills.io standard?
  **Target:** existing SKILL.md frontmatter examples plus any project documentation describing the skill format (e.g., `.claude/CLAUDE.md`, `README.md`, or `docs/`)

- Q5: Does the repo contain a documented or referenced "Anthropic skill builder skill" the ticket points to, and if so, where does it live and what does it expect as inputs?
  **Target:** the module responsible for skill creation (e.g., `.claude/skills/skill-creator/` if present) and any related documentation

- Q6: How are `allowed-tools` listed for skills in this repo, and what is the convention for restricting/exposing Bash, Read, Write, Edit, and MCP tools?
  **Target:** the `allowed-tools` field across existing SKILL.md files

## State Management

- Q7: Where do skills typically store any persistent state, configuration, or output, and is there a convention for output paths used by skill scripts?
  **Target:** existing skills that ship `scripts/` (search `.claude/skills/*/scripts/`) plus repo-level conventions documented in `.claude/CLAUDE.md` or `~/.agents/AGENTS.md`

## Edge Cases

- Q8: How do existing skills handle missing prerequisites (e.g., a CLI tool not installed, authentication not configured) — do they fail fast, print remediation steps, or silently degrade?
  **Target:** any existing skill whose subject is a CLI tool (search SKILL.md files referencing `kubectl`, `gh`, `git`, `gt`, or similar) for prior-art patterns

- Q9: Is there a length/token budget enforced or recommended for SKILL.md bodies in this repo, and how is overflow handled (e.g., move content into `references/`)?
  **Target:** existing skill files plus any guidance in `.claude/CLAUDE.md`, `~/.agents/AGENTS.md`, or skill-creator documentation

- Q10: How are skills expected to behave when an agent invokes them with ambiguous or missing arguments?
  **Target:** existing skills that take arguments (e.g., `qrspi-work`, `deep-research`) — examine their argument-hint and input-handling patterns

## Testing

- Q11: Does this repo have an evals harness for skills (referenced in `.claude/CLAUDE.md` as `evals/` and `scripts/`), and what is the convention for adding new evals for a new skill?
  **Target:** `evals/` directory and `scripts/` directory at repo root

- Q12: How does the QRSPI workflow expect new skills to be tested before being declared done — manual smoke tests, evals, or both?
  **Target:** project documentation (e.g., `.claude/CLAUDE.md`, `README.md`) and any existing skill that documents its own test plan

## Observability

- Q13: What logging, progress-printing, or status-update conventions do existing skills follow (e.g., printing "Phase 1 complete" lines, emitting Markdown summaries) that a new argocd skill should mirror?
  **Target:** existing skill bodies — look for explicit `Print:` directives or stdout conventions (e.g., qrspi-work uses "Print:" markers extensively)
