# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> Scope note: This repository is the **qrspi** workflow tooling itself. There is **no `skill-creator` skill and no `argo` CLI integration present in the repo**. The global `skill-creator` skill and `argo` tooling referenced by the questions live outside `REPO_ROOT` and are therefore out of scope. The repo's own skills (`.claude/skills/*`) are the only concrete precedent available for SKILL.md structure, frontmatter, and references conventions. Findings below describe those precedents.

## Q1: What directory layout (SKILL.md plus references/, scripts/, assets/) do existing skills in this repository use, and where on disk are skill directories created relative to the repo root?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, each containing a single `SKILL.md`. One skill (`qrspi-work`) additionally has a `references/` subdirectory. No skill in the repo uses a `scripts/` or `assets/` subdirectory — shared executable logic lives in the top-level `scripts/` directory instead, and agent prompt bodies live in `.claude/agents/`. There are 10 skill directories:

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
.claude/skills/qrspi-plan/SKILL.md
.claude/skills/qrspi-pr/SKILL.md
.claude/skills/qrspi-questions/SKILL.md
.claude/skills/qrspi-research/SKILL.md
.claude/skills/qrspi-structure/SKILL.md
.claude/skills/qrspi-ticket/SKILL.md
.claude/skills/qrspi-work/SKILL.md          + references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
```

**Evidence:**

```
.claude/skills/qrspi-work/
├── SKILL.md
└── references/
    └── review-cascade.md
```

— `.claude/skills/` (directory listing)
**Dependencies:** Skills are discovered by Claude Code from `.claude/skills/`. Most QRSPI skills are thin wrappers that delegate to a peer agent prompt in `.claude/agents/<name>.md` (e.g., `qrspi-research/SKILL.md:11`).
**Implicit contracts:** Skill directory name matches the `name:` frontmatter value and the `/command` (e.g. directory `qrspi-research`, `name: qrspi-research`, `command: /qrspi-research`). The convention is one `SKILL.md` per directory; `references/` is optional and only used when the body would otherwise be large.

## Q2: How does the skill-creator skill consume an input description and emit a generated skill — what files does it read as templates and where does it write its output?

**Answer:** NOT FOUND in repo scope. There is no `skill-creator` skill under `.claude/skills/` and no generator script anywhere in `REPO_ROOT`. Searches: `find . -name SKILL.md` (returns only the 10 qrspi skills); `grep -rli 'skill-creator|skill_creator'` returns only `.claude/agents/qrspi-structure.md` (a passing mention in prompt text) and the questions file. The `skill-creator` skill referenced is a global skill outside `REPO_ROOT`.

The closest in-repo analog for "consume a description → emit an artifact" is the QRSPI wrapper pattern: a thin SKILL.md parses `$ARGUMENTS`, resolves paths, and spawns an agent that reads a template from `.qrspi/templates/<phase>.md` and writes output to `.qrspi/<ticket-id>/<phase>.md`.

**Evidence:**

```
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
   - Prompt body containing the five inputs:
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/research.md`
     - `RESEARCH_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/research.md`
```

— `.claude/skills/qrspi-research/SKILL.md:17-25`
**Dependencies:** Template-driven generation reads from `.qrspi/templates/`, writes to `.qrspi/<ticket-id>/`.
**Implicit contracts:** Wrappers verify the artifact exists and is non-empty after the agent returns (`qrspi-research/SKILL.md:25`).

## Q3: What fields are required and optional in the SKILL.md frontmatter (e.g., name, description, version) according to existing skills and any schema the repo enforces?

**Answer:** No schema or validator is enforced in the repo (no frontmatter validation logic exists — see Q11). By convention, every SKILL.md frontmatter contains exactly these fields, all present in all 10 skills:

- `name` — slug matching the directory
- `description` — trigger guidance (one of the longest fields; can be a quoted multi-sentence string, e.g. `qrspi-work/SKILL.md:3`)
- `command` — the slash command, `/<name>`
- `argument-hint` — e.g. `<ticket-id>` or `<ticket-id> <slice-number>`
- `allowed-tools` — comma-separated tool allowlist

There is **no `version` field** in any skill (see Q5). `allowed-tools` varies per skill and may scope Bash (e.g. `Bash(pwd:*)`) and list specific MCP tools.

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
**Dependencies:** `allowed-tools` references the Agent tool and `mcp__linear-russelltsherman__*` tools by exact name (e.g. `qrspi-design/SKILL.md:6`, `qrspi-work/SKILL.md:6`).
**Implicit contracts:** All five fields appear in all 10 skills; `name` == directory == `command` minus the leading slash. Tool names in `allowed-tools` must match real tool identifiers.

## Q4: What argo CLI command groups and flags appear in existing skill or reference material in this repo, if any, that could be reused or that establish a naming/style precedent?

**Answer:** NOT FOUND in skill/reference material. `grep -rli 'argo'` matches only unrelated container-sandbox research docs (`docs/container-sandbox/research/q06,q14,q15,q16-*.md`) and the questions file — none reference an `argo` workflows CLI; these are about CDN allowlisting, package installation, policy storage, and test-runner sandboxing. No `argo`, `argo submit`, `argo workflows`, or related command groups appear in any SKILL.md, agent prompt, or `references/` file.

The only CLI precedent for command/flag style in skills is the Graphite CLI usage embedded in `qrspi-work/SKILL.md` (e.g. `gt checkout <branch> --no-interactive` at `:269`, `gt modify -c --no-interactive` at `:277`) — these establish a `--no-interactive` non-interactive-flag convention for CLI calls inside skills.

**Evidence:**

```
git branch --show-current | grep -q '<ticket-id>/planning' || gt checkout <ticket-id>/planning --no-interactive
```

— `.claude/skills/qrspi-work/SKILL.md:269`
**Dependencies:** Graphite CLI (`gt`) is the only CLI invoked from skill bodies.
**Implicit contracts:** CLI calls inside skills append non-interactive flags (`--no-interactive`) because the harness blocks interactive prompts.

## Q5: How is skill versioning recorded and incremented in this repo — is there a version field or changelog convention applied when a skill is created or modified?

**Answer:** There is **no per-skill version field and no per-skill changelog**. `grep -rni 'version:'` across `.claude/skills/` and `.qrspi/templates/` returns nothing; no `CHANGELOG*` file exists anywhere. Versioning exists only at the **eval-iteration level**, not the skill-definition level: the eval harness computes a content hash of the skill file and tracks scored versions `v1..vN` in a results ledger.

**Evidence:**

```python
# Compute skill version hash
skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]
```

— `scripts/run_eval.py:154-155`

```python
def build_ledger_entry(version: dict, parent: str, regressions: list) -> dict:
    ...
    return {
        "version": version["version"],
        "parent": parent,
        ...
    }
```

— `scripts/report.py:57-74`
**Dependencies:** `report.py` reads `results/<version>/grades.json` and writes `results/ledger.json`; versions are directory names (`v1`, `v2`, …) created by `run_loop.sh` (`run_loop.sh:33-34`).
**Implicit contracts:** A "version" is an iteration of a prompt under eval, identified by a 12-char sha256 prefix of file content, not a frontmatter field. Editing a skill changes its hash, which is how the ledger distinguishes versions.

## Q6: Where are reference files (references/ directory) linked from within SKILL.md bodies, and what mechanism loads them on demand versus inlining them?

**Answer:** Only `qrspi-work` uses a `references/` directory, and it is referenced exactly once, by a relative-path instruction telling the agent to read the file at the moment it is needed (on-demand / progressive disclosure), rather than inlining the content. The mechanism is a natural-language directive ("Read `references/review-cascade.md`") executed via the agent's `Read` tool; there is no automatic include/templating system.

**Evidence:**

```
   c. Read `references/review-cascade.md` for cascade logic.
   d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
```

— `.claude/skills/qrspi-work/SKILL.md:272-273`
**Dependencies:** `qrspi-work`'s `allowed-tools` includes `Read` (`qrspi-work/SKILL.md:6`), which is what loads the reference file.
**Implicit contracts:** References are linked by relative path (relative to the skill directory) and loaded only when the relevant branch of the workflow is reached — keeping the main body lean. The reference is consulted, not inlined.

## Q7: What enforces the SKILL.md body limit (under 500 lines / 5000 tokens), and is there an existing lint, test, or eval that fails when a skill body exceeds that threshold?

**Answer:** Nothing in the repo enforces a SKILL.md body limit. There is a generic `line_count(filename, max_lines, result)` check in the grade registry, but it operates on **eval execution output**, not on SKILL.md files, and no eval case applies it to a skill body (the suite has no skill-creation cases — see Q10). No lint, pre-commit hook, or test checks SKILL.md length. Empirically, the limit is **violated** by `qrspi-work/SKILL.md` at **730 lines** (see Inconsistencies). Other bodies range 25–119 lines.

**Evidence:**

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:35-40`
**Dependencies:** `line_count` is registered in `CHECKS` (`grade.py:146-157`) and invoked only for programmatic assertions in `evals/suite.json` cases.
**Implicit contracts:** `line_count` checks `result["output"]` (an agent's produced artifact), not a file on disk. To enforce a SKILL.md budget you would need a new check + a new eval/lint; none exists.

## Q8: How do existing skills handle content that exceeds the body size budget — what is the established convention for pushing detail into references/ versus keeping it in SKILL.md?

**Answer:** The established (and only) precedent for offloading detail is `qrspi-work`, which keeps orchestration logic in the body and pushes the review-feedback "cascade logic" into `references/review-cascade.md`, loaded on demand (Q6). However, this is applied inconsistently: `qrspi-work/SKILL.md` is still 730 lines despite having a references file, while the other thin-wrapper skills keep bodies tiny (25–35 lines) by delegating the entire prompt to a peer file in `.claude/agents/`. So there are effectively **two offloading strategies** in the repo:

1. Wrapper → agent prompt: SKILL.md is a ~25-line dispatcher; the real instructions live in `.claude/agents/<name>.md` (e.g. `qrspi-research/SKILL.md:11`).
2. Body + references/: detail-heavy branches read a `references/*.md` on demand (`qrspi-work/SKILL.md:272`).

**Evidence:**

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:11`
Line counts: `qrspi-research` 26, `qrspi-structure` 25, `qrspi-worktree` 25, `qrspi-ticket` 119, `qrspi-work` 730.
**Dependencies:** Strategy 1 depends on `.claude/agents/` peer files; strategy 2 depends on the skill's own `references/`.
**Implicit contracts:** Thin wrappers must keep behavioral parity by pointing to exactly one agent prompt; the references strategy assumes the agent will read the file when the relevant step is reached.

## Q9: What naming and collision rules apply to a new skill directory and its `name` frontmatter value, and what happens if a name duplicates an existing skill?

**Answer:** No collision-detection or registration logic exists in the repo. There is no discovery/registration module; skills are discovered by Claude Code from `.claude/skills/`. The only observable rule is a **convention**, consistently followed across all 10 skills: directory name == `name:` frontmatter == `command:` without the leading slash. All current names are `qrspi-*`. What happens on a duplicate is **NOT FOUND** in repo scope — there is no code that detects or resolves duplicate `name` values; behavior would be determined by the (external) Claude Code harness, not this repo.

**Evidence:**

```
name: qrspi-worktree
command: /qrspi-worktree
```
(directory: `.claude/skills/qrspi-worktree/`)
— `.claude/skills/qrspi-worktree/SKILL.md:2-4`
**Dependencies:** None in-repo; discovery/registration is external to `REPO_ROOT`.
**Implicit contracts:** Uniqueness of `name`/directory/`command` is assumed but unenforced. New skills should pick an unused slug; the `qrspi-` prefix is the de-facto namespace for this project.

## Q10: How does the skill-creator eval loop measure skill performance, and what command or harness runs evals for a single skill?

**Answer:** The repo has a generic 5-stage eval harness (not specific to `skill-creator`, which is absent). The orchestrator is `run_loop.sh`, invoked as `./run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]`. Each iteration runs: (1) `run_eval.py` executes N trials/case; (2) `grade.py` scores with weighted programmatic + LLM-judge assertions; (3) checks target/regression; (4) `diagnose.py` + `revise.py` propose edits. Performance is the mean test-split score (0–1). Note: agent execution, LLM judge, and script checks are **stubs** (return zeros/None), so the loop runs end-to-end but produces zero scores today.

**Evidence:**

```bash
python3 scripts/run_eval.py --skill "$SKILL_PATH" --suite "$EVAL_SUITE" \
    --output "$OUTPUT_DIR" --trials "$TRIALS" --workers "$WORKERS"
...
python3 scripts/grade.py --results "${OUTPUT_DIR}/results.json" --suite "$EVAL_SUITE"
```

— `run_loop.sh:43-55`

```python
# Replace this block with actual agent invocation:
messages = build_messages(case)
result.output = ""
```

— `scripts/run_eval.py:117-133` (execution stub)
**Dependencies:** `run_loop.sh` → `run_eval.py` → `grade.py` → (`diagnose.py`, `revise.py`) → `report.py`. Suite default: 3 trials, 120s timeout, 4 workers (`run_eval.py:37-39`).
**Implicit contracts:** A "skill" passed to the harness is any prompt file path (`--skill`); the harness is content-agnostic and would run against a new SKILL.md or agent prompt the same way. Per-case scoring is weighted-passed/max normalized to 0–1 (`grade.py:246-265`).

## Q11: Are there existing tests or eval fixtures that validate SKILL.md frontmatter and directory structure conformance to the agentskills.io standard?

**Answer:** NOT FOUND. `grep -rni 'agentskills'` matches only the questions file. There is no test, eval case, fixture, or schema that validates SKILL.md frontmatter or directory structure. The eval suite (`evals/suite.json`, 15 cases `case_001`–`case_015`) covers only the QRSPI phases (questions, research, design, structure, plan, worktree, implement, pr) — none target skill creation or structure conformance. The programmatic checks in `grade.py` validate artifact content (sections, citations, line counts, no-solution-language), not SKILL.md conformance.

**Evidence:**

```
case_001 questions (train) | case_003 research | case_005 design |
case_007 structure | case_009 plan | case_010 worktree |
case_011 implement | case_013 pr ...   (no skill-creation case)
```

— `evals/suite.json` (15 cases; enumerated via parse) and `docs/eval-system.md:15-28`
**Dependencies:** Fixtures live in `evals/fixtures/`, golden outputs in `evals/golden/` (currently `.gitkeep` only). Per `docs/eval-system.md:80-103`, only 4 of 21 referenced fixtures exist.
**Implicit contracts:** Validating SKILL.md conformance would require a new check function + a new eval case/fixture; the harness has the extension point (the `CHECKS` registry, `grade.py:146-157`) but no such check is implemented.

## Q12: How are skill eval results reported (output format, location of result artifacts, variance/benchmark output), and where would a reviewer look to confirm a new skill passes?

**Answer:** Results are JSON artifacts written under `results/<version>/`. `run_eval.py` writes `results/<version>/results.json` (raw trial outputs). `grade.py` writes `results/<version>/grades.json` with per-case `mean_score`/`stddev` and suite-level `train_score`, `test_score`, `train_test_gap`. `report.py` writes `results/report.json` and `results/ledger.json`, comparing versions and emitting plateau/overfitting/regression alerts plus promotion criteria. A reviewer confirms a new skill passes by checking `grades.json` (`test_score` meets target) and `report.json` (no regressions, gap ≤ 0.1, promotion `true`).

**Evidence:**

```python
output = { "train_score": train_scores["mean"], "test_score": test_scores["mean"],
           "train_test_gap": round(abs(...), 4), ... "cases": case_grades }
grades_path = os.path.join(out_dir, "grades.json")
```

— `scripts/grade.py:350-365`

```python
"alerts": {"plateau": plateau, "overfitting": overfitting,
           "has_regressions": latest["regression_count"] > 0}
```

— `scripts/report.py:145-149`
**Dependencies:** `results/` currently holds only `.gitkeep`. Promotion criteria: test score no-regression, no per-case drop > 0.2, gap ≤ 0.1 (`report.py:77-90`).
**Implicit contracts:** Reviewer-facing signal is `test_score` (test split = held-out, the trustworthy number) and the promotion block; variance is the per-case `stddev` and suite `stddev`/`min`/`max` (`grade.py:268-277`).

---

## Discovered Patterns

- **Thin-wrapper + agent split.** 8 of 10 skills are ~25-line dispatchers whose only job is to parse `$ARGUMENTS`, resolve `REPO_ROOT` from `pwd`, and spawn a peer agent in `.claude/agents/<name>.md`. The real prompt lives in the agent file. (`qrspi-research/SKILL.md:11`, `qrspi-implement/SKILL.md:11`)
- **Template/artifact path convention.** Generation reads `.qrspi/templates/<phase>.md` and writes `.qrspi/<ticket-id>/<phase>.md`; the template is reference-only and never overwritten. (`qrspi-research/SKILL.md:22-23`)
- **Post-spawn verification.** Wrappers verify the produced artifact exists and is non-empty before declaring success. (`qrspi-research/SKILL.md:25`, `qrspi-implement/SKILL.md:34`)
- **Frontmatter shape is uniform.** Exactly `name`, `description`, `command`, `argument-hint`, `allowed-tools` in every skill; `allowed-tools` scopes Bash (`Bash(pwd:*)`) and lists MCP tools by exact name.
- **Non-interactive CLI discipline.** Every `git`/`gt` call inside a skill passes `--no-interactive`. (`qrspi-work/SKILL.md:269,277`)
- **Eval harness is content-agnostic and stub-backed.** It runs against any prompt file path; execution, LLM judge, and script checks are placeholders returning zeros/None (`run_eval.py:117-137`, `grade.py:208-241`).
- **Versioning is iteration-level, not definition-level.** Skill identity for evals = sha256 prefix of file content; no frontmatter version. (`run_eval.py:154-155`)

## Inconsistencies

- **`qrspi-work/SKILL.md` is 730 lines** — far over the 500-line / 5000-token budget implied by Q7. It even has a `references/` directory (the offloading mechanism) yet keeps most logic inline, contradicting the progressive-disclosure pattern it partially adopts.
- **No enforcement of the body-size budget.** `grade.py:35` has a `line_count` check, but it targets eval output, not SKILL.md files, and no eval applies it to a skill body — so the 730-line violation goes undetected.
- **`run_loop.sh` example path is stale.** Its usage comment references `.qrspi/agents/01-questions.md` (`run_loop.sh:10`), but agent prompts actually live at `.claude/agents/qrspi-questions.md`. The old numbered-agent naming no longer matches the codebase.
- **Eval harness advertised as functional but is mostly stubbed.** `docs/eval-system.md:108` confirms the pipeline "produces zeros" — agent execution, LLM judge, and script checks are unimplemented, and 17 of 21 fixtures are missing (`docs/eval-system.md:80-103`).
- **Check registry is incomplete.** `docs/eval-system.md:96` states 14 of ~37 referenced checks are implemented in `grade.py`; suite assertions can reference unimplemented checks, which `grade.py:194-197` silently skips (`passed: None`).
- **No `skill-creator` and no `argo` in repo.** Both subjects of the questions are absent from `REPO_ROOT`; conclusions about them must be drawn from external/global tooling, not this codebase.
