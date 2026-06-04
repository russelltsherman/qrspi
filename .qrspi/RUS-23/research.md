# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

> Scope note: Several questions target the **`skill-creator`** skill. That skill is NOT part of this
> repository — it is a globally-available skill (listed in the harness skill registry) whose definition
> lives outside `REPO_ROOT`. Per the research firewall, files outside the project were not read. Those
> questions are answered "NOT FOUND — outside project scope" with the in-repo evidence that does exist.

## Q1: What directory layout and file set does an existing skill produce (SKILL.md plus references/, scripts/, assets/), and where does this repo place skill source so a new Crossplane skill matches the established location?

**Answer:** Skill source lives under `.claude/skills/<skill-name>/`, one directory per skill, each
containing a `SKILL.md` as the entry point. Of the 10 skills present, 9 contain ONLY a `SKILL.md`; the
single multi-file example is `qrspi-work/`, which adds a `references/` subdirectory holding one file
(`review-cascade.md`). No skill in this repo currently ships a `scripts/` or `assets/` subdirectory —
those are conventional but unused here. A new Crossplane skill matching the established location would be
`.claude/skills/<name>/SKILL.md` (+ optional `references/`). Note the architectural split unique to this
repo: the QRSPI *phase* skills are thin slash-command wrappers; the substantive prompt logic lives in a
sibling tree, `.claude/agents/<name>.md` (8 agent files).

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md          (only file)
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   <- only references/ dir in repo
.claude/agents/qrspi-design.md   ... qrspi-pr.md          (8 agent prompt files)
```

— `.claude/skills/` (directory listing); `.claude/skills/qrspi-work/references/review-cascade.md:1`
— `README.md:76-98` documents the `agents/` vs `skills/` split

**Dependencies:** Skill wrappers depend on (spawn) the matching `.claude/agents/<name>.md` agent; agents depend on `.qrspi/templates/` for output formats.
**Implicit contracts:** Directory name == frontmatter `name` == `command` slug (minus the leading `/`). Phase skills delegate all real content to `.claude/agents/`; only `qrspi-ticket` and `qrspi-work` carry full inline logic in SKILL.md.

## Q2: How does the skill-creator skill ingest source material and emit the generated SKILL.md plus reference files — what inputs does it expect and what output paths does it write to?

**Answer:** NOT FOUND — outside project scope. The `skill-creator` skill is not defined anywhere under
`REPO_ROOT`. Searches across `*.md`, `*.js`, `*.py` returned only *references to* skill-creator, never a
definition. The only in-repo mention as a process step is in the structure-phase agent, which names
"invoking skill-creator" as a validation action but does not specify its inputs or output paths.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final
   step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`
Searches attempted: `grep -rn -i "skill-creator|skill creator|agentskills"` over the repo (only hits: this agent file + the questions artifact); `find . -type d -name "*skill-creator*"` (no results).

**Dependencies:** N/A (definition out of scope).
**Implicit contracts:** N/A.

## Q3: What exact fields are required in SKILL.md frontmatter (name, description, and any others) for it to be considered valid per the agentskills.io pattern this repo follows?

**Answer:** No schema/validator for SKILL.md frontmatter exists in the repo, so "required" is observed
empirically from the 10 existing skills. Every SKILL.md uses YAML frontmatter delimited by `---` lines.
Fields present across ALL 10 skills: `name`, `description`, `command`, `allowed-tools`. Nine of ten also
include `argument-hint` (the wrapper skills); `qrspi-ticket` is the one without it. There is no
`agentskills.io`-named convention file in the repo. Tool-permission scoping appears via Bash globs
(e.g., `Bash(pwd:*)`).

**Evidence:**

```
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-7`

**Dependencies:** `allowed-tools` enumerates the tools the spawned agent may use (e.g., `Agent`, `Read`, `Bash`, `mcp__linear__*`).
**Implicit contracts:** Frontmatter is the FIRST content in the file (line 1 `---`). `command` is the slash form of `name`. There is no automated frontmatter validator in this repo — validity is convention-enforced.

## Q4: What are the description-field conventions used by existing skills (length, trigger phrasing, "use when" structure)?

**Answer:** Descriptions are single-line strings. Measured lengths range from 74 chars (`qrspi-worktree`)
to 489 chars (`qrspi-work`); the eight thin wrappers cluster at 74-161 chars, while the orchestrator
`qrspi-work` is far longer (489) because it embeds explicit trigger phrasing. The dominant pattern is
"<what it does>. Use when/after <condition>." Short wrappers state the post-condition (e.g., "Use after
research is approved."). `qrspi-work` is the richest example, with an explicit "Trigger on any variant
of:" list of natural-language phrasings, and is the only description wrapped in double quotes (because it
contains a colon and commas).

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user
asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of:
'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference
to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (489 chars); compare `.claude/skills/qrspi-worktree/SKILL.md:3` (74 chars: "Build a session-aware task DAG from the plan. Use after plan is approved.")

**Dependencies:** Description quality drives auto-invocation/trigger matching by the harness.
**Implicit contracts:** "Use when/after …" clause encodes the lifecycle gate (sequential phase ordering). Descriptions with special chars (`:`, quotes) must be quoted.

## Q5: Does the skill-creator skill provide an eval/benchmark sub-capability, and what command or entry point invokes it for measuring skill triggering and performance?

**Answer:** NOT FOUND — outside project scope. The `skill-creator` skill is not defined in the repo, so
its eval sub-capability (if any) cannot be observed here. What DOES exist in-repo is an independent eval
harness (`scripts/run_eval.py` + `evals/suite.json` + `docs/eval-system.md`), but that harness targets
QRSPI *phase prompts*, not skill triggering, and the suite contains no skill-creator or
trigger-accuracy cases (see Q10/Q11).

**Evidence:** `evals/suite.json:15-779` — all 15 cases have `"phase"` of questions/research/design/structure/plan/worktree/implement/pr; none reference skill triggering. No `grep` hit for skill-creator eval entry points in the repo.

**Dependencies:** N/A.
**Implicit contracts:** N/A.

## Q6: How are reference documents under a skill's `references/` directory linked or referenced from SKILL.md so an agent loads them on demand?

**Answer:** The single in-repo example links a reference file by a relative-path mention in backticks
inside prose — there is no special directive syntax. `qrspi-work/SKILL.md` says "(see
`references/review-cascade.md`)" at the point where the cascade logic is relevant; the agent is expected
to read that file on demand rather than have it inlined. The repo also uses the same pattern to point at
`docs/` files (e.g., "See `docs/qrspi-pr-gated-lifecycle-design.md`"). So the convention is: keep the
SKILL.md body lean and refer to `references/<file>.md` by relative path in backticks where it applies.

**Evidence:**

```
... the cascade is bounded to the phase's own artifacts (see `references/review-cascade.md`).
Do NOT touch downstream phases here ...
```

— `.claude/skills/qrspi-work/SKILL.md:282`; reference target `.claude/skills/qrspi-work/references/review-cascade.md:1-77`
Also: `.claude/skills/qrspi-work/SKILL.md:24` ("See `docs/qrspi-pr-gated-lifecycle-design.md`")

**Dependencies:** The referenced file (`review-cascade.md`) is consumed only by `qrspi-work`.
**Implicit contracts:** Relative path is resolved from the skill directory (`references/…`) for repo docs from repo root (`docs/…`). Loading is "on demand" — the link is a prose pointer, not an include directive.

## Q7: What mechanism enforces the SKILL.md body size limit (under 500 lines / 5000 tokens), and how do existing large skills split content between the body and references/ to stay within it?

**Answer:** No automated mechanism enforces a SKILL.md size limit in this repo — there is no linter,
hook, or test that checks SKILL.md line/token counts. (The only line-count assertion in the eval suite,
`line_count('design.md') <= 300`, targets the design *artifact*, not SKILL.md — `evals/suite.json:242`.)
Observed sizes: eight wrappers are 25-35 lines; `qrspi-ticket` is 127 lines; `qrspi-work` is **565
lines — exceeding the 500-line guideline cited in the question**. The repo's actual size-control
strategy is structural, not enforced: phase skills externalize logic into `.claude/agents/<name>.md`,
and `qrspi-work` further offloads the cascade subsection into `references/review-cascade.md` (77 lines).

**Evidence:**

```
565 .claude/skills/qrspi-work/SKILL.md          <- over the 500-line guideline
127 .claude/skills/qrspi-ticket/SKILL.md
 77 .claude/skills/qrspi-work/references/review-cascade.md
 25-35  the eight thin wrapper SKILL.md files
```

— `wc -l` across `.claude/skills/*/SKILL.md`; reference offload at `.claude/skills/qrspi-work/SKILL.md:282` → `references/review-cascade.md`

**Dependencies:** None automated.
**Implicit contracts:** Size is managed by convention (wrapper-vs-agent split, references/ offload), not validated. A new skill cannot rely on tooling to flag oversize.

## Q8: How do existing skills express version-dependent or branching guidance, and is there an established "default to X unless environment indicates Y" pattern?

**Answer:** No skill encodes software *version* branching (no v1/v2 toggles). The established pattern for
conditional judgment is "resolve from config; if unset/missing, fall back to a default, else
discover/ask." The clearest example is `qrspi-ticket`'s team resolution: read `.qrspi/config.json`; if
`linearTeam` is missing, list teams and use the only one or ask. Defaults-on-unset also appears for
`project` ("defaulting to `QRSPI` when unset"). The harness-wide convention (documented in CLAUDE.md) is
"resolved (not hard-coded)" config with `@me`/`QRSPI` fallbacks. Branching is expressed as numbered
imperative prose with explicit `if … otherwise …` clauses, not as data tables.

**Evidence:**

```
- `team`: use its `linearTeam` field. If the file is missing or has no `linearTeam`,
  call `mcp__linear__list_teams`; if exactly one team exists, use it, otherwise ask the
  user which team to file under.
- `project`: use its `linearProject` field, defaulting to `"QRSPI"` when unset.
```

— `.claude/skills/qrspi-ticket/SKILL.md:108-112`

**Dependencies:** Config source `.qrspi/config.json` (gitignored; example at `.qrspi/config.example.json`).
**Implicit contracts:** "default to X unless Y" is realized as: config value → single-candidate auto-pick → ask the user. Never hard-code the environment-specific value.

## Q9: When skill-creator is asked to create a skill whose name collides with an existing one, how does it behave, and what naming constraints apply to the skill directory and frontmatter name?

**Answer:** Collision behavior: NOT FOUND — outside project scope (skill-creator is not in the repo).
Naming constraints are observable empirically from existing skills: directory names and frontmatter
`name` values are identical lowercase kebab-case strings (`qrspi-design`, `qrspi-work`, etc.), all sharing
the `qrspi-` prefix here; `command` is the same string with a leading `/`. Names use only
`[a-z0-9-]`. Because each skill is its own directory under `.claude/skills/`, a name collision would mean
two directories of the same path — the filesystem itself would prevent a second skill of the same name in
the same location.

**Evidence:**

```
name: qrspi-worktree        # dir: .claude/skills/qrspi-worktree/   command: /qrspi-worktree
name: qrspi-questions       # dir: .claude/skills/qrspi-questions/  command: /qrspi-questions
```

— `.claude/skills/qrspi-worktree/SKILL.md:2-4`, `.claude/skills/qrspi-questions/SKILL.md:2-4` (pattern holds for all 10)

**Dependencies:** N/A for collision behavior.
**Implicit contracts:** dirname == `name` == `command` slug; lowercase kebab-case; uniqueness enforced by the one-dir-per-skill filesystem layout, not by any tool.

## Q10: What eval or verification harness exists for skills in this repo, and is it functional or a placeholder?

**Answer:** A 5-stage eval pipeline exists on paper: `run_eval.py` (execute), `grade.py` (score),
`report.py` (compare), `diagnose.py` (categorize failures), `revise.py` (propose edits), driven by
`evals/suite.json` (15 cases). It is a **non-functional placeholder**. `run_eval.py`'s `execute_single`
is an explicit stub that returns empty output and zero tokens (no agent is invoked). `docs/eval-system.md`
states the three critical gaps (agent execution, LLM-judge integration, missing fixtures) and that the
pipeline "runs end-to-end but produces zeros." Of the actual pipeline scripts, only `run_eval.py`,
`grade.py` (referenced), and `check_scope.py` exist in `scripts/`; `check_scope.py` IS present and
implemented. CLAUDE.md corroborates: "The `evals/` + `scripts/run_eval.py` harness is a non-functional
placeholder." Note: this harness targets QRSPI *phase prompts*, not skill creation/triggering.

**Evidence:**

```
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
...
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:117-137`; status table at `docs/eval-system.md:93-108` ("Agent execution runtime | Stub"); `.claude/CLAUDE.md:106`

**Dependencies:** `run_eval.py` reads `--skill` (a prompt file) and `--suite` (`evals/suite.json`); writes `results.json` to `--output`. `evals/fixtures/` supplies case context (only 4 of 21 fixtures exist — `docs/eval-system.md:80-89`).
**Implicit contracts:** A suite must have top-level `name` + `cases`; each case needs `id`, `prompt`, `assertions` (validated in `load_suite`, `scripts/run_eval.py:42-58`). Three assertion types: `programmatic`, `llm_judge`, `script`.

## Q11: How are skill triggering accuracy and description quality measured (variance analysis, benchmarks), and what command produces those metrics?

**Answer:** NOT FOUND in the repo for *skill triggering/description* metrics specifically. The in-repo
eval harness measures *phase-output quality* (file existence, section presence, citation compliance, LLM-
judge criteria), not whether a skill's `description` triggers correctly — `evals/suite.json` has no
triggering/variance case. The harness does compute variance-style aggregates (mean, stddev, min, max per
suite; train/test split with overfitting/plateau detection in `report.py`), and the nominal command is
`python3 scripts/run_eval.py --skill <prompt> --suite evals/suite.json --output <dir>` — but per Q10 it
returns zeros. Skill *triggering* benchmarking would be a capability of the out-of-scope `skill-creator`
skill, not this repo.

**Evidence:**

```
- Per-suite: mean across cases, with stddev, min, max.
- Train and test scores are computed separately; the train-test gap flags overfitting.
```

— `docs/eval-system.md:42-55`; CLI surface at `scripts/run_eval.py:217-236` (`--skill/--suite/--output/--trials/--workers/--timeout`)

**Dependencies:** `report.py`/`grade.py` are named in `docs/eval-system.md:7-11` but are stubs/partial per the status table.
**Implicit contracts:** Variance metrics assume real per-trial scores, which the stub runtime does not produce.

## Q12: How does the skill-creator skill surface progress, validation results, or errors during generation?

**Answer:** NOT FOUND — outside project scope (skill-creator not in repo). For comparison, the in-repo
eval *runner* surfaces progress via stdout: a per-execution `[i/N] case trial OK|ERROR (Xms)` line, a
header with the skill hash and worker count, and a final "Results written to …" line; per-trial errors
are captured into `ExecutionResult.error` and reported as `ERROR`/`EXCEPTION` rather than crashing the
run. No frontmatter-validation or size-limit-violation reporting exists anywhere in the repo (consistent
with Q3/Q7 — there is no SKILL.md validator).

**Evidence:**

```
print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ({result.duration_ms:.0f}ms)")
...
print(f"\nResults written to {output_path}")
```

— `scripts/run_eval.py:179-213`; error capture at `scripts/run_eval.py:139-141`

**Dependencies:** N/A for skill-creator.
**Implicit contracts:** N/A.

---

## Discovered Patterns

- **Wrapper-vs-agent split (unique to this repo).** Phase skills under `.claude/skills/<name>/SKILL.md`
  are thin slash-command wrappers (25-35 lines) whose body says "All prompt content lives in
  `.claude/agents/<name>.md`." The substantive logic lives in 8 sibling agent files. Only `qrspi-ticket`
  and `qrspi-work` carry full inline logic in their SKILL.md. A generic "agentskills.io" single-file
  skill (everything in SKILL.md) is the exception here, not the rule. (`README.md:76-98`)
- **Frontmatter field set is consistent but un-validated:** `name`, `description`, `command`,
  `allowed-tools` on all 10; `argument-hint` on 9. No schema/linter enforces it.
- **Naming identity:** dirname == frontmatter `name` == `command` minus `/`, lowercase kebab-case,
  `qrspi-` prefixed.
- **"Resolve, don't hard-code" config idiom:** read `.qrspi/config.json`, fall back to a default
  (`QRSPI`, `@me`), else discover/ask. Used for Linear team/project and PR reviewers.
  (`.claude/skills/qrspi-ticket/SKILL.md:106-112`; `.claude/CLAUDE.md` reviewers section)
- **Templates as single source of truth:** output formats live in `.qrspi/templates/`; skills/agents
  reference them rather than embedding format. (`README.md:126`)
- **References offload by prose pointer:** large skills point at `references/<file>.md` in backticks
  rather than inlining or using an include directive. Only one such file exists.
- **Self-locating stdlib-only Python scripts with `_test.py` siblings** is the repo's tooling
  convention (`scripts/qrspi_*.py`), though the eval scripts are the placeholder exception.

## Inconsistencies

- **500-line guideline vs reality:** `qrspi-work/SKILL.md` is 565 lines, exceeding the under-500-line
  guideline cited in Q7. Nothing enforces the limit, and the repo's own flagship orchestrator skill
  violates it. (`.claude/skills/qrspi-work/SKILL.md`, 565 lines)
- **Documented pipeline vs implemented pipeline:** `docs/eval-system.md:7-11` describes 5 scripts
  (`run_eval.py`, `grade.py`, `report.py`, `diagnose.py`, `revise.py`); only `run_eval.py` and
  `check_scope.py` were found present in `scripts/`. The doc itself admits stubs (`docs/eval-system.md:93-108`).
- **Eval suite scope vs questions' premise:** several questions assume a skill-creation/triggering eval
  capability in-repo, but `evals/suite.json` covers only QRSPI phase outputs — there is no
  skill-triggering, variance-of-triggering, or skill-creator case.
- **`skill-creator` referenced as a real process step but undefined in-repo:** `.claude/agents/qrspi-structure.md:40`
  instructs "invoking skill-creator" as a validation step, yet no skill-creator definition exists under
  `REPO_ROOT` (it is a global skill). A reader of this repo alone cannot find its contract.
- **Missing fixtures:** `evals/suite.json` references 21 fixture files; only 4 exist
  (`docs/eval-system.md:80-89`), so even the programmatic checks cannot run for most cases.
