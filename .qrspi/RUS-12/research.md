# Research — Codebase Map

**Questions source:** questions.md @ /workspaces/qrspi/.worktrees/RUS-12/.qrspi/RUS-12/questions.md
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

> Scope note: Several questions target skills named `using-graphite-cli`, `skill-creator`,
> and `claude-api`. These do **not** exist anywhere under `REPO_ROOT`
> (`/workspaces/qrspi/.worktrees/RUS-12`). The only skills checked into this repo are the ten
> `qrspi-*` skills under `.claude/skills/`. The named skills are global (provided by the harness,
> outside the project boundary) and are out of research scope. Where a question can be answered by
> the closest in-repo analogue, that analogue is used and the substitution is stated.

## Q1: What is the on-disk directory layout of an existing skill in this repo, and where do skill definitions live versus their slash-command wrappers?

**Answer:** Skills live in `.claude/skills/<name>/SKILL.md`. There are ten, all `qrspi-*`. Two
distinct patterns exist:

1. **Thin-wrapper skills** (most phase skills, e.g. `qrspi-research`, `qrspi-design`,
   `qrspi-questions`, `qrspi-plan`, `qrspi-structure`, `qrspi-worktree`, `qrspi-implement`,
   `qrspi-pr`): the `SKILL.md` is a short (~25-35 line) wrapper that parses `$ARGUMENTS`, resolves
   `REPO_ROOT` from `pwd`, and spawns a sub-agent via the `Agent` tool. The actual prompt content
   lives in a sibling file under `.claude/agents/<name>.md`.
2. **Self-contained skills** (`qrspi-work` 565 lines, `qrspi-ticket` 119 lines): the full logic
   lives in `SKILL.md` itself; there is no paired agent file.

So "definition vs wrapper" is split across two directories: `SKILL.md` (the wrapper /
slash-command entry) in `.claude/skills/`, and the agent prompt in `.claude/agents/`.

**Evidence:**

```
.claude/skills/qrspi-research/SKILL.md   (only SKILL.md — wrapper)
.claude/agents/qrspi-research.md         (the agent prompt the wrapper spawns)
.claude/skills/qrspi-work/SKILL.md       (565 lines — fully self-contained, no agent file)
.claude/skills/qrspi-work/references/review-cascade.md
```

— `.claude/skills/qrspi-research/SKILL.md:9-26` ("Thin wrapper that spawns the `qrspi-research`
agent. All prompt content lives in `.claude/agents/qrspi-research.md`.")
— `.claude/CLAUDE.md` ("Phase agent definitions live in `.claude/agents/`; their slash-command
wrappers live in `.claude/skills/`")

Agent files present: `.claude/agents/qrspi-{design,implement,plan,pr,questions,research,structure,worktree}.md`
(8 files — note `qrspi-work` and `qrspi-ticket` have **no** agent file because they are self-contained).

**Dependencies:** A wrapper SKILL.md depends on the existence of its `.claude/agents/<name>.md`
counterpart and on the `Agent` tool (`subagent_type: <name>`). Self-contained skills depend on no
agent file.
**Implicit contracts:** Wrapper and agent share the same `name` (`qrspi-research` ↔
`subagent_type: qrspi-research`). The wrapper passes a labelled input contract with absolute paths;
the agent reads those inputs.

## Q2: How does a SKILL.md reference its supporting material (`references/`, `scripts/`, `assets/`), and what path conventions do existing skills use for those links?

**Answer:** Only **one** in-repo skill has a supporting subdirectory: `qrspi-work/` has a
`references/` directory containing `review-cascade.md`. It is referenced from `SKILL.md` by a
**relative path inline in prose**: `` `references/review-cascade.md` `` (relative to the skill
directory). There are no `scripts/` or `assets/` subdirectories inside any skill. (Project-level
scripts live in the top-level `scripts/`, not inside skills.)

**Evidence:**

```
.claude/skills/qrspi-work/references/review-cascade.md
```

— `.claude/skills/qrspi-work/SKILL.md:282` ("...bounded to the phase's own artifacts (see
`references/review-cascade.md`).")

The only supporting-material directory in any skill:
```
$ find .claude -type d -name references -o -type d -name scripts -o -type d -name assets
.claude/skills/qrspi-work/references
```

**Dependencies:** `qrspi-work/SKILL.md` → `qrspi-work/references/review-cascade.md` (relative link).
**Implicit contracts:** Supporting docs live in a `references/` subfolder of the skill and are cited
by a path relative to the skill directory, not absolute and not repo-relative.

## Q3: What frontmatter fields are present in existing SKILL.md files (e.g. name, description, trigger conditions), and which are required versus optional?

**Answer:** SKILL.md frontmatter is YAML. Observed fields across all ten skills:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`. (NOTE: the question targets
`skill-creator`/`using-graphite-cli` frontmatter, which are not in-repo — these findings are from
the in-repo `qrspi-*` skills, the only available evidence.)

- `name` — present in all 10.
- `description` — present in all 10 (encodes trigger/usage guidance in prose; see Q5).
- `command` — present in all 10 (the slash command, e.g. `/qrspi-research`).
- `argument-hint` — present in all 10 (e.g. `<ticket-id>`).
- `allowed-tools` — present in all 10 (comma-separated tool list).

There is **no enforced/documented required-vs-optional split in-repo** (no schema or validator was
found — see Q9). Empirically every skill carries the same five fields, so the de-facto convention is
all five. Agent files (`.claude/agents/*.md`) use a *different* frontmatter shape: `name`,
`description`, and a nested `claude:`/`tools:` block (e.g. `qrspi-research.md`), or a top-level
`claude:` with `tools:`.

**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. ...
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`

Agent-file frontmatter (different shape):
```
---
name: qrspi-research
description: Internal QRSPI workflow agent ...
claude:
  tools: Read, Write, Glob, Grep
---
```
— `.claude/agents/qrspi-research.md:1-6`

**Dependencies:** The harness/Claude Code reads this frontmatter to register the skill.
**Implicit contracts:** `name` must match the directory name and the `command` stem;
`allowed-tools` constrains what the skill may invoke (e.g. `qrspi-research` allows only
`Agent, Bash(pwd:*)` — codebase exploration is intentionally pushed into the spawned agent).

## Q4: What is the exact invocation contract for the Anthropic skill builder skill referenced in the ticket — what inputs it expects and what outputs it produces?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. No
`skill-creator` (or `skill_creator`) skill, agent, doc, or any file referencing one exists under
`REPO_ROOT`.

Searches attempted (all from `REPO_ROOT`):
- `find .claude -name "SKILL.md"` → only ten `qrspi-*` skills; no `skill-creator`.
- `grep -rln "skill-creator\|skill_creator" . --include=*.py` (and across `.claude/`, `docs/`) →
  no matches.

The `skill-creator` skill is a global/harness-provided skill, not part of this repository. Its
invocation contract cannot be documented from in-repo evidence.

**Dependencies:** N/A (out of scope).
**Implicit contracts:** N/A.

## Q5: How are skill `description` fields phrased to encode trigger conditions, and what format do existing skills use to signal "TRIGGER when / SKIP when"?

**Answer:** (The question names `claude-api`/`using-graphite-cli`, which are out-of-repo; findings
below are from in-repo `qrspi-*` skills.) In-repo descriptions encode triggers as **prose**, not a
structured `TRIGGER when / SKIP when` block. The richest example is `qrspi-work`, whose description
enumerates trigger phrases inline: "Use when the user asks to 'work on' a ticket ... Trigger on any
variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'...". Simpler skills
use a one-sentence "Use when..." clause. No in-repo skill uses an explicit `SKIP:` keyword.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user
asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on
<ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a
QRSPI ticket through its lifecycle."
```
— `.claude/skills/qrspi-work/SKILL.md:3`

```
description: Map codebase facts by answering questions from the Questions phase. The feature
ticket is intentionally hidden. Use after questions are approved.
```
— `.claude/skills/qrspi-research/SKILL.md:3`

**Dependencies:** The harness uses `description` for skill auto-triggering / dispatch.
**Implicit contracts:** Triggers are expressed as natural-language "Use when..." / "Trigger on..."
phrasing embedded in the single `description` string; there is no separate trigger field. The
explicit `TRIGGER when: / SKIP:` format named in the question is a *global*-skill convention
(e.g. the harness `claude-api` skill) not present in any in-repo skill.

## Q6: Is there an existing convention or precedent for a skill that wraps a CLI tool (auth state, environment variables, non-interactive mode), and how does it document those stateful concerns?

**Answer:** The closest in-repo precedent for CLI-wrapping is **`qrspi-work/SKILL.md`**, which
orchestrates the `gt` (Graphite) and `gh` (GitHub) CLIs (the dedicated `using-graphite-cli` skill is
global, not in-repo). It documents stateful CLI concerns explicitly:

- **Non-interactive mode:** a hard rule that every `gt` command includes `--no-interactive`
  (`SKILL.md:482`), and every `gh`/`gt` example carries the flag.
- **Auth / environment state:** GitHub auth and `OWNER/REPO` are resolved deterministically by a
  helper script (`scripts/qrspi_resolve.py`) rather than re-derived; the skill warns sub-agents do
  NOT inherit cwd and must `cd` + use absolute paths (`SKILL.md:126-129`).
- **Stale-state recovery:** a whole section on stale PR associations in `.git/.graphite_pr_info`
  and how to detect/recover (`SKILL.md:491-521`).
- **Infrastructure-error firewall:** a HARD STOP rule forbidding auth/permission workarounds
  (`SKILL.md:547-565`).

**Evidence:**

```
## Git/Graphite Rules
- All `gt` commands include `--no-interactive`.
- All commit messages use heredoc format and include the co-authorship trailer.
- The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit.
```
— `.claude/skills/qrspi-work/SKILL.md:480-484`

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve
... When ANY operation fails due to permissions, authentication, configuration, or tooling
errors (`EACCES`, `permission denied`, expired auth, ...): 1. STOP. ...
**Explicitly forbidden:** `chmod`/`chown`; routing around config via env vars (`XDG_CONFIG_HOME`)...
```
— `.claude/skills/qrspi-work/SKILL.md:547-560`

**Dependencies:** `qrspi-work` → `gt`, `gh`, `git` CLIs; `scripts/qrspi_resolve.py` (auth/OWNER/REPO);
`.git/.graphite_pr_info` (Graphite PR-pinning state).
**Implicit contracts:** CLI invocations are always non-interactive; auth/env resolution is delegated
to a deterministic script; CLI infra failures must hard-stop, never be worked around.

## Q7: How do existing skills document non-interactive / CI execution contexts and environment-variable-driven configuration, given the ticket requires both interactive and CI auth coverage?

**Answer:** In-repo documentation of non-interactive execution is concentrated in `qrspi-work`
and the project CLAUDE.md / batch workflow. The pattern is: pass an explicit `--no-interactive`
flag on every CLI call, and resolve environment/config via self-locating scripts rather than reading
env vars ad hoc. There is **no in-repo skill that documents a dedicated "CI auth" or
"interactive vs CI auth" toggle** — the harness `gh` CLI auth model is not described in-repo (it is a
global concern). The closest documented stance is the *prohibition* on environment-variable
workarounds for auth (`XDG_CONFIG_HOME` is explicitly forbidden) in the HARD STOP block.

**Evidence:**

```
**Explicitly forbidden:** ... routing around config via env vars (`XDG_CONFIG_HOME`); copying
config files elsewhere; ...
```
— `.claude/skills/qrspi-work/SKILL.md:557-558`

```
gt submit --publish --no-edit --no-interactive
```
— `.claude/skills/qrspi-work/SKILL.md:184` (the canonical non-interactive submit idiom)

The batch orchestrator (`.claude/workflows/qrspi-batch.js`) is the automation/CI driver — it "drives
the autonomously-runnable actions ... it skips `wait` and the manual `revise`" (`.claude/CLAUDE.md`).

**Dependencies:** `gt`/`gh` non-interactive flags; `scripts/qrspi_resolve.py` for config resolution;
`.claude/workflows/qrspi-batch.js` as the unattended driver.
**Implicit contracts:** Automation never prompts (always `--no-interactive`); config/auth resolution
is deterministic and script-driven; env-var routing of auth/config is forbidden, not a sanctioned CI
pattern.

## Q8: Does this project already mandate a git/GitHub workflow (the using-graphite-cli skill and CLAUDE.md git-delegation rule) that could conflict with a skill encouraging direct `gh` usage, and how is that boundary expressed?

**Answer:** Yes — there is a strong project-wide mandate that all git/Graphite/PR mutations go
through the orchestration layer, which would conflict with a skill encouraging ad-hoc direct CLI use.
The boundary is expressed three ways:

1. **Global directive (memory index):** "All git actions use the using-graphite-cli skill —
   Every git/gt operation must go through the using-graphite-cli skill, no exceptions"
   (surfaced in the session global instructions / `~/.agents/MEMORY.md` index — this is a *global*
   rule, referenced here because it governs the repo but its source file is outside `REPO_ROOT`).
2. **Orchestrator monopoly (in-repo):** `qrspi-work/SKILL.md` states "The orchestrator is the ONLY
   place git/graphite operations happen — sub-agents never commit" (`SKILL.md:484`). Sub-agents
   (research, implement) are explicitly forbidden from git mutations.
3. **Project conventions (in-repo):** `.claude/CLAUDE.md` documents the PR-gated lifecycle where
   `gt`/`gh` operations are funneled through `qrspi-work` / `qrspi-batch.js` and the resolver scripts.

`gh` *is* used in-repo, but only inside the orchestrator for read/PR-management (`gh pr view`,
`gh pr edit`, `gh api graphql`), never as free-form direct usage by arbitrary agents.

**Evidence:**

```
- The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit.
```
— `.claude/skills/qrspi-work/SKILL.md:484`

```
gh pr edit <slice-1-pr> --body "$(cat .qrspi/<ticket-id>/pr-summary.md)"
```
— `.claude/skills/qrspi-work/SKILL.md:246` (sanctioned `gh` use, inside the orchestrator)

— `.claude/CLAUDE.md` ("### Lifecycle — PR-gated" + "Codebase conventions" naming
`qrspi_resolve.py`, `qrspi_pr_state.py` as the PR/gh-GraphQL layer)

**Dependencies:** Global `using-graphite-cli` skill (out of repo) ← project policy; in-repo
`qrspi-work`/`qrspi-batch.js` enforce it.
**Implicit contracts:** Mutation operations are centralized in the orchestrator; `gh` is permitted
for read/PR-metadata operations within that orchestrator but direct mutation by other agents is
prohibited.

## Q9: What enforces the SKILL.md body size limit (under 500 lines / 5000 tokens) cited in the acceptance criteria — is there a lint, eval, or documented check?

**Answer:** NOT FOUND — no in-repo mechanism enforces a SKILL.md body-size limit. There is no lint,
no eval assertion targeting SKILL.md line/token count, and no documented check.

Searches attempted (from `REPO_ROOT`):
- `grep -n "500\|5000\|line\|size\|lint\|valid" docs/eval-system.md` → matches concern only
  artifact docs (e.g. design `line_count <= 300`), not SKILL.md.
- `grep -rn ".claude/skills\|SKILL.md" scripts/*_test.py` → no matches (no test covers skills).
- The eval suite (`evals/suite.json`) has `line_count`/`section_count`/`question_count` checks but
  only for **workflow artifacts** (questions.md, research.md, design.md, etc.), never for SKILL.md.

Notably this limit is *not even applied to the existing skills*: `qrspi-work/SKILL.md` is **565
lines** (`wc -l`), which exceeds a 500-line cap. Nothing flags it. (See Inconsistencies.)

**Evidence:**
```
$ wc -l .claude/skills/*/SKILL.md
  565 .claude/skills/qrspi-work/SKILL.md   <-- exceeds 500
  119 .claude/skills/qrspi-ticket/SKILL.md
   25-35 lines each for the eight wrapper skills
```
— measured under `.claude/skills/`

**Dependencies:** None — the limit is unenforced in-repo.
**Implicit contracts:** Skill size is governed only by author discipline; no automated gate exists.

## Q10: How are skills validated or evaluated in this repo, and is the eval harness functional or a placeholder for skill-level checks?

**Answer:** The eval harness is a **non-functional placeholder/stub**. `scripts/run_eval.py` defines
the full 5-stage structure (load suite, execute, grade, report) but its `execute_*` trial function
is an explicit stub that returns empty output — it does not actually run any agent. Project memory
and CLAUDE.md both flag it as a placeholder. There is no skill-level (SKILL.md) validation at all;
the suite targets workflow *artifacts*, not skills.

**Evidence:**

```python
    """Execute a single trial of a single test case.
    In a real implementation, this would:
    1. Spin up an isolated container/sandbox  ...
    This stub captures the structure for integration with the actual agent runtime.
    """
    ...
        # ── Placeholder for agent execution ──
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
```
— `scripts/run_eval.py:99-137`

— `docs/eval-system.md:108` ("The pipeline runs end-to-end but produces zeros — the three critical
gaps are agent execution, LLM judge integration, and the 17 missing fixture files.")
— `.claude/CLAUDE.md` ("The `evals/` + `scripts/run_eval.py` harness is a **non-functional
placeholder** — verify pure logic with the unit tests and orchestration changes with manual
end-to-end runs")

**Dependencies:** `run_eval.py` → `evals/suite.json` (15 cases) + `grade.py` (check registry) +
fixtures (17 missing); none of it exercises skills.
**Implicit contracts:** Eval results are currently meaningless (zeros); the real verification path is
the stdlib unit tests + manual e2e runs, per CLAUDE.md.

## Q11: What testing precedent exists for non-code artifacts (skills, templates) versus the stdlib `_test.py` unit tests used for the resolver/persist scripts?

**Answer:** There is **no automated test precedent for non-code artifacts (skills or templates)**.
The only unit tests are stdlib `unittest`/`_test.py` siblings for the four Python orchestration
scripts. None reference `.claude/skills/`, SKILL.md, or `.qrspi/templates/`.

Test files present (all pure-logic Python, stdlib only, run with `python3`):
- `scripts/qrspi_resolve_state_test.py`
- `scripts/qrspi_resolve_test.py`
- `scripts/qrspi_pr_state_test.py`
- `scripts/qrspi_persist_test.py`

`grep -rn "\.claude/skills\|SKILL.md\|skills/" scripts/*_test.py` → **no matches**. Skills/templates
are verified only by the (non-functional) eval suite and by manual review.

**Evidence:**
```
$ ls scripts/*_test.py
scripts/qrspi_persist_test.py
scripts/qrspi_pr_state_test.py
scripts/qrspi_resolve_state_test.py
scripts/qrspi_resolve_test.py
```
— `.claude/CLAUDE.md` ("All of the above have stdlib-only unit tests as `_test.py` siblings
(`scripts/qrspi_*_test.py`, run with `python3`).")

**Dependencies:** The `_test.py` files import only their sibling script + stdlib; no skill/template
coupling.
**Implicit contracts:** Pure-logic code is unit-tested; prose artifacts (skills/templates) have no
automated test gate — they rely on human review and the placeholder eval harness.

## Q12: How does the skill-creator workflow surface and report skill performance, triggering accuracy, or eval results, so the new skill's quality is observable after creation?

**Answer:** NOT FOUND for `skill-creator` specifically — it is a global skill, outside `REPO_ROOT`,
so its reporting behavior cannot be documented from in-repo evidence (same gap as Q4).

For the **in-repo** eval reporting analogue: `scripts/report.py` and `scripts/grade.py` form the
reporting/grading stages, and `docs/eval-system.md` describes a 5-stage pipeline (assertions →
programmatic + llm_judge → score → report). But because execution is stubbed (Q10), reported metrics
are currently zeros. Results are written under an output dir (`results/` exists at repo root) and the
suite defines `train`/`test` splits and per-assertion weights for scoring (`evals/suite.json`). No
in-repo mechanism measures *triggering accuracy* of a skill `description`.

**Evidence:**
- `scripts/report.py`, `scripts/grade.py` (reporting + grading stages present)
- `results/` directory exists at repo root (eval output destination)
- `evals/suite.json` defines weighted assertions + `split` (train 0.65 / test 0.35, seed 42)
— `docs/eval-system.md:5` ("The eval harness is a 5-stage pipeline for iterating on QRSPI
skill/agent prompts") and `:108` (pipeline produces zeros)

**Dependencies:** `run_eval.py` → `grade.py` → `report.py` → `results/`; all gated on the missing
execution stage.
**Implicit contracts:** N/A for `skill-creator` (out of scope); in-repo, observability is
aspirational pending a real execution backend.

---

## Discovered Patterns

- **Two skill archetypes.** (1) Thin wrapper (`SKILL.md` ~25-35 lines) that spawns a sibling agent
  in `.claude/agents/<name>.md`; (2) self-contained (`qrspi-work`, `qrspi-ticket`) with all logic in
  `SKILL.md`. New skills should pick one archetype deliberately.
- **Uniform frontmatter.** Every in-repo `SKILL.md` carries exactly `name`, `description`,
  `command`, `argument-hint`, `allowed-tools`. Agent files use a different shape (`name`,
  `description`, `claude.tools`). `name` always matches the directory.
- **`allowed-tools` as a capability firewall.** Tools are scoped tightly (e.g. `qrspi-research`
  wrapper = `Agent, Bash(pwd:*)`; the research *agent* = `Read, Write, Glob, Grep`, no Linear/Bash
  mutation). Restriction is structural, not just instructional.
- **Centralized git/CLI mutation.** All `gt`/`gh`/`git` mutations happen only in the orchestrator
  (`qrspi-work` / `qrspi-batch.js`); sub-agents never commit. Every CLI call is `--no-interactive`.
- **Deterministic helper scripts over ad-hoc shell.** Path/auth/decision logic is folded into
  self-locating Python (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_resolve_state.py`,
  `qrspi_pr_state.py`), each with a stdlib `_test.py` sibling. Motivated by a weak worker model
  mangling paths (project MEMORY note).
- **Staging-then-move artifact persistence.** Phase agents write to a short token-free staging path
  (`/tmp/phase-stage/<id>/<artifact>.md`) and a deterministic script moves it to the canonical
  `.qrspi/<id>/` path (`.claude/CLAUDE.md`, "Fix A").
- **Trigger conditions live in prose `description`.** No in-repo skill uses a structured
  `TRIGGER when: / SKIP:` block; that format is a global-skill convention.
- **Supporting material in `references/`.** The one example (`qrspi-work/references/review-cascade.md`)
  is cited by a path relative to the skill directory.
- **Research firewall pattern.** The research phase is deliberately walled off from the ticket and
  from outside-repo reads (defense-in-depth across agent tool list + orchestrator contract + scope
  block). Relevant precedent for any skill that must respect a project boundary.

## Inconsistencies

- **`qrspi-work/SKILL.md` is 565 lines**, exceeding the "under 500 lines" SKILL.md body limit cited
  in the questions/acceptance criteria. Nothing enforces or flags this (Q9) — the limit is neither
  applied nor checked in-repo.
- **No required-vs-optional frontmatter spec exists.** Q3's question presumes a documented
  required/optional split; in-repo there is none — all five fields simply appear in every skill by
  convention. Any "required field" claim would be inferred, not enforced.
- **Eval suite vs reality.** `evals/suite.json` and `docs/eval-system.md` describe a functioning
  5-stage scoring pipeline with weighted assertions, but `run_eval.py:117-137` is an explicit stub
  returning empty output. The docs read as functional; the code is a placeholder (acknowledged at
  `docs/eval-system.md:108` and `.claude/CLAUDE.md`). The suite also targets workflow artifacts only
  — **no assertion validates a SKILL.md**.
- **Skills referenced by the questions are not in the repo.** `using-graphite-cli`, `skill-creator`,
  and `claude-api` are global/harness skills, not under `REPO_ROOT`. Questions Q4 and Q12 (and the
  out-of-repo halves of Q5/Q6/Q8) cannot be answered from in-repo evidence; the closest in-repo
  analogues (`qrspi-work` for CLI-wrapping, `report.py`/`grade.py` for eval reporting) were
  substituted where noted.
- **Two frontmatter dialects.** `SKILL.md` files use `allowed-tools` (top-level, comma string);
  agent `.md` files use a nested `claude:\n  tools:` block. Same concept (tool gating), two shapes —
  a potential source of confusion when authoring a new skill + agent pair.
