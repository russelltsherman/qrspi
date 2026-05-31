# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> **Scope note:** This repo's "skills" are QRSPI workflow phase wrappers under `.claude/skills/`. There is **no `skill-creator` skill, no `agentskills.io` standard reference, and no skill-authoring/eval tooling inside this repo**. The `skill-creator` skill mentioned in `.claude/CLAUDE.md`-adjacent context is a *global* skill that lives outside `REPO_ROOT` (e.g. `~/.claude/skills/`), which the research firewall forbids reading. Several questions (Q2, Q5, Q6, Q9, Q11) target that out-of-repo skill or a skill-eval harness that does not exist here; those are answered NOT FOUND with the in-repo analogue noted. The eval harness that *does* exist (`evals/`, `scripts/`) evaluates QRSPI **agent/skill prompts**, not generated skills.

## Q1: What is the on-disk directory structure of an existing agent skill in this repo, and where do `SKILL.md`, `references/`, `scripts/`, and `assets/` sit relative to one another?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, one directory per skill, each containing a `SKILL.md`. There are 10 skills: `qrspi-{ticket,questions,research,design,structure,plan,worktree,implement,pr,work}`. Only **one** skill has a `references/` subdirectory (`qrspi-work/references/review-cascade.md`). **No skill has a `scripts/` or `assets/` subdirectory** — those directory conventions are not used in this repo. Per-skill scripts do not exist; the only scripts live at the repo-level `scripts/` (the eval harness), unrelated to skill packaging. Note: skill *prompt bodies* are deliberately thin wrappers; the substantive prompts live separately in `.claude/agents/<name>.md` (see Discovered Patterns).

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
.claude/skills/qrspi-work/references/review-cascade.md   <- only references/ dir
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing, full tree)

The README documents the layout (no scripts/ or assets/ shown):

```
.claude/
  skills/              # Skill definitions (one SKILL.md per phase)
    qrspi-ticket/
    ...
    qrspi-work/        # Autonomous orchestrator
```

— `README.md:75-87`

**Dependencies:** Skills depend on `.claude/agents/<name>.md` (prompt bodies) and `.qrspi/templates/*.md` (output formats). The `references/` file is loaded on-demand by its owning skill body.
**Implicit contracts:** A skill directory name equals its `name:` frontmatter field equals its `/command`. `references/` is a sibling of `SKILL.md`, loaded by relative path (`Read references/review-cascade.md` at `.claude/skills/qrspi-work/SKILL.md:281`). No `scripts/`/`assets/` convention exists to model a new skill on.

## Q2: How does the skill-creator skill consume its inputs and where does it write the generated skill output (target path, naming convention)?

**Answer:** **NOT FOUND.** There is no `skill-creator` skill inside `REPO_ROOT`. The only skills present are the 10 `qrspi-*` workflow skills (see Q1). The `skill-creator` referenced in surrounding context is a global Claude Code skill installed outside the repo (e.g. `~/.claude/skills/skill-creator/`), which is outside project scope and forbidden by the research firewall.

**Search queries attempted:**
- `find . -name "SKILL.md"` → only `qrspi-*` skills
- `grep -rin "skill-creator" .claude docs scripts evals` → 0 hits
- `grep -rin "agentskills" .` → 0 hits

The only in-repo analogue of "generate an artifact to a target path" is the QRSPI agent pattern: each phase skill spawns its agent and writes to a path passed in the spawn contract (e.g. research writes to `RESEARCH_PATH`, a caller-supplied absolute path at `.claude/skills/qrspi-research/SKILL.md:23`). No naming convention for *generated skills* exists in-repo.

**Dependencies:** N/A (out of repo).
**Implicit contracts:** N/A.

## Q3: What exact frontmatter fields and value formats does the agentskills.io standard require in `SKILL.md` (name, description, and any others), as evidenced by existing skills in this repo?

**Answer:** No `agentskills.io` standard is referenced anywhere in-repo (`grep "agentskills"` → 0 hits). The *observed* frontmatter contract across all 10 in-repo skills is: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. Two of these five (`name`, `description`) appear in every skill; `command`, `argument-hint`, `allowed-tools` also appear in every skill. The separate **agent** files (`.claude/agents/*.md`) use a *different* frontmatter shape: `name`, `description`, `model`, and a nested `claude: tools:` block.

**Evidence (skill frontmatter):**

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

`description` may be a bare scalar or a quoted string (used when it contains commas/colons/parens), e.g. the long quoted description at `.claude/skills/qrspi-work/SKILL.md:3`. `allowed-tools` is a comma-separated list; tools may be parameter-scoped, e.g. `Bash(pwd:*)`.

**Evidence (agent frontmatter — different shape):**

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

**Dependencies:** Claude Code's skill loader reads frontmatter to register the `/command` and gate `allowed-tools`.
**Implicit contracts:** `name` must match the directory name. `command` is `/<name>`. `allowed-tools` restricts the tool surface (wrapper skills only get `Agent`, `Bash(pwd:*)`, and optionally one Linear MCP tool). There is no in-repo evidence of the agentskills.io standard fields; only Claude Code's native frontmatter is in use.

## Q4: What is the established naming convention for skill names and directories in this repo, and what would the canonical name for the Codex CLI skill be?

**Answer:** All skills use a lowercase, hyphen-separated `qrspi-<phase>` slug. The directory name, the `name:` frontmatter value, and the `/command` are identical (e.g. directory `qrspi-design/` → `name: qrspi-design` → `command: /qrspi-design`). Every existing skill carries the `qrspi-` prefix because they are all QRSPI workflow phases. There is **no precedent in-repo for a non-`qrspi` skill name**, so the canonical name cannot be derived from existing convention with certainty. Following the lowercase-hyphenated slug convention, a plausible canonical name is `codex-cli` (slug = directory = `name:` = `/codex-cli`); whether to keep or drop a `qrspi-` prefix is undetermined by existing evidence (this is a design decision, not a fact).

**Evidence:**

```
name: qrspi-design        (dir: .claude/skills/qrspi-design/)   cmd: /qrspi-design
name: qrspi-implement     (dir: .claude/skills/qrspi-implement/) cmd: /qrspi-implement
name: qrspi-questions     (dir: .claude/skills/qrspi-questions/) cmd: /qrspi-questions
...
```

— frontmatter `name:`/`command:` lines, all 10 `.claude/skills/*/SKILL.md`

**Dependencies:** None.
**Implicit contracts:** slug = directory = `name:` = `/command` (three-way identity). Lowercase, hyphen-separated. All current skills are `qrspi-`-prefixed, but the prefix is a domain marker, not a hard naming rule.

## Q5: How is the skill-creator's eval loop invoked and where are its eval artifacts, harness, and pass/fail thresholds stored?

**Answer:** **NOT FOUND for skill-creator** (it is out of repo — see Q2). The in-repo eval harness evaluates **QRSPI agent/skill prompts**, not generated skills, and is the closest analogue. It is invoked via `run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]`, which orchestrates a 5-stage pipeline: `run_eval.py` → `grade.py` → (`report.py`) with `diagnose.py` + `revise.py` in the optimization loop.

**Thresholds (in-repo eval harness):**
- Default `target_score = 0.85`, default `max_iter = 5` — `run_loop.sh:14-15`.
- Loop-level regression threshold: `0.05` drop triggers rollback — `run_loop.sh:79-91`.
- Promotion criteria: test score no-regression, `regression_count == 0`, `train_test_gap <= 0.1` — `scripts/report.py:77-90`.
- Per-case regression flag: `drop > 0.2` (>1 pt on 5-pt scale) — `scripts/report.py:46`.

**Evidence:**

```bash
SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
EVAL_SUITE=${2:?...}
MAX_ITER=${3:-5}
TARGET_SCORE=${4:-0.85}
```

— `run_loop.sh:12-15`

Eval artifacts: suite at `evals/suite.json`; fixtures at `evals/fixtures/`; `evals/golden/.gitkeep` (empty placeholder); per-version results written to `results/v<N>/{results.json,grades.json}` (`run_loop.sh:34`, `scripts/grade.py:363`); aggregate `results/report.json` + `results/ledger.json` (`scripts/report.py`).

**Dependencies:** `run_loop.sh` → `scripts/{run_eval,grade,diagnose,revise,report}.py`; all read `evals/suite.json`.
**Implicit contracts:** A "skill_path" passed to the harness is a single prompt **file** (`load_skill` does `open(skill_path).read()` at `scripts/run_eval.py:61-64`), e.g. `.qrspi/agents/01-questions.md` per the `run_loop.sh:10` usage example — note this example path does not match the actual `.claude/agents/qrspi-*.md` layout (see Inconsistencies).

## Q6: Where are the size/length constraints (SKILL.md under 500 lines / 5000 tokens, content offloaded to `references/`) enforced or measured, if anywhere, in the existing tooling?

**Answer:** **Not enforced or measured for skills anywhere in the eval tooling.** The eval harness has no skill-length check. The "under 500 lines" guidance exists only as prose in a doc, not as code. There is **no 5000-token check** anywhere in-repo (`grep "5000 token"` / `"token count"` → 0 hits; the only `tokens` references in `scripts/` are the per-run usage placeholder `{"input":0,"output":0}` and `max_tokens` config).

The grading harness *does* enforce **line/length limits on generated artifacts** (not skills) via `grade.py`:
- `line_count('design.md') <= 300` — `evals/suite.json` case_005; impl at `scripts/grade.py:35-40`.
- `code_snippets_under_limit('research.md', 20)`, `total_steps('plan.md') <= 100`, `question_count <= 15` — `evals/suite.json` (research/plan/questions cases).

**Evidence (prose-only 500-line guidance):**

```
The skill prompt may be too long. Check that each `SKILL.md` is under 500 lines
and under ~40 distinct instructions. The instruction budget ceiling is real.
```

— `docs/qrspi_claude_code_guide.md:592`

Reality check: `qrspi-work/SKILL.md` is **791 lines** (`wc -l`), violating that 500-line guidance — confirming it is advisory, not enforced.

**Dependencies:** `grade.py` length checks operate on artifact `output`, not on skill files.
**Implicit contracts:** Content offloading to `references/` is an observed practice (only `qrspi-work` does it, at 791 lines) but no tooling measures when material *should* move out of the body. The 500-line/instruction-budget rule is a human convention documented in `docs/qrspi_claude_code_guide.md`.

## Q7: How do existing skills in this repo split content between `SKILL.md` body and `references/` files, and at what point is material moved out of the body?

**Answer:** Only `qrspi-work` uses a `references/` split. Its `SKILL.md` (791 lines) keeps the orchestrator state machine, dispatch table, and inline procedures in the body, and offloads exactly one self-contained decision-logic topic — the review cascade rules — to `references/review-cascade.md` (64 lines). The reference is loaded **on demand**, only in the Plan-Review feedback path, via an explicit instruction. The other 9 skills are thin (25–119 lines) and have no references. There is no documented numeric trigger for offloading; the observed heuristic is "self-contained branch logic consulted only in a specific state → reference file."

**Evidence (on-demand load):**

```
   b. Analyze which artifacts are affected by the feedback.
   c. Read `references/review-cascade.md` for cascade logic.
   d. Address feedback starting from the earliest affected artifact ...
```

— `.claude/skills/qrspi-work/SKILL.md:280-282`

Reference file scope (a single decision topic, table-driven):

```
# Review Cascade Logic
... The planning artifacts form a dependency chain:
Questions → Research → Design → Structure → Plan → Work Tree
## Cascade Rules
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-17`

**Dependencies:** `qrspi-work/SKILL.md` → `references/review-cascade.md` (relative-path Read).
**Implicit contracts:** Reference files are loaded lazily by an explicit `Read references/<file>.md` instruction tied to a specific branch/state, keeping the always-loaded body smaller. Material moves out when it is (a) a cohesive sub-topic and (b) only needed in a narrow execution path.

## Q8: Are there existing skills documenting an external CLI tool (approval modes, sandbox modes, config files) that establish a pattern for encoding tool-specific conventions, and how do they structure that material?

**Answer:** No skill *documents* an external CLI as its subject, but the QRSPI workflow heavily encodes **Graphite (`gt`) and GitHub (`gh`) CLI conventions**, primarily inside `qrspi-work/SKILL.md`. The structuring pattern: tool-specific operational knowledge is grouped into dedicated trailing sections with fenced `bash` command blocks, hazard callouts, and recovery procedures. There is also a separate Graphite eval (`evals/graphite-evals.json`, not the agent suite). The closest "wraps a CLI" precedent for a new tool skill is therefore the **structure of qrspi-work's git/graphite sections**, not a standalone tool skill.

**Evidence (dedicated tool-convention sections in qrspi-work):**

```
## Git/Graphite Rules
- All `gt` commands include `--no-interactive`.
- All commit messages use heredoc format and include the co-authorship trailer.
...
### Resubmitting when the prior PR was closed or merged
```

— `.claude/skills/qrspi-work/SKILL.md:654-689` (also `### Staging — NEVER use -a flag` at 702, `## Worktree Management` at 729)

Approval/sandbox/interactivity is encoded as a hard convention (`--no-interactive` on every `gt`; `--confirm` on merges), and a HARD STOP infrastructure-error block governs tooling failures — `.claude/skills/qrspi-work/SKILL.md:770-792`. A devcontainer sandbox exists at `.devcontainer/` (referenced `README.md:102`) but is not documented inside a skill.

**Dependencies:** `qrspi-work` invokes `gt`, `gh`, `git` via Bash; `evals/graphite-evals.json` evaluates a separate Graphite skill.
**Implicit contracts:** CLI conventions are encoded as (1) imperative rule lists, (2) fenced `bash` example blocks, (3) named recovery procedures for known failure states, and (4) explicit "never do X" hazard callouts. Approval/sandbox behavior is expressed as mandatory non-interactive flags plus a HARD STOP rule, not as a config-file schema.

## Q9: Does any existing skill or repo convention dictate how platform-specific behavior (e.g. macOS vs. Linux) is documented within a single skill?

**Answer:** **NOT FOUND.** No skill, agent file, template, or doc in-repo documents macOS-vs-Linux (or any OS-conditional) behavior, and there is no authoring guideline for it (the `skill-creator` references that might contain such guidance are out of repo — see Q2).

**Search queries attempted:**
- `grep -rin "macos\|darwin\|linux\|platform\|uname\|os.name" .claude docs evals scripts` → no platform-branching convention found (the only OS-adjacent material is container/sandbox PRD content under `docs/container-sandbox/`, which concerns Kata/Firecracker microVMs, not per-skill OS documentation).

The repo is implicitly Linux-oriented: it runs in a `.devcontainer/` (`README.md:102`) and the eval/loop scripts are bash + `python3`. No skill encodes platform conditionals.

**Dependencies:** N/A.
**Implicit contracts:** N/A — no established pattern exists to follow.

## Q10: What does the skill-creator eval harness measure for a generated skill (description triggering accuracy, body length, structural validity), and what command runs it?

**Answer:** **NOT FOUND for a skill-creator / "generated skill" harness** (out of repo — Q2). The in-repo harness does **not** measure description-triggering accuracy or skill body length; it measures **generated-artifact quality** for QRSPI phases. What it measures, per `evals/suite.json` + `scripts/grade.py`:
- **Structural validity** — `output_file_exists`, `has_section(<heading>)`.
- **Length/size** — `line_count <= N`, `code_snippets_under_limit`, `question_count` bounds, `total_steps <= 100`, `pr_title_under_limit`.
- **Content rules** — `no_solution_language`, `current_state_has_citations`, `all_evidence_has_file_citations`, `no_code_blocks`, `all_slices_have_verification`.
- **Subjective quality** — `llm_judge` criteria (currently a stub returning `passed: null`, `scripts/grade.py:208-227`).
- **Scope** — one `script`-type check, `scripts/check_scope.py` (case_011).

**Command:** `python3 scripts/run_eval.py --skill <prompt> --suite evals/suite.json --output results/<v>` then `python3 scripts/grade.py --results <...>/results.json --suite evals/suite.json` (orchestrated by `./run_loop.sh`).

**Evidence:**

```python
parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
parser.add_argument("--output", required=True, help="Output directory for results")
```

— `scripts/run_eval.py:219-221`

Note: `run_eval.py`'s `execute_single` is a **stub** — it does not actually invoke an agent; `result.output`/`files` are empty placeholders (`scripts/run_eval.py:117-137`). So the harness is structurally complete but not wired to a real runtime.

**Dependencies:** `run_eval.py` produces `results.json`; `grade.py` consumes it + `suite.json`; `check_scope.py` is invoked for script-type assertions.
**Implicit contracts:** A "skill" to the harness = a single prompt file path. Assertions are weighted; programmatic checks must be registered in `grade.py`'s `CHECKS` dict (`scripts/grade.py:146-157`) or they're skipped as "Unknown check function."

## Q11: Are there fixtures, example prompts, or golden outputs used to validate skills, and what format do they take?

**Answer:** Fixtures exist for the **QRSPI agent eval suite** (not for skill validation). Format: markdown ticket fixtures under `evals/fixtures/` plus an empty golden directory. The suite references additional fixtures (questions/research/design/structure/plan/worktree/impl-log/git-diff) that are **not present on disk** — only 4 of the referenced fixtures exist (see Inconsistencies). No golden outputs exist yet (`evals/golden/` holds only `.gitkeep`).

**Evidence (fixtures on disk):**

```
evals/fixtures/ticket_15_acceptance_criteria.md
evals/fixtures/ticket_multi_tenancy.md
evals/fixtures/ticket_rest_endpoint.md
evals/fixtures/ticket_websocket.md
evals/golden/.gitkeep
```

— `evals/` (directory listing)

Fixture format (markdown ticket with standard sections):

```
# Ticket: DASH-417
## Title
Add user preference endpoint for notification and display settings
## Description ...
## Acceptance Criteria
- [ ] GET /api/users/:id/preferences returns notification and display prefs ...
## Constraints ... ## Out of Scope ...
```

— `evals/fixtures/ticket_rest_endpoint.md:1-28`

Fixtures are injected as user-message context by `build_messages` (`scripts/run_eval.py:74-89`), which reads each `context.files` entry — silently skipping any that don't exist (`os.path.exists` guard, line 79).

**Dependencies:** `evals/suite.json` `context.files` → `evals/fixtures/*.md`; `build_messages` reads them.
**Implicit contracts:** Fixtures are plain markdown loaded verbatim into the prompt. Missing fixtures are skipped silently, not errored — so a case can "run" with incomplete context. Golden outputs are planned (`golden/` dir exists) but unpopulated.

## Q12: How are skill eval results reported and surfaced (output format, location, variance/benchmark reporting), and where would a reviewer look to confirm the new skill passed?

**Answer:** Results are JSON files written under `results/`. Per-version: `results/v<N>/results.json` (raw executions, `scripts/run_eval.py:209`) and `results/v<N>/grades.json` (scored, `scripts/grade.py:363`). Aggregate across versions: `results/report.json` and `results/ledger.json` (`scripts/report.py`). Variance is reported as **stddev** across trials per case and across cases per split; benchmarking is a **train/test split** comparison with regression/plateau/overfitting alerts. A reviewer confirms a pass by checking `test_score` against the `target_score` (default `0.85`) and the alerts in `report.json`.

**Evidence (grades output shape + console summary):**

```python
output = {
    "timestamp": ..., "skill_hash": ...,
    "train_score": train_scores["mean"],
    "test_score": test_scores["mean"],
    "train_test_gap": round(abs(train_scores["mean"] - test_scores["mean"]), 4),
    ...
}
```

— `scripts/grade.py:350-359`; console prints `Train score / Test score / Train-test gap` at `scripts/grade.py:367-369`.

Report alerts (where a reviewer looks):

```python
"alerts": {
    "plateau": plateau,
    "overfitting": overfitting,
    "has_regressions": latest["regression_count"] > 0,
},
```

— `scripts/report.py:145-149`

`run_loop.sh` extracts `grades.json["test_score"]` and compares to `TARGET_SCORE` to decide pass/break — `run_loop.sh:59-74`.

**Dependencies:** `grade.py` → `results/v<N>/grades.json`; `report.py` reads all `results/v*/grades.json` → `results/report.json` + `ledger.json`.
**Implicit contracts:** "Passed" = `test_score >= target_score` (default 0.85) AND no large per-case regressions (`drop > 0.2`) AND `train_test_gap <= 0.1` (promotion criteria, `scripts/report.py:77-90`). LLM-judge and script assertions currently return `null` (stubs), so present scores reflect only programmatic checks — a reviewer cannot yet confirm subjective-quality passes from the tooling alone.

---

## Discovered Patterns

- **Skill = thin wrapper; agent = real prompt.** 9 of 10 phase skills are 25–35 line wrappers whose body just parses `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, and spawns an agent by `subagent_type`. The substantive instructions live in `.claude/agents/qrspi-<phase>.md` (e.g. `.claude/skills/qrspi-research/SKILL.md:9-11` says "All prompt content lives in `.claude/agents/qrspi-research.md`"). A new skill could follow either the thin-wrapper+agent split or be self-contained like `qrspi-ticket` (119 lines, no agent).
- **Templates as single source of truth.** Output formats live in `.qrspi/templates/*.md`; skills/agents pass a `TEMPLATE_PATH` rather than embedding the format (`README.md:110`).
- **Input-contract spawning.** Agents receive labelled inputs (`KEY = value`) including absolute paths; sub-agents must `cd` first and use absolute paths (`.claude/skills/qrspi-work/SKILL.md:87-91`).
- **Firewalls via tool lockdown.** Phase isolation is enforced structurally — the research agent's frontmatter grants only `Read, Write, Glob, Grep` (no Linear MCP, no Bash), `.claude/agents/qrspi-research.md:5-6`.
- **HARD STOP on infrastructure errors.** A repeated, emphatic convention forbidding workarounds to tooling/permission failures (`.claude/skills/qrspi-work/SKILL.md:770-792`); the same rule is echoed in agent prompts.
- **Weighted assertion grading with train/test split + variance.** The eval system (`docs/eval-system.md`) is a 5-stage prompt-optimization loop with programmatic + llm_judge + script assertions, 3 trials, stddev, and overfitting guards.
- **Two separate eval suites.** `evals/suite.json` (QRSPI agents, 15 cases) and `evals/graphite-evals.json` (Graphite skill, 5 cases) — precedent for adding a *new* tool-specific suite (`docs/eval-system.md`).

## Inconsistencies

- **`run_loop.sh` example path is stale.** `run_loop.sh:10` documents `./run_loop.sh .qrspi/agents/01-questions.md ...`, but agents actually live at `.claude/agents/qrspi-questions.md` and there is no `.qrspi/agents/` directory. The project `.claude/CLAUDE.md` also claims "Agent prompt definitions live in `.qrspi/agents/`" — both references are wrong; agents are in `.claude/agents/`.
- **Suite references missing fixtures.** `evals/suite.json` references `questions_rest_endpoint.md`, `research_rest_endpoint.md`, `questions_websocket.md`, `research_websocket.md`, `design_rest_endpoint.md`, `structure_rest_endpoint.md`, `plan_rest_endpoint.md`, `worktree_session1.md`, `impl_log_complete.md`, `git_diff_rest_endpoint.txt`, and more — but only 4 ticket fixtures exist on disk (`ticket_{rest_endpoint,websocket,multi_tenancy,15_acceptance_criteria}.md`). `build_messages` silently skips missing files (`scripts/run_eval.py:79`), so those cases run with incomplete context.
- **500-line guidance vs. reality.** `docs/qrspi_claude_code_guide.md:592` says each `SKILL.md` should be under 500 lines, yet `qrspi-work/SKILL.md` is 791 lines. The guidance is advisory and unenforced.
- **Eval harness is a stub.** `scripts/run_eval.py:117-137` (`execute_single`) and the `llm_judge`/`script` graders (`scripts/grade.py:208-241`) are placeholders returning empty output / `null`. The pipeline is structurally complete but not wired to a real agent runtime, so reported scores currently reflect only programmatic checks on empty outputs.
- **Skill-authoring tooling absent.** Despite project docs referencing a `skill-creator` workflow, no skill-creator skill, no agentskills.io schema, and no skill-length/triggering-accuracy validation exist inside `REPO_ROOT`. Any such tooling lives in the global Claude install, outside project scope.
