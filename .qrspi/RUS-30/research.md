# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: What directory does the agentskills.io standard require for a skill, and what files/subdirectories (SKILL.md, references/, scripts/, assets/) appear in existing skills in this repo?

**Answer:** Skills live under `.claude/skills/<skill-name>/`. Every skill has a `SKILL.md` at its root. Only one existing skill uses a subdirectory: `qrspi-work` has a `references/` folder containing `review-cascade.md`. No existing skill in this repo ships a `scripts/` or `assets/` directory — so for RUS-30 the `scripts/` directory (required by the ticket's acceptance criteria) will be a new convention for this repo, not a copy of an existing one.
**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
```

— `.claude/skills/` (directory listing)
**Dependencies:** Skills are discovered by the Claude Code harness from `.claude/skills/`.
**Implicit contracts:** A skill directory is named exactly as the skill's `name` frontmatter field; `SKILL.md` must exist at its root.

## Q2: How do existing skills split content between SKILL.md and references/ files?

**Answer:** Two patterns exist. (1) **Thin wrapper** — most QRSPI skills (design, structure, plan, pr, questions, research, worktree, implement) keep SKILL.md at ~25-35 lines: frontmatter + a short "Steps" list that spawns an agent. The substantive content lives in `.claude/agents/<name>.md`. (2) **Self-contained orchestrator** — `qrspi-work/SKILL.md` is 730 lines and holds the full state machine inline, deferring only cascade logic to `references/review-cascade.md`. For RUS-30 (a standalone reference skill, not an agent wrapper), the relevant model is: keep SKILL.md as the concise procedural body and push exhaustive detail (gotcha tables, alias sets, full lifecycle command transcripts) into `references/`.
**Evidence:**

```
   25  .claude/skills/qrspi-structure/SKILL.md
  119  .claude/skills/qrspi-ticket/SKILL.md
  730  .claude/skills/qrspi-work/SKILL.md
```

— `wc -l` over `.claude/skills/*/SKILL.md`
**Dependencies:** Wrapper skills depend on a matching agent in `.claude/agents/`.
**Implicit contracts:** `references/*.md` are loaded on demand, not auto-injected; the SKILL.md body must explicitly point the reader to them.

## Q3: What exact frontmatter fields does a valid SKILL.md use, and which are required?

**Answer:** Observed fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`, and (in agents, not skills) `model`. Across all 10 skills, the consistently-present fields are `name`, `description`, and `allowed-tools`. `command` and `argument-hint` appear on all QRSPI skills (they are command-style skills). For a reference/knowledge skill like RUS-30 that is auto-invoked rather than slash-invoked, `name` + `description` + `allowed-tools` are the load-bearing fields; `command`/`argument-hint` are optional. `qrspi-ticket` uses a plain tool list (`Read, Glob, Grep, Write, Bash, ...`) while wrapper skills use `Agent, Bash(pwd:*)`.
**Evidence:**

```
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation. ...
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
```

— `.claude/skills/qrspi-ticket/SKILL.md:1-7`
**Dependencies:** The harness parses YAML frontmatter to register the skill and gate its tools.
**Implicit contracts:** `description` is the trigger surface — it must describe WHEN to use the skill. `allowed-tools` restricts the skill's tool access.

## Q4: What is the established naming convention for skill name/command fields?

**Answer:** All project skills use the `qrspi-<phase>` prefix with lowercase-hyphenated names; `command` is `/<name>`. RUS-30 is NOT a QRSPI-workflow phase, so it should NOT take the `qrspi-` prefix. The ticket title says "named using git worktrees", which maps to a skill `name: using-git-worktrees`. This matches the global skill-naming style already present in the environment (e.g., `using-graphite-cli` is an installed skill with that exact gerund-prefixed style). Recommended: `name: using-git-worktrees`.
**Evidence:**

```
name: qrspi-structure
command: /qrspi-structure
```

— `.claude/skills/qrspi-structure/SKILL.md:2-4`; global skill `using-graphite-cli` referenced in repo `.claude/CLAUDE.md` skill list and AGENTS.md memory.
**Dependencies:** None.
**Implicit contracts:** Skill directory name must equal the `name` field.

## Q5: How are scripts/ referenced and invoked from within an existing skill?

**Answer:** NOT FOUND in this repo's skills — no `.claude/skills/*/scripts/` directory and no `*.sh` under `.claude/skills/` exist. The closest precedent for executable helpers is the repo-level `scripts/` directory at the root, which holds Python (`*.py`) eval tooling. Those scripts are executable (`-rwxr-xr-x`) with shebangs and are invoked by path. For RUS-30's bare-repo bootstrap script, the convention to adopt: place it under `.claude/skills/using-git-worktrees/scripts/`, make it executable, give it a `#!/usr/bin/env bash` shebang, and reference it from SKILL.md by its relative path within the skill directory.
**Evidence:**

```
-rwxr-xr-x  scripts/check_scope.py
-rwxr-xr-x  scripts/run_eval.py
```

— repo-root `scripts/` listing (`ls -la scripts/`)
**Dependencies:** None within skills today.
**Implicit contracts:** Root `scripts/*.py` are the project's only executable-helper precedent; they are kept executable and shebang'd. The user's global memory mandates the `writing-bash-scripts` skill for any `.sh` file (ShellCheck-clean).

## Q6: Is there a skill-builder skill available, and what does it expect?

**Answer:** No PROJECT-local skill-creator exists (`.claude/skills/skill-creator/` is absent). However, the environment provides a global `skill-creator` skill (and the user's global memory `feedback_skill_creator.md` mandates: "Always invoke the skill-creator skill and its eval loop when creating or substantially modifying a skill; never ship a SKILL.md ad-hoc"). The ticket's "Anthropic skill builder skill" requirement therefore maps to invoking the global `skill-creator` skill during implementation. Its expected output is a well-formed skill directory (SKILL.md + supporting dirs) plus an eval/triggering check.
**Evidence:**

```
no project skill-creator dir   (ls -d .claude/skills/skill-creator → absent)
```

— `.claude/skills/` listing; global skill `skill-creator` is available in the environment skill list; user memory `~/.agents/memory/feedback_skill_creator.md`.
**Dependencies:** Implementation phase must call the global `skill-creator` skill.
**Implicit contracts:** skill-creator owns the SKILL.md scaffolding and description-triggering optimization; do not hand-author frontmatter ad-hoc.

## Q7: Where should the new skill physically live, and does the repo distinguish project-local from global skills?

**Answer:** The new skill lives at `.claude/skills/using-git-worktrees/` (project-local). The repo's `.claude/CLAUDE.md` explicitly distinguishes project-local skills (in this repo's `.claude/skills/`) from global skills. Critically, the user's global memory imposes a HARD project-scope boundary: skills built for a ticket MUST live inside the project repo, never in `~/.claude/skills/`. The qrspi-work orchestrator's "Project scope restriction" block reiterates: "The deliverable for a ticket must live within the project repo."
**Evidence:**

```
### Codebase conventions
- Agent prompt definitions live in `.qrspi/agents/`
- Artifact templates live in `.qrspi/templates/` (reference only)
- Eval harness lives in `evals/` and `scripts/`
```

— `.claude/CLAUDE.md` (project instructions)
**Dependencies:** Harness skill discovery from `.claude/skills/`.
**Implicit contracts:** Ticket deliverables stay in-repo; writing to home-dir paths is forbidden.

## Q8: Does this repo use the bare-repo worktree pattern or the linked-worktree pattern, and would the skill's recommended layout conflict with the repo's own QRSPI worktree convention?

**Answer:** This repo uses the **linked-worktree** pattern, NOT the bare-repo pattern. The main checkout stays on `main`; per-ticket worktrees are created at `.worktrees/<ticket-id>/` and are gitignored. The ticket asks the SKILL to recommend the **bare-repo** pattern as primary. These do not conflict in code (the skill is documentation/guidance), but the research surfaces a real tension to call out in design: the repo's own convention is the linked pattern, so the skill should present bare-repo as the recommended pattern for fresh dedicated-worktree projects while acknowledging the linked pattern (which qrspi itself uses) as the lighter alternative for an existing single checkout.
**Evidence:**

```
.worktrees/      (.gitignore:1)
```
```
Each ticket gets an isolated git worktree at `.worktrees/<ticket-id>/`. ...
The main repo checkout stays on `main`; all ticket work happens in worktrees.
```

— `.gitignore:1`; `.claude/CLAUDE.md` Worktrees section
**Dependencies:** None — guidance only.
**Implicit contracts:** `.worktrees/` is gitignored and local-only; the skill's own examples should not assume the bare layout exists in this repo.

## Q9: What is the SKILL.md body size budget, and how do existing skills measure against it?

**Answer:** Acceptance criteria cap the body at under 500 lines / 5000 tokens. Existing skills are well under: the thin wrappers are 25-35 lines; `qrspi-ticket` is 119 lines; only `qrspi-work` (730 lines) exceeds 500 — and it is the outlier orchestrator, not a model for a reference skill. Target for RUS-30: keep SKILL.md comparable to `qrspi-ticket` (~100-200 lines) and push the exhaustive gotcha tables, alias sets, and full command transcripts into `references/`.
**Evidence:**

```
  119  .claude/skills/qrspi-ticket/SKILL.md
  730  .claude/skills/qrspi-work/SKILL.md
```

— `wc -l` over SKILL bodies
**Dependencies:** None.
**Implicit contracts:** Body stays concise; detail goes to references.

## Q10: How should the skill describe submodule and shared-stash gotchas without overstepping scope guidance?

**Answer:** The pattern to follow is content-partitioning, as `qrspi-work` does with `references/review-cascade.md`: keep the SKILL.md body to the actionable lifecycle (create → work → PR → merge → remove → prune) and the primary bare-repo pattern, then place the gotchas (submodules incomplete, shared `git stash`, shared hooks, IDE caveats) into a `references/gotchas.md`. Scope guidance from the ticket explicitly excludes general branching strategy and IDE-specific setup detail — so gotchas should be stated as warnings with the minimal mitigating command, not expanded into tutorials.
**Evidence:**

```
.claude/skills/qrspi-work/references/review-cascade.md   (the only references precedent)
```

— `.claude/skills/qrspi-work/references/`
**Dependencies:** None.
**Implicit contracts:** References are loaded on demand; SKILL.md must link to them explicitly.

## Q11: Does this repo have an eval harness for skills that a new skill must conform to, and what shape do skill evals take?

**Answer:** Yes. `evals/` holds `suite.json` (24KB, an array of `cases` each with `id`, `name`, `phase`, `prompt`, `context.files`, and weighted `assertions`), `graphite-evals.json`, `fixtures/` (ticket markdown inputs), and `golden/` (currently empty). Assertions are mostly `programmatic` checks like `output_file_exists(...)`, `section_count(...)`, `question_count(...)`. The runner is `scripts/run_eval.py` with `grade.py`, `diagnose.py`, `report.py`, `revise.py`, `check_scope.py`. IMPORTANT: every existing eval case targets a `phase` of the QRSPI workflow (questions, research, etc.). There is NO eval case shape for a standalone reference skill like `using-git-worktrees`. So conforming to this harness is not required for RUS-30 unless design chooses to add a case; the skill-creator skill's own eval loop (Q13) is the relevant validation path.
**Evidence:**

```
"cases": [ { "id": "case_001", "name": "questions_happy_path", "phase": "questions",
  "assertions": [ { "type": "programmatic", "check": "output_file_exists('questions.md')", ...
```

— `evals/suite.json:16-30`
**Dependencies:** `scripts/run_eval.py` consumes `evals/suite.json` and `evals/fixtures/`.
**Implicit contracts:** Eval cases are keyed by QRSPI phase; a non-phase skill does not slot into this suite without a new case type.

## Q12: How is the bare-repo bootstrap script expected to be validated — is there a ShellCheck/lint convention?

**Answer:** No repo-level `.shellcheckrc` or shell-lint CI config was found, and there are currently no `.sh` files in the repo (root `scripts/` is all Python). The binding convention is the USER's global memory: the `writing-bash-scripts` skill is mandatory for any `.sh` file and requires ShellCheck-clean, robust scripts (`set -euo pipefail` style). So the bootstrap script must be authored via / conform to the `writing-bash-scripts` skill and pass ShellCheck, even though no repo-local lint config enforces it.
**Evidence:**

```
no .sh files under repo;  root scripts/ contains only *.py
```

— `find .claude/skills -name '*.sh'` (empty); `ls scripts/` (Python only)
**Dependencies:** Global `writing-bash-scripts` skill governs `.sh` authoring.
**Implicit contracts:** Bash scripts must be ShellCheck-clean per user directive.

## Q13: How does an agent verify a skill is well-formed and triggers correctly?

**Answer:** Two signals. (1) **Structural validity** — valid YAML frontmatter with `name`/`description`/`allowed-tools`, directory named after the skill, body under the size budget. (2) **Triggering** — the global `skill-creator` skill includes an eval/benchmark loop that measures description-triggering accuracy and variance; the user's memory mandates running it when creating a skill. The repo's own `evals/` harness (`run_eval.py` → `grade.py` → `report.py`) is phase-specific and not the validation path for this skill. Therefore the "does it work" feedback surface for RUS-30 is the skill-creator eval loop plus manual confirmation that the lifecycle commands in the body are correct git invocations.
**Evidence:**

```
scripts/run_eval.py  scripts/grade.py  scripts/report.py   (phase-keyed eval tooling)
```

— root `scripts/` listing; global `skill-creator` skill (environment) and user memory `feedback_skill_creator.md`.
**Dependencies:** skill-creator eval loop is the relevant validator.
**Implicit contracts:** Description must encode WHEN-to-use for accurate triggering.

---

## Discovered Patterns

- **Thin-wrapper vs. fat-orchestrator split.** Nine of ten skills are ~25-35-line wrappers delegating to `.claude/agents/<name>.md`; only `qrspi-work` is a self-contained 730-line state machine. RUS-30 is neither a workflow phase nor an agent wrapper — it is a self-contained KNOWLEDGE/reference skill, the first of its kind in this repo. Its closest structural model is `qrspi-ticket` (119 lines, self-contained, no agent).
- **References are the overflow mechanism.** The single precedent (`qrspi-work/references/review-cascade.md`) shows references hold detailed tables/logic the body links to. RUS-30's gotchas, alias set, and full command transcripts belong there.
- **Gerund skill-naming for knowledge skills.** Workflow skills use `qrspi-<phase>`; the global knowledge skill `using-graphite-cli` uses `using-<tool>`. RUS-30 should follow the latter: `using-git-worktrees`.
- **No existing `scripts/` or `assets/` inside any skill.** RUS-30 introduces the first `scripts/` directory under a skill — bootstrap script is net-new convention.
- **Hard in-repo deliverable boundary.** Both `.claude/CLAUDE.md` and the qrspi-work scope block forbid writing skill deliverables to `~/.claude/`. The skill MUST be created at `.claude/skills/using-git-worktrees/`.

## Inconsistencies

- **Repo's own worktree pattern contradicts the ticket's recommended pattern.** This repo uses the LINKED pattern (`.worktrees/<ticket-id>/`, main checkout on `main`), while the ticket asks the skill to recommend the BARE-repo pattern as primary. Not a code conflict (the skill is guidance), but design must reconcile the two so the skill doesn't appear to contradict the host repo's documented convention.
- **`allowed-tools` style varies.** Wrapper skills use `Agent, Bash(pwd:*)`; `qrspi-ticket` uses a broad explicit tool list. There is no single canonical `allowed-tools` value to copy — design must choose an appropriate minimal set for a reference skill (likely `Read, Bash` for running the bootstrap/lifecycle commands, or none if purely advisory).
- **Eval harness scope gap.** `evals/suite.json` cases are all keyed to QRSPI phases; there is no fixture or assertion shape for a standalone reference skill, so the repo eval harness cannot directly grade RUS-30 without a new case type. Validation falls to the skill-creator eval loop instead.
