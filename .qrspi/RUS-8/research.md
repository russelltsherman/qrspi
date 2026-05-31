# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: How are existing agent skills in this repository structured on disk — what directories, frontmatter fields, and required files constitute a valid skill?

**Answer:** Skills live under `.claude/skills/<skill-name>/`. Each directory contains a required `SKILL.md` file and may include optional `references/` subdirectories. Only `qrspi-work` ships an additional `references/` directory in this repo. Agent prompt definitions live in a parallel `.claude/agents/<agent-name>.md` file; skills serve as thin wrappers that spawn agents via the `Agent` tool. The README documents this layout.

**Evidence:**

```
.claude/
  skills/              # Skill definitions (one SKILL.md per phase)
    qrspi-ticket/
    qrspi-questions/
    qrspi-research/
    ...
    qrspi-work/        # Autonomous orchestrator
```

— `README.md:78-97`

```
=== .claude/skills/qrspi-design/ ===
SKILL.md
=== .claude/skills/qrspi-work/ ===
references
SKILL.md
```

— directory listing of `.claude/skills/` (ls output)

**Dependencies:** Skills depend on the `.claude/agents/` peer directory for prompt content; skill bodies dispatch to agents.
**Implicit contracts:** A SKILL.md is the entry point. Subdirectories (`references/`) are loaded on demand from within the skill body.

## Q2: What naming convention is used for skill directories, SKILL.md frontmatter `name` fields, and command/argument-hint fields in the existing skills?

**Answer:** Skill directories use kebab-case prefixed with the project namespace (`qrspi-`). The frontmatter `name` field matches the directory name exactly. `command` is `/<name>`. `argument-hint` uses angle-bracketed argument names (e.g., `<ticket-id>`).

**Evidence:**

```
---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-questions/SKILL.md:1-7`

```
---
name: qrspi-implement
...
argument-hint: <ticket-id> <slice-number>
allowed-tools: Agent, Read, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-implement/SKILL.md:1-6`

**Dependencies:** None.
**Implicit contracts:** The slash command surfaced to the user is derived from `command`; `argument-hint` is shown in the CLI prompt UX.

## Q3: Where do `references/`, `scripts/`, and `assets/` subdirectories live for skills that already use them, and what conventions govern their contents?

**Answer:** Only `qrspi-work` uses a `references/` subdirectory in this repo. It contains a single Markdown file (`review-cascade.md`) loaded on demand by the orchestrator. No skills in this repo currently ship `scripts/` or `assets/` subdirectories. Repo-level scripts (eval tooling) live at the top-level `scripts/` directory, not inside skills.

**Evidence:**

```
=== .claude/skills/qrspi-work/ ===
references
SKILL.md
```

```
$ ls .claude/skills/qrspi-work/references/
review-cascade.md
```

— directory listing

```
   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:272` (orchestrator loads reference on demand)

**Dependencies:** Referenced docs are pulled in by skill body text; not loaded automatically by the framework.
**Implicit contracts:** Reference files are project-internal Markdown documents the skill body explicitly tells the agent to read.

## Q4: What frontmatter fields are required vs optional in SKILL.md files in this repo, and how do they correspond to the agentskills.io standard?

**Answer:** Every existing SKILL.md uses exactly four frontmatter fields: `name`, `description`, `command`, `argument-hint`, plus `allowed-tools`. No optional fields like `model:`, `version`, or `author` appear in any existing skill. The repo has no internal documentation file describing the frontmatter schema beyond example skills. The agentskills.io standard referenced by the ticket is external; no local document maps repo fields to that standard.

**Evidence:**

```
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-7`

— `grep "^allowed-tools" .claude/skills/*/SKILL.md` shows the same five-field shape across all 10 skills.

**Dependencies:** None — frontmatter is parsed by the Claude Code runtime, not by repo code.
**Implicit contracts:** All five fields are present in every skill; treat them as required for consistency.

## Q5: Does the repo contain a documented or referenced "Anthropic skill builder skill" the ticket points to, and if so, where does it live and what does it expect as inputs?

**Answer:** NOT FOUND — the repo contains no local "skill-creator" or "skill-builder" skill under `.claude/skills/`. The only reference to "skill-creator" is a single mention in an agent prompt as one possible validation tool. The Anthropic skill builder referenced by the ticket is a global skill (available via the global skills list visible to Claude Code sessions), not a project-local file. Searches: `grep -rn "skill-creator\|skill builder" .claude/ docs/`.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:41`

**Dependencies:** Global skills are not present in the repo tree; they are invoked through the Skill tool when available in the session.
**Implicit contracts:** The skill-creator skill, when invoked, is expected to scaffold and evaluate a new SKILL.md according to Anthropic's authoring guidelines.

## Q6: How are `allowed-tools` listed for skills in this repo, and what is the convention for restricting/exposing Bash, Read, Write, Edit, and MCP tools?

**Answer:** Most QRSPI phase skills declare `allowed-tools: Agent, Bash(pwd:*)` — they only need to spawn a sub-agent and resolve their working directory. Skills that fetch from Linear add the specific MCP read tool (`mcp__linear-russelltsherman__get_issue`). The orchestrator `qrspi-work` and the human-facing `qrspi-ticket` declare broader tool sets because they do orchestration or interactive work directly. Bash glob restrictions (e.g., `Bash(pwd:*)`) limit which commands the skill can shell out to.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md:allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
.claude/skills/qrspi-implement/SKILL.md:allowed-tools: Agent, Read, Bash(pwd:*)
.claude/skills/qrspi-pr/SKILL.md:allowed-tools: Agent, Bash(pwd:*)
.claude/skills/qrspi-plan/SKILL.md:allowed-tools: Agent, Bash(pwd:*)
.claude/skills/qrspi-research/SKILL.md:allowed-tools: Agent, Bash(pwd:*)
.claude/skills/qrspi-questions/SKILL.md:allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
.claude/skills/qrspi-ticket/SKILL.md:allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
.claude/skills/qrspi-work/SKILL.md:allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, mcp__linear-russelltsherman__get_issue_status, mcp__linear-russelltsherman__save_issue, mcp__linear-russelltsherman__list_issue_statuses, mcp__linear-russelltsherman__save_comment
```

— `grep "^allowed-tools" .claude/skills/*/SKILL.md`

**Dependencies:** The runtime enforces `allowed-tools` at invocation time.
**Implicit contracts:** Grant only the tools the skill itself needs; sub-agents declare their own tools in their own frontmatter (e.g., `.claude/agents/qrspi-research.md` declares `Read, Write, Glob, Grep`).

## Q7: Where do skills typically store any persistent state, configuration, or output, and is there a convention for output paths used by skill scripts?

**Answer:** Skills do not store internal state. All persistent artifacts go under `.qrspi/<ticket-id>/` per the QRSPI workflow convention. Templates (referenced for output formats) live under `.qrspi/templates/`. Skills accept absolute paths in their input contracts when delegating to sub-agents, and the orchestrator constructs paths using `<WORKTREE_PATH>/.qrspi/<ticket-id>/<artifact>.md`.

**Evidence:**

```
- `ARTIFACT_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/questions.md`
- `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/questions.md`
```

— `.claude/skills/qrspi-questions/SKILL.md:24-25`

```
.qrspi/
  templates/           # Canonical output formats (single source of truth)
  <ticket-id>/         # Per-ticket artifacts (created at runtime)
```

— `README.md:89-100`

**Dependencies:** Skills produce artifacts that downstream phases read.
**Implicit contracts:** Output paths are always absolute when crossing the sub-agent boundary.

## Q8: How do existing skills handle missing prerequisites (e.g., a CLI tool not installed, authentication not configured) — do they fail fast, print remediation steps, or silently degrade?

**Answer:** NOT FOUND — there are no existing CLI-wrapping skills in this repo (no skills exist for kubectl, gh, git, gt, etc. that wrap an external CLI tool). The closest pattern is `qrspi-work` which uses `gh` and `gt` commands inside its body, and applies a "HARD STOP" rule: if any infrastructure error (`EACCES`, permission denied, command not found, auth failure) occurs, stop immediately, print the exact error verbatim, and exit without retry, workaround, or alternate tooling. This is the canonical failure-handling pattern in the project.

**Evidence:**

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve

This is a non-negotiable constraint. There is NO exception.

When ANY operation fails due to permissions, authentication, configuration, or tooling errors (e.g., `EACCES`, `permission denied`, auth token expired, config file inaccessible, tool not found):

1. **STOP. Do not execute another command.**
2. **Print the exact error verbatim** ...
3. **Exit the skill.**
```

— `.claude/skills/qrspi-work/SKILL.md:709-718`

**Dependencies:** Same rule is duplicated in `.claude/agents/qrspi-research.md:56-58` and likely other agent files — the pattern is enforced at both skill and agent layers.
**Implicit contracts:** Never `chmod`, never `sudo`, never swap to an alternate tool, never retry. Fail loudly so the human can intervene.

## Q9: Is there a length/token budget enforced or recommended for SKILL.md bodies in this repo, and how is overflow handled (e.g., move content into `references/`)?

**Answer:** No repo-level enforcement of a length budget exists. Existing skill bodies are quite short — most QRSPI phase skills are 25-35 lines because they are thin wrappers around sub-agents. The two outliers are `qrspi-ticket` (119 lines) and `qrspi-work` (730 lines), the latter of which keeps a sub-section in `references/`. The ticket itself (RUS-8) declares an external limit: "SKILL.md body under 500 lines / 5000 tokens" — that requirement is sourced from the agentskills.io standard, not the repo. The convention demonstrated by `qrspi-work` is: when a section would be long and consulted only sometimes (e.g., cascade rules), move it into `references/` and reference it inline.

**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
   35 .claude/skills/qrspi-implement/SKILL.md
   26 .claude/skills/qrspi-plan/SKILL.md
   28 .claude/skills/qrspi-pr/SKILL.md
   26 .claude/skills/qrspi-questions/SKILL.md
   26 .claude/skills/qrspi-research/SKILL.md
   25 .claude/skills/qrspi-structure/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  730 .claude/skills/qrspi-work/SKILL.md
   25 .claude/skills/qrspi-worktree/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`

```
   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:272` (example of overflow handled via reference)

**Dependencies:** None.
**Implicit contracts:** Long-form documentation that is only sometimes needed belongs in `references/`; the main body should stay scannable.

## Q10: How are skills expected to behave when an agent invokes them with ambiguous or missing arguments?

**Answer:** Existing skills parse `$ARGUMENTS` deterministically in their first step. `qrspi-questions` (and siblings) extract `<ticket-id>` and immediately call Linear to validate. `qrspi-work` parses the argument, then re-reads the Linear status and dispatches by state. None of the existing skills emit clarifying questions to the user when arguments are missing — they either fetch and fail with a clear error (Linear lookup fails) or stop. There is no explicit "ambiguous arguments" branch; the workflow rule is to fetch, validate, and fail loudly. `qrspi-ticket` is the exception — it is conversational by design.

**Evidence:**

```
1. Parse `$ARGUMENTS` to get `<ticket-id>` (e.g., `RUS-42`).
2. Fetch the ticket: call `mcp__linear-russelltsherman__get_issue` with `id: "<ticket-id>"`. Capture `title` and `description` as `TICKET_CONTENT`.
```

— `.claude/skills/qrspi-questions/SKILL.md:16-17`

```
1. Parse `$ARGUMENTS` to extract `<ticket-id>`.
2. **ALWAYS re-read the Linear ticket status, even if you have it in context from a prior invocation.**
3. Fetch the ticket: call `mcp__linear-russelltsherman__get_issue` with identifier `<ticket-id>`.
   - If the call fails, retry **once**.
   - If the retry fails, this is a **hard stop error** — print the exact error and exit.
```

— `.claude/skills/qrspi-work/SKILL.md:15-19`

**Dependencies:** Linear MCP for ticket fetch; failures propagate as hard stops.
**Implicit contracts:** A missing or invalid argument turns into a hard stop, not a clarifying question.

## Q11: Does this repo have an evals harness for skills (referenced in `.claude/CLAUDE.md` as `evals/` and `scripts/`), and what is the convention for adding new evals for a new skill?

**Answer:** Yes. `evals/suite.json` declares cases; `scripts/run_eval.py`, `scripts/grade.py`, `scripts/report.py`, `scripts/revise.py`, `scripts/diagnose.py`, and `scripts/check_scope.py` form the harness. Fixtures live in `evals/fixtures/` and golden answers in `evals/golden/`. Each case maps to one QRSPI phase (`questions`, `research`, ...) and contains a prompt, context files, and weighted programmatic assertions (e.g., `output_file_exists`, `question_count >= 8`). The convention is to extend `evals/suite.json` with a new case object pointing at a fixture and adding programmatic checks. There is no current eval for a non-QRSPI-phase skill, so the pattern for evaluating a new tool-wrapping skill is not yet established in this repo.

**Evidence:**

```
{
  "id": "case_001",
  "name": "questions_happy_path",
  "phase": "questions",
  ...
  "assertions": [
    { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
    { "type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0 }
  ]
}
```

— `evals/suite.json:15-44`

```
$ ls scripts/
check_scope.py  diagnose.py  grade.py  report.py  revise.py  run_eval.py
```

— directory listing

**Dependencies:** Python (the scripts are Python). `evals/fixtures/` carries the input tickets; `evals/golden/` is currently empty (no golden answers stored yet).
**Implicit contracts:** Each phase has at least one happy-path case in `suite.json`. Programmatic checks are deterministic boolean expressions, not LLM grading.

## Q12: How does the QRSPI workflow expect new skills to be tested before being declared done — manual smoke tests, evals, or both?

**Answer:** The acceptance criteria for skill changes are documented per-ticket. Reading the existing repo, validation passes (linting, running a review tool, invoking skill-creator) are described in agent prompts as the final step of a slice rather than a separate slice. The repo's eval harness covers QRSPI phase agents specifically; there is no established practice for evaluating a non-QRSPI skill (such as a CLI-wrapper skill). Manual invocation is the only proven test path for new utility skills in this repo.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:41`

```
- Eval harness lives in `evals/` and `scripts/`
```

— `.claude/CLAUDE.md:43`

**Dependencies:** skill-creator (global skill) for validating SKILL.md authoring; no project-local validator exists for skill structure.
**Implicit contracts:** New skills should be checked by invoking `skill-creator` per `.claude/agents/qrspi-structure.md`; manual smoke tests of the slash command on a representative input are the de-facto acceptance bar.

## Q13: What logging, progress-printing, or status-update conventions do existing skills follow (e.g., printing "Phase 1 complete" lines, emitting Markdown summaries) that a new argocd skill should mirror?

**Answer:** The orchestrator `qrspi-work` uses explicit `Print:` directives that emit short user-facing status lines ("Questions generated. Moving to Research...", "Created worktree for `<ticket-id>` ..."). Phase wrappers like `qrspi-questions` end by telling the user the artifact path and the next step ("Questions written to .qrspi/<ticket-id>/questions.md. Review, edit, then tell me 'approved' to proceed to Research."). Sub-agents return one-line summaries (e.g., "Wrote 11 questions across 6 categories to <path>"). There is no logging framework — status comes via printed strings.

**Evidence:**

```
Print: "Using existing worktree at `.worktrees/<ticket-id>/`"
Print: "Created worktree for `<ticket-id>` from existing branch."
Print: "Created worktree for `<ticket-id>` with new planning branch."
```

— `.claude/skills/qrspi-work/SKILL.md:44, 70, 81`

```
6. Tell the user: "Questions written to `.qrspi/<ticket-id>/questions.md`. Review, edit, then tell me 'approved' to proceed to Research."
```

— `.claude/skills/qrspi-questions/SKILL.md:26`

```
4. Return a one-line summary (e.g., "Wrote 11 questions across 6 categories to <path>").
```

— `.claude/agents/qrspi-questions.md:23`

**Dependencies:** None — printing is just stdout text.
**Implicit contracts:** Skills emit short, actionable status lines, point at artifacts by path, and conclude with the next action the user should take.

---

## Discovered Patterns

- **Wrapper-and-agent split.** Every QRSPI phase skill is a 25-35 line wrapper. The actual prompt content lives in `.claude/agents/qrspi-<phase>.md`. The skill's only job is to fetch any external inputs (e.g., Linear ticket) and spawn the agent with a labelled input contract using the `Agent` tool. This separation supports per-agent tool restrictions independent of the user-facing skill.
- **Input contract by labelled assignment.** Skill bodies pass inputs to agents as `KEY = value` lines (e.g., `TICKET_ID = RUS-42`, `ARTIFACT_PATH = /abs/path/...`). Agents declare these inputs in their own frontmatter or hard-constraint block.
- **Absolute paths across boundaries.** Whenever an instruction crosses the orchestrator/sub-agent boundary, paths are made absolute and rooted at the worktree. Relative paths are explicitly forbidden in the orchestrator's "Sub-Agent Rules" section.
- **Hard-stop on infrastructure errors.** Both orchestrator (`qrspi-work`) and agents (e.g., `qrspi-research`) carry an identical HARD STOP block forbidding workarounds for permission, auth, config, or tooling errors. This is a project-wide rule, not phase-specific.
- **Templates as single source of truth.** Output formats live in `.qrspi/templates/`. Skills do not embed the format inline; they pass `TEMPLATE_PATH` and expect the agent to read it. Changing a template propagates to every phase.
- **Linear is the state machine.** All phase transitions are gated by Linear status. Skills never write transitions speculatively — they require a Linear status change as proof of human approval.
- **One reference file pattern.** Long-form supplementary docs (e.g., `review-cascade.md`) sit in `<skill>/references/` and are read on demand by the skill body via an explicit instruction. They are not loaded automatically.
- **No global skill examples in the repo.** Every skill in `.claude/skills/` is QRSPI-internal. The repo does not yet contain a "wrap an external CLI" skill, so RUS-8 is establishing a new pattern.

## Inconsistencies

- **`allowed-tools` granularity drift.** Some skills declare `Bash(pwd:*)` (path-restricted), while `qrspi-ticket` and `qrspi-work` declare bare `Bash`. There is no documented rule for which form is required. New skills must choose one without explicit guidance.
- **`.claude/CLAUDE.md` lists `.qrspi/agents/` as the location for agent prompt definitions, but they actually live at `.claude/agents/`.** See `.claude/CLAUDE.md:42` vs the actual directory at `.claude/agents/`. This documentation drift could mislead future skill authors.
- **`evals/golden/` is empty.** The harness expects golden answers but none are committed for current cases. Whether RUS-8 should add a golden answer is undefined.
- **No documented validation step for new skills.** `qrspi-structure.md:41` references "invoking skill-creator" as a validation step but no project-local file documents how to run that, nor what passing/failing looks like. New skills have no acceptance ritual aside from manual review.
