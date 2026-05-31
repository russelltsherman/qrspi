# Questions — Create a new agent skill: using-codex-cli

**Ticket:** RUS-21
**Generated:** 2026-05-31T17:01:05Z
**Status:** draft

## Data Flow

- Q1: How is an existing skill's directory laid out in this repo — what files and subdirectories (SKILL.md, references/, scripts/, assets/) are present, and where do they live relative to the repo root?
  **Target:** `.claude/skills/` directory tree, especially a representative skill like `.claude/skills/qrspi-research/`
- Q2: How does content flow from a SKILL.md body into its `references/` files — what is the convention for when material is inlined in SKILL.md versus split into a reference file?
  **Target:** an existing skill that uses a `references/` directory, if any; otherwise the qrspi agent definitions in `.claude/agents/`

## API Surface

- Q3: What exact frontmatter fields and value formats appear in existing SKILL.md files (name, description, command, argument-hint, allowed-tools, model, and any others)?
  **Target:** frontmatter blocks of `.claude/skills/qrspi-work/SKILL.md` and `.claude/skills/qrspi-research/SKILL.md`
- Q4: Is there a documented or de-facto agentskills.io standard reference already captured in this repo (a skill-creator skill, a README, or eval harness) that defines the required SKILL.md structure and frontmatter?
  **Target:** repo root README, `evals/`, `scripts/`, and any skill-creator or skill-authoring assets in `.claude/`

## State Management

- Q5: Where should the new `using-codex-cli` skill physically live, and what naming convention do sibling skills follow for their directory name versus their frontmatter `name` field?
  **Target:** `.claude/skills/` directory listing and the `name:` field of each sibling SKILL.md
- Q6: How is a skill's `description` field written so the harness can auto-trigger it — what length, phrasing, and trigger-keyword patterns do existing descriptions use?
  **Target:** the `description:` field across `.claude/skills/*/SKILL.md`

## Edge Cases

- Q7: What enforces or measures the acceptance criteria "SKILL.md body under 500 lines / 5000 tokens" — is there a linter, eval, or script in the repo that checks skill size or frontmatter validity?
  **Target:** `evals/`, `scripts/`, and any CI or pre-commit configuration in the repo
- Q8: How do existing skills handle platform-specific or conditional guidance (e.g., macOS vs. Linux behavior) without bloating the SKILL.md body — is branching pushed into reference files?
  **Target:** the body and `references/` of any existing skill that documents environment-specific behavior
- Q9: The ticket says to build the skill "using the Anthropic skill builder skill" — is that skill-creator skill present and invocable in this environment, and what artifacts does it expect to produce or consume?
  **Target:** `.claude/skills/` for a skill-creator/skill-builder skill and its SKILL.md instructions

## Testing

- Q10: How are skills validated or tested in this repo — is there an eval harness in `evals/` that runs against skills, and what input/output contract does it expect?
  **Target:** `evals/` directory and `scripts/` that drive evaluation
- Q11: What test or verification convention does the project's contributor guidance require for a new skill (e.g., a SKILL.md presence check, frontmatter schema check, or trigger-accuracy eval)?
  **Target:** repo root README, CONTRIBUTING, or `.claude/` documentation; the skill-creator eval loop if present

## Observability

- Q12: How would a reviewer or operator confirm the new skill is discoverable and correctly registered — is there a manifest, index, or listing that skills must be added to, or are they auto-discovered from `.claude/skills/`?
  **Target:** `.claude/` configuration, any skills index/manifest file, and `.claude/settings*.json`
