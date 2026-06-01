# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

> Scope note: Several questions target the **skill-creator** skill, its eval loop, the
> `references/scripts/assets` agentskills.io layout, and a documented `session_id` capture
> pattern. The skill-creator skill is NOT present inside `REPO_ROOT` — it is a global skill
> outside project scope (only an incidental mention exists in
> `.claude/agents/qrspi-structure.md:41`). Those questions are answered against the closest
> in-repo equivalents (this repo's own skill conventions and its `evals/`+`scripts/` harness),
> with the gap flagged explicitly. See Inconsistencies.

## Q1: How does the skill-creator skill consume an initial description and emit the SKILL.md plus references/scripts/assets layout, and where in its flow is the agentskills.io directory structure enforced?

**Answer:** NOT FOUND inside `REPO_ROOT`. There is no `skill-creator` skill, no SKILL.md for
it, and no `references/`+`scripts/`+`assets/` scaffolding logic anywhere under
`/workspaces/qrspi/.worktrees/RUS-9`. The only reference to skill-creator in the repo is an
incidental mention as a validation pass in the implement-phase guidance:

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:41`

The closest in-repo analog to "consume a description → emit a SKILL.md" is the existing skill
layout: every skill is a single `SKILL.md` under `.claude/skills/<name>/`, and the
qrspi-questions skill body documents the "read input → produce artifact" pattern at
`docs/qrspi_claude_code_guide.md:96-119`. Only one skill in the repo uses a `references/`
subdirectory: `.claude/skills/qrspi-work/references/review-cascade.md`.

Search queries attempted: `find . -iname "*skill-creator*"`, `grep -rl "skill-creator"`,
`grep -rni "references/\|assets\|agentskills"`.
**Dependencies:** none in-repo.
**Implicit contracts:** none discoverable in-repo.

## Q2: How do existing skills in this repo split content between the SKILL.md body and the `references/` directory, and what is the convention for cross-linking from the body into reference files?

**Answer:** The dominant convention is a **thin SKILL.md wrapper that delegates to an agent
definition** rather than a SKILL.md/references split. All eight qrspi-* phase skills are thin
wrappers whose body says the prompt content lives in the corresponding `.claude/agents/*.md`:

```
# /qrspi-research
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:9-11`

Only `qrspi-work` uses a `references/` directory. Its SKILL.md is the orchestration body and
it offloads one large decision table into a reference file. The repo's only example of a
references/ file is `.claude/skills/qrspi-work/references/review-cascade.md` (a 64-line cascade
ruleset). Cross-linking convention observed: references are pulled in by the workflow logic /
agent prompt, not via an inline markdown hyperlink in the body — I found no explicit
`[link](references/...)` from a body into its reference file. The split rationale is "big
secondary detail tables/logic live in references; the body stays orchestration-level."
**Dependencies:** `.claude/skills/qrspi-*/SKILL.md` depend (by reference) on `.claude/agents/qrspi-*.md`.
**Implicit contracts:** SKILL.md basename directory == `name` frontmatter == agent `name` (e.g. `qrspi-research`); the wrapper spawns `subagent_type: qrspi-research`.

## Q3: What YAML frontmatter fields and value formats are used by existing skills in this repo (name, description, and any others), and which are required versus optional?

**Answer:** Frontmatter fields observed across all `.claude/skills/*/SKILL.md`: `name`,
`description`, `command`, `argument-hint`, `allowed-tools`. Every skill carries all five
except where noted. Example:

```
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-6`

Value formats:
- `name`: kebab-case identifier matching the directory (`qrspi-design`).
- `description`: single line normally; `qrspi-work` quotes it because it contains a colon and embedded quotes — `.claude/skills/qrspi-work/SKILL.md:3`.
- `command`: slash form (`/qrspi-design`).
- `argument-hint`: angle-bracket placeholders (`<ticket-id>`, `<ticket-id> <slice-number>`, `<initial description>`).
- `allowed-tools`: comma-separated tool list; supports scoped Bash (`Bash(pwd:*)`) and namespaced MCP tools (`mcp__linear-russelltsherman__get_issue`).

Agent definition files use a DIFFERENT frontmatter shape — `name`, `description`, `model`, and
a nested `claude: { tools: ... }` block (`.claude/agents/qrspi-research.md:1-6`). Required vs
optional is not enforced by any in-repo validator (see Q7/Q10); "required" is convention only.
The questions phase rules note skills must stay under 500 lines (`docs/qrspi_claude_code_guide.md:592`).
**Dependencies:** consumed by the Claude Code skill/agent loader (external runtime).
**Implicit contracts:** `name` must equal the containing directory name; `command` must equal `/` + `name`.

## Q4: What is the canonical directory location and naming convention for a new skill in this repo — `.claude/skills/<name>/SKILL.md` — and is there a separate agent definition wrapper expected under `.claude/agents/`?

**Answer:** Confirmed. Skills live at `.claude/skills/<name>/SKILL.md`; `<name>` is kebab-case
and equals the `name` frontmatter value. There are 10 skill directories
(qrspi-design, qrspi-implement, qrspi-plan, qrspi-pr, qrspi-questions, qrspi-research,
qrspi-structure, qrspi-ticket, qrspi-work, qrspi-worktree).

The agent/skill split is the established architecture: phase skills are thin wrappers and the
real prompt lives at `.claude/agents/<name>.md`. There are 8 agent definitions
(qrspi-design, qrspi-implement, qrspi-plan, qrspi-pr, qrspi-questions, qrspi-research,
qrspi-structure, qrspi-worktree). Note `qrspi-ticket` and `qrspi-work` have SKILL.md but NO
agent file — they are self-contained skills (not phase agents). The project CLAUDE.md states
the convention authoritatively:

```
- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
```

— `.claude/.../CLAUDE.md` (project instructions). Note the worktree's `.claude/CLAUDE.md` says
agents live in `.qrspi/agents/` — see Inconsistencies.
**Dependencies:** loader resolves `.claude/skills/` and `.claude/agents/`.
**Implicit contracts:** a phase skill REQUIRES a same-named agent under `.claude/agents/`; a self-contained skill (ticket/work) does not.

## Q5: How does the skill-creator eval loop persist intermediate state (draft skill, eval results, scores) between iterations, and where are those artifacts written?

**Answer:** NOT FOUND for skill-creator specifically (no such loop in-repo). The repo's own
eval optimization loop is `run_loop.sh`, which persists per-iteration state to `results/<version>/`:

```
VERSION="v${i}"
OUTPUT_DIR="results/${VERSION}"
```

— `run_loop.sh:33-34`

Per iteration it writes: `results/v<i>/results.json` (raw execution output —
`scripts/run_eval.py:209-211`), `results/v<i>/grades.json` (scores —
`scripts/grade.py:362-365`), `results/v<i>/diagnosis.json` (`run_loop.sh:97-99`), and revises
the skill file in place (`scripts/revise.py`, `--output "$SKILL_PATH"`, `run_loop.sh:103-106`).
Cross-iteration history is aggregated into `results/report.json` and `results/ledger.json` by
`scripts/report.py` (`generate_report` + `update_ledger`, `report.py:188-200`). The "draft
skill" between iterations is the skill file itself, mutated in place; the previous version is
recoverable only via git (the rollback is a TODO comment: `run_loop.sh:88`).
**Dependencies:** `run_loop.sh` → `run_eval.py` → `grade.py` → `diagnose.py` → `revise.py` → `report.py`.
**Implicit contracts:** version dirs are named `v<n>`; `report.py` discovers them by sorted iteration over `results/` looking for `grades.json` (`report.py:19-30`).

## Q6: How are session IDs and conversation state captured and reused across multi-step invocations elsewhere in this repo (the documented `session_id` capture pattern), so the skill's session-management guidance matches existing usage?

**Answer:** NOT FOUND. There is no `session_id` / `sessionId` / `--resume` / `--continue`
capture pattern anywhere in `REPO_ROOT` (grep returned no matches in the workflow JS or
elsewhere). What DOES exist is a different mechanism for carrying state across multi-step
(slice-by-slice) invocations: a **"Notes for next session"** hand-off threaded through the
implementation loop in the batch workflow. Each slice's commit worker reads the notes from
that slice's `impl-log.md` and the orchestrator passes them as `PREVIOUS_NOTES` to the next
slice:

```
// the "Notes for next session" so the next slice gets PREVIOUS_NOTES.
...
previousNotes = commit.notesForNext || ''
```

— `.claude/workflows/qrspi-batch-v2.js:339,351`; consumed as `PREVIOUS_NOTES` at `qrspi-batch-v2.js:326-327`.

State is otherwise persisted as files on disk (the `.qrspi/<ticket-id>/` artifacts) and via
git branches per slice, not via an SDK session id. "Resume" in this repo means
"skip a phase whose artifact already exists" (`qrspi-batch-v2.js:154`).
**Dependencies:** `qrspi-batch-v2.js` ↔ `impl-log.md` artifact ↔ Graphite branches.
**Implicit contracts:** continuity between invocations rides on disk artifacts + the free-text "Notes for next session" block in impl-log.md, NOT on an opaque session token.

## Q7: How are the SKILL.md size limits (under 500 lines / 5000 tokens) measured and verified in this repo, and is there an existing check or eval that fails when a SKILL.md exceeds them?

**Answer:** No automated SKILL.md size check exists in-repo. The 500-line guidance is
documentation-only:

```
The skill prompt may be too long. Check that each `SKILL.md` is under 500 lines and under ~40 distinct instructions. The instruction budget ceiling is real.
```

— `docs/qrspi_claude_code_guide.md:592`

I found NO mention of a 5000-token SKILL.md limit (the only token figure is the eval runtime
budget "128k max tokens", `docs/eval-system.md:28` / `evals/suite.json` defaults). A generic
`line_count(filename, max_lines, result)` check exists in the grader, but it measures an
agent's OUTPUT artifact, not a SKILL.md file, and is parameterized per eval case:

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
```

— `scripts/grade.py:35-40`. Search queries: `grep -rni "500\|5000\|max_lines\|token" scripts/`.
**Dependencies:** `grade.py` CHECKS registry (`grade.py:146-157`).
**Implicit contracts:** size limits are reviewer-enforced by hand; "under 500 lines / ~40 instructions" is the stated ceiling. No 5000-token rule is codified here.

## Q8: What does the skill-creator do when a generated skill fails one or more acceptance checks (e.g., missing required reference files or invalid frontmatter) — does it retry, halt, or report?

**Answer:** NOT FOUND for skill-creator (not in repo). The repo's own optimization loop
(`run_loop.sh`) behavior on failure: it does ALL THREE depending on condition.
1. **Halt-on-success:** if the test score meets target it breaks (`run_loop.sh:70-74`).
2. **Rollback + retry:** if a regression > 0.05 vs previous score is detected, it logs the
   regression, "rolls back" (currently a TODO comment, not real), and `continue`s to the next
   iteration (`run_loop.sh:77-91`).
3. **Diagnose + revise + retry:** otherwise it runs `diagnose.py` then `revise.py` and loops
   (`run_loop.sh:93-111`), up to `MAX_ITER` (default 5, `run_loop.sh:14`).

```
if [ "$TARGET_MET" = "1" ]; then echo "  ✓ Target score reached!"; break; fi
...
if [ "$REGRESSED" = "1" ]; then ... continue; fi
```

— `run_loop.sh:70-91`

For an individual eval case, a failed programmatic assertion is recorded with
`passed: False` + evidence and contributes 0 weight to the case score; an unknown check yields
`passed: None` (skipped with warning) — `scripts/grade.py:182-205`. It reports, never throws.
**Dependencies:** `run_loop.sh` ← `grade.py`/`diagnose.py`/`revise.py`/`report.py`.
**Implicit contracts:** loop is bounded by MAX_ITER; regression threshold 0.05 (loop) / 0.2 (report regression flag, `report.py:46`).

## Q9: How do existing skills document experimental or version-gated features (analogous to the experimental agent-teams behavior), and where is that "experimental status" labeling placed?

**Answer:** NOT FOUND. There is no "experimental" / "version-gated" / "agent-teams" labeling
convention in any SKILL.md or `references/` file under `REPO_ROOT`. The only versioning signal
observed is a `version` field in the eval suite manifest (`evals/suite.json:3`,
`"version": "0.1.0"`) and version directories `v1..vN` in `results/` — neither is an
experimental-feature gate on a skill. Skills do encode *lifecycle ordering / gating* in prose
(e.g. "Use after research is approved", `.claude/skills/qrspi-design/SKILL.md:3`) and the
CLAUDE.md review-gate state machine, but that is phase sequencing, not experimental status.
Search queries: `grep -rni "experimental\|version-gated\|agent-teams\|beta\|preview"` (no
matches in `.claude/skills/`).
**Dependencies:** none.
**Implicit contracts:** none — the repo has no established experimental-labeling pattern to mirror.

## Q10: What test or eval mechanism verifies a skill's frontmatter validity and directory structure conformance, and how is it invoked?

**Answer:** No frontmatter-validity or directory-conformance test exists. The eval harness
validates the SUITE schema and CASE schema (not skill files) at load time:

```
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
...
case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:47-56`

`run_eval.py` reads the skill file as raw text only (`load_skill`, `run_eval.py:61-64`) and
hashes it for versioning (`run_eval.py:155`); it never parses or validates YAML frontmatter.
Invocation: `python3 scripts/run_eval.py --skill <path> --suite <suite.json> --output <dir>`
(`run_eval.py:217-236`), typically driven by `run_loop.sh:43-48`. The one structural assertion
in the suite is `scripts/check_scope.py` (verifies an implementation only touched allowed
files), invoked as a `--log`/`--allowed` CLI script and intended as a `script`-type assertion —
but note `run_script_check` is a stub returning `passed: None` (`grade.py:230-241`).
**Dependencies:** `run_eval.py` (suite/case schema) ; `check_scope.py` (scope assertion).
**Implicit contracts:** suites need `{name, cases}`; cases need `{id, prompt, assertions}`. Skill frontmatter conformance is unenforced by tests.

## Q11: How does the skill-creator measure skill description triggering accuracy, and what command or harness runs that benchmark?

**Answer:** NOT FOUND. No description-triggering-accuracy benchmark exists in `REPO_ROOT`.
There is no classifier, no "does this description fire on these prompts" harness, and no
trigger-precision metric. The eval harness measures task-output quality (weighted programmatic
assertions + LLM-judge + script checks aggregated into train/test scores with stddev) — not
triggering. Relevant scoring code: `score_case`/`score_suite` (`scripts/grade.py:246-277`) and
the loop's target/regression gates (`run_loop.sh:59-91`). The LLM-judge and script paths that
might host such a check are stubs (`grade.py:208-241`, return `passed: None`). The closest
"description" handling is that descriptions are just frontmatter text consumed by the external
loader (Q3). Search queries: `grep -rni "trigger\|triggering\|description accuracy\|classifier\|precision\|recall"` (no relevant matches).
**Dependencies:** none.
**Implicit contracts:** none — accuracy of description triggering is not measured in-repo.

## Q12: How are skill-creator eval runs and their pass/fail results logged or surfaced (console output, written report file, scores), so the new skill's build can be confirmed against the acceptance criteria?

**Answer:** Logging/surfacing in the repo's eval loop happens via BOTH console output AND
written JSON files (no skill-creator-specific path exists).

Console: `run_eval.py` prints per-execution `[n/total] case trial OK|ERROR (ms)`
(`run_eval.py:187`); `grade.py` prints train/test scores ± stddev and the train-test gap
(`grade.py:367-370`); `report.py` prints a banner summary with plateau/overfitting ALERTs
(`report.py:159-169`); `run_loop.sh` prints per-iteration banners and the score-vs-target line
(`run_loop.sh:66`).

Written files (under `results/`): `results/<version>/results.json` (raw,
`run_eval.py:209-211`), `results/<version>/grades.json` (per-case + suite scores, train/test
split, gap — `grade.py:350-365`), `results/<version>/diagnosis.json`, and the cross-version
`results/report.json` + `results/ledger.json` (`report.py:154-156,188-189`). Acceptance is
expressed as promotion criteria — no test regression, zero large case drops, train-test gap
<= 0.1:

```
"acceptable_gap": entry["train_test_gap"] <= 0.1,
```

— `scripts/report.py:77-90`
**Dependencies:** `results/` directory consumed by `report.py:14-32`.
**Implicit contracts:** a build is "confirmed" when `grades.json` test_score meets the `run_loop.sh` TARGET_SCORE (default 0.85, `run_loop.sh:15`) and `report.py` promotion criteria pass.

---

## Discovered Patterns

- **Thin-skill / fat-agent split.** Phase skills under `.claude/skills/<name>/SKILL.md` are
  delegating wrappers; the substantive prompt lives in `.claude/agents/<name>.md`
  (`.claude/skills/qrspi-research/SKILL.md:9-11`). Two skills (qrspi-ticket, qrspi-work) are
  self-contained with no agent file.
- **Two distinct frontmatter schemas.** Skills use `name/description/command/argument-hint/allowed-tools`;
  agents use `name/description/model` + nested `claude.tools` (`.claude/agents/qrspi-research.md:1-6`).
- **`references/` for offloaded detail.** Only `qrspi-work` uses it
  (`references/review-cascade.md`); the body stays orchestration-level.
- **File-and-branch state, not session tokens.** Cross-invocation continuity rides on
  `.qrspi/<ticket-id>/` artifacts, Graphite per-slice branches, and a free-text
  "Notes for next session" block in `impl-log.md` (`qrspi-batch-v2.js:339-351`).
- **Versioned eval results.** `results/v<n>/{results,grades,diagnosis}.json` + aggregate
  `report.json`/`ledger.json`; promotion gated on test score, regressions, and train-test gap.
- **Stubbed grading backends.** LLM-judge and script-check graders return `passed: None`
  pending real integration (`grade.py:208-241`); `run_eval.py:execute_single` is also a
  placeholder (`run_eval.py:99-137`). The harness scaffolding is real; the execution/judging
  is not yet wired to a model runtime.
- **Self-application is implied.** The implement-phase guidance lists "invoking skill-creator"
  as a validation pass (`.claude/agents/qrspi-structure.md:41`), implying the project expects
  skill-creator to exist as an external/global tool.

## Inconsistencies

- **skill-creator is out of scope.** Q1, Q5, Q7, Q8, Q11, Q12 reference a skill-creator skill,
  its eval loop, and the `references/scripts/assets` agentskills.io layout. None of that lives
  in `REPO_ROOT`; skill-creator is a global skill. Those questions were answered against the
  repo's own `evals/`+`scripts/` harness as the nearest analog, with the gap flagged.
- **Agent location doc conflict.** The project `.claude/CLAUDE.md` (root checkout) states
  "Phase agent definitions live in `.claude/agents/`". The WORKTREE copy
  `/workspaces/qrspi/.worktrees/RUS-9/.claude/CLAUDE.md` says "Agent prompt definitions live in
  `.qrspi/agents/`". The actual files are in `.claude/agents/`; `.qrspi/agents/` does not exist.
  The worktree CLAUDE.md is stale.
- **No 5000-token SKILL.md rule in-repo.** Q7 assumes an "under 500 lines / 5000 tokens" limit.
  Only the 500-line/~40-instruction guidance exists (`docs/qrspi_claude_code_guide.md:592`); no
  5000-token figure is codified anywhere (the 128k token figure is the eval runtime budget,
  `docs/eval-system.md:28`).
- **No experimental-status convention (Q9).** Nothing in-repo labels experimental/version-gated
  features; the premise has no codebase precedent to mirror.
- **No frontmatter/trigger validation (Q3, Q10, Q11).** "Required vs optional" frontmatter and
  description-triggering accuracy are conventions/aspirations, not enforced by any test or eval.
- **Two batch workflows coexist.** `.claude/workflows/qrspi-batch.js` and `qrspi-batch-v2.js`
  both exist; the v2 file carries the current resume/notes logic cited above. Unclear which is
  canonical — both are present with no deprecation marker.
- **`run_loop.sh` example path is stale.** Its usage example points at
  `.qrspi/agents/01-questions.md` (`run_loop.sh:10`), a path/naming that no longer exists
  (agents are now `.claude/agents/qrspi-questions.md`).
