# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: What directory layout does an existing skill use for `SKILL.md` plus supporting `references/`, `scripts/`, and `assets/`, and where in the repo do skill source files live versus where they are installed/discovered?

**Answer:** Project skills live under `.claude/skills/<skill-name>/SKILL.md`. There are 10 skills today, all under `.claude/skills/`. Only one skill ships a supporting directory: `qrspi-work` has a `references/` subdirectory. No skill in the repo uses `scripts/` or `assets/` subdirectories. The minimal/common layout is a single `SKILL.md` per skill directory.

**Evidence:**

```
.claude/skills/qrspi-design        .claude/skills/qrspi-questions
.claude/skills/qrspi-implement     .claude/skills/qrspi-research
.claude/skills/qrspi-plan          .claude/skills/qrspi-structure
.claude/skills/qrspi-pr            .claude/skills/qrspi-ticket
.claude/skills/qrspi-work          .claude/skills/qrspi-worktree
.claude/skills/qrspi-work/references/review-cascade.md
```

— `.claude/skills/` (directory listing) and `.claude/skills/qrspi-work/references/review-cascade.md`

**Dependencies:** Skills are discovered by Claude Code from `.claude/skills/`. The repo has no install/build step — skill source IS the installed form.
**Implicit contracts:** Skill directory name matches the `name` frontmatter key and the `/command` (e.g. `qrspi-questions` → `name: qrspi-questions`, `command: /qrspi-questions`). A `references/` subdir is the established place for overflow content (only `qrspi-work` uses it, holding `review-cascade.md`).

## Q2: How does the skill builder skill consume input and emit a finished skill — what files does it create, and where does it write them?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. There is no `skill-creator`/skill-builder skill inside `.claude/skills/` of this repo. It is referenced only as an external dependency: `.claude/agents/qrspi-structure.md` is the sole file mentioning skill creation tooling. The Anthropic "skill builder" (skill-creator) is a global/plugin skill that lives outside `REPO_ROOT` and cannot be read here. Its input/output contract must be treated as an external unknown to be exercised at implementation time.

**Evidence:**

```
grep -rl -i "skill-creator|skill builder|skill_creator" . --include='*.md'
→ .claude/agents/qrspi-structure.md   (the only match in-repo, excluding our artifacts)
```

— search across repo

**Dependencies:** Implementation depends on an externally-provided skill-creator skill not present in the repo.
**Implicit contracts:** None enforceable from repo facts; the produced skill must still conform to the in-repo `.claude/skills/<name>/SKILL.md` layout regardless of which tool generates it.

## Q3: What fields are required and optional in `SKILL.md` frontmatter, and what are the formatting/length constraints on the `description` field?

**Answer:** Existing SKILL.md frontmatter uses these keys: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. The orchestrator (`qrspi-work`) additionally omits `argument-hint` in some but includes `allowed-tools`. The `model: opus` key appears in agent definitions (`.claude/agents/*.md`) but NOT in skill frontmatter. `description` is a single-line plain string; the longest is the multi-sentence trigger description on `qrspi-work`. No explicit machine-enforced length limit on `description` exists in repo tooling — but `grade.py` has a `line_count(filename, max_lines)` check used to bound whole-file size (see Q7).

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

**Dependencies:** Claude Code's skill loader parses this frontmatter.
**Implicit contracts:** `allowed-tools` scopes which tools the skill may call (e.g. `Bash(pwd:*)` restricts Bash to `pwd`). `name`, `description`, `command` are present on every skill.

## Q4: How is a skill invoked — what naming convention maps a skill to its `/command` trigger, and how is the skill name expected to read for a PRD-writing skill?

**Answer:** Each skill sets `command: /<name>` matching its directory name. All project skills are namespaced `qrspi-*`. Skills are auto-invoked by the `description` trigger or explicitly via the `/command`. A PRD-writing skill would follow the same pattern: directory `.claude/skills/<name>/`, `name: <name>`, `command: /<name>`, with a `description` that names PRD/Product Requirements Document triggers.

**Evidence:**

```
name: qrspi-ticket
command: /qrspi-ticket
```

— `.claude/skills/qrspi-ticket/SKILL.md:2,4`

**Dependencies:** Skill loader maps `command` → invocation.
**Implicit contracts:** Directory name == `name` == command (minus leading `/`). The repo's skills are all `qrspi-` prefixed, but that prefix is a project-namespace convention, not a loader requirement.

## Q5: What is the established convention for splitting content between the `SKILL.md` body and `references/` files, and what triggers content being moved into a reference file?

**Answer:** Most skills are thin — 25-35 lines — and keep everything inline. Two skills are large: `qrspi-ticket` (119 lines, a full guided-conversation procedure inline) and `qrspi-work` (730 lines, the orchestrator). `qrspi-work` is the only skill that externalizes content: it moves the cascade decision table into `references/review-cascade.md` and reads it on demand ("Read `references/review-cascade.md` for cascade logic"). The trigger for externalizing appears to be: detailed decision logic / lookup tables that are only needed in a specific branch, not on every invocation.

**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  730 .claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md  (cascade table, loaded on demand)
```

— `wc -l .claude/skills/*/SKILL.md`; `.claude/skills/qrspi-work/SKILL.md:272` ("Read `references/review-cascade.md`")

**Dependencies:** Body links to reference by relative path.
**Implicit contracts:** Reference files are loaded lazily ("Read X for Y"), keeping the always-loaded SKILL.md body small.

## Q6: How are templates and example output stored and referenced by existing skills (inline fenced blocks vs separate files)?

**Answer:** Two distinct mechanisms. (1) Skill-internal inline templates: `qrspi-ticket` embeds the draft template as a fenced code block directly in SKILL.md (`.claude/skills/qrspi-ticket/SKILL.md:71-98`) AND points to a separate canonical template file (`.qrspi/templates/ticket.md`). (2) Workflow artifact templates live in `.qrspi/templates/` (design.md, plan.md, questions.md, research.md, structure.md, ticket.md, worktree.md, pr-summary.md, impl-log.md, revision-log.md) and are referenced by absolute/relative path, never duplicated into the skill body. For a PRD skill, the established pattern would be to ship the PRD template either inline in SKILL.md (small) or as a `references/` file (large), mirroring qrspi-ticket and qrspi-work respectively.

**Evidence:**

```
Read the ticket template at `.qrspi/templates/ticket.md` to understand the target format.
...
Then present the full draft inline, following the structure from `.qrspi/templates/ticket.md`:
```​```
---
DRAFT — New Ticket
---
## Title
...
```​```
```

— `.claude/skills/qrspi-ticket/SKILL.md:28, 69-98`

**Dependencies:** `.qrspi/templates/` holds workflow artifact templates; skills reference them by path.
**Implicit contracts:** Templates are "reference only — not written locally" per project CLAUDE.md. A self-contained skill (like a PRD skill that is NOT a QRSPI phase) should bundle its template under its own skill directory (`references/`), not under `.qrspi/templates/`, since the latter is QRSPI-pipeline-specific.

## Q7: What is the documented hard ceiling on `SKILL.md` size, and how is it enforced or verified for existing skills?

**Answer:** No skill-loader-level hard ceiling is documented in-repo. However the eval harness provides a `line_count(filename, max_lines)` programmatic check in `grade.py:35` that can assert a generated file stays under a line budget. The grading system supports both programmatic checks (exact, scriptable) and LLM-judge checks. So a "SKILL.md under N lines" requirement is verified by adding a `line_count('SKILL.md', N)` assertion to an eval case. Today no skill SKILL.md exceeds 730 lines, and only `qrspi-work` is large; the thin wrappers are 25-35 lines.

**Evidence:**

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
```

— `scripts/grade.py:35`

**Dependencies:** `grade.py` is invoked by the eval pipeline (`run_eval.py` → `grade.py` → `report.py`).
**Implicit contracts:** File-size limits are enforced as eval assertions, not by the loader. To gate a SKILL.md size limit, add a `line_count` assertion to the suite.

## Q8: How do existing skills encode a "must ask clarifying questions when evidence is missing" gate?

**Answer:** `qrspi-ticket` is the canonical example of a conditional-questioning gate. It runs a guided conversation: restate understanding, ask the most important unanswered question first, never more than 2 at once, and "Continue until all required fields have enough information." It also self-reviews before drafting and explicitly refuses to embed solution content. This is the in-repo pattern a PRD skill would copy to enforce "ask clarifying questions when problem-statement evidence is missing."

**Evidence:**

```
### Conversation rules
1. Begin by restating your understanding of the user's description in 1–2 sentences.
2. Ask the most important unanswered question first. Never ask more than 2 questions at once.
...
6. Continue until all required fields have enough information to write the ticket.
```

— `.claude/skills/qrspi-ticket/SKILL.md:42-48`

**Dependencies:** None — it is a self-contained conversational procedure.
**Implicit contracts:** Gating is expressed as imperative prose rules in the SKILL.md body, plus a self-review checkpoint ("Could someone who doesn't know the solution understand what success looks like?").

## Q9: How do existing skills express "opinionated defaults with flexible overrides" — a default mode plus an expanded/alternate mode?

**Answer:** The clearest in-repo example of branching modes is `qrspi-work`, a state machine that dispatches to different action sections based on Linear status (a State Dispatch table mapping status → action section). It encodes a default path and alternate paths within one SKILL.md using a table plus per-state sections. `qrspi-questions` agent encodes minimum/expansion bounds (8-15 questions, at least 2 Edge Case + 1 Observability). The pattern for "lean default that scales up" would be: a default template/section set, plus an explicit "expand when X" rule block — analogous to qrspi-work's dispatch table.

**Evidence:**

```
| Linear Status | Action |
|---|---|
| `Backlog` or `Selected` | → Run Planning |
| `Plan Review` | → Address Planning Feedback |
...
```

— `.claude/skills/qrspi-work/SKILL.md` (State Dispatch table, ~line 95)

**Dependencies:** Dispatch reads external state (Linear status) to pick a mode.
**Implicit contracts:** A single SKILL.md can hold multiple modes; the default is selected first and alternates are reached by explicit conditions.

## Q10: What eval/test harness exists for skills, what format do eval cases take, and how is a skill's behavior scored?

**Answer:** The harness lives in `evals/` (suite + fixtures + golden) and `scripts/`. `evals/suite.json` defines cases: each case has `id`, `name`, `phase`, `prompt`, `context.files` (fixtures), and an `assertions` array. Assertions are weighted and have a `type` — `programmatic` (a `check` string like `question_count('questions.md') >= 8`), `llm` judge, or `script`. `scripts/run_eval.py` executes each case for `trials_per_case` (default 3) trials in isolated environments capturing transcripts/outputs/tokens. `scripts/grade.py` runs the checks and scores. `scripts/report.py` reports. Defaults: 3 trials, 120000ms timeout. The suite splits train/test 0.65/0.35 with seed 42.

**Evidence:**

```json
"assertions": [
  { "type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0 },
  { "type": "programmatic", "check": "no_solution_language('questions.md')", "weight": 2.0 },
  ...
]
```

— `evals/suite.json:18-...` (case_001 `questions_happy_path`)

```python
def question_count(filename: str, result: dict) -> int:
def no_solution_language(filename: str, result: dict) -> tuple[bool, str]:
def all_questions_have_target(filename: str, result: dict) -> tuple[bool, str]:
```

— `scripts/grade.py:43,50,66`

**Dependencies:** `run_eval.py` → produces results → `grade.py` scores against `suite.json` → `report.py` summarizes. Fixtures in `evals/fixtures/*.md` provide ticket inputs.
**Implicit contracts:** A new skill is tested by adding case(s) to `evals/suite.json` referencing fixture inputs and asserting on output files (e.g. `output_file_exists('prd.md')`, `has_section('prd.md', 'Non-Goals')`, `line_count('SKILL.md', 500)`).

## Q11: How is the skill builder skill's own eval loop invoked, and is running it a required gate before a skill is complete?

**Answer:** Partially NOT FOUND for the external skill-builder's own loop (that tooling is outside REPO_ROOT, see Q2). In-repo, the eval loop is invoked by `run_loop.sh` at repo root plus `scripts/run_eval.py`. `scripts/revise.py` and `scripts/diagnose.py` exist, suggesting a generate→eval→diagnose→revise loop. `docs/eval-system.md` documents the system. Whether passing evals is a hard merge gate is not encoded in any CI config found in-repo (no CI workflow file was located); it appears to be a developer-run loop (`run_loop.sh`) rather than an automated gate.

**Evidence:**

```
run_loop.sh
scripts/run_eval.py  scripts/grade.py  scripts/report.py
scripts/revise.py    scripts/diagnose.py
docs/eval-system.md
```

— repo root listing; `scripts/` listing

**Dependencies:** `run_loop.sh` orchestrates the Python scripts.
**Implicit contracts:** The eval loop is the in-repo quality gate for prompts/skills; see `docs/eval-system.md` for the documented workflow.

## Q12: How does the repo verify a newly authored skill is well-formed and discoverable (lint, frontmatter validation, registration)?

**Answer:** No dedicated frontmatter-validation or skill-registration script was found (no `validate`, `lint`, or `register` script in `scripts/`; scripts are `check_scope.py`, `diagnose.py`, `grade.py`, `report.py`, `revise.py`, `run_eval.py`). `scripts/check_scope.py` enforces the project-scope firewall (paths must stay inside the repo), not frontmatter shape. Discoverability is implicit: placing `<name>/SKILL.md` under `.claude/skills/` makes it discoverable to Claude Code. Correctness signals are therefore: (1) valid YAML frontmatter with `name`/`description`/`command`, (2) the eval harness picking it up via an added suite case, (3) the skill triggering on its `/command` and description.

**Evidence:**

```
scripts/check_scope.py   (path-scope firewall, not frontmatter validation)
scripts/grade.py         (output-content assertions)
```

— `scripts/` listing; `scripts/check_scope.py`

**Dependencies:** Claude Code skill loader provides discovery; eval harness provides behavioral verification.
**Implicit contracts:** "Well-formed" = parseable frontmatter + correct directory placement. There is no separate lint gate; verification is behavioral via evals.

---

## Discovered Patterns

- **Thin-wrapper vs. self-contained skills.** Eight of ten skills are thin wrappers (25-35 lines) that fetch a ticket and spawn a `.claude/agents/qrspi-<phase>.md` agent via the `Agent` tool; the heavy prompt logic lives in the agent definition, not the skill. Two skills (`qrspi-ticket`, `qrspi-work`) are self-contained and hold their full procedure inline. A PRD-writing skill that is NOT a QRSPI pipeline phase would most naturally be **self-contained** (like `qrspi-ticket`): all guidance in SKILL.md (+ optional `references/`), no companion agent required.
- **Two template homes.** `.qrspi/templates/` holds QRSPI-pipeline artifact templates (reference-only, not written locally per CLAUDE.md). Skill-specific templates are either inline fenced blocks (`qrspi-ticket`) or — for overflow — a `references/` file under the skill's own directory (`qrspi-work/references/`). A PRD template belongs with the skill, not in `.qrspi/templates/`.
- **Problem-before-solution is already a house value.** `qrspi-ticket` aggressively strips solution content and enforces problem-space framing, and the whole QRSPI pipeline separates problem (Ticket/Questions) from solution (Design/Structure/Plan). A PRD skill enforcing "problem statement must precede solution" aligns directly with existing conventions.
- **Verification is eval-driven, not lint-driven.** Quality gating happens through weighted assertions in `evals/suite.json` graded by `scripts/grade.py`, run via `run_loop.sh`/`run_eval.py`. `grade.py` already has reusable checks: `output_file_exists`, `has_section`, `line_count`, `no_solution_language`. New content requirements are enforced by adding assertions, sometimes new check functions.
- **Frontmatter keys observed:** `name`, `description`, `command`, `argument-hint`, `allowed-tools` (skills); `name`, `description`, `model`, `claude.tools` (agents under `.claude/agents/`).

## Inconsistencies

- **`scripts/` directory absent inside skills despite agentskills layout allowing it.** No skill uses `scripts/` or `assets/`; only `references/` (once). The repo demonstrates the layout but not its full breadth — there is no in-repo precedent for a skill shipping executable `scripts/`.
- **The "skill builder" dependency is unresolvable from repo facts.** The ticket-implied tool (skill-creator) is referenced once in `.claude/agents/qrspi-structure.md` but is not present in `.claude/skills/`. Its file-output contract (Q2) and its own eval loop (Q11) cannot be confirmed from within the project; they are external dependencies that must be exercised at implementation time.
- **No machine-enforced SKILL.md size limit.** A line/token ceiling can only be checked via an eval `line_count` assertion; nothing in the loader prevents an over-long SKILL.md. So any size requirement must be wired into `evals/suite.json` explicitly.
- **No CI gate located.** The eval loop exists as developer tooling (`run_loop.sh`) but no continuous-integration config enforcing it was found in-repo, so "evals pass" is a manual gate.
