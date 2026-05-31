# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> Scope note: This repository is the QRSPI workflow itself. Agent skills here are
> Claude Code SKILL.md prompt files under `.claude/skills/`, not ArgoCD/Kubernetes
> automation. The `skill-creator` skill referenced by several questions is NOT
> present in this repository — it is a global/plugin skill that lives outside
> `REPO_ROOT`. Per the research scope firewall, files outside
> `/workspaces/qrspi/.worktrees/RUS-8/` were not read. Questions targeting
> `skill-creator` internals are answered "NOT FOUND — outside project scope" with
> the in-repo evidence that does exist.

## Q1: Where are agent skills stored in this repo, and what is the on-disk layout of an existing skill (SKILL.md plus references/, scripts/, assets/) that the new argocd skill must mirror?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, one directory per skill, each containing a `SKILL.md`. There are 10 skills (all `qrspi-*`). Only one skill (`qrspi-work`) uses a `references/` subdirectory; no skill in this repo uses `scripts/` or `assets/` subdirectories. The minimal layout is a single `SKILL.md`; the multi-file layout is `SKILL.md` + `references/<topic>.md`.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
.claude/skills/qrspi-plan/SKILL.md
.claude/skills/qrspi-pr/SKILL.md
.claude/skills/qrspi-questions/SKILL.md
.claude/skills/qrspi-research/SKILL.md
.claude/skills/qrspi-structure/SKILL.md
.claude/skills/qrspi-ticket/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
```

— layout enumerated under `.claude/skills/`

The README documents this convention explicitly:

```
.claude/
  skills/              # Skill definitions (one SKILL.md per phase)
    qrspi-ticket/
    ...
    qrspi-work/        # Autonomous orchestrator
```

— `README.md:75-87`

**Dependencies:** Skills are discovered by the Claude Code harness from `.claude/skills/`. Some skills reference templates at `.qrspi/templates/*.md` and agent prompts at `.claude/agents/qrspi-*.md`.
**Implicit contracts:** Directory name matches the `name` frontmatter field exactly (e.g., directory `qrspi-work/` ↔ `name: qrspi-work`). A new `argocd` skill should be a new directory `.claude/skills/<name>/SKILL.md` mirroring this layout; add a `references/` subdir only if body content must be split out.

## Q2: How does the skill-creator skill consume an input description and emit a SKILL.md plus reference files — what is its expected input format and output directory convention?

**Answer:** NOT FOUND — the `skill-creator` skill is not present in this repository. Searches for `skill-creator`, frontmatter-schema modules, and scaffolding scripts returned no in-repo definition (the only matches are the questions.md file itself and a passing mention in `.claude/agents/qrspi-structure.md:41`). `skill-creator` is a global/plugin skill that lives outside `REPO_ROOT`; per the scope firewall it was not read. The in-repo convention it would have to follow is: emit a directory `.claude/skills/<name>/SKILL.md` (see Q1), with frontmatter per Q3 and reference splitting per Q9.

**Evidence:**

```
.claude/agents/qrspi-structure.md:41:9. Validation passes (linting, running a review tool,
  invoking skill-creator) are the final step of the slice that produced the files
```

— `.claude/agents/qrspi-structure.md:41` (only non-question reference to skill-creator in repo)

**Dependencies:** None in-repo. `skill-creator` is external.
**Implicit contracts:** Output must conform to the `.claude/skills/<name>/SKILL.md` layout this repo already enforces (Q1).

## Q3: What exact frontmatter fields (name, description, and any others) does a valid SKILL.md require in this repo, and what are the format/length constraints on each?

**Answer:** Observed frontmatter fields across all 10 skills: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. There is no in-repo schema file or validator defining "required" — the requirement is established by example/convention only. All 10 skills include `name` and `description`. `command` and `argument-hint` appear in every standalone phase skill. `allowed-tools` is a comma-separated tool allowlist. The `description` may be a bare YAML scalar or a double-quoted string (quoted when it contains a colon or embedded examples, e.g. `qrspi-work`). No length constraint is enforced programmatically, but the body is held under 500 lines / ~40 instructions (see Q8).

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

```
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>'..."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, ...
```

— `.claude/skills/qrspi-work/SKILL.md:2-6`

Note: agent files under `.claude/agents/` use a DIFFERENT frontmatter shape (`name`, `description`, `model`, `claude.tools`) — not the skill shape:

```
name: qrspi-research
description: Internal QRSPI workflow agent ...
model: opus
claude:
  tools: Read, Write, Glob, Grep
```

— `.claude/agents/qrspi-research.md:2-6`

**Dependencies:** The harness parses this frontmatter to register the slash command and enforce `allowed-tools`.
**Implicit contracts:** `command` = `/` + `name`. `allowed-tools` supports scoped Bash like `Bash(pwd:*)`. An argocd skill would need `allowed-tools` to include `Bash` (likely scoped, e.g. `Bash(argocd:*)`) since CLI wrapping requires shell execution.

## Q4: What naming convention is enforced for skill directories and the `name` field — does an existing skill demonstrate the kebab-case / prefix pattern the argocd skill should follow?

**Answer:** Convention (by example, not enforced by tooling): lowercase kebab-case, with a `qrspi-` domain prefix on every skill in this repo. The directory name equals the `name` field equals the slash command minus the leading `/`. No validator enforces this — it is observed across all 10 skills.

**Evidence:**

```
name: qrspi-structure
command: /qrspi-structure
```

— `.claude/skills/qrspi-structure/SKILL.md:2,4` (directory `qrspi-structure/`)

All ten directory names: `qrspi-ticket, qrspi-questions, qrspi-research, qrspi-design, qrspi-structure, qrspi-plan, qrspi-worktree, qrspi-implement, qrspi-pr, qrspi-work`.

**Dependencies:** Harness slash-command registration.
**Implicit contracts:** Triple identity directory==`name`==command-without-slash. An argocd skill would follow kebab-case (e.g. `argocd`, or a prefixed form if the repo adopts a non-qrspi prefix). NOTE: there is no precedent for a non-`qrspi-`-prefixed skill in this repo — the prefix is universal here, so an `argocd` skill is a new naming precedent.

## Q5: How do existing skills reference their `references/` files from the SKILL.md body (relative paths, link syntax, progressive-disclosure pattern)?

**Answer:** Exactly one skill (`qrspi-work`) references a `references/` file. It does so with a plain relative path inside an imperative instruction, not a markdown link — "Read `references/review-cascade.md` for cascade logic." The progressive-disclosure pattern: the SKILL.md keeps a one-line pointer and defers the detailed decision logic to the reference file, instructing the agent to read it only when that branch is reached (during plan-review feedback).

**Evidence:**

```
c. Read `references/review-cascade.md` for cascade logic.
d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
```

— `.claude/skills/qrspi-work/SKILL.md:272-273`

The reference file itself is a standalone topic doc (cascade rules + decision table + worked example):

```
# Review Cascade Logic
...
| Change type | Cascade? |
|---|---|
| Typo, wording fix, clarification | No cascade — fix only the targeted artifact |
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-23`

**Dependencies:** Path is relative to the skill directory (`.claude/skills/qrspi-work/references/...`).
**Implicit contracts:** Reference path is relative to the SKILL.md's own directory; referenced lazily ("Read X for Y") so it loads into context only when that code path executes — the progressive-disclosure pattern the argocd skill should mirror for verbose CLI command catalogs or troubleshooting tables.

## Q6: Is there an eval harness or metadata registry that tracks skills, and must a newly created skill be registered there to be discoverable/triggerable?

**Answer:** There is an eval harness (`evals/` + `scripts/`) but it is NOT a skill registry — it is a prompt-quality test suite. Skills are discovered by the harness purely from the `.claude/skills/` directory; there is no manifest/index file a skill must be added to for discoverability. The eval suite enumerates phases by hardcoded test cases, not by scanning skills. The current suite covers 8 phases (`design, implement, plan, pr, questions, research, structure, worktree`) — it does NOT cover `qrspi-ticket` or `qrspi-work`, confirming the suite is a curated case list, not an auto-registry.

**Evidence:**

```
$ python3 -c "import json;d=json.load(open('evals/suite.json'));print(sorted(set(c['phase'] for c in d['cases'])))"
['design', 'implement', 'plan', 'pr', 'questions', 'research', 'structure', 'worktree']
num cases 15
```

— derived from `evals/suite.json` (`cases` array; top keys: `name, version, description, split, defaults, cases`)

`run_eval.py` takes an explicit `--skill <path>` argument; it does not scan a registry:

```
parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
```

— `scripts/run_eval.py:219-220`

**Dependencies:** Discovery = filesystem (`.claude/skills/`). Eval = manual invocation pointing at a specific skill/agent file + suite.
**Implicit contracts:** A new argocd skill becomes triggerable simply by existing at `.claude/skills/<name>/SKILL.md` with valid frontmatter (no registration). To be *eval-tested*, a new case must be hand-added to `evals/suite.json` (see Q12).

## Q7: How is a skill's `description` used for trigger matching, and what existing examples show the pattern for writing a triggering description?

**Answer:** The `description` is the trigger surface — the harness matches it against user intent for auto-invocation. The richest example is `qrspi-work`, whose description front-loads purpose, then gives a concrete example, then an explicit "Trigger on any variant of:" list of phrasings. Shorter phase skills use a "Use after X is approved" / "Use when Y" pattern naming the precondition and trigger phrase. No in-repo tool scores descriptions; the pattern is convention. (The description-optimization guidance asked about belongs to the external `skill-creator` skill — NOT FOUND in repo.)

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

```
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-questions/SKILL.md:3`

**Dependencies:** Harness trigger-matching reads this field.
**Implicit contracts:** Effective descriptions: (1) state purpose, (2) give a concrete user-phrase example, (3) for high-traffic skills, enumerate trigger variants and exclusions. The argocd skill's description should list the user intents it serves (deploy/sync/diff/rollback an app via argocd CLI) and ideally what it does NOT cover (see Q10 — no precedent for explicit exclusions in descriptions here).

## Q8: What enforces the SKILL.md body limit (under 500 lines / 5000 tokens), and is there tooling to measure token count so reference material can be split out correctly?

**Answer:** NOTHING in-repo enforces or measures it. The 500-line / ~40-instruction budget is documented as guidance in `docs/qrspi_claude_code_guide.md`, but there is no linter, hook, or token-counter script in `scripts/`. The grade harness has a generic `line_count(filename, max_lines, ...)` check function, but it operates on *output artifacts* during evals, not on SKILL.md source files, and it counts lines, not tokens. The questions.md premise of a "5000 token" limit and "tooling to measure token count" is NOT supported by any in-repo tool — token measurement would be external (skill-creator) or manual.

**Evidence:**

```
The skill prompt may be too long. Check that each `SKILL.md` is under 500 lines and under ~40 distinct instructions. The instruction budget ceiling is real.
```

— `docs/qrspi_claude_code_guide.md:592`

Observed actual sizes (only `qrspi-work` is large at 730 lines — exceeding the 500 guideline):

```
 28 qrspi-design   35 qrspi-implement   26 qrspi-plan   28 qrspi-pr
 26 qrspi-questions  26 qrspi-research   25 qrspi-structure
119 qrspi-ticket  730 qrspi-work   25 qrspi-worktree
```

— `wc -l .claude/skills/*/SKILL.md`

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
```

— `scripts/grade.py:35` (operates on eval output artifacts, not SKILL.md sources)

**Dependencies:** None — guidance only.
**Implicit contracts:** Budget is honor-system. Note inconsistency: `qrspi-work` at 730 lines violates the documented 500-line ceiling (see Inconsistencies).

## Q9: How do existing skills handle content that exceeds the body budget — what is the established split point between SKILL.md and `references/` files?

**Answer:** The single established split point is in `qrspi-work`: detailed *branch-specific decision logic* (the review-cascade rules) is extracted into `references/review-cascade.md`, while the SKILL.md retains the orchestration flow and a one-line pointer. The reference file holds a decision table, the re-run procedure, and a worked example. The split criterion observed: content that is (a) only needed on one conditional path and (b) is a self-contained decision procedure gets moved to references; the main control flow stays in SKILL.md. Notably, `qrspi-work` still runs 730 lines even after this split, so the split was used for one logical chunk, not to aggressively meet a line budget.

**Evidence:**

```
# Review Cascade Logic
...
## Cascade Rules
### Identify the earliest affected artifact
...
### Re-running a downstream phase
...
### Example
Reviewer says: "The design should use event sourcing instead of CRUD for the audit log."
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-54` (the extracted, deferred-load chunk)

**Dependencies:** Loaded only when `qrspi-work` reaches plan-review feedback handling (`SKILL.md:272`).
**Implicit contracts:** Split point = self-contained decision procedure tied to one code path. The argocd skill should extract verbose command references / troubleshooting matrices into `references/` and keep the main flow + a one-line "Read references/X.md for Y" pointer in SKILL.md.

## Q10: Are there existing CLI-wrapper or kubectl/Helm-adjacent skills whose scope boundaries (in-scope vs defer-to-other-skill) demonstrate how this skill should declare its out-of-scope deferrals?

**Answer:** NOT FOUND — no CLI-wrapper, kubectl, Helm, or argocd skill exists in this repo. All skills wrap the internal QRSPI workflow, not external CLIs. However, two relevant *patterns* exist that demonstrate scope-deferral and tool-wrapping discipline: (1) `qrspi-ticket` explicitly declares out-of-scope content and redirects it to a later phase; (2) `qrspi-work` repeatedly defers git operations to graphite (`gt`) and never raw `git` when a `gt` equivalent exists — a wrap-one-CLI-don't-bypass-it pattern. There is also a global `using-graphite-cli` skill the project mandates for all git ops, evidencing a "defer to the dedicated tool" convention.

**Evidence:**

```
4. Do not propose solutions, architectures, or implementation approaches — even if the user volunteers them ...
5. If the user provides implementation details, redirect: "That sounds like it belongs in the Design phase ..."
```

— `.claude/skills/qrspi-ticket/SKILL.md:46-47` (explicit scope deferral pattern)

```
- Never run raw `git` commands when a `gt` equivalent exists.
```

— `.claude/skills/qrspi-work/SKILL.md:637` (CLI-wrapping discipline)

**Dependencies:** `using-graphite-cli` is a global skill (outside repo); referenced as the mandated git path.
**Implicit contracts:** The repo's deferral idiom is an inline imperative ("X belongs in phase Y" / "Never use raw X when Y exists"), not a dedicated frontmatter field. An argocd skill would declare out-of-scope work as prose do/don't statements (e.g. "for raw cluster ops use kubectl directly; this skill only wraps `argocd`").

## Q11: What format do existing skills use to encode opinionated defaults and judgment-call guidance (decision tables, flowcharts, do/don't lists) that the argocd skill's escalation paths should follow?

**Answer:** Three concrete formats are used in-repo: (1) markdown decision tables (two-column "condition | action"); (2) numbered do/don't and anti-pattern lists; (3) explicit "HARD STOP" callout blocks for error/escalation handling. The `qrspi-work` state machine also uses a state→action dispatch table.

**Evidence:**

Decision table (cascade depth judgment):

```
| Change type | Cascade? |
|---|---|
| Typo, wording fix, clarification | No cascade — fix only the targeted artifact |
| New question added to questions.md | Re-run Research ... |
```

— `.claude/skills/qrspi-work/references/review-cascade.md:21-24`

State-dispatch table:

```
| Linear Status | Action |
|---|---|
| `Backlog` or `Selected` | → [Run Planning](#...) |
```

— `.claude/skills/qrspi-work/SKILL.md:95-97`

Anti-pattern / do-not list and HARD STOP escalation block:

```
### Anti-patterns — do NOT include in the ticket body
Before drafting, verify the ticket contains NONE of these:
- Specific technical approaches, tool choices, or library recommendations
```

— `.claude/skills/qrspi-ticket/SKILL.md:50-53`

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve
This is a non-negotiable constraint. There is NO exception.
... 1. STOP. Do not execute another command. ...
**Explicitly forbidden responses to infrastructure errors:**
- Changing directory ownership or permissions (`chmod`, `chown`)
```

— `.claude/skills/qrspi-work/SKILL.md:709-728`

**Dependencies:** None — pure prompt-authoring conventions.
**Implicit contracts:** Judgment calls = decision tables; safety rails = numbered do/don't lists + bold "HARD STOP" blocks listing explicitly forbidden actions. The argocd skill's escalation paths (sync failures, out-of-sync drift, rollback decisions) should use these same three formats.

## Q12: How are skills evaluated in this repo — what does the eval harness expect (eval cases, scoring, variance analysis) and what artifacts must accompany a new skill to be testable?

**Answer:** The harness is a Python pipeline: `run_eval.py` (execute trials) → `grade.py` (score assertions) → `report.py` / `diagnose.py` / `revise.py`, orchestrated by `run_loop.sh`. A skill is tested by adding case(s) to `evals/suite.json`. Each case has `id`, `name`, `phase`, `prompt`, `context` (fixture files, conversation history, user prefs), and `assertions`. Assertions have a `type` (`programmatic`, `llm_judge`, or `script`), a `check` expression, and a `weight`. Programmatic checks are functions registered in `grade.py`'s `CHECKS` dict (e.g. `output_file_exists`, `has_section`, `line_count`, `no_solution_language`). Fixtures live in `evals/fixtures/` (ticket markdown files); golden outputs in `evals/golden/`. Defaults: 3 trials per case, 120s timeout. NOTE: `run_eval.py`'s `execute_single` is a stub — actual agent invocation is a placeholder, so the harness scaffolds scoring but does not yet run a live agent.

**Evidence:**

```
"defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 },
"cases": [ { "id": "case_001", "name": "questions_happy_path", "phase": "questions",
  "prompt": "Generate questions for the following ticket.",
  "context": { "files": ["fixtures/ticket_rest_endpoint.md"], ... },
  "assertions": [ { "type": "programmatic",
    "check": "output_file_exists('questions.md')", "weight": 1.0 }, ... ] } ]
```

— `evals/suite.json:11-30`

```
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
messages = build_messages(case)
result.output = ""
```

— `scripts/run_eval.py:117-133` (execution is a stub)

`run_loop.sh` is the optimization driver:

```
# Usage: ./run_loop.sh <skill_path> <eval_suite> [max_iterations] [target_score]
# Example: ./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85
```

— `run_loop.sh:6-10`

Fixtures available: `ticket_websocket.md`, `ticket_15_acceptance_criteria.md`, `ticket_multi_tenancy.md`, `ticket_rest_endpoint.md` (`evals/fixtures/`).

**Dependencies:** `grade.py` scores `run_eval.py` output; `report.py`/`diagnose.py`/`revise.py` consume grades; `run_loop.sh` ties them together.
**Implicit contracts:** To be testable, a new argocd skill needs: (a) ≥1 case in `evals/suite.json` with a `phase`, `prompt`, `context.files` fixture, and weighted `assertions`; (b) any custom check must be added to the `CHECKS` registry in `grade.py` (or use `type: script`/`llm_judge`); (c) optionally a fixture in `evals/fixtures/`.

## Q13: Is there a validation command or linter that checks SKILL.md frontmatter and directory structure, and how is it invoked?

**Answer:** NOT FOUND — there is no SKILL.md frontmatter linter or structure validator in this repo. `scripts/` contains only eval-pipeline tools: `run_eval.py`, `grade.py`, `report.py`, `diagnose.py`, `revise.py`, `check_scope.py`. `check_scope.py` validates that an *implementation* stayed within its allowed file list (parsing `impl-log.md` vs a worktree session manifest) — it does not validate skill frontmatter or directory structure. `run_eval.py`'s `load_suite()` validates the *eval suite JSON* shape (requires `name`, `cases`; each case needs `id`, `prompt`, `assertions`), not SKILL.md files. Any SKILL.md frontmatter validation would be performed by the external `skill-creator` skill (outside repo).

**Evidence:**

```
def check_scope(impl_log_path: str, worktree_session_path: str) -> dict:
    """Check if implementation stayed within scope."""
```

— `scripts/check_scope.py:39-40` (validates impl scope, NOT skill frontmatter)

```
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
```

— `scripts/run_eval.py:47-50` (validates the eval suite JSON, not SKILL.md)

scripts/ inventory: `check_scope.py, diagnose.py, grade.py, report.py, revise.py, run_eval.py` — no `validate*`/`lint*` script.

**Dependencies:** None for skill validation.
**Implicit contracts:** Frontmatter correctness is currently enforced only by convention + the harness's own parsing at load time. A new argocd skill cannot be "linted" in-repo; correctness is verified by matching the existing skills' frontmatter shape (Q3).

## Q14: How does skill trigger/invocation get logged or surfaced (hooks, harness logging) so the argocd skill's auto-invocation behavior can be verified after creation?

**Answer:** NOT FOUND in repo. There is no `.claude/settings.json` or `.claude/settings.local.json` in this worktree, and no `hooks/` directory under the project. (The global `~/.agents/hooks/pre-tool-memory.sh` PreToolUse hook mentioned in global CLAUDE.md lives OUTSIDE `REPO_ROOT` and was not read per the scope firewall.) The eval harness `run_eval.py` is designed to capture `tool_calls`, `transcript`, and `tokens` per trial (the `ExecutionResult` dataclass), which is where invocation behavior *would* be observed once the execution stub is implemented — but it is currently a placeholder returning empty traces.

**Evidence:**

```
$ find .claude -name 'settings*.json'   # (no results)
$ find . -type d -name hooks            # (no results under REPO_ROOT)
```

— filesystem search under `REPO_ROOT`

```
@dataclass
class ExecutionResult:
    case_id: str
    trial_id: int
    output: str = ""
    files: list = field(default_factory=list)
    duration_ms: float = 0.0
    tokens: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
```

— `scripts/run_eval.py:19-29` (where invocation/tool traces would be captured)

**Dependencies:** Harness logging is the only in-repo surfacing mechanism, and it is stubbed. Live harness hooks (PreToolUse) are global, outside repo scope.
**Implicit contracts:** Auto-invocation is driven by the `description` field (Q7); there is no in-repo logging to verify it post-creation. Verification would rely on the (not-yet-implemented) `run_eval.py` transcript capture, or on external harness logging outside the repo.

---

## Discovered Patterns

- **Thin-skill / fat-agent split.** Most phase skills (`qrspi-research`, `qrspi-design`, `qrspi-plan`, `qrspi-structure`, `qrspi-worktree`, `qrspi-pr`, `qrspi-questions`, `qrspi-implement`) are 25–35-line thin wrappers whose only job is to spawn a `subagent_type: qrspi-<phase>` agent with an input contract. The real prompt content lives in `.claude/agents/qrspi-*.md`. Only `qrspi-ticket` (119 lines) and `qrspi-work` (730 lines) carry substantial in-skill logic. (`.claude/skills/qrspi-research/SKILL.md:11`)
- **Two distinct frontmatter shapes.** Skill files use `name/description/command/argument-hint/allowed-tools`. Agent files use `name/description/model/claude.tools`. An argocd skill must use the SKILL shape; if it also gets a dedicated agent, that file uses the agent shape.
- **Templates as single source of truth.** Output formats live in `.qrspi/templates/`; skills/agents reference them rather than embedding (`README.md:110`).
- **Input-contract spawning.** Orchestrator passes labelled `KEY = value` inputs with absolute worktree-prefixed paths to sub-agents (`.claude/skills/qrspi-work/SKILL.md:134-139`).
- **HARD STOP safety pattern.** Both the agent prompts and `qrspi-work` carry an identical "HARD STOP: Infrastructure Errors" block forbidding chmod/sudo/config-rewrite workarounds (`qrspi-work/SKILL.md:709-728`; `agents/qrspi-research.md:56-58`). A CLI-wrapping argocd skill should adopt this for auth/cluster-access failures.
- **CLI discipline.** "Never run raw `git` when a `gt` equivalent exists" (`qrspi-work/SKILL.md:637`) and scoped `allowed-tools` like `Bash(pwd:*)` show the repo prefers narrowly-scoped shell access — relevant precedent for scoping `Bash(argocd:*)`.
- **Universal `qrspi-` prefix.** Every existing skill is prefixed `qrspi-`; an `argocd` skill is the first non-workflow, non-prefixed skill — a new precedent with no direct template.

## Inconsistencies

- **`qrspi-work` violates the documented body budget.** `docs/qrspi_claude_code_guide.md:592` states every `SKILL.md` should be "under 500 lines"; `qrspi-work/SKILL.md` is 730 lines. So the 500-line guidance is documented but not honored, and not enforced by any tool (Q8).
- **`skill-creator` is referenced but absent.** `.claude/agents/qrspi-structure.md:41` instructs "invoking skill-creator" as a validation step, and the questions assume it lives here, but no `skill-creator` exists under `REPO_ROOT`. It is a global/plugin skill outside project scope.
- **Eval suite ≠ skill set.** The suite covers 8 phases but omits `qrspi-ticket` and `qrspi-work` (`evals/suite.json` cases), so two real skills have no eval coverage despite the harness existing.
- **Eval execution is a stub.** `run_eval.py:117-133` never invokes a live agent (`result.output = ""`); the grading/reporting pipeline is built on top of an execution layer that produces empty results, so "eval scores" cannot currently be produced end-to-end (Q12, Q14).
- **Co-author trailer model drift.** `qrspi-work` commit templates hardcode `Claude Opus 4.7` (e.g. `SKILL.md:146`), a version string that may diverge from the actual model used — a maintenance inconsistency, not a functional one.
- **questions.md premise mismatch.** Several questions assume in-repo `skill-creator`, a "5000 token" body limit, and token-measurement tooling. The repo has none of these — only a documented 500-line/~40-instruction guideline and no measurement script (Q8, Q13).
