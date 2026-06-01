# Questions — Create a new agent skill for using the Claude Code CLI

**Ticket:** RUS-9
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the skill-creator skill consume an initial description and emit the SKILL.md plus references/scripts/assets layout, and where in its flow is the agentskills.io directory structure enforced?
  **Target:** the skill-creator skill (`.claude/skills/` or the skill-creator SKILL.md and its eval loop)
- Q2: How do existing skills in this repo split content between the SKILL.md body and the `references/` directory, and what is the convention for cross-linking from the body into reference files?
  **Target:** existing SKILL.md files under `.claude/skills/` (e.g., qrspi-* and writing-bash-scripts)

## API Surface

- Q3: What YAML frontmatter fields and value formats are used by existing skills in this repo (name, description, and any others), and which are required versus optional?
  **Target:** frontmatter blocks of existing SKILL.md files under `.claude/skills/`
- Q4: What is the canonical directory location and naming convention for a new skill in this repo — `.claude/skills/<name>/SKILL.md` — and is there a separate agent definition wrapper expected under `.claude/agents/`?
  **Target:** `.claude/skills/` and `.claude/agents/` directory layout

## State Management

- Q5: How does the skill-creator eval loop persist intermediate state (draft skill, eval results, scores) between iterations, and where are those artifacts written?
  **Target:** the skill-creator skill and any `evals/` or `scripts/` it references
- Q6: How are session IDs and conversation state captured and reused across multi-step invocations elsewhere in this repo (the documented `session_id` capture pattern), so the skill's session-management guidance matches existing usage?
  **Target:** the module/workflow responsible for orchestration (`.claude/workflows/qrspi-batch.js`)

## Edge Cases

- Q7: How are the SKILL.md size limits (under 500 lines / 5000 tokens) measured and verified in this repo, and is there an existing check or eval that fails when a SKILL.md exceeds them?
  **Target:** the skill-creator eval harness and any size-checking script under `evals/` or `scripts/`
- Q8: What does the skill-creator do when a generated skill fails one or more acceptance checks (e.g., missing required reference files or invalid frontmatter) — does it retry, halt, or report?
  **Target:** the skill-creator skill's eval/iteration logic
- Q9: How do existing skills document experimental or version-gated features (analogous to the experimental agent-teams behavior), and where is that "experimental status" labeling placed?
  **Target:** existing SKILL.md and `references/` files under `.claude/skills/`

## Testing

- Q10: What test or eval mechanism verifies a skill's frontmatter validity and directory structure conformance, and how is it invoked?
  **Target:** the eval harness in `evals/` and `scripts/`
- Q11: How does the skill-creator measure skill description triggering accuracy, and what command or harness runs that benchmark?
  **Target:** the skill-creator skill and its eval/benchmark scripts

## Observability

- Q12: How are skill-creator eval runs and their pass/fail results logged or surfaced (console output, written report file, scores), so the new skill's build can be confirmed against the acceptance criteria?
  **Target:** the skill-creator eval loop output and any report destination under `evals/` or `scripts/`
