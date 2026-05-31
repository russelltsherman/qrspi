# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: What is the existing on-disk layout of the `using-graphite-cli` skill, and what files (SKILL.md, references/, scripts/, assets/) already exist versus need to be created?

**Answer:** There is NO `using-graphite-cli` skill on disk anywhere in the repo. A recursive search for `*using-graphite-cli*` and for any path containing `using-graphite-cli` under `REPO_ROOT` returned nothing. The skills directory is `.claude/skills/` and contains exactly 10 skills, all prefixed `qrspi-`:

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

Only `qrspi-work` has a `references/` subdirectory. No skill has a `scripts/` or `assets/` subdirectory. So for a new `using-graphite-cli` skill, **everything must be created**: the directory `.claude/skills/using-graphite-cli/`, its `SKILL.md`, and any `references/` content. Note there IS an existing eval file `evals/graphite-evals.json` (`skill_name: "graphite"`) — see Q9/Q10.

**Evidence:**

```
$ find . -path "*using-graphite-cli*"   # (no output)
$ find .claude/skills -type d
.claude/skills/qrspi-work/references   # only references dir present
```

— `find` over `/workspaces/qrspi/.worktrees/RUS-6/.claude/skills`
**Dependencies:** Skills are discovered by Claude Code from `.claude/skills/<name>/SKILL.md`. No build step.
**Implicit contracts:** Skill directory name conventionally matches the frontmatter `name` field (e.g., dir `qrspi-work` ↔ `name: qrspi-work`).

## Q2: How does the skill-creator skill ingest source material and emit a finished skill, and what inputs does it expect to produce SKILL.md plus the references/ directory?

**Answer:** NOT FOUND in repo scope. There is no `skill-creator` skill or supporting script under `REPO_ROOT`. A search for `*skill-creator*` directories returned nothing; the only textual mentions of "skill-creator" are: (a) `.qrspi/RUS-6/questions.md` (the questions artifact itself), and (b) `.claude/agents/qrspi-structure.md:41`, which references it only as an example validation pass — not a definition:

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:41`

The `skill-creator` skill exists in the global Claude Code environment (it appears in the session's available-skills list), but its definition lives outside `REPO_ROOT` (in the global `~/.claude/` skill set) and is therefore **out of scope** for this research — its ingestion mechanism and input contract cannot be verified from repo files.
**Dependencies:** Out of project scope.
**Implicit contracts:** None observable in-repo.

## Q3: What frontmatter fields and value constraints does the agentskills.io / Anthropic skill standard require in SKILL.md (name, description, and any others), and how are they validated in this repo?

**Answer:** No formal schema or validation script exists in the repo. The de-facto standard is inferred from the 10 existing SKILL.md frontmatter blocks. Every one uses these YAML fields between `---` fences at the top of the file:

- `name` — matches the directory name (e.g., `qrspi-research`).
- `description` — natural-language trigger guidance; usually a plain scalar, but quoted with `"..."` when it contains special characters (`qrspi-work` and the inline-comma descriptions). Often includes explicit "Use when…" / "Trigger on…" phrasing.
- `command` — slash command form, e.g., `/qrspi-research`.
- `argument-hint` — e.g., `<ticket-id>` or `<initial description>`.
- `allowed-tools` — comma-separated tool allowlist (the tool lockdown).

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

`qrspi-ticket` differs: its `allowed-tools` is a broad list (`Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue`) — `.claude/skills/qrspi-ticket/SKILL.md:1-8`.
**Dependencies:** Consumed by Claude Code's skill loader (outside repo). No in-repo validator.
**Implicit contracts:** `name` == directory name; `allowed-tools` is the security boundary (e.g., `qrspi-research` and `qrspi-questions` deliberately exclude Linear MCP / Glob-Grep-Bash as firewalls — see `.claude/skills/qrspi-work/SKILL.md:575-604`). `Bash(pwd:*)` shows tool-scoping syntax (restrict Bash to a command prefix).

## Q4: What is the canonical directory structure (`SKILL.md` + optional `references/`, `scripts/`, `assets/`) the standard pattern expects, and how do other skills in this repo organize these subdirectories?

**Answer:** The canonical layout is `.claude/skills/<skill-name>/SKILL.md` with an optional `references/` subdirectory holding supplementary `.md` files. The ONLY example of a multi-file skill is `qrspi-work`, which keeps its main file plus one reference:

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
```

No skill in the repo uses `scripts/` or `assets/` subdirectories. (Eval scripts live in the top-level `scripts/`, not inside any skill.) The QRSPI phase agents follow a split pattern unrelated to skills: thin SKILL.md wrapper + detailed prompt in `.claude/agents/qrspi-<phase>.md` (see Q5).
**Evidence:** `find .claude/skills -type d` output (see Q1).
— `/workspaces/qrspi/.worktrees/RUS-6/.claude/skills/`
**Dependencies:** None — directory layout only.
**Implicit contracts:** `references/` files are progressively disclosed: SKILL.md instructs the agent to read them on demand rather than inlining (see Q6).

## Q5: Where is the skill description text consumed for trigger matching, and what existing description format do comparable skills in this repo use?

**Answer:** Trigger matching is performed by Claude Code's skill loader (outside `REPO_ROOT`); the in-repo source of truth is the `description` field in each SKILL.md frontmatter. The richest, most trigger-oriented example is `qrspi-work`, which packs the use-case, concrete examples, and multiple phrasings into one description:

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

Comparable skills use a shorter two-part format: one sentence describing what it does + one "Use when/after …" sentence, e.g. `qrspi-questions` ("Generate 8-15 targeted technical questions … Use when starting a new QRSPI feature workflow or when the user says \"questions for\" a ticket.") — `.claude/skills/qrspi-questions/SKILL.md:3`.
**Dependencies:** Claude Code loader (out of scope) reads `description` for auto-invocation.
**Implicit contracts:** Descriptions front-load concrete trigger phrases and example invocations; quoting is required when the value contains `:`, `'`, or commas that would otherwise break YAML.

## Q6: How are `references/` files referenced from within SKILL.md (relative paths, link syntax, progressive-disclosure pattern), based on existing multi-file skills?

**Answer:** The single example (`qrspi-work`) references its `references/` file by **bare relative path in prose**, not as a markdown link, and instructs the agent to read it on demand (progressive disclosure):

```
c. Read `references/review-cascade.md` for cascade logic.
d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
```

— `.claude/skills/qrspi-work/SKILL.md:272-273`

The path is relative to the skill directory (`references/review-cascade.md`), backtick-wrapped, and the surrounding text tells the agent when to load it. The referenced file is a self-contained markdown doc with its own headings and tables (`.claude/skills/qrspi-work/references/review-cascade.md:1-64`).
**Dependencies:** The agent reading SKILL.md must resolve `references/` relative to the skill's own directory.
**Implicit contracts:** Reference files are loaded only when the described condition occurs (keeps the main SKILL.md lean) — a progressive-disclosure convention.

## Q7: What is the measured token count and line count of comparable SKILL.md files in this repo, so the new SKILL.md can stay under the 500-line / 5000-token acceptance criterion?

**Answer:** Measured line and byte counts (`wc -l`, `wc -c`). No token counter exists in-repo, so bytes are the proxy (rough rule ≈ 4 bytes/token):

| SKILL.md | Lines | Bytes | ≈ tokens (bytes/4) |
|---|---|---|---|
| qrspi-structure | 25 | 1111 | ~278 |
| qrspi-worktree | 25 | 1063 | ~266 |
| qrspi-plan | 26 | 1116 | ~279 |
| qrspi-questions | 26 | 1455 | ~364 |
| qrspi-research | 26 | 1240 | ~310 |
| qrspi-design | 28 | 1514 | ~379 |
| qrspi-pr | 28 | 1192 | ~298 |
| qrspi-implement | 35 | 2107 | ~527 |
| qrspi-ticket | 119 | 4883 | ~1221 |
| qrspi-work | 730 | 32763 | ~8191 |

The phase wrappers are tiny (25-35 lines). The two outliers are `qrspi-ticket` (119 lines, single-file conversational skill) and `qrspi-work` (730 lines / ~8k tokens — the only file that EXCEEDS a 500-line / 5000-token budget, and it offloads only a small slice to `references/`). The `references/review-cascade.md` is 64 lines.
**Evidence:** `wc -l` / `wc -c` over `.claude/skills/*/SKILL.md`.
— `/workspaces/qrspi/.worktrees/RUS-6/.claude/skills/`
**Dependencies:** None.
**Implicit contracts:** Thin-wrapper skills delegate heavy content to `.claude/agents/qrspi-<phase>.md` (e.g., `qrspi-research/SKILL.md:11` says "All prompt content lives in `.claude/agents/qrspi-research.md`"), keeping each SKILL.md small.

## Q8: How does the repo's tooling or convention handle the boundary between content that belongs in SKILL.md versus content that must move to `references/` (e.g., full command reference, edge cases)?

**Answer:** No tooling enforces this boundary; it is a convention observed in two forms. (1) **Wrapper/agent split** — phase SKILL.md files are thin dispatchers that move all operational detail into `.claude/agents/qrspi-<phase>.md`:

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:11`

(2) **references/ offload** — `qrspi-work` keeps the main state-machine logic inline but moves the self-contained, conditionally-needed "cascade rules" decision table into `references/review-cascade.md`, loaded only when planning-review feedback arrives (`.claude/skills/qrspi-work/SKILL.md:272`). The pattern: keep the always-needed control flow in SKILL.md; move large, situational reference material (decision tables, full command catalogs, edge-case rules) into `references/`.
**Dependencies:** None — editorial convention.
**Implicit contracts:** Content that is needed on every invocation stays inline; content needed only in a specific branch is externalized and loaded on demand.

## Q9: Are there existing validation, lint, or eval checks that would fail if SKILL.md frontmatter is malformed or if required directory entries are missing?

**Answer:** No frontmatter/directory validator exists. The eval harness validates eval **suite JSON**, not SKILL.md structure. `run_eval.py:load_suite` requires the suite to have top-level `name` and `cases`, and each case to have `id`, `prompt`, `assertions`:

```python
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:47-56`

CRITICAL MISMATCH: `evals/graphite-evals.json` uses top-level keys `skill_name` and `evals` (not `name`/`cases`), and its items use `expected_output`/`assertions` with `assertions` as `{text, type}` objects — `evals/graphite-evals.json:1-16`. As written, `run_eval.py` would raise `ValueError` ("Suite missing required fields: {'name','cases'}") if pointed at `graphite-evals.json`. `evals/suite.json` is the conforming schema. `grade.py` has a programmatic check registry (`output_file_exists`, `has_section`, `line_count`, `question_count`, `no_solution_language`, …) but operates on eval result text, not on SKILL.md files (`scripts/grade.py:20-60`).
**Dependencies:** `run_eval.py` → suite JSON; `grade.py` → results JSON + suite; `check_scope.py` → worktree session manifest.
**Implicit contracts:** Eval suites for `run_eval.py` MUST use the `name`/`cases` schema. There is no automated guard for malformed SKILL.md frontmatter.

## Q10: What eval or test pattern does this repo use to verify a skill triggers correctly and behaves as intended, and where would a test for the `using-graphite-cli` skill live?

**Answer:** The repo uses a 5-stage eval pipeline (`docs/eval-system.md:1-12`): `run_eval.py` (execute cases × trials) → `grade.py` (programmatic + LLM-judge + script assertions) → `report.py` (regression/plateau guard) → `diagnose.py` (8 root-cause categories) → `revise.py` (surgical prompt edits). `run_loop.sh` orchestrates one full optimization cycle, taking a `<skill_path>` and `<eval_suite>` and looping until a target score (`run_loop.sh:12-16, 32-112`).

A Graphite eval already exists at `evals/graphite-evals.json` — 5 cases (commit, submit, log, move, sync), each with a `prompt`, `expected_output`, and `{text, type}` assertions like `command_check`, `flag_check`, `safety_check`, `workflow_check` (`evals/graphite-evals.json:1-67`). This is where a `using-graphite-cli` skill's behavioral tests would live / be extended. Note it does NOT currently conform to `run_eval.py`'s expected schema (see Q9).

Triggering is NOT tested by any in-repo harness — there is no trigger-accuracy/description-matching test; `grade.py` checks behavior of produced output, not whether a description fires. The 15-case `evals/suite.json` covers only QRSPI phases, not the graphite skill (`docs/eval-system.md:15-30`).
**Evidence:**

```
$ ./run_loop.sh .claude/skills/using-graphite-cli/SKILL.md evals/graphite-evals.json 5 0.85
```

— pattern per `run_loop.sh:11`
**Dependencies:** Pipeline scripts in `scripts/`, suites in `evals/`.
**Implicit contracts:** A skill's evals are a JSON suite under `evals/`; behavior is graded against weighted assertions; promotion requires no test-score regression and train-test gap ≤ 0.1 (`docs/eval-system.md:49-55`).

## Q11: How does skill-creator's eval loop measure skill performance and trigger accuracy, and what artifacts does it produce?

**Answer:** NOT FOUND for skill-creator specifically (out of scope — see Q2). The repo's OWN eval loop (the closest analog) measures performance via weighted assertion scoring, not trigger accuracy. Per `docs/eval-system.md:41-55`: per-case score = weighted sum of passed assertions / max possible, normalized 0-1; LLM-judge scores on a 1-5 scale normalized to 0-1; per-suite mean with stddev/min/max; train vs. test computed separately (65/35 split, seed 42) to flag overfitting. Artifacts produced per iteration (from `run_loop.sh`): `results/<version>/results.json` (`run_eval.py:209-211`), `results/<version>/grades.json`, `results/<version>/diagnosis.json`, the revised skill file in place, and a final `results/report.json` (`run_loop.sh:43-121`). **Trigger accuracy is NOT measured by any in-repo tooling.**
**Evidence:**

```
[1/4] run_eval.py  → results/v{i}/results.json
[2/4] grade.py     → results/v{i}/grades.json
[3/4] diagnose.py  → results/v{i}/diagnosis.json
[4/4] revise.py    → overwrites SKILL_PATH
final: report.py   → results/report.json
```

— `run_loop.sh:43-121`
**Dependencies:** All five `scripts/*.py` plus `run_loop.sh`.
**Implicit contracts:** Output dir layout is `results/<version>/`; the loop reads `grades.json['test_score']` to decide promotion/stop (`run_loop.sh:59-69`).

## Q12: What logging, output, or reporting does the skill-creator process emit during generation, and where can its results be inspected to confirm the skill was built correctly?

**Answer:** NOT FOUND for skill-creator (out of scope — see Q2). For the repo's own eval/optimization process: `run_eval.py` prints per-execution progress lines (`[n/total] case_id trial=t OK/ERROR (Nms)`) to stdout and writes structured `results.json` (`run_eval.py:161-213`). `run_loop.sh` prints a banner and `[1/4]…[4/4]` step logs plus the score-vs-target line, regression warnings, and rollback notices (`run_loop.sh:19-110`). Results are inspectable under `results/` (one subdir per version) and the final `results/report.json`. A top-level `results/` directory already exists (`ls` at repo root). There is no logging/reporting tied to building a SKILL.md per se — confirmation that a skill was "built correctly" would come from running its eval suite through this pipeline and inspecting `grades.json`.
**Evidence:** `run_eval.py:186-213`, `run_loop.sh:19-121`.
— `/workspaces/qrspi/.worktrees/RUS-6/scripts/run_eval.py`, `/workspaces/qrspi/.worktrees/RUS-6/run_loop.sh`
**Dependencies:** Eval pipeline scripts; output under `results/`.
**Implicit contracts:** Generation/optimization output is human-readable stdout + machine-readable JSON under `results/<version>/`.

---

## Discovered Patterns

- **Thin-wrapper-over-agent split.** Eight of ten QRSPI skills are ~25-35 line SKILL.md wrappers whose only job is to spawn a `subagent_type: qrspi-<phase>` agent; all operational detail lives in `.claude/agents/qrspi-<phase>.md`. The standalone exceptions are `qrspi-ticket` (119 lines, fully self-contained conversational skill) and `qrspi-work` (730-line orchestrator). A new `using-graphite-cli` skill could follow either model.
- **`allowed-tools` as a security firewall.** Tool allowlists are deliberately minimal and used to enforce constraints structurally: `qrspi-research`/`qrspi-questions` exclude Linear MCP and codebase-exploration tools by design (`.claude/skills/qrspi-work/SKILL.md:575-604`). `Bash(pwd:*)` demonstrates command-prefix scoping.
- **Description front-loads trigger phrases.** Descriptions consistently include "Use when…/Use after…" and, for the orchestrator, multiple literal example phrasings. This is the auto-invocation contract.
- **Progressive disclosure via `references/`.** Large situational content is externalized and loaded on demand (the `qrspi-work` → `review-cascade.md` pattern).
- **Templates as single source of truth.** Output formats live in `.qrspi/templates/`; skills/agents reference them rather than inlining (README.md:110).
- **Eval-driven skill iteration.** Every skill is meant to be measurable: a JSON suite under `evals/`, run through the 5-stage `scripts/` pipeline via `run_loop.sh`. A Graphite suite already exists (`evals/graphite-evals.json`).

## Inconsistencies

- **Eval schema mismatch (load-bearing).** `evals/graphite-evals.json` uses top-level `skill_name` + `evals` with `{text, type}` assertion objects, but `scripts/run_eval.py:47-56` requires top-level `name` + `cases` and each case to have `id`/`prompt`/`assertions`. Feeding `graphite-evals.json` to `run_eval.py` as-is would raise `ValueError`. `evals/suite.json` is the conforming format. Any work that runs the existing graphite evals through the harness must reconcile these schemas.
- **No trigger-accuracy measurement.** Q11/Q12 ask about trigger accuracy, but no in-repo tooling measures whether a skill's `description` fires correctly. `grade.py` only grades produced output against assertions. The eval-system doc (`docs/eval-system.md`) never claims trigger testing.
- **`skill-creator` is referenced but absent.** `.claude/agents/qrspi-structure.md:41` names "invoking skill-creator" as a validation step, implying skill authors should use it, yet no skill-creator definition exists in-repo (it lives in the global Claude environment, outside `REPO_ROOT`).
- **Harness is largely stubbed.** `docs/eval-system.md:92-108` documents that agent execution (`run_eval.py:117-137`), LLM-judge integration (`grade.py`), and script-check execution are stubs returning zeros/None, and 17 of 21 fixtures are missing. The pipeline runs end-to-end but currently produces zero scores — relevant if "build the skill" implies running real evals.
- **Budget outlier.** `qrspi-work/SKILL.md` is 730 lines / ~8k bytes-as-tokens, far over a 500-line / 5000-token guideline, despite the project's otherwise-strict thin-wrapper convention — evidence the budget is aspirational, not enforced.
