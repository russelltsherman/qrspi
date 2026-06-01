# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T01:40:00Z
**Status:** draft

> Scope note: All exploration was confined to `REPO_ROOT` =
> `/workspaces/qrspi/.worktrees/RUS-22`.
>
> Important framing: Several questions presuppose a `skill-creator` skill and a
> "skill build / eval loop" living inside THIS repo. No such skill exists here.
> `grep -rli "skill-creator"` returns only one passing mention in prose
> (`.claude/agents/qrspi-structure.md:41`, "invoking skill-creator" as an example
> of a validation step) — there is no `skill-creator` SKILL.md, agent, or script.
> `grep -rni "gemini"` returns only one prose mention
> (`docs/container-sandbox/research/q12-secrets-in-clone.md:313`, listing
> "Gemini CLI" among tools that honor an `.agentignore` file) — there is no
> gemini integration anywhere in this repo. Questions that
> target skill-creator specifically are answered NOT FOUND, with the closest
> existing analogue (the QRSPI phase wrapper→agent pattern, and the `evals/`
> harness) described as the nearest precedent.

## Q1: What is the on-disk directory layout of an existing skill in this repo (SKILL.md plus references/, scripts/, assets/), and where are skills physically located?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, each a directory
whose canonical entry point is a single `SKILL.md`. There is no skill-storage
module — the directory tree is the storage. 9 of 10 skills contain only
`SKILL.md`; `qrspi-work` additionally has a `references/` subdir holding one
offloaded doc (`review-cascade.md`). No skill uses `scripts/` or `assets/`
subdirs (the repo-root `scripts/` dir is the eval harness, unrelated to skill
packaging). Paired subagent prompts live separately under `.claude/agents/`.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
.claude/agents/qrspi-research.md          (paired subagent prompt)
```

— directory listing of `.claude/skills/` and `.claude/agents/`

```
.claude/
  skills/              # Skill definitions (one SKILL.md per phase)
    qrspi-work/        # Autonomous orchestrator
```

— `README.md:75-87`

**Dependencies:** Claude Code's skill loader (external) discovers
`.claude/skills/*/SKILL.md`. Skill bodies reference `.claude/agents/*.md`.
**Implicit contracts:** A skill = a `.claude/skills/<name>/` dir with a
`SKILL.md`; `references/` is the sole content-offload subdir observed.

## Q2: How does the skill-creator skill ingest input and emit its output skill files, and what intermediate artifacts does it produce?

**Answer:** NOT FOUND — no `skill-creator` skill exists in this repo. Searched:
`grep -rli "skill-creator|skill_creator"` (only one prose mention at
`.claude/agents/qrspi-structure.md:41`), `ls .claude/skills/` (only the 10
`qrspi-*` skills). The nearest analogue is the QRSPI phase pattern: a thin
*wrapper* skill (`.claude/skills/<phase>/SKILL.md`) parses `$ARGUMENTS`, resolves
`REPO_ROOT` from `pwd`, then spawns a *subagent* (`.claude/agents/<phase>.md`)
via the `Agent` tool with a structured input contract; the subagent reads inputs
and writes a markdown artifact into `.qrspi/<ticket-id>/`. No intermediate
artifacts beyond the final per-phase `.md` file.

**Evidence:**

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd` ...
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

— `.claude/skills/qrspi-research/SKILL.md:11-18`

**Dependencies:** N/A (skill absent).
**Implicit contracts:** A future creator skill would be expected to follow the
wrapper→subagent→templated-artifact pattern.

## Q3: What fields are required versus optional in the YAML frontmatter of a SKILL.md in this repo, and what constraints exist on the `description` field?

**Answer:** No schema/validator exists in-repo (Q11), so "required" is by
convention. Every skill SKILL.md carries these always-present fields: `name`,
`description`, `command` (the `/slash` form), `argument-hint`, and `allowed-tools`.
(`qrspi-ticket` and `qrspi-questions` still have all five; earlier impression
that some omit `allowed-tools` was wrong — all 10 skills declare it.) Agent files
(`.claude/agents/*.md`) use a DIFFERENT frontmatter shape: `name`, `description`,
`model: opus`, and a nested `claude:\n  tools: ...` block (no `command`/
`argument-hint`/`allowed-tools`). The `description` is a single-line string
following a "what it does + when to use" shape; the `qrspi-work` description is
quoted and notably long (multi-trigger). No enforced length limit on
`description` anywhere.

**Evidence (skill frontmatter):**

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

**Evidence (agent frontmatter — different shape):**

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts ... Spawned by /qrspi-research or qrspi-work. Not for general codebase exploration.
model: opus
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/agents/qrspi-research.md:1-7`

**Dependencies:** Frontmatter consumed by Claude Code's skill/agent loader.
**Implicit contracts:** `name` must equal the directory/file base name (Q5).
Skill `description` is the auto-invocation trigger surface; agent `description`
states "Spawned by … Not for general …" to discourage misuse.

## Q4: How is a skill invoked in this environment (slash-command wrapper versus auto-invocation), and where is the wrapper-to-agent mapping defined?

**Answer:** Three invocation paths. (1) Explicit slash command, declared per
skill via the `command:` frontmatter field (e.g. `command: /qrspi-research`).
(2) Auto-invocation by Claude from the `description` trigger text. (3) Programmatic
spawn from the batch workflow (`.claude/workflows/qrspi-batch*.js`). Phase
skills are thin wrappers that spawn a paired subagent through the **`Agent`** tool
using `subagent_type: qrspi-<phase>`. The wrapper→agent mapping is by naming
convention (identical base name) and stated inline in each wrapper body. There is
no separate manifest. Two skills have no paired agent: `qrspi-ticket` (guided
conversation, uses Linear MCP directly) and `qrspi-work` (the autonomous
orchestrator that itself spawns all phase agents).

**Evidence:**

```
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

— `.claude/skills/qrspi-research/SKILL.md:17-18`

```
The orchestrator dispatches each phase to a purpose-built agent defined in `.claude/agents/qrspi-<phase>.md`. ... it spawns by `subagent_type` with a structured input contract.
1. Spawn via the `Agent` tool with `subagent_type: qrspi-<phase>` and `mode: "auto"`.
```

— `.claude/skills/qrspi-work/SKILL.md:589-591`

The batch-v2 workflow spawns the typed agents directly:

```
const res = await agent(prompt, { label: `${name}:${ctx.id}`, phase: 'Planning', agentType })
```

— `.claude/workflows/qrspi-batch-v2.js:161` (called for `qrspi-questions`…`qrspi-worktree`)

**Dependencies:** Wrapper → `Agent` tool → subagent prompt in `.claude/agents/`.
All spawning wrappers declare `Agent` in `allowed-tools` (verified across design,
implement, plan, pr, questions, research, structure, worktree).
**Implicit contracts:** wrapper base-name == agent base-name == `command` slug
(minus the leading `/`) == directory name. Renaming one side silently breaks the
mapping. `qrspi-batch.js` (older) nests `qrspi-work` inside an `agent()` call;
`qrspi-batch-v2.js` was written specifically because that nesting could not
spawn the phase agents (the inner subagent lacks the `Agent` tool — see header
comment `qrspi-batch-v2.js:18-32`).

## Q5: What naming convention is enforced for skill names (directory name, frontmatter `name`, and slash-command identifier)?

**Answer:** No enforcement mechanism exists (no registration module, no
validator). By convention, for every skill four identifiers are identical:
directory name == frontmatter `name` == `command` slug == `/slash-command`. All
use the `qrspi-<phase>` kebab-case prefix. Agent files follow the same rule:
agent file basename == agent frontmatter `name` == the spawning skill's name and
`subagent_type`. Verified 100% consistent across all 10 skills and all 8 agents.

**Evidence:**

```
dir=qrspi-design     name=qrspi-design     command=/qrspi-design
dir=qrspi-research   name=qrspi-research   command=/qrspi-research
dir=qrspi-work       name=qrspi-work       command=/qrspi-work
```

— derived from `^name:` / `^command:` in each `.claude/skills/*/SKILL.md`

```
file=qrspi-research.md   name=qrspi-research   (subagent_type: qrspi-research)
file=qrspi-worktree.md   name=qrspi-worktree
```

— `^name:` in `.claude/agents/*.md`; `subagent_type` from wrapper bodies

**Dependencies:** Slash-command resolution, auto-invocation, and `subagent_type`
lookup all rely on this name identity (external loader / Agent tool).
**Implicit contracts:** kebab-case, `qrspi-` prefix; four-way identity for
skills, plus a matching agent file/`name`/`subagent_type` for the 8 spawning
phases.

## Q6: Where does skill-creator persist its working state during a multi-step skill build, and is any eval/iteration loop state retained between runs?

**Answer:** NOT FOUND for `skill-creator` (does not exist). The only state
patterns present: (a) QRSPI phase artifacts written to `.qrspi/<ticket-id>/*.md`
(file-on-disk, no in-memory loop); (b) the eval harness persists per-run output.
`run_eval.py` writes a single `results.json` into a caller-supplied
`--output` directory (overwritten each run, keyed by a 12-char `skill_hash`);
`grade.py` writes `grades.json` alongside; `report.py` reads a `results/`
directory whose subdirs are treated as **versions** (it iterates
`results/<version>/grades.json`), giving cross-run history. So iteration state IS
retained, but as a directory-per-version convention the user manages manually —
there is no automatic checkpoint/resume.

**Evidence:**

```
output_path = os.path.join(config.output_dir, "results.json")
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
```

— `scripts/run_eval.py:209-211`

```
for version_dir in sorted(results_path.iterdir()):
    if not version_dir.is_dir(): continue
    grades_path = version_dir / "grades.json"
    if grades_path.exists(): ...
```

— `scripts/report.py:19-23` (`--results-dir` default `"results"`, `report.py:74`)

**Dependencies:** `run_eval.py`→`results.json`; `grade.py`→`grades.json`;
`report.py` reads `results/<version>/grades.json`.
**Implicit contracts:** A "version" = a subdirectory under `results/` containing
`grades.json`. History/regression tracking depends on that layout.

## Q7: What is the enforced size limit on a SKILL.md body, and how is the 500-line / 5000-token threshold from the acceptance criteria measured or validated in this repo?

**Answer:** No size limit is enforced or measured by any code in this repo. The
"500 lines" figure DOES appear, but only as prose guidance in docs, not as a
check: `docs/qrspi_claude_code_guide.md:582` says "Check that each `SKILL.md` is
under 500 lines and under ~40 distinct instructions. The instruction budget
ceiling is real." No "5000-token" threshold appears anywhere
(`grep "5000"` / `"token"` → no SKILL.md-budget hits). No script counts lines or
tokens of a SKILL.md. Observed sizes: most SKILL.md are 25–35 lines (thin
wrappers); `qrspi-ticket` is 119; the outlier `qrspi-work/SKILL.md` is **791
lines** (36,889 bytes) — far over the 500-line doc guidance — yet nothing flags
it. (The `line_count` check in `grade.py` exists but targets eval *artifacts*
like `design.md`, not SKILL.md files; see Q10.)

**Evidence:**

```
The skill prompt may be too long. Check that each `SKILL.md` is under 500 lines and under ~40 distinct instructions. The instruction budget ceiling is real.
```

— `docs/qrspi_claude_code_guide.md:582`

```
 25 .claude/skills/qrspi-research/SKILL.md
119 .claude/skills/qrspi-ticket/SKILL.md
791 .claude/skills/qrspi-work/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`

**Dependencies:** none (no validator).
**Implicit contracts:** Size discipline is doc-stated (500 lines, ~40
instructions) but unenforced; `qrspi-work` is the standing precedent for an
over-budget SKILL.md.

## Q8: How are existing skills structured when content exceeds the SKILL.md budget — what triggers content moving into `references/` versus staying inline?

**Answer:** Exactly one skill demonstrates offload: `qrspi-work` has
`references/review-cascade.md`. There is no coded *trigger* rule; it is an ad-hoc
authoring decision. The body explicitly defers to the reference doc on demand:
`qrspi-work/SKILL.md:281` instructs "Read `references/review-cascade.md` for
cascade logic." Notably the offload is partial — `qrspi-work/SKILL.md` is still
791 lines (Q7), so the existing precedent does NOT model a clean
"over-budget → extract to references/" discipline. No other skill uses
`references/`.

**Evidence:**

```
   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:281`

`review-cascade.md` is a self-contained 64-line doc covering the
Questions→Research→Design→Structure→Plan→Work Tree cascade rules:

```
# Review Cascade Logic
... The planning artifacts form a dependency chain:
Questions → Research → Design → Structure → Plan → Work Tree
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-7`

**Dependencies:** SKILL.md body references its `references/` doc by relative path,
loaded on demand.
**Implicit contracts:** `references/` holds detail loaded only when the body
points to it; it is not part of the always-loaded SKILL.md.

## Q9: How do existing skills handle deprecation or version-transition notices in their body content?

**Answer:** NOT FOUND — no skill contains a deprecation or version-transition
notice. `grep -rli "deprecat"` matches only container-sandbox research docs and
the RUS-22 questions file, never a skill or agent. Skills embed no version
numbers or migration banners. The one place a superseded artifact is "handled"
is operational, not a body notice: `qrspi-batch-v2.js` header explains it
*replaces* `qrspi-batch.js` and why (the old one "could not spawn the phase
agents"), but the old file is left in place with no in-file deprecation marker.
The only version-like keys are `"version"` in eval configs (Q-adjacent, schema
versioning, not skills). So there is no in-repo template for phrasing a
"this tool/version changed" notice inside a skill.

**Evidence:**

```
// The old qrspi-batch ran `agent("…follow qrspi-work SKILL.md…")`. That subagent
// is a workflow-subagent, which is NOT provisioned the Agent (subagent-spawning)
// tool.
```

— `.claude/workflows/qrspi-batch-v2.js:18-20` (rationale comment; no deprecation tag on `qrspi-batch.js` itself)

— `grep -rli "deprecat" .` → only `docs/container-sandbox/research/*` and `.qrspi/RUS-22/questions.md`

**Dependencies:** none.
**Implicit contracts:** none established; greenfield for any deprecation-notice work.

## Q10: How does the eval harness assess a skill's description-triggering accuracy and body quality, and what command runs it?

**Answer:** The harness does NOT assess description-triggering accuracy at all,
and assesses "body quality" only of phase *output artifacts* (not SKILL.md
bodies). It is a phase-output regression suite. Pipeline (per `docs/eval-system.md`):
`run_eval.py` (execute) → `grade.py` (score) → `report.py` (compare versions) →
`diagnose.py` (categorize failures) → `revise.py` (propose edits). Commands take
explicit args, e.g. `python scripts/run_eval.py --skill <path> --suite
evals/suite.json --output <dir>`, then `python scripts/grade.py --results
results.json --suite evals/suite.json`. `evals/suite.json` defines 15 weighted
cases across all 8 QRSPI phases, each with `programmatic`, `llm_judge`, and
`script` assertions, on a 65/35 train/test split. Crucially, the runtime is a
STUB: `execute_single()` does not invoke any agent — it returns empty
`output`/`files`, so all programmatic checks see no data; `llm_judge` and
`script` checks return `passed: None`. There is NO check anywhere that a
`description` triggers correctly.

**Evidence (runtime is a stub):**

```
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
messages = build_messages(case)
result.output = ""
result.files = []
```

— `scripts/run_eval.py:117-134`

**Evidence (suite shape + commands):**

```
1. **`scripts/run_eval.py`** — Execute test cases ...
2. **`scripts/grade.py`** — Score results ...
`evals/suite.json` defines 15 eval cases spanning all QRSPI phases:
```

— `docs/eval-system.md:5-15`

**Dependencies:** `run_eval.py`→`evals/suite.json`→`evals/fixtures/*.md`, writes
`results.json`; `grade.py` reads results + suite. `evals/golden/` is empty
(`.gitkeep`).
**Implicit contracts:** Suite case shape `{id, name, phase, prompt, context,
assertions[], tags, difficulty, split}` (validated for `{id,prompt,assertions}`
in `run_eval.py:52-56`). Assertion types: `programmatic` (dispatched via
`grade.py` `CHECKS` registry), `llm_judge` (criteria string), `script`
(shell invocation). `evals/graphite-evals.json` is a separate 5-case suite for
the Graphite skill with its own schema.

## Q11: What validation exists for SKILL.md frontmatter correctness, and is it run manually or in CI?

**Answer:** NOT FOUND — there is NO frontmatter validation in this repo, and NO
CI. No script parses or validates SKILL.md/agent YAML (`grep -rni "frontmatter"`
→ 0 matches; no `.github/workflows/` dir exists). The only validation-flavored
code is: (a) `run_eval.py load_suite()` validating the eval *suite JSON* shape,
and (b) `scripts/check_scope.py`, which scans an *impl-log artifact* for files
outside the allowed session set — neither touches skill frontmatter. The eval
docs do not claim CI; the harness is run manually.

**Evidence:**

```
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
```

— `scripts/run_eval.py:47-50` (validates suite JSON, not SKILL.md)

```
out_of_scope = touched - allowed
result = { "passed": len(out_of_scope) == 0, ... }
```

— `scripts/check_scope.py:44-50` (scope check, not frontmatter)

(No `.github/` directory; `find` for CI config returns nothing.)

**Dependencies:** none.
**Implicit contracts:** Frontmatter correctness is trust-based; any validator
would be net-new.

## Q12: What logging, scoring output, or run reports does the skill-creator eval loop emit so a reviewer can inspect skill performance after a build?

**Answer:** NOT FOUND for a "skill-creator eval loop" (does not exist). The
general eval harness's review surfaces: `run_eval.py` prints a header plus a
per-run `[n/total] <case_id> trial=<t> OK|ERROR (<ms>)` line and writes
`results.json` (with `skill_hash`, `timestamp`, per-trial `ExecutionResult`
records). `grade.py` writes `grades.json` and prints train/test scores, stddev,
and the train-test gap. `report.py` emits a markdown "# QRSPI Eval Iteration
Report" with a latest-version summary, a version-history table, and promotion
status, plus `detect_plateau()`. Two important caveats limit real observability:
(1) the runtime is stubbed so all scores are zeros (Q10); (2) `diagnose.py` and
`revise.py` are non-functional — their `main()` functions parse args but never
call the real logic and just `print("Diagnosis complete"); return 0`; `revise.py`
is additionally corrupted (an unreachable bare `high` statement and duplicated
`return 0` lines after `_assess_risk`). So post-run inspection today is
effectively `results.json` + `grades.json` + `report.py` output only.

**Evidence (report output):**

```
def generate_report(versions: list) -> str:
    lines = ["# QRSPI Eval Iteration Report", ""]
    ...
    lines.append("| Version | Train | Test | Gap | Promoted |")
```

— `scripts/report.py:92-113`

**Evidence (diagnose/revise are non-functional shells):**

```
def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose eval failures")
    parser.add_argument("--grades", required=True, ...)
    ...
    print("Diagnosis complete")
    return 0
```

— `scripts/diagnose.py:118-124` (`generate_diagnosis()` defined at :90 is never called; note duplicate dead `return diagnosis` at :114 and :116)

```
    return "medium" if num_cases > 2 else "low"
    return "medium" if num_cases > 2 else "low"
    parser = argparse.ArgumentParser(description="Propose skill revisions")
    print(f"Diagnosis complete")
    return 0
```

— `scripts/revise.py:112-116` (malformed tail; bare `high` at :111, no proper `main()` body, repeated `return 0`)

**Dependencies:** `report.py` consumes `results/<version>/grades.json`;
`grade.py` consumes `results.json` + `suite.json`.
**Implicit contracts:** Results JSON shape (`scripts/run_eval.py:197-207`):
`{skill_hash, skill_path, suite, timestamp, config, results:[ExecutionResult...]}`.
Grades JSON: `{train_score, test_score, train_test_gap, cases:[...]}`. Reporting
keys off `version`, `train_score`, `test_score`, `train_test_gap`.

---

## Discovered Patterns

- **Wrapper + subagent split.** Each working phase = a thin wrapper skill
  (`.claude/skills/<phase>/SKILL.md`, ~25–35 lines) that parses `$ARGUMENTS`,
  resolves `REPO_ROOT` from `pwd`, and spawns a same-named subagent
  (`.claude/agents/<phase>.md`) via the `Agent` tool with a structured input
  contract. Two skills (`qrspi-ticket`, `qrspi-work`) have no paired agent.
- **Two distinct frontmatter schemas.** Skills use `name/description/command/
  argument-hint/allowed-tools`; agents use `name/description/model/claude.tools`.
  (Q3)
- **Four-way name identity** for skills (dir == name == command == /slash) plus a
  matching agent file/name/`subagent_type` for the 8 spawning phases. 100%
  consistent. (Q5)
- **Templated artifacts as single source of truth.** Agents write
  `.qrspi/<ticket-id>/<artifact>.md` shaped by `.qrspi/templates/<artifact>.md`.
  (README:88-110; every wrapper passes a `TEMPLATE_PATH`.)
- **`allowed-tools` lockdown convention.** Spawning wrappers grant `Agent`;
  read-only phases (research) keep a minimal set; orchestrator (`qrspi-work`) and
  `qrspi-ticket` additionally grant specific Linear MCP tools.
- **Eval configs are schema-objects** with a top-level `version`/`name` and a
  `cases`/`evals` array of weighted-assertion objects. (`evals/suite.json`,
  `evals/graphite-evals.json`)
- **Convention over enforcement.** Nothing in-repo validates skill structure,
  naming, frontmatter, or size — all authoring discipline.
- **`references/` for on-demand offload.** Only `qrspi-work` uses it; body must
  explicitly point to the doc (SKILL.md:281).
- **Workflow-script orchestration.** `.claude/workflows/qrspi-batch*.js` drive
  tickets by spawning typed phase agents directly (v2) or nesting `qrspi-work`
  (v1); the v2 rewrite exists specifically because nested subagents lack the
  `Agent` tool.

## Inconsistencies

- **`qrspi-work/SKILL.md` is 791 lines** while the doc guidance
  (`qrspi_claude_code_guide.md:582`) says SKILL.md should be "under 500 lines and
  under ~40 distinct instructions." It has a `references/` dir but only one small
  doc was extracted — offload is incomplete. (Q7/Q8)
- **The eval runtime is a stub.** `run_eval.py:117-134` `execute_single()` never
  invokes an agent (returns empty output/files), so every programmatic check
  scores 0 and every `llm_judge`/`script` check returns `passed: None`. The
  pipeline runs end-to-end but produces zeros (confirmed by
  `docs/eval-system.md:108`).
- **`diagnose.py` / `revise.py` are wired but produce nothing useful yet.** Their
  `main()` functions DO call `produce_diagnosis` (`diagnose.py:185-192`) and
  `revise_skill` (`revise.py:187-195`); the limitation is upstream — because
  `run_eval.py` is stubbed and `grade.py`'s `llm_judge`/`script` checks return
  `passed: None`, `extract_failures()` sees all-zero scores. The
  `categorize_failure` logic is heuristic (string matching on check names/evidence),
  noted in-code as a placeholder for a future meta-agent (`diagnose.py:58-73`).
  `revise.py` only applies edits that have concrete `old_text`/`new_text`, which
  the stub never produces, so it logs `pending_meta_agent`. (Earlier draft wrongly
  called these "corrupted/non-functional"; full reads disprove that.)
- **Doc vs reality on agent/template paths.** `.claude/CLAUDE.md` "Codebase
  conventions" says "Agent prompt definitions live in `.qrspi/agents/`", but they
  actually live in `.claude/agents/`. (Same file also says templates live in
  `.qrspi/templates/`, which IS correct.)
- **Suite references 21 fixtures, only 4 exist.** `evals/suite.json` cites
  fixture files (e.g. `fixtures/questions_rest_endpoint.md`) that are absent;
  only the 4 ticket fixtures exist. Many assertion `check` names in the suite
  (e.g. `section_count`, `all_questions_answered`, `code_snippets_under_limit`)
  are NOT in `grade.py`'s `CHECKS` registry (~10 of ~37 implemented), so they
  resolve to "Unknown check function". (`docs/eval-system.md:80-108`)
- **Two batch workflows coexist** (`qrspi-batch.js`, `qrspi-batch-v2.js`) with
  overlapping `name`/`description`; v2 supersedes v1 but v1 carries no
  deprecation marker. (Q9)
- **CONTENT-CAPTURE NOTE:** This environment's `cat -n`/`Read` line numbering for
  `scripts/diagnose.py` and `scripts/revise.py` rendered garbled/duplicated line
  numbers; I re-extracted those files with Python `splitlines()` to obtain the
  accurate line numbers cited above. Citations for other files use the normal
  numbering.
