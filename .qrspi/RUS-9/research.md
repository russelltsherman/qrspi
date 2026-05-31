# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> Scope note: Many questions (Q4–Q13, and the builder half of Q2) ask about the
> behavior of the external `claude` CLI binary — flag parsing, session
> persistence, permission evaluation, JSON output, subagent loading, stdin caps,
> bare mode. **None of that lives in this repository.** This repo is a collection
> of Markdown skill/agent prompts, Markdown docs, JSON eval suites, and Python
> eval-harness scripts. There is no `claude` CLI source, no flag-parsing module,
> no session/permission engine here. Those questions are answered "NOT FOUND —
> targets a resource outside the project scope" with the searches attempted.
> The questions that ARE answerable from this codebase are Q1, Q3, and Q10
> (skill directory layout, SKILL.md frontmatter schema, and the eval harness).

## Q1: What directory structure and required files does an existing skill in this repo use (SKILL.md, references/, scripts/, assets/), and where on disk are skills authored so the new skill lands in the correct location?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, each containing a single
required `SKILL.md`. There are 10 existing skills (all `qrspi-*`). One skill
(`qrspi-work`) also has a `references/` subdirectory holding an auxiliary Markdown
file loaded on demand. No skill in this repo uses `scripts/` or `assets/`
subdirectories — those are not present. The convention `.claude/CLAUDE.md` documents
is "Agent prompt definitions live in `.qrspi/agents/`" but the actual agent files
live in `.claude/agents/*.md` (see Inconsistencies). A new skill should be authored
at `.claude/skills/<new-skill-name>/SKILL.md`.

**Evidence:**

```
.claude/skills/
  qrspi-design/SKILL.md
  qrspi-implement/SKILL.md
  qrspi-plan/SKILL.md
  qrspi-pr/SKILL.md
  qrspi-questions/SKILL.md
  qrspi-research/SKILL.md
  qrspi-structure/SKILL.md
  qrspi-ticket/SKILL.md
  qrspi-work/SKILL.md
  qrspi-work/references/review-cascade.md
  qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing); `.claude/skills/qrspi-work/references/review-cascade.md`

The skills are thin wrappers: each SKILL.md delegates the real prompt body to a
matching agent file. Example:

```
# /qrspi-questions
Thin wrapper that fetches the ticket from Linear and spawns the `qrspi-questions`
agent. All prompt content lives in `.claude/agents/qrspi-questions.md`.
```

— `.claude/skills/qrspi-questions/SKILL.md:9-11`

**Dependencies:** Skills reference agent definitions in `.claude/agents/*.md` via the
`Agent` tool (`subagent_type: <name>`). They also depend on templates in
`.qrspi/templates/*.md` and write artifacts to `.qrspi/<ticket-id>/*.md`.
**Implicit contracts:** Skill directory name matches the `name:` frontmatter field
and the `command:` (`/qrspi-questions` ↔ `qrspi-questions` ↔ dir `qrspi-questions/`).
The wrapper pattern (skill = thin dispatcher, agent = prompt body) is the dominant
convention for any skill that does real work.

## Q2: How does the skill-creator skill consume its inputs and where does it write generated skill output, so the new CLI skill is produced through the mandated builder rather than authored ad-hoc?

**Answer:** NOT FOUND in this repository. There is no `skill-creator` (or
`skill_creator` / `skill-builder`) SKILL.md anywhere under `REPO_ROOT`. The only
in-repo references to "skill-creator" are: (1) the questions file itself, and (2)
a one-line mention in an agent prompt instructing that "invoking skill-creator" is
a validation step — it does not define or invoke any local builder.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are
   the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:41`

Searches attempted (all scoped to `REPO_ROOT`):
- `grep -rln "skill-creator\|skill_creator\|skill-builder"` → only
  `.claude/agents/qrspi-structure.md` and `.qrspi/RUS-9/questions.md`
- `ls .claude/skills/` → no `skill-creator` directory
- No `scripts/` or `assets/` under any skill that would host a builder.

**Dependencies:** none locatable.
**Implicit contracts:** The user's global instructions reference a `skill-creator`
skill and an eval loop, but its definition is outside `REPO_ROOT` (global skill
scope) and therefore out of bounds for this research.

## Q3: What YAML frontmatter fields are required and validated for a SKILL.md in this repo (name, description, and any others), and what are the format constraints on each?

**Answer:** There is no programmatic validator for SKILL.md frontmatter in this repo
(no schema file, no linter script). The de facto schema is established by the 10
existing skills, all consistent. Fields observed:
- `name` — present in all 10. Matches the skill directory name (e.g. `qrspi-questions`).
- `description` — present in all 10. A trigger sentence; may be quoted (the long
  `qrspi-work` value is wrapped in double quotes, the rest are bare scalars). States
  what the skill does plus "Use when…" triggering guidance.
- `command` — present in all 10. The slash command, prefixed `/` (e.g. `/qrspi-questions`).
- `argument-hint` — present in all 10. Examples: `<ticket-id>`, `<initial description>`,
  `<ticket-id> <slice-number>`.
- `allowed-tools` — present in all 10. Comma-separated tool list. Bash is scoped with
  glob specifiers, e.g. `Bash(pwd:*)`. MCP tools use the `mcp__<server>__<tool>` form
  (e.g. `mcp__linear-russelltsherman__get_issue`).

No `model`, `disable-model-invocation`, or other fields appear in any SKILL.md.
(Agent files in `.claude/agents/` use a *different* frontmatter shape — see Q6 / Q9
note and Inconsistencies.)

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

Field census across all 10 SKILL.md frontmatters: `name` ×10, `command` ×10,
`argument-hint` ×10, `description` ×10, `allowed-tools` ×10. — derived from
`.claude/skills/*/SKILL.md`

**Dependencies:** Frontmatter is consumed by the Claude Code harness (external),
not by any in-repo code.
**Implicit contracts:** `name` must equal the directory name; `command` must be
`/<name>`; `allowed-tools` must enumerate every tool the body uses, with Bash
scoped via `Bash(<cmd>:*)` and MCP tools via `mcp__<server>__<tool>`. No required
field is enforced by code — consistency is by convention only.

## Q4: What is the documented `claude` CLI flag set currently available in this environment (interactive, `-p`, `--bare`, `--bg`, `--output-format`, session flags, permission flags)?

**Answer:** NOT FOUND. No `claude --help` output, man page, flag reference doc, or
flag-parsing source exists under `REPO_ROOT`. The repo documents *Claude Code skill
authoring* (slash commands, `/clear`, `/compact`, `/context`) but never the headless
`claude` binary's flag surface.

Searches attempted (scoped to `docs/`, `README.md`, repo-wide):
`--bare`, `--output-format`, `--bg`, `--fork-session`, `--no-session-persistence`,
`--allowedTools`, `--disallowedTools`, `--max-budget`, `bypassPermissions`,
`acceptEdits`, `--mcp-config`, `--agents`, `headless`, `print mode`, `claude -p`.
The only matches were slash-command UI references (`/clear`, `/compact`, `/context`)
in `docs/qrspi_claude_code_guide.md` (lines 83, 540, 598) — not CLI flags.

**Dependencies:** the `claude` CLI binary (external to repo).
**Implicit contracts:** n/a — resource outside project scope.

## Q5: How are Claude CLI sessions persisted and resumed (`-c`, `-r`, `-n`, `--fork-session`, `--no-session-persistence`), and where is `session_id` exposed in JSON output?

**Answer:** NOT FOUND — targets the external `claude` CLI / its JSON output, which
has no source or documentation under `REPO_ROOT`. Searched repo-wide for
`session_id`, `--fork-session`, `--no-session-persistence`, `resume`, `-c`/`-r`/`-n`
session flags, `--output-format json`: zero matches relating to CLI session handling.
The word "session" in this repo refers exclusively to QRSPI *worktree session
boundaries* (a planning concept for splitting work across fresh `/clear` contexts),
e.g. `docs/qrspi_claude_code_guide.md:310-316`, not CLI session persistence.

**Dependencies:** external CLI.
**Implicit contracts:** n/a — outside project scope.

## Q6: How are custom subagents and their frontmatter (`name`, `description`, `model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`) loaded from `.claude/agents/` versus passed ephemerally via `--agents '{JSON}'`?

**Answer:** Partial / mostly NOT FOUND. This repo *contains* `.claude/agents/*.md`
agent definitions and shows their frontmatter shape, but it contains **no loader
code** and **no documentation** of how the harness discovers them or how `--agents
'{JSON}'` ephemeral injection works — those are external CLI behaviors.

What the repo does show: 8 agent files exist (`qrspi-design`, `qrspi-implement`,
`qrspi-plan`, `qrspi-pr`, `qrspi-questions`, `qrspi-research`, `qrspi-structure`,
`qrspi-worktree`). Their frontmatter uses `name`, `description`, `model`, and a
nested `claude:` block with `tools:` — NOT the flat field set the question lists
(`tools`, `permissionMode`, `skills`, `mcpServers`, `hooks` were not observed).

**Evidence:**

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts ...
model: opus
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/agents/qrspi-research.md:1-6`

Skills spawn these agents by `subagent_type` via the `Agent` tool, e.g.
"Spawn the research agent via the Agent tool with `subagent_type: qrspi-research`"
— `.claude/skills/qrspi-work/SKILL.md:154`. No `--agents` JSON usage appears anywhere.

**Dependencies:** the `Agent` tool / harness subagent loader (external).
**Implicit contracts:** agent `name` matches its filename and the `subagent_type`
used by spawning skills. Tools are declared under a nested `claude.tools` key in
agents (vs. flat `allowed-tools` in skills).

## Q7: What is the documented behavior when piped stdin exceeds the 10MB cap, and how is that surfaced to the caller?

**Answer:** NOT FOUND — targets the external `claude` CLI's stdin handling. No `10MB`/
`10 MB` cap, no stdin-handling module, and no print/headless-mode source exists under
`REPO_ROOT`. Searched repo-wide for `10MB`, `10 MB`, `stdin`, `print mode`, `headless`:
no matches describing a stdin size cap.

**Dependencies:** external CLI.
**Implicit contracts:** n/a — outside project scope.

## Q8: In bare mode, which auto-discovered resources (hooks, skills, plugins, MCP servers, CLAUDE.md) are skipped, and what must be passed explicitly (e.g. `--mcp-config`) for MCP tools to function?

**Answer:** NOT FOUND — targets `claude --bare` behavior. No `--bare` flag, bare-mode
logic, resource-discovery module, or `--mcp-config` documentation exists under
`REPO_ROOT`. Searched repo-wide for `--bare`, `bare mode`, `--mcp-config`,
`auto-discover`/`discovery`: no matches.

**Dependencies:** external CLI.
**Implicit contracts:** n/a — outside project scope.

## Q9: What is the documented constraint that subagents cannot spawn other subagents, and how does that differ from agent teams where teammates each get their own context window?

**Answer:** NOT FOUND as a documented CLI constraint. The repo never states a
"subagents cannot spawn subagents" rule, nor does it document "agent teams" with
per-teammate context windows. There is a *related architectural fact*: `qrspi-batch`
(per the global skill list) was replaced by `qrspi-batch-v2` because the older
version "nested qrspi-work inside agent() and therefore could not spawn the phase
agents" — but that is described in the harness-level skill descriptions outside
`REPO_ROOT`, not in any repo file. Inside the repo, the orchestration model is
"one orchestrator skill (`qrspi-work`) spawns single phase agents via the `Agent`
tool; agents themselves do not spawn further agents" — but this is implied by the
prompts, not stated as a hard CLI constraint.

Searches attempted: `subagent`, `agent team`, `teammate`, `context window`,
`cannot spawn` — repo-wide. Only matches are the spawn instructions in
`.claude/skills/qrspi-work/SKILL.md` (e.g. lines 565-577 "Sub-Agent Rules"), which
describe orchestrator→agent dispatch, not a nesting prohibition.

**Dependencies:** external CLI orchestration model.
**Implicit contracts:** the repo's own pattern is single-level fan-out: an
orchestrator skill spawns leaf phase agents; phase agents do file work only.

## Q10: What eval harness exists for skills in this repo (`evals/`, `scripts/`), and what format do skill eval cases take so the new CLI skill can be benchmarked per the skill-creator eval loop?

**Answer:** A 5-stage Python eval pipeline exists under `scripts/`, driven by JSON
suites under `evals/`. Stages: `run_eval.py` (execute cases) → `grade.py` (score) →
`report.py` (compare versions / regression guard) → `diagnose.py` (categorize
failures) → `revise.py` (propose prompt edits). The suite `evals/suite.json` defines
15 cases across QRSPI phases; `evals/graphite-evals.json` is a separate 5-case suite.

Case format (from `evals/suite.json`): each case is a JSON object with `id`, `name`,
`phase`, `prompt`, `context` (`files` [], `conversation_history` [], `user_preferences`
{}), `assertions` [], `tags` [], `difficulty`, and `split` ("train"|"test"). Suite-level
keys: `name`, `version`, `description`, `split` (train/test ratio + seed 42),
`defaults` (`trials_per_case`, `timeout_ms`, `max_tokens`), and `cases` [].

Assertions are weighted and come in three types:
- `programmatic` — deterministic checks via a `check` string, e.g.
  `output_file_exists('questions.md')`, `question_count('questions.md') >= 8`,
  `no_solution_language('questions.md')`.
- `llm_judge` — a natural-language `criteria` string scored 1-5 (normalized 0-1).
- `script` — external script execution, e.g.
  `scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md`.

**Evidence:**

```json
{
  "id": "case_001",
  "name": "questions_happy_path",
  "phase": "questions",
  "prompt": "Generate questions for the following ticket.",
  "context": { "files": ["fixtures/ticket_rest_endpoint.md"], "conversation_history": [], "user_preferences": {} },
  "assertions": [
    { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
    { "type": "llm_judge", "criteria": "Questions are specific and answerable by reading code...", "weight": 2.0 }
  ],
  "tags": ["questions", "happy-path", "rest-endpoint"],
  "difficulty": "easy", "split": "train"
}
```

— `evals/suite.json:16-81` (abridged)

Suite loader validates required keys `{"name","cases"}` per suite and
`{"id","prompt","assertions"}` per case:

```
required = {"name", "cases"}
...
case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:47-56`

**CRITICAL gap for benchmarking:** the harness does not actually run an agent. The
execution step is a stub that returns empty output and zero tokens:

```
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
...
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:117-137`

`docs/eval-system.md:96-108` confirms: agent execution (`run_eval.py:117-137`),
LLM judge (`grade.py:208-227`), and script-check execution (`grade.py:230-241`) are
all stubs; only 14 of ~37 referenced programmatic checks are implemented; 4 of 21
fixtures exist; `evals/golden/` holds only `.gitkeep`. "The pipeline runs end-to-end
but produces zeros."

**Dependencies:** `run_eval.py` reads suite JSON + skill/agent prompt file +
`evals/fixtures/*`; `grade.py` consumes its output; `report.py`/`diagnose.py`/
`revise.py` chain after. `check_scope.py` is the only fully-implemented script check.
**Implicit contracts:** to benchmark a new skill, add a case object with the required
keys to a suite JSON, supply any referenced `context.files` under `evals/fixtures/`,
and (because execution is stubbed) wire a real agent invocation into
`run_eval.py:117-137` first — otherwise scores are 0. Programmatic `check` strings
must map to functions in `grade.py`'s check registry, most of which are unimplemented.

## Q11: What metadata does `--output-format json` emit beyond `result` and `session_id` (cost, token usage, budget), and how are `--max-budget-usd` and `--max-turns` limits reported when hit?

**Answer:** NOT FOUND — targets the external `claude` CLI's JSON output schema and
budget/turn accounting. No `--output-format`, `--max-budget-usd`, `--max-turns`, or
JSON-result-formatting source exists under `REPO_ROOT`. Searched repo-wide for
`--output-format`, `--max-budget`, `--max-turns`, `session_id`, `cost`, `token usage`:
no CLI-related matches. (The eval harness has its own unrelated `tokens`/`duration_ms`
fields on `ExecutionResult` in `scripts/run_eval.py:19-29`, but those are for the eval
runner, not the `claude` CLI's `--output-format json`.)

**Dependencies:** external CLI.
**Implicit contracts:** n/a — outside project scope.

## Q12: What are the documented permission modes (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`), the deny->ask->allow rule evaluation order, and the settings hierarchy (Managed > CLI args > Local > Shared > User)?

**Answer:** NOT FOUND — targets the external `claude` CLI permission engine. No
permission-mode constants, rule-evaluation logic, or settings-precedence
documentation exists under `REPO_ROOT`. Searched repo-wide for `acceptEdits`,
`bypassPermissions`, `dontAsk`, `permissionMode`, `deny`/`ask`/`allow`,
`Managed`/`settings hierarchy`: no matches. The repo does carry an untracked
`.claude/settings.local.json`, but that is a generated harness config, not the
permission-engine definition, and it is not part of the committed codebase.

**Dependencies:** external CLI.
**Implicit contracts:** n/a — outside project scope.

## Q13: What is the exact rule syntax for `--allowedTools` / `--disallowedTools` including glob specifiers and the `mcp__<server>__<tool>` pattern used to scope MCP tools in headless runs?

**Answer:** Partial. The CLI flags `--allowedTools` / `--disallowedTools` and their
formal grammar are NOT documented anywhere under `REPO_ROOT`. However, the repo
demonstrates the *tool-rule syntax* in SKILL.md `allowed-tools:` frontmatter, which
uses the same conventions the question describes:
- Bare tool names: `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Agent`, `Bash`.
- Bash glob scoping: `Bash(pwd:*)` — `<tool>(<command>:*)`.
- MCP tool scoping: `mcp__<server>__<tool>`, e.g.
  `mcp__linear-russelltsherman__get_issue`.

**Evidence:**

```
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
```

— `.claude/skills/qrspi-questions/SKILL.md:6`

```
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent,
  mcp__linear-russelltsherman__get_issue, mcp__linear-russelltsherman__get_issue_status,
  mcp__linear-russelltsherman__save_issue, mcp__linear-russelltsherman__list_issue_statuses,
  mcp__linear-russelltsherman__save_comment
```

— `.claude/skills/qrspi-work/SKILL.md:6`

The exact `--allowedTools`/`--disallowedTools` CLI flag grammar (full glob spec,
precedence between allow/deny on the command line) is NOT FOUND — that is external
CLI documentation. The in-repo `allowed-tools` frontmatter is the closest analog and
shows the shared `mcp__<server>__<tool>` and `Bash(<cmd>:*)` patterns.

**Dependencies:** external CLI flag parser; in-repo: the harness reads `allowed-tools`
from SKILL.md / `claude.tools` from agent frontmatter.
**Implicit contracts:** MCP tools are always referenced as `mcp__<server>__<tool>`;
Bash sub-commands are scoped with `Bash(<cmd>:*)`. These conventions are consistent
across all skills and are the syntax a new CLI skill should reuse for its own
`allowed-tools`.

---

## Discovered Patterns

- **Thin-skill / fat-agent split.** Every skill that does real work is a thin
  wrapper SKILL.md that parses `$ARGUMENTS`, optionally fetches Linear data, then
  spawns a purpose-built agent (`.claude/agents/<name>.md`) by `subagent_type`. The
  prompt body lives in the agent file, not the skill. (`.claude/skills/qrspi-questions/SKILL.md:9-11`,
  `.claude/skills/qrspi-work/SKILL.md:565-573`).
- **Two distinct frontmatter dialects.** Skills use flat `name`/`description`/
  `command`/`argument-hint`/`allowed-tools`. Agents use `name`/`description`/`model`
  plus a nested `claude:` block with `tools:` (`.claude/agents/qrspi-research.md:1-6`).
  A new CLI *skill* should follow the skill dialect.
- **Tool-rule syntax is uniform:** bare names, `Bash(<cmd>:*)` for Bash scoping,
  `mcp__<server>__<tool>` for MCP. Used identically in skill `allowed-tools`.
- **Naming triple invariant:** directory name == `name:` == `command:` minus the `/`.
- **Eval cases are declarative JSON** with weighted assertions of three types
  (programmatic / llm_judge / script); train/test split with fixed seed 42.
- **The eval harness is a scaffold, not a working benchmark** — execution, LLM
  judging, and script checks are all stubs producing zeros (`scripts/run_eval.py:117-137`,
  `docs/eval-system.md:96-108`).
- **Hard-stop-on-infrastructure-error discipline** is a repeated convention baked
  into agent/skill prompts (`.claude/skills/qrspi-work/SKILL.md:709-731`).

## Inconsistencies

- **Agent location doc mismatch.** `.claude/CLAUDE.md` states "Agent prompt
  definitions live in `.qrspi/agents/`", but the actual agent files are in
  `.claude/agents/*.md`. There is no `.qrspi/agents/` directory. The same CLAUDE.md
  text is duplicated in `.claude/CLAUDE.md` of both the worktree and (per project
  conventions) the main repo.
- **Co-author trailer version drift.** `.claude/skills/qrspi-work/SKILL.md` commit
  templates hard-code `Co-Authored-By: Claude Opus 4.7 (1M context)` (e.g. lines 146,
  167, 280), while the active environment/model is Opus 4.8.
- **Eval suite vs. implementation gap.** `evals/suite.json` references ~37 programmatic
  checks and 21 fixtures, but only 14 checks and 4 fixtures exist; `evals/golden/`
  is empty (`docs/eval-system.md:80-108`). Cases reference fixtures like
  `fixtures/questions_rest_endpoint.md` that are not present on disk.
- **skill-creator is mandated but absent locally.** User-global instructions and the
  questions file assume a `skill-creator` skill with an eval loop, and
  `.claude/agents/qrspi-structure.md:41` lists "invoking skill-creator" as a
  validation step, yet no `skill-creator` definition exists under `REPO_ROOT` (it
  lives in global skill scope, outside this project).
