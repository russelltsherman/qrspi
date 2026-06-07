# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T12:31:04Z
**Status:** draft

> **Scope note:** Many questions target the `skill-creator` skill and the `omlx` CLI.
> Neither exists anywhere under `REPO_ROOT` (`/workspaces/qrspi/.worktrees/RUS-24`).
> `skill-creator` is an external/global skill (surfaced in the harness skill list, not in
> the project tree); `omlx` returns zero hits in the repo. Per the research firewall, those
> sub-questions are marked **NOT FOUND — outside project scope** with the exact searches
> attempted. The repo-internal facts that *do* bear on each question (skill on-disk layout,
> frontmatter conventions, naming/collision surface, eval harness) are documented in full.

## Q1: What is the on-disk directory layout an agentskills.io-standard skill must follow in this repo (SKILL.md plus references/, scripts/, assets/), and where do existing skills physically live?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, one directory per skill, each
containing a `SKILL.md` as its entry point. Ten skills exist. Only one skill uses a companion
subdirectory: `qrspi-work` has a `references/` directory holding `review-cascade.md`. No skill
in the repo currently has a `scripts/` or `assets/` subdirectory, so there is no in-repo
precedent for those two — only `SKILL.md` (universal) and `references/` (one example) are
observed. There is no validator, manifest, or schema file in the repo enforcing an
"agentskills.io-standard" layout; the layout is convention-only.

Note a parallel, distinct structure: `.claude/agents/<name>.md` holds the *agent definitions*
(flat `.md` files, no directories), and `.claude/skills/<name>/SKILL.md` holds the
slash-command *wrappers*. CLAUDE.md states this split explicitly: "Phase agent definitions
live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`".

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
  qrspi-work/references/review-cascade.md   <-- only companion dir in repo
  qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing)

```
.claude/agents/   <-- separate: flat agent .md files, NOT skill dirs
  qrspi-design.md  qrspi-implement.md  qrspi-plan.md  qrspi-pr.md
  qrspi-questions.md  qrspi-research.md  qrspi-structure.md  qrspi-worktree.md
```

— `.claude/agents/` (directory listing)

**Dependencies:** Claude Code skill loader (external) discovers `.claude/skills/*/SKILL.md`.
SKILL.md wrappers reference `.claude/agents/<name>.md` for the actual prompt body (e.g.
`.claude/skills/qrspi-questions/SKILL.md:11` — "All prompt content lives in
`.claude/agents/qrspi-questions.md`").
**Implicit contracts:** Skill folder name == frontmatter `name` == the slash command suffix
(e.g. folder `qrspi-questions`, `name: qrspi-questions`, `command: /qrspi-questions`).
Companion files are referenced by *relative* path from SKILL.md (see Q6).

## Q2: What frontmatter fields, ordering, and value formats are required and validated for a SKILL.md, and what is the maximum length of the description field?

**Answer (validation source):** NOT FOUND — outside project scope. No frontmatter schema,
validator, or documented field-length limit (e.g. 1024 chars) exists anywhere under
`REPO_ROOT`. The `skill-creator` skill that would own such validation is not in the project
tree. Searches for `5000 token`, `500 line`, `1024`, `max.*description` returned no
validation rule.

**Answer (observed convention in-repo):** Every in-repo `SKILL.md` opens with YAML frontmatter
delimited by `---`. The de-facto field set and ordering across all 10 skills is:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`. Value formats observed:

- `name`: bare kebab-case scalar (`qrspi-questions`).
- `description`: plain scalar, OR double-quoted when it contains a colon/quotes/parentheses
  (e.g. `qrspi-work` quotes its description because it embeds `'work on <ticket-id>'`).
- `command`: `/<name>`.
- `argument-hint`: angle-bracket placeholder (`<ticket-id>`, `<ticket-id> <slice-number>`,
  `<initial description>`).
- `allowed-tools`: comma-separated list, supporting scoped forms like `Bash(pwd:*)` and MCP
  tool names like `mcp__linear__get_issue`.

Note the *agent* definitions use a different frontmatter shape: `name`, `description`, then a
nested `claude:` block with `tools:` — NOT `allowed-tools` (see Q1 evidence /
`.claude/agents/qrspi-research.md:1-5`). So "frontmatter format" differs between
`.claude/skills/*/SKILL.md` and `.claude/agents/*.md`.

**Evidence:**

```yaml
---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear__get_issue
---
```

— `.claude/skills/qrspi-questions/SKILL.md:1-7`

```yaml
---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... "
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear__get_issue, ...
---
```

— `.claude/skills/qrspi-work/SKILL.md:1-7` (only skill that double-quotes its description)

**Dependencies:** Consumed by the external Claude Code skill loader.
**Implicit contracts:** Field ordering `name → description → command → argument-hint →
allowed-tools` is consistent across all 10 skills; a new skill should match it. Descriptions
encode trigger phrases ("Use when…") — see Discovered Patterns.

## Q3: How is the skill builder ("Anthropic skill builder skill") invoked in this environment, and what inputs/arguments does it expect to scaffold a new skill?

**Answer:** NOT FOUND — outside project scope. The `skill-creator` skill definition is not in
`REPO_ROOT`. The only in-repo reference to it is a passing mention as a *validation pass*, not
an invocation contract: `.claude/agents/qrspi-structure.md:40` lists "invoking skill-creator"
as one example of a final validation step within a slice. No arguments, inputs, or invocation
syntax for the builder are documented anywhere in the project.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the
   final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

**Searches attempted:** `grep -rni 'skill-creator|skill builder'` (1 hit, above);
`find -iname '*skill*creator*'` (0 hits); `find -iname '*omlx*'` (0 hits).
**Dependencies:** External/global skill registry (the harness skill list), not the repo.
**Implicit contracts:** None discoverable in scope.

## Q4: What naming convention governs the skill identifier (folder name and frontmatter `name`), and is there a constraint preventing a name like "using-omlx-cli" from colliding with existing skills?

**Answer (convention):** kebab-case, lowercase, hyphen-separated. All in-repo skills are
namespaced `qrspi-*`; a `using-omlx-cli`-style name follows the same kebab-case shape and the
"using-…-cli" pattern already used by the external `using-graphite-cli` skill (referenced in
the harness skill list but not in the repo). The hard contract is the three-way identity:
**folder name == `name` frontmatter == `/command` suffix** (Q1 implicit contract).

**Answer (collision enforcement):** NOT FOUND — outside project scope. No code in `REPO_ROOT`
enforces name-uniqueness; collision detection (if any) lives in the external skill loader /
`skill-creator`, neither in scope. The de-facto collision surface that *can* be checked in
scope is the existing folder set: the 10 `.claude/skills/<name>/` directories listed in Q1.
A new name does not collide with any of them, since all existing names are `qrspi-*`.

**Evidence:** Folder/`name`/`command` identity, e.g. folder `qrspi-research`,
`name: qrspi-research`, `command: /qrspi-research` — `.claude/skills/qrspi-research/SKILL.md:2,4`.
Existing names to avoid colliding with: the 10 directories in Q1 evidence.
**Dependencies:** External skill loader resolves names → directories.
**Implicit contracts:** Uniqueness of folder name within `.claude/skills/` is the only
in-scope guarantee against collision.

## Q5: Where does the skill-creator place generated skill files (target directory), and does it write to a staging path or directly into `.claude/skills/`?

**Answer (skill-creator behavior):** NOT FOUND — outside project scope. The builder's
file-output logic is not in `REPO_ROOT`.

**Answer (where a skill must end up to be discovered, in-repo fact):** For a skill to be
loaded in this repo it must physically reside at `.claude/skills/<name>/SKILL.md` (Q1). That
is the destination regardless of how it is authored.

**Note on a *different* staging mechanism in-repo (do not conflate):** The QRSPI workflow
itself uses a staging-then-deterministic-move pattern for *phase artifacts* (not for skills):
agents write to `/tmp/phase-stage/<id>/<artifact>.md` and `scripts/qrspi_persist.py` moves the
file into `.worktrees/<id>/.qrspi/<id>/`. This is "Fix A" in CLAUDE.md and is unrelated to
skill scaffolding, but it is the only staging convention present in the project.

**Evidence:**

```
Phase artifacts are persisted with **Fix A** (staging + deterministic move): each phase agent
writes to a short, token-free staging path (`/tmp/phase-stage/<id>/<artifact>.md` ...) ... and
`scripts/qrspi_persist.py` ... moves it to `.worktrees/<id>/.qrspi/<id>/`.
```

— `.claude/CLAUDE.md` ("Codebase conventions" section)

**Dependencies:** `scripts/qrspi_persist.py` (artifact staging, not skill staging).
**Implicit contracts:** Skill discovery requires the final path `.claude/skills/<name>/SKILL.md`.

## Q6: How are optional companion directories (references/, scripts/, assets/) registered or referenced from SKILL.md so the agent loads them on demand rather than inlining their content?

**Answer:** By a **relative path reference inside the SKILL.md prose**, not by any manifest or
frontmatter registration. The single in-repo example: `qrspi-work/SKILL.md` mentions
`references/review-cascade.md` in body text, instructing the agent to consult it. There is no
declarative "files:" list or index — the convention is "name the relative file in the body so
the agent reads it on demand." This matches the broader repo pattern where SKILL.md wrappers
point to a larger prompt body in `.claude/agents/<name>.md` rather than inlining it
(`.claude/skills/qrspi-questions/SKILL.md:11`).

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`

```
Thin wrapper that fetches the ticket from Linear and spawns the `qrspi-questions` agent.
All prompt content lives in `.claude/agents/qrspi-questions.md`.
```

— `.claude/skills/qrspi-questions/SKILL.md:11`

**Dependencies:** Relative-path resolution is relative to the SKILL.md's own directory.
**Implicit contracts:** Companion content is referenced by relative path and read on demand;
inlining is avoided to keep SKILL.md thin (the repo's wrapper-vs-body split).

## Q7: What enforcement or guidance exists for keeping the SKILL.md body under 500 lines / 5000 tokens, and what is the prescribed pattern for overflowing detailed material into references/?

**Answer (enforcement/guidance):** NOT FOUND — outside project scope. No 500-line or
5000-token rule, linter, or guidance text exists under `REPO_ROOT` (grep for `500 line`,
`5000 token` → 0 hits). Such budget guidance would live in the external `skill-creator`.

**Answer (observed overflow pattern, in-repo):** The repo *does* demonstrate the overflow
pattern even without a stated limit: keep SKILL.md a thin wrapper and push bulk into either
`.claude/agents/<name>.md` (the full agent prompt) or a `references/` companion file
(`qrspi-work` → `references/review-cascade.md`). In-repo SKILL.md sizes are small; the largest
is `qrspi-work/SKILL.md` (~282+ lines, the only one that needed a `references/` offload).

**Evidence:** Wrapper-vs-body offload — `.claude/skills/qrspi-questions/SKILL.md:11`;
references offload — `.claude/skills/qrspi-work/SKILL.md:282` (both quoted in Q6).
**Dependencies:** External budget enforcement (not in repo).
**Implicit contracts:** Thin wrapper + relative reference offload (same as Q6).

## Q8: Is there an evaluation/benchmark mechanism for a new skill (the skill-creator eval loop), and what does it require as input to run against a draft skill?

**Answer:** There is a repo eval harness, but it is a **non-functional placeholder** for
skill/agent *prompt* evaluation (not specifically a skill-creator loop, which is out of
scope). `scripts/run_eval.py` runs an eval suite against a skill/agent prompt file. Required
inputs (CLI args): `--skill <path to skill/agent prompt file>`, `--suite <path to suite JSON>`,
`--output <output dir>`; optional `--trials` (default 3), `--workers` (default 4),
`--timeout` (default 120000ms). The suite JSON must have top-level `name` + `cases`, and each
case must have `id`, `prompt`, `assertions` (validated in `load_suite`).

Critically, the agent-execution core is a stub that produces zeros — no real agent is invoked.

**Evidence:**

```python
def execute_single(skill_text, case, trial_id, timeout_ms) -> ExecutionResult:
    ...
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    messages = build_messages(case)
    result.output = ""
    result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:93-137`

```python
required = {"name", "cases"}
...
case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:47-56` (suite/case validation)

**Dependencies:** `evals/suite.json` (15 cases), `evals/fixtures/` (only 4/21 fixtures exist),
`evals/golden/` (empty / `.gitkeep` only), downstream `scripts/grade.py`, `report.py`,
`diagnose.py`, `revise.py` (all stubs per `docs/eval-system.md:93-108`).
**Implicit contracts:** Suite schema (`name`+`cases`; case `id`+`prompt`+`assertions`).
The harness "runs end-to-end but produces zeros" (`docs/eval-system.md:108`).

## Q9: How does the skill-creator handle modifying or regenerating an already-existing skill directory versus creating a net-new one (overwrite, merge, or refuse)?

**Answer:** NOT FOUND — outside project scope. The `skill-creator` create-vs-edit code path
is not in `REPO_ROOT`. No in-repo logic governs overwrite/merge/refuse semantics for skill
directories. (The only in-repo guidance touching create-vs-edit is the *artifact* persistence
gate `scripts/qrspi_persist.py`, which is for phase artifacts, not skills — see Q5.)

**Searches attempted:** `grep -rni 'skill-creator'` (1 unrelated hit, Q3);
`find -iname '*skill*creator*'` (0 hits).
**Dependencies:** External skill-creator.
**Implicit contracts:** None in scope.

## Q10: What is the documented method for verifying a skill triggers correctly (description triggering accuracy) and for measuring its performance/variance in this repo?

**Answer:** Two layers, both in-repo but caveated. (1) **Documented project guidance** in
CLAUDE.md: "verify pure logic with the unit tests and orchestration changes with manual
end-to-end runs"; the eval harness is explicitly called a non-functional placeholder. (2) The
**eval harness** (`docs/eval-system.md`) describes a 5-stage pipeline that, when functional,
would score skills with per-suite mean + stddev/min/max and a train/test split (seed 42) to
flag overfitting and variance — but its agent-execution, LLM-judge, and script-check stages
are stubs, so it currently produces zeros. There is no implemented "description triggering
accuracy" check specifically; triggering is encoded via the description's "Use when…" phrases
(see Discovered Patterns) and verified manually.

**Evidence:**

```
The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` ("Codebase conventions")

```
- Per-suite: mean across cases, with stddev, min, max.
- Train and test scores are computed separately; the train-test gap flags overfitting.
```

— `docs/eval-system.md:43-45` (variance/overfitting design, currently stubbed)

**Dependencies:** `evals/suite.json`, `evals/graphite-evals.json` (separate Graphite-CLI
eval, 5 cases), `scripts/run_eval.py`, `grade.py`, `report.py`.
**Implicit contracts:** Trigger reliability is conveyed through the description's "Use when…"
phrasing; measurement is manual today.

## Q11: How does the skill-creator surface validation failures (invalid frontmatter, oversized body, naming collisions) back to the author, and where are those errors reported?

**Answer:** NOT FOUND — outside project scope. The `skill-creator` validation/reporting path
is external to `REPO_ROOT`. The only *in-repo* validation-failure surfacing patterns
(analogous, not skill-creator) are: (1) the SKILL.md wrappers' own check-and-stop step —
e.g. "verify the artifact exists and is non-empty … If missing or empty, report the error and
stop" (`.claude/skills/qrspi-questions/SKILL.md:25`); and (2) the eval harness's
`load_suite` raising `ValueError` on missing required fields
(`scripts/run_eval.py:49-56`). Neither validates SKILL.md frontmatter, body size, or name
collisions.

**Evidence:**

```
6. ... verify the artifact exists and is non-empty ... If missing or empty, report the
   error and stop.
```

— `.claude/skills/qrspi-questions/SKILL.md:25`

```python
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
```

— `scripts/run_eval.py:49-50`

**Dependencies:** External skill-creator for actual skill validation.
**Implicit contracts:** In-repo convention is "verify post-condition, report error, stop" —
fail-loud rather than silent.

---

## Discovered Patterns

- **Wrapper / body split.** Each `.claude/skills/<name>/SKILL.md` is a thin slash-command
  wrapper that delegates to a heavier prompt in `.claude/agents/<name>.md`
  (`.claude/skills/qrspi-questions/SKILL.md:11`). The two frontmatter shapes differ: skills use
  `allowed-tools:` (flat list); agents use a nested `claude:` → `tools:` block
  (`.claude/agents/qrspi-research.md:1-5`).
- **Three-way name identity.** folder name == frontmatter `name` == `/command` suffix, applied
  uniformly across all 10 skills.
- **Trigger phrasing in descriptions.** Every description embeds activation cues
  ("Use when…", "Use after …", "Trigger on any variant of: …"), the de-facto mechanism for
  triggering accuracy in absence of a programmatic check.
- **Consistent frontmatter field order:** `name → description → command → argument-hint →
  allowed-tools`.
- **Companion files by relative reference, read on demand** (`references/review-cascade.md`
  from `qrspi-work/SKILL.md:282`); no manifest. Only `references/` is exemplified; no
  `scripts/` or `assets/` subdir exists in any skill.
- **Staging + deterministic move** is the repo's reliability idiom for generated *artifacts*
  (`/tmp/phase-stage/<id>/…` → `scripts/qrspi_persist.py`), distinct from skill placement.
- **Tooling is stdlib-only Python with `_test.py` siblings** (CLAUDE.md); the eval harness is
  explicitly a placeholder.

## Inconsistencies

- **Two unrelated "staging" concepts risk conflation.** Q5/Q9 ask about where the *skill*
  creator writes; the repo's only staging mechanism (`qrspi_persist.py`,
  `/tmp/phase-stage/...`) is for *phase artifacts*, not skills. Anyone reading CLAUDE.md could
  mistakenly apply the artifact staging pattern to skill scaffolding.
- **`skill-creator` is referenced as a real validation step but is not in the repo.**
  `.claude/agents/qrspi-structure.md:40` instructs "invoking skill-creator" as a validation
  pass, yet no `skill-creator` exists under `REPO_ROOT` — it is assumed available from the
  global harness, an undocumented external dependency.
- **Frontmatter shape mismatch between skills and agents.** Skills use `allowed-tools:`;
  agents use `claude: { tools: }`. The two are easy to swap by mistake when authoring a new
  skill+agent pair. No validator catches this in-repo.
- **`docs/eval-system.md` describes a rich eval/variance pipeline as if operational** (scoring,
  train/test split, overfitting alerts) while its own Completeness table and CLAUDE.md flag the
  execution core as a stub producing zeros (`docs/eval-system.md:97-108`). Design doc reads more
  capable than the code is.
- **`evals/golden/` is empty and 17/21 fixtures are missing** (`docs/eval-system.md:80-103`),
  so any "benchmark a draft skill" claim (Q8/Q10) cannot actually run to a meaningful score
  today.
