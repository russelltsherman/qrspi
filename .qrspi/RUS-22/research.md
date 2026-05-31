# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> **Scope note:** This repository (`qrspi`) is the QRSPI workflow itself. Several
> questions reference skills named `skill-creator`, `using-graphite-cli`, and
> `workflow-creator`. Those are **global** skills installed under `~/.claude/`,
> which is **outside `REPO_ROOT`** and therefore off-limits to this phase. Where a
> question targets such a skill, the answer documents the closest in-repo evidence
> (e.g., the in-repo `qrspi-*` skills and the `graphite-evals.json` eval) and marks
> the external resource NOT FOUND — out of project scope.

## Q1: What directory structure and file layout do existing skills in this repository follow, and where would a new skill's `SKILL.md`, `references/`, `scripts/`, and `assets/` be placed?

**Answer:** Skills live under `.claude/skills/<skill-name>/SKILL.md`. There are 10
skills, all `qrspi-*` workflow phases. Each skill directory contains a single
`SKILL.md`. The **only** skill that uses a subdirectory is `qrspi-work`, which has a
`references/` folder holding one file (`review-cascade.md`). **No skill in the repo
uses `scripts/` or `assets/` subdirectories** — those conventions are not exercised
here. Repo-level `scripts/` (eval harness) is unrelated to skills. By convention a new
skill would be placed at `.claude/skills/<name>/SKILL.md`, with optional
`references/` alongside it (the only demonstrated pattern).

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
...
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   # only subdir in any skill
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing); `find .claude/skills -mindepth 2 -type d` returns only `.claude/skills/qrspi-work/references`
**Dependencies:** Skills are loaded by the Claude Code harness (external to repo). Phase skills delegate to agent prompts in `.claude/agents/`.
**Implicit contracts:** One `SKILL.md` per skill directory; directory name matches the `name:` frontmatter field; `references/` (when present) holds long-form material linked from the body. `scripts/`/`assets/` are unused — no in-repo precedent.

## Q2: How does the skill-builder skill referenced in the ticket consume an input description and produce a `SKILL.md` plus supporting files?

**Answer:** NOT FOUND — out of project scope. No `skill-creator`/`skill-builder`
skill exists inside `REPO_ROOT`. Searched `.claude/skills/` (only `qrspi-*` skills
present) and grepped the repo for "skill-creator"/"skill-builder" (no matches in
source; the name appears only in the global skill catalog injected into context,
which lives under `~/.claude/`, outside scope). The closest **in-repo** analogue of
the wrapper→agent→artifact pattern: each `qrspi-*` SKILL.md is a thin wrapper that
parses `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, and spawns a `subagent_type`
agent which writes the artifact.

**Evidence:**

```
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-plan`
```

— `.claude/skills/qrspi-plan/SKILL.md:14-21`
**Dependencies:** Wrapper (SKILL.md) → `Agent` tool → agent prompt (`.claude/agents/<name>.md`) → writes artifact via `Write`.
**Implicit contracts:** Wrappers carry no logic ("All prompt content lives in `.claude/agents/...`"); the agent owns generation. A skill-creation skill is not modeled in-repo.

## Q3: What fields are required in `SKILL.md` YAML frontmatter (name, description, and any others) for a skill to be valid and discoverable in this repository?

**Answer:** Every in-repo `SKILL.md` uses YAML frontmatter with these fields:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`. The
`.claude/agents/*.md` files (a different artifact type) use a different frontmatter
shape: `name`, `description`, `model`, and a nested `claude:\n  tools:` block. No
JSON schema or loader enforcing required fields exists in-repo (skill loading is done
by the external Claude Code harness), so "required" is inferred from the consistent
convention across all 10 skills.

**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`
Agent frontmatter (different shape):

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts ...
model: opus
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/agents/qrspi-research.md:1-7`
**Dependencies:** Frontmatter consumed by external harness skill registry; `allowed-tools` restricts callable tools (e.g., `Bash(pwd:*)` scopes Bash to `pwd`).
**Implicit contracts:** `name` must equal the directory name. `command` is the slash invocation (`/qrspi-*`). `argument-hint` documents positional args. `allowed-tools` is a comma-separated allowlist with optional argument scoping `Tool(pattern:*)`.

## Q4: What naming, description, and triggering conventions do existing skill descriptions use so the new Gemini CLI skill is routed correctly?

**Answer:** Descriptions follow a "what + when" pattern: a capability statement
followed by an explicit trigger phrase ("Use when…", "Use after…", or "Trigger on
any variant of…"). Two registration patterns are visible: short single-sentence
descriptions (most phase skills) and a long quoted multi-trigger description
(`qrspi-work`) that enumerates phrasings ("'work on <ticket-id>', 'continue
<ticket-id>', 'pick up <ticket-id>'"). Names are lowercase, hyphenated, prefixed by
domain (`qrspi-`). The `using-graphite-cli`/`workflow-creator` skills cited in the
question are global (outside scope); their descriptions are not readable here.

**Evidence:**

```
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-questions/SKILL.md:2-3`

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`
**Dependencies:** Description text is the routing signal for the harness's skill selector.
**Implicit contracts:** Description = capability + explicit trigger conditions; long descriptions are double-quoted to allow colons/commas; concrete example invocations improve routing.

## Q5: How do existing skills that wrap external CLIs separate the body of `SKILL.md` from detailed reference material placed in `references/`?

**Answer:** No in-repo skill wraps an external CLI. The closest in-repo example of
SKILL-body / reference separation is `qrspi-work`, whose body delegates cascade
logic to `references/review-cascade.md`. The external-CLI conventions the question
implies live in the global `using-graphite-cli` skill (out of scope). However, the
repo **does** encode Graphite-CLI usage conventions indirectly via the eval file
`evals/graphite-evals.json`, which specifies expected command forms, flags, and
safety rules for the (external) Graphite skill.

**Evidence:**

```
{
  "skill_name": "graphite",
  "evals": [
    { "id": 1, "prompt": "... commit my changes ...",
      "assertions": [
        {"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
        {"text": "Includes --no-interactive flag", "type": "flag_check"},
        ...
```

— `evals/graphite-evals.json:1-16`
The only in-repo body→reference link pattern:
— `.claude/skills/qrspi-work/references/review-cascade.md:1-8` (cascade rules factored out of the 730-line SKILL.md body)
**Dependencies:** `references/` files are linked from / loaded on demand by the skill body.
**Implicit contracts:** Heavy, situational logic is extracted into `references/`; the body stays focused on the control flow. CLI-wrapping conventions are not modeled as an in-repo skill.

## Q6: What conventions exist for keeping a `SKILL.md` body under the 500-line / 5000-token budget while linking out to deeper reference files?

**Answer:** Most skills are far under budget: 8 of 10 SKILL.md bodies are 25–35
lines because they are thin wrappers that defer all content to `.claude/agents/*.md`
("All prompt content lives in `.claude/agents/...`"). Two exceed typical guidance:
`qrspi-ticket` (119 lines) embeds its full prompt inline (no separate agent), and
`qrspi-work` (730 lines) is the orchestrator and **exceeds a 500-line budget** while
offloading some logic to `references/review-cascade.md`. So the demonstrated
budget-control techniques are (a) wrapper-delegates-to-agent and (b) extract
situational logic into `references/`. No automated line/token enforcement exists in
the repo.

**Evidence:**

```
 28 .claude/skills/qrspi-design/SKILL.md
 35 .claude/skills/qrspi-implement/SKILL.md
 ...
119 .claude/skills/qrspi-ticket/SKILL.md
730 .claude/skills/qrspi-work/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`
— `.claude/skills/qrspi-design/SKILL.md:11` ("All prompt content lives in `.claude/agents/qrspi-design.md`.")
**Dependencies:** Thin wrappers depend on the agent registry; orchestrator depends on `references/`.
**Implicit contracts:** Wrapper skills stay short by holding zero domain logic; long skills factor logic into `references/`. The 500-line target is not enforced and `qrspi-work` overruns it.

## Q7: Where in the codebase or skill conventions is the handling of deprecation/migration notices documented, so the timeline note is encoded consistently?

**Answer:** NOT FOUND — no skill or convention documents deprecation/migration
**notices** for tools. Grepping the repo for "deprecat" / "migration" surfaces only
unrelated usages: a billing-migration eval fixture (`fixtures/design_billing_migration.md`,
referenced in `suite.json`) and "migration" as a domain word in container-sandbox
docs. The only "version transition over time" precedent is the eval **version
ledger** in `report.py`/`docs/eval-system.md` (regression/plateau detection across
prompt versions), which is about prompt iteration, not external-tool deprecation
timelines. No date-stamped caveat convention exists.

**Evidence:**

```
`report.py` builds a version ledger and checks promotion criteria:
- Test score must not regress vs. previous version
...
Alerts: plateau detection (last 3 versions within 0.01), overfitting detection ...
```

— `docs/eval-system.md:49-55`
Searched: `grep -i "deprecat|migration"` → matches in `evals/suite.json` (billing-migration fixture name) and `docs/container-sandbox/*` only; none documenting a deprecation-notice convention.
**Dependencies:** None for tool deprecation.
**Implicit contracts:** None established. A consistent "timeline/deprecation note" format would be a new convention.

## Q8: What patterns exist for documenting destructive or autonomous operations so risk guidance is surfaced rather than buried?

**Answer:** Three concrete patterns exist. (1) **`allowed-tools` allowlisting** in
skill frontmatter restricts what a skill may invoke and scopes arguments (e.g.,
`Bash(pwd:*)` permits only `pwd`). (2) **Explicit "Hard constraints" sections** in
agent prompts forbid mutation ("Do not commit or run any git/gt mutation commands")
and a prominent **"HARD STOP: Infrastructure Errors"** block forbids workarounds.
(3) The Graphite eval encodes a **`safety_check` assertion type** requiring user
confirmation before destructive/remote operations (e.g., `gt submit`). The
orchestrator `qrspi-work` is explicitly autonomous ("Run autonomously — no approval
gates between phases") but bounded by hard-stop rules.

**Evidence:**

```
## Hard constraints
- Do not commit or run any git/gt mutation commands. The orchestrator handles all commits.
...
## HARD STOP: Infrastructure Errors
If ANY command fails with a permissions error ... STOP IMMEDIATELY. ... Do not attempt workarounds.
```

— `.claude/agents/qrspi-implement.md:42-60`

```
{"text": "Asks user for confirmation before submitting (safety rule)", "type": "safety_check"}
```

— `evals/graphite-evals.json:26` (and `:62` "Checks git status ... before syncing")
— `.claude/skills/qrspi-work/SKILL.md:11` ("Run autonomously — no approval gates between phases.")
**Dependencies:** `allowed-tools` enforced by harness; `safety_check` assertions enforced by the eval grader.
**Implicit contracts:** Destructive ops require (a) tool-allowlist restriction, (b) a Hard-constraints/HARD-STOP prose block, and/or (c) a confirmation gate verified by a `safety_check` eval assertion. Risk guidance is surfaced as named sections, not prose footnotes.

## Q9: How do existing skills document conflicting precedence rules (analogous to Gemini's CLI args > env vars > project settings > global settings hierarchy)?

**Answer:** No skill documents a config-precedence hierarchy. The closest **in-repo**
precedence pattern is the **eval scoring/promotion precedence** (programmatic >
llm_judge > script assertion types, weighted; test-score-must-not-regress promotion
gates) and the **review-cascade dependency ordering** (Questions → Research → Design
→ Structure → Plan → Work Tree, "use the earliest affected artifact"). The
`allowed-tools` frontmatter is a flat allowlist, not a layered hierarchy. No
`settings.json` files exist in the repo to define a project/global settings layering.
Mark the Gemini-style 4-level hierarchy NOT FOUND as an in-repo convention.

**Evidence:**

```
### Identify the earliest affected artifact
... If a comment affects multiple artifacts, use the earliest one in the chain.
```

— `.claude/skills/qrspi-work/references/review-cascade.md:11-15`
— `docs/eval-system.md:33-46` (weighted assertion precedence and promotion criteria)
Searched: `find .claude -name 'settings*.json'` → none.
**Dependencies:** Cascade ordering depends on the artifact dependency chain; eval precedence on the grader.
**Implicit contracts:** Precedence is expressed as an ordered dependency chain (earliest wins) or weighted assertion scoring — not as a documented CLI/env/settings override hierarchy.

## Q10: What eval or verification harness exists for skills in this repository, and what would be required to validate the new skill's triggering and content?

**Answer:** A 5-stage Python eval pipeline exists under `scripts/`, driven by
`evals/suite.json` (15 cases across QRSPI phases) plus a separate
`evals/graphite-evals.json` (5 cases for the external Graphite skill). Stages:
`run_eval.py` (execute cases), `grade.py` (programmatic + llm_judge + script
assertions), `report.py` (version ledger/regression), `diagnose.py` (8 failure
categories), `revise.py` (prompt edits). **Critical gaps:** agent execution is a stub
(`run_eval.py:117-137`), LLM-judge integration is a stub (`grade.py:208-227`), script
checks are a stub (`grade.py:230-241`), and only 4/21 fixtures exist — "the pipeline
runs end-to-end but produces zeros." Validating a **new** skill would require: adding
eval case(s) (a JSON block with `prompt`, `context.files`, weighted `assertions`),
supplying fixtures, and — to actually score triggering/content — real agent execution
and judge integration that are not yet implemented.

**Evidence:**

```
1. `scripts/run_eval.py` — Execute test cases against a skill prompt (multi-trial, parallel)
2. `scripts/grade.py` — Score results using programmatic checks + LLM judges
...
| Agent execution runtime | Stub | `run_eval.py:117-137` — no actual agent invocation |
| LLM judge integration | Stub | `grade.py:208-227` — returns None |
```

— `docs/eval-system.md:5-11`, `docs/eval-system.md:97-99`
**Dependencies:** `run_eval.py` → `grade.py` → `report.py`/`diagnose.py`/`revise.py`; cases reference `evals/fixtures/*` and `evals/golden/*`.
**Implicit contracts:** A case needs `id`, `name`, `phase`, `prompt`, `context.files`, and weighted `assertions` of types `programmatic` | `llm_judge` | `script`. Graphite-style skills use a separate eval file shape (`skill_name`, `evals[]` with `assertions[].type` like `command_check`/`flag_check`/`safety_check`).

## Q11: How are skill description/triggering accuracy and `SKILL.md` correctness currently measured for existing skills?

**Answer:** Two distinct eval shapes. (a) **QRSPI phase skills** are measured by
`evals/suite.json` cases scoring *output artifacts* (e.g., `output_file_exists`,
`has_section`, `no_solution_language`, plus `llm_judge` criteria) — content
correctness, not triggering. (b) The **Graphite skill** is measured by
`evals/graphite-evals.json` with assertion types `command_check`, `flag_check`,
`content_check`, `workflow_check`, and `safety_check` — i.e., whether the right CLI
command/flags/safety behavior is produced for a given prompt. **Triggering/routing
accuracy itself is not directly measured** by either harness; cases supply a `prompt`
and grade the response, but there is no description-routing benchmark. Scoring is
weighted-sum normalized 0–1 (llm_judge 1–5 normalized), with train/test split
(65/35, seed 42) to flag overfitting.

**Evidence:**

```
"assertions": [
  {"type": "programmatic", "check": "no_solution_language('questions.md')", "weight": 2.0},
  {"type": "llm_judge", "criteria": "Questions are specific and answerable by reading code ...", "weight": 2.0}
]
```

— `evals/suite.json:53-76`

```
{"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
{"text": "Includes --no-interactive flag", "type": "flag_check"},
```

— `evals/graphite-evals.json:11-12`
**Dependencies:** Grading per `grade.py` check registry (14 of ~37 checks implemented); llm_judge/script checks are stubs.
**Implicit contracts:** Correctness is asserted against produced artifacts/commands, weighted and normalized. New skills are validated by authoring matching assertions; pure description-trigger accuracy has no dedicated measurement here.

## Q12: How is skill invocation, triggering, or activation recorded or surfaced in this repository so the new skill's usage can be observed after it ships?

**Answer:** NOT FOUND for runtime invocation logging — there is no in-repo module
that records or surfaces skill triggering/activation at runtime (skill loading and
invocation are handled by the external Claude Code harness, outside `REPO_ROOT`; no
`settings.json` or logging hook exists in-repo). What the repo **does** surface: (a)
the orchestrator prints verbose progress for human observation ("Print verbose
progress so the operator can observe"); (b) Linear status transitions + comments act
as the observable phase-tracking signal (per `.claude/CLAUDE.md`: "Linear is used for
status tracking and phase-transition comments only"); (c) eval results under
`results/` (currently only `.gitkeep`) capture offline scoring, not production usage.

**Evidence:**

```
You are a state machine. ... Run autonomously ... Print verbose progress so the operator can observe.
```

— `.claude/skills/qrspi-work/SKILL.md:11`
— `.claude/CLAUDE.md` ("Linear is used for status tracking and phase-transition comments only — artifacts are not uploaded as attachments.")
— `results/.gitkeep` (eval output dir, empty)
**Dependencies:** Runtime invocation tracking belongs to the external harness; status observability depends on the Linear MCP server.
**Implicit contracts:** Observability is via (operator-facing) stdout progress and Linear status/comments, plus offline eval results — not an in-repo invocation log.

---

## Discovered Patterns

- **Wrapper → agent → artifact.** Every phase skill is a ~25–35 line `SKILL.md` that
  parses `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, and spawns a
  `subagent_type` agent; all domain logic lives in `.claude/agents/<name>.md`.
  Exceptions: `qrspi-ticket` (inline prompt, 119 lines) and `qrspi-work`
  (orchestrator, 730 lines). — `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`
- **Two frontmatter dialects.** Skills use `name/description/command/argument-hint/allowed-tools`;
  agents use `name/description/model/claude.tools`. — `.claude/skills/qrspi-research/SKILL.md:1-7` vs `.claude/agents/qrspi-research.md:1-7`
- **Named safety sections.** Agents repeat a "Hard constraints" + "HARD STOP:
  Infrastructure Errors" block forbidding mutations and workarounds, and a
  "Project scope boundary" requiring every path to start with `REPO_ROOT/`/`WORKTREE_DIR/`.
  — `.claude/agents/qrspi-implement.md:42-60`, `.claude/agents/qrspi-research.md:38-58`
- **Description = capability + explicit trigger.** Routing relies on "Use when…/Use
  after…/Trigger on any variant of…" phrasing, sometimes enumerating example invocations.
  — `.claude/skills/qrspi-work/SKILL.md:3`
- **Two eval shapes coexist.** Artifact-grading cases (`evals/suite.json`) and
  CLI-command-grading cases (`evals/graphite-evals.json`) use different assertion
  vocabularies. The latter is the only model in-repo for evaluating an external-CLI skill.
- **Templates as single source of truth.** Output formats live in `.qrspi/templates/`
  and are referenced, not embedded. — `README.md:110`, `.qrspi/templates/ticket.md:1-4`

## Inconsistencies

- **CLAUDE.md misstates the agents path.** `.claude/CLAUDE.md` says "Agent prompt
  definitions live in `.qrspi/agents/`", but that directory does not exist; agent
  prompts actually live in `.claude/agents/`. — `.claude/CLAUDE.md` ("Codebase
  conventions") vs `ls .qrspi/agents` → "No such file or directory".
- **`qrspi-work` exceeds the implied SKILL budget.** Q6 references a 500-line /
  5000-token budget, yet `qrspi-work/SKILL.md` is 730 lines with only partial
  offloading to `references/`. — `wc -l .claude/skills/qrspi-work/SKILL.md` = 730.
- **Eval harness is largely stubbed despite a "Done" framing.** `docs/eval-system.md`
  presents a 5-stage pipeline, but agent execution, LLM-judge, and script checks are
  stubs and 17/21 fixtures are missing — "the pipeline runs end-to-end but produces
  zeros." — `docs/eval-system.md:97-108`.
- **`scripts/`/`assets/` skill conventions are referenced but unused.** Q1 assumes
  `scripts/` and `assets/` skill subdirectories; no skill in the repo uses them (only
  `qrspi-work/references/`). Repo-root `scripts/` is the eval harness, a different concern.
- **External skills cited by questions are unreadable here.** `skill-creator`,
  `using-graphite-cli`, and `workflow-creator` are global (`~/.claude/`), outside
  `REPO_ROOT`; Q2 (and parts of Q4/Q5/Q9) cannot be answered from in-repo files.
