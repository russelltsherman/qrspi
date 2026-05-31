# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: How does an existing skill's SKILL.md flow from frontmatter to body to `references/` files — what content lives in the body versus what is deferred to reference files?

**Answer:** Skills in this repo follow two body styles. The `qrspi-*` phase skills are *thin wrappers*: a short frontmatter block plus a one-paragraph body that delegates all logic to an agent definition in `.claude/agents/`. The richer pattern is `qrspi-work`, whose SKILL.md body is a long procedural document (731 lines) that defers only one piece of branching logic to a `references/` file. The body holds the always-needed procedure; the reference file holds a sub-procedure loaded on demand.
**Evidence:**

```
# /qrspi-design

Thin wrapper that fetches the ticket from Linear and spawns the `qrspi-design` agent. All prompt content lives in `.claude/agents/qrspi-design.md`.
```

— `.claude/skills/qrspi-design/SKILL.md:9-12`

```
   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:272`
**Dependencies:** SKILL.md body → `.claude/agents/<name>.md` (for wrappers); SKILL.md body → `references/<file>.md` (for on-demand sub-procedures).
**Implicit contracts:** Reference files are addressed by a path relative to the skill directory (`references/<file>.md`), and the body explicitly instructs "Read `references/...`" at the point of need rather than inlining it.

## Q2: Where do skill source files physically live in this repo, and is there a distinction between project-local skills (`.claude/skills/`) and the agent-skills standard layout the ticket references?

**Answer:** All project-local skills live under `.claude/skills/<skill-name>/SKILL.md`. There are 10 directories, all `qrspi-*` workflow skills. Only `qrspi-work` carries a `references/` subdirectory. No skill in this repo has a `scripts/` or `assets/` subdirectory. The repo separately has top-level `scripts/`, `evals/`, `docs/`, and `results/` directories that belong to the eval harness, not to any individual skill.
**Evidence:**

```
=== .claude/skills dirs ===
qrspi-design  qrspi-implement  qrspi-plan  qrspi-pr  qrspi-questions
qrspi-research  qrspi-structure  qrspi-ticket  qrspi-work  qrspi-worktree
=== skills with references/ ===
.claude/skills/qrspi-work/references
=== skills with scripts/ ===
(none)
```

— directory listing of `.claude/skills/` and `find .claude/skills -type d -name references|scripts`
**Dependencies:** `.claude/skills/` is the install location the harness loads skills from.
**Implicit contracts:** A new skill is a new directory `.claude/skills/<kebab-name>/` containing at minimum `SKILL.md`; optional `references/`, `scripts/`, `assets/` subdirectories are co-located inside that directory. The agent-skills standard layout the ticket references maps directly onto this `.claude/skills/<name>/` convention.

## Q3: What is the exact required SKILL.md frontmatter schema as used by skills already in this repo?

**Answer:** Every SKILL.md begins with a YAML frontmatter block delimited by `---`. Observed fields: `name` (kebab-case, matches directory), `description` (a triggering blurb), `command` (slash command, e.g. `/qrspi-design`), `argument-hint` (e.g. `<ticket-id>`), and `allowed-tools` (comma-separated tool allowlist). `name` and `description` appear in all skills; `command`/`argument-hint` appear in all invokable skills; `allowed-tools` appears in all. `qrspi-work` additionally quotes its multi-sentence `description` value.
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
**Dependencies:** The harness parses this frontmatter to register the slash command and the auto-trigger description.
**Implicit contracts:** `name` must equal the directory name. `description` is the auto-invocation signal — it states *when to use* the skill, often with explicit trigger phrases. `allowed-tools` constrains the tools available while the skill runs.

## Q4: What does the skill-creator skill expect as inputs and what directory structure does it produce, and does it include an eval loop?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. The `skill-creator` (Anthropic skill builder) skill is a global skill; no copy exists under `REPO_ROOT/.claude/skills/`. Searched `ls .claude/skills/` (only `qrspi-*` present) and `find .claude/skills -name '*creator*'` (no matches). Its inputs, output structure, and eval loop cannot be confirmed from within the repo.
**Evidence:**

```
=== .claude/skills dirs ===
qrspi-design  qrspi-implement  qrspi-plan  qrspi-pr  qrspi-questions
qrspi-research  qrspi-structure  qrspi-ticket  qrspi-work  qrspi-worktree
```

— directory listing of `.claude/skills/`
**Dependencies:** Unknown from within scope.
**Implicit contracts:** Unknown from within scope. The standard skill layout (Q2) is the only in-repo signal for the structure a skill builder would target.

## Q5: What naming convention is used for skill directory names and the `name` field, and is there a collision constraint with existing skill names?

**Answer:** Directory names and `name` fields are kebab-case and verb-first or noun-phrase (`qrspi-design`, `qrspi-worktree`). All existing project skills share the `qrspi-` prefix because they belong to one workflow family; a new unrelated skill need not adopt that prefix. The `name` field always equals the directory name. No skill named for GitLab pipelines exists, so a new `writing-gitlab-pipelines` (or similar kebab name) does not collide.
**Evidence:**

```
name: qrspi-worktree   (dir: .claude/skills/qrspi-worktree/)
name: qrspi-ticket     (dir: .claude/skills/qrspi-ticket/)
```

— `.claude/skills/qrspi-worktree/SKILL.md:2`, `.claude/skills/qrspi-ticket/SKILL.md:2`
**Dependencies:** Harness keys skills by `name`/directory.
**Implicit contracts:** kebab-case; `name` == directory name; uniqueness across `.claude/skills/`.

## Q6: Are there constraints on SKILL.md body length or token budget enforced anywhere (lint, eval, CI)?

**Answer:** No automated length/token check exists for SKILL.md bodies. The eval harness (`evals/suite.json`, `scripts/run_eval.py`, `scripts/grade.py`) evaluates the *qrspi workflow agent prompts* against fixture tickets — it does not lint arbitrary new skills for body length. The "under 500 lines / 5000 tokens" target in the ticket is a convention, not a CI-enforced rule in this repo. (Observed: `qrspi-work/SKILL.md` is itself 731 lines, so the budget is not universally applied even internally.)
**Evidence:**

```
"name": "qrspi-agent-evals",
"description": "Eval suite for QRSPI workflow agent prompts",
...
"check": "section_count('questions.md', '## ') >= 5",
```

— `evals/suite.json:2-3,...` (assertions target generated artifacts like `questions.md`, not SKILL.md length)
**Dependencies:** `scripts/run_eval.py` → `evals/suite.json` → `evals/fixtures/*`.
**Implicit contracts:** Body-length budgets must be self-enforced by the author; nothing in-repo validates them automatically.

## Q7: How are `references/`, `scripts/`, and `assets/` subdirectories referenced from the SKILL.md body in existing skills?

**Answer:** The only in-repo example is `qrspi-work` referencing `references/review-cascade.md` with a relative path, instructed at the point of use ("Read `references/review-cascade.md` for cascade logic"). There are no in-repo examples of a skill referencing `scripts/` or `assets/` from its body. The convention is: relative path from the skill directory, loaded on demand via an explicit "Read X" instruction embedded in the procedure.
**Evidence:**

```
   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:272`
**Dependencies:** Body → `references/<file>.md` (relative to skill dir).
**Implicit contracts:** Reference material is pulled in lazily, named explicitly, addressed relative to the skill root. No central manifest lists reference files; the body is the index.

## Q8: How do existing skills encode opinionated "prefer X over deprecated Y" guidance and anti-pattern callouts?

**Answer:** NOT FOUND in project-local skills — the repo's `qrspi-*` skills are workflow orchestration, not opinionated style guides, so they contain no "prefer X over Y" tables. The closest in-repo opinionated guidance is in `qrspi-work` SKILL.md's hard-rule sections (e.g., "NEVER use `-a` flag", "HARD STOP: Infrastructure Errors") which use bold imperative headers, explicit DO/DON'T lists, and a rationale ("Why this is absolute:"). That format — bolded directive, forbidden-list, short rationale — is the in-repo precedent for opinionated/anti-pattern content. (Style-guide skills like `writing-bash-scripts` are global and out of scope.)
**Evidence:**

```
### Staging — NEVER use `-a` flag

The `-a` flag stages ALL files ... This will capture other work-in-progress ...

Always stage specific files before committing:
```

— `.claude/skills/qrspi-work/SKILL.md:641-647`
**Dependencies:** None.
**Implicit contracts:** Opinionated rules are stated as imperatives with a brief "why", and forbidden actions are enumerated explicitly rather than implied.

## Q9: How do existing skills handle version-gated or environment-specific behavior?

**Answer:** NOT FOUND — no project-local skill documents version-gated or SaaS-vs-self-managed conditional behavior. The `qrspi-*` skills target a single fixed toolchain (Linear + Graphite + git worktrees) with no version caveats. There is no in-repo precedent for "GA since vX" annotations. The author of the new skill will be establishing this convention; the nearest analog is the conditional dispatch table in `qrspi-work` (status → action), which uses a Markdown table to map a condition to behavior.
**Evidence:**

```
| Linear Status | Action |
|---|---|
| `Backlog` or `Selected` | → Run Planning |
```

— `.claude/skills/qrspi-work/SKILL.md` state-dispatch table
**Dependencies:** None.
**Implicit contracts:** Conditional behavior is commonly expressed as a Markdown mapping table; version annotations have no existing pattern to copy.

## Q10: What is the convention for splitting a large topic across multiple `references/` files versus one large file?

**Answer:** The single in-repo data point: `qrspi-work` uses one focused reference file per discrete sub-topic (`review-cascade.md` for review cascade logic), kept out of the main body to preserve the body's readability. There is no example of multiple reference files in one skill, but the precedent (one file = one cohesive sub-topic, named for its concern) generalizes cleanly to the ticket's six reference topics: one `references/<topic>.md` per topic.
**Evidence:**

```
.claude/skills/qrspi-work/references/review-cascade.md
```

— directory listing; the only reference file in the repo, scoped to a single concern
**Dependencies:** Body names each reference file at point of use (Q7).
**Implicit contracts:** One reference file per cohesive concern, named after the concern, pulled in on demand.

## Q11: What does the eval harness in `evals/` and `scripts/` measure, and is there an existing pattern a new skill is expected to ship with?

**Answer:** The harness evaluates the *qrspi workflow phase agents* (questions, research, etc.) against fixture tickets. `evals/suite.json` defines cases with `phase`, `prompt`, `context.files` (fixtures), and `assertions` (programmatic checks like `output_file_exists`, `section_count`, `question_count`, plus weights). `scripts/run_eval.py`, `grade.py`, `report.py`, `diagnose.py`, `revise.py`, and `check_scope.py` drive run/grade/report/scope-check. Fixtures live in `evals/fixtures/`; `evals/golden/` exists but is empty. The harness is phase-agent-specific — it does **not** currently include a generic "evaluate any new skill" case. A new, unrelated skill (GitLab pipelines) is not wired into this suite and there is no existing template case to copy for it.
**Evidence:**

```
"id": "case_001",
"name": "questions_happy_path",
"phase": "questions",
...
"assertions": [
  { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
  { "type": "programmatic", "check": "section_count('questions.md', '## ') >= 5", "weight": 1.0 },
```

— `evals/suite.json` case_001
**Dependencies:** `scripts/run_eval.py` → `evals/suite.json` → `evals/fixtures/*`; `scripts/grade.py` consumes assertions.
**Implicit contracts:** Eval cases are tied to a `phase` and assert on generated artifact files. There is no generic skill-quality eval; shipping eval coverage for a brand-new skill would require adding cases/fixtures, which is not currently the established pattern for non-qrspi skills.

## Q12: Is there an existing test or validation that a SKILL.md's frontmatter is parseable / description triggers correctly?

**Answer:** NOT FOUND for SKILL.md frontmatter specifically. `scripts/check_scope.py` exists (name implies scope-boundary validation for research, per the firewall), but no script validates SKILL.md frontmatter parseability or description-trigger accuracy. The eval assertions operate on generated artifacts, not on skill frontmatter. Searched `scripts/` (6 python files, none frontmatter-focused) and `evals/suite.json` (no frontmatter assertions).
**Evidence:**

```
scripts/: check_scope.py  diagnose.py  grade.py  report.py  revise.py  run_eval.py
```

— `scripts/` listing
**Dependencies:** None relevant.
**Implicit contracts:** Frontmatter correctness is author-enforced; no automated gate exists in-repo.

## Q13: How is skill triggering accuracy observed/measured in this repo?

**Answer:** NOT FOUND — there is no in-repo mechanism to benchmark skill `description` triggering accuracy. The eval harness measures phase-agent output quality, not whether a description auto-invokes on intended prompts. The `description` field is the sole triggering signal (it embeds explicit trigger phrases, e.g. qrspi-work's "Trigger on any variant of: 'work on <ticket-id>'..."), but its accuracy is not logged or scored anywhere in the repo. Description-optimization tooling (part of the global skill-creator) is out of scope.
**Evidence:**

```
description: "Single entry point ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (trigger phrases live in `description`)
**Dependencies:** None in-repo.
**Implicit contracts:** Triggering quality is encoded by writing explicit trigger phrases into `description`; there is no measurement loop for it within the project.

---

## Discovered Patterns

- **Two skill body archetypes.** (1) Thin wrapper: frontmatter + one paragraph delegating to a `.claude/agents/<name>.md` agent (all `qrspi-*` phase skills). (2) Self-contained procedural skill: a long, fully-specified body with on-demand `references/` files (`qrspi-work`). A standalone guidance skill like the GitLab one fits archetype (2): a self-contained body plus reference files, with no companion agent.
- **Frontmatter is the trigger surface.** `description` is consistently written as "what it does + when to use it", frequently with literal trigger phrases. `name` always equals the directory name; `allowed-tools` is always present.
- **References are lazy and self-indexed.** No manifest; the body names each reference file at its point of need with a relative path.
- **Opinionated rules use bold imperatives + forbidden-lists + short rationale** (`qrspi-work` hard-stop and staging sections) — the closest in-repo template for the ticket's "prefer X over deprecated Y" and anti-pattern requirements.
- **The eval harness is qrspi-phase-specific.** It asserts on generated artifacts per `phase`; it is not a generic new-skill validator.

## Inconsistencies

- The "under 500 lines / 5000 tokens" body-budget convention is contradicted in-repo by `qrspi-work/SKILL.md` (731 lines). The budget is a target for *guidance* skills, but the project's own orchestrator skill exceeds it — so the budget is aspirational, not enforced.
- The ticket's process step "Use the Anthropic skill builder skill" references a global `skill-creator` skill that is not present in this repo. The skill-builder and its eval/description-optimization loop cannot be inspected or relied upon from within project scope; only the standard `.claude/skills/<name>/` layout it produces is observable here.
- `evals/golden/` exists but is empty, while `evals/fixtures/` is populated — golden-output comparison appears scaffolded but unused.
