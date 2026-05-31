# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T16:02:52Z
**Generated:** 2026-05-31T16:05:00Z
**Status:** draft

## Q1: What is the on-disk directory layout of an existing agent skill in this repo (SKILL.md plus any references/, scripts/, assets/ subdirectories), and where do skills physically live?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, each containing a `SKILL.md`. There are 10 skill directories, all `qrspi-*`. Only one skill (`qrspi-work`) has a subdirectory: `references/`. None has `scripts/` or `assets/`. So the repo's only precedent for the agentskills.io `references/` pattern is `qrspi-work/references/`.

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
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing)
**Dependencies:** Skill directories are self-contained; no cross-skill imports observed.
**Implicit contracts:** Skill directory name matches the `name:` frontmatter field (kebab-case).

## Q2: How are reference files under a skill's references/ directory linked or pointed to from the SKILL.md body in existing skills?

**Answer:** References are linked by a relative path from the skill root, written as inline prose instructing the agent to read the file. The only example: `qrspi-work/SKILL.md` line 272 says `Read references/review-cascade.md for cascade logic.` — i.e. a bare relative path `references/<file>.md`, not a markdown link.

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md:272:   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:272`
**Dependencies:** The body assumes the agent's cwd is the skill root (or resolves relative to SKILL.md).
**Implicit contracts:** Reference docs are loaded on demand ("read X when Y"), not inlined — keeps the body small.

## Q3: What exact frontmatter fields are required and permitted in a SKILL.md, and what are their value formats?

**Answer:** Observed frontmatter fields across the 10 skills: `name` (kebab-case string, required, matches dir name), `description` (string; may be quoted when it contains a colon, as in qrspi-work), `command` (slash command, e.g. `/qrspi-design`), `argument-hint` (e.g. `<ticket-id>`), `allowed-tools` (comma-separated tool list; supports scoped forms like `Bash(pwd:*)` and MCP tool names). The phase **agent** definitions in `.claude/agents/*.md` use a different schema: `name`, `description`, `model: opus`, and a `claude:` block with `tools:`. For an agentskills.io content skill, `name` + `description` are the load-bearing fields; `command`/`argument-hint`/`allowed-tools` are present on the qrspi command-style skills but are optional for an auto-triggered content skill.

**Evidence:**

```
---
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation. Use when starting a new QRSPI workflow or when the user wants to create a ticket.
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
---
```

— `.claude/skills/qrspi-ticket/SKILL.md:1-7`
**Dependencies:** Tool gating is enforced by `allowed-tools` (skills) or `claude.tools` (agents).
**Implicit contracts:** `description` carries the trigger guidance ("Use when…"); descriptions consistently end with usage triggers.

## Q4: Is there a naming convention for the skill directory and the name: field that "writing-dockerfiles" must conform to?

**Answer:** Yes — kebab-case. All existing skills use kebab-case directory names that exactly equal their `name:` field (e.g., `qrspi-ticket`, `qrspi-work`). The repo's skills are namespaced with a `qrspi-` prefix, but that prefix denotes the workflow family; a standalone content skill is not required to carry it. The ticket's requested name "writing-dockerfiles" is already valid kebab-case.

**Evidence:**

```
name: qrspi-worktree   (dir: .claude/skills/qrspi-worktree/)
name: qrspi-work       (dir: .claude/skills/qrspi-work/)
```

— `.claude/skills/qrspi-worktree/SKILL.md:2`, `.claude/skills/qrspi-work/SKILL.md:2`
**Dependencies:** Directory name == name field (discovery relies on this).
**Implicit contracts:** Skill discovery is by directory name; the `name:` must match to avoid ambiguity.

## Q5: What does the Anthropic "skill builder" / skill-creator skill require as input and produce as output, and is it available in this environment?

**Answer:** NOT FOUND in the repo. There is no `skill-creator` or "skill builder" definition under `.claude/` or anywhere in `REPO_ROOT`. Searches for `skill-creator`, `skill builder`, and a manifest (`plugin.json`, `marketplace.json`) returned nothing in-repo. The skill-creator is a host-level (global) Claude Code capability outside `REPO_ROOT`, so its exact I/O contract cannot be confirmed from the codebase. Per scope rules it is "NOT FOUND — targets a resource outside the project scope."
**Evidence:** `find` for manifests returned no results; `.claude/skills/` contains only `qrspi-*` skills.
**Dependencies:** None in-repo.
**Implicit contracts:** None observable.

## Q6: Are skills registered anywhere (index, manifest, settings.json, plugin listing) that a new skill must be added to, or are they auto-discovered by directory presence?

**Answer:** Auto-discovered by directory presence. No `settings.json`/`settings.local.json` exists under `.claude/` in the worktree, and no skill manifest/index file exists anywhere in the repo. Therefore creating `.claude/skills/writing-dockerfiles/SKILL.md` is sufficient for discovery; no registry edit is required.

**Evidence:**

```
=== settings files ===   (find .claude -name 'settings*.json' → no output)
=== any manifest/index ===  (find for plugin.json/marketplace.json/*.manifest → no output)
```

— `find .claude -name 'settings*.json'` (empty), repo-wide manifest find (empty)
**Dependencies:** Skill loader scans `.claude/skills/*/SKILL.md`.
**Implicit contracts:** No central list to keep in sync — directory presence is the source of truth.

## Q7: What enforces or measures the "SKILL.md body under 500 lines / 5000 tokens" constraint — is there an existing linter, eval, or convention?

**Answer:** No automated enforcement for this specific skill type. The eval harness (`evals/suite.json`, `scripts/run_eval.py`, `scripts/grade.py`) is purpose-built for the QRSPI workflow phase prompts (cases keyed by `phase: questions|research|design|...`) and asserts on generated artifacts like `questions.md`, not on SKILL.md body size. The "500 lines / 5000 tokens" is a convention from the ticket/agentskills.io, not a repo-enforced check. As a reference point, existing bodies range from 25 lines (most phase skills) to 730 lines (`qrspi-work`), so 500 is a soft target the repo already exceeds in one case.

**Evidence:**

```
   25 .claude/skills/qrspi-research/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  730 .claude/skills/qrspi-work/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`; `evals/suite.json` cases are phase-scoped
**Dependencies:** Body size can be checked manually with `wc -l` / token count.
**Implicit contracts:** Smaller is preferred; large procedural skills (qrspi-work) are tolerated but are the exception.

## Q8: How do existing skills handle the boundary between concise SKILL.md guidance and detailed references/ material — what lives in the body vs. references?

**Answer:** Only `qrspi-work` demonstrates the split. Its SKILL.md holds the primary procedure (state machine, phase dispatch, git rules) inline, and offloads one self-contained decision algorithm — the review cascade logic — to `references/review-cascade.md`, loaded on demand. The reference file is a focused topic (cascade rules) that would bloat the main flow. Pattern: body = always-needed guidance; references = deep, situational detail pulled in only when the relevant branch is hit.

**Evidence:**

```
# Review Cascade Logic
When planning review feedback requires changes to an artifact, downstream artifacts
may be invalidated. The planning artifacts form a dependency chain:
Questions → Research → Design → Structure → Plan → Work Tree
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-7`
**Dependencies:** Body references the file by relative path (Q2).
**Implicit contracts:** Each reference file is a single coherent topic; the body tells the agent precisely when to open it.

## Q9: Is there an existing eval/test pattern that verifies a skill triggers correctly on its description and produces expected behavior?

**Answer:** Partial. `evals/suite.json` defines cases with programmatic and (likely) model-graded assertions, but every case targets a QRSPI workflow phase that produces a named artifact (e.g. `output_file_exists('questions.md')`, `no_solution_language(...)`). There is no existing eval case for a content/reference skill like writing-dockerfiles, and no trigger-accuracy harness in-repo (description triggering is a host concern). The skill-creator's own eval loop (host-level) is the mechanism the ticket process implies, but it is not present in `REPO_ROOT`.

**Evidence:**

```
"assertions": [
  { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
  { "type": "programmatic", "check": "no_solution_language('questions.md')", "weight": 2.0 }
]
```

— `evals/suite.json` (case_001 assertions)
**Dependencies:** `scripts/run_eval.py` loads `suite.json`; `scripts/grade.py` scores.
**Implicit contracts:** Eval cases assert on produced artifacts and forbidden language, not on prose-skill content.

## Q10: What testing/validation convention applies to a documentation-only skill (no executable code), and what would "tested" mean here per project TDD expectations?

**Answer:** For a prose/reference skill there is no compile/run target, so "tested" reduces to verifiable, mechanical checks: valid YAML frontmatter (parseable, required `name`/`description` present), body within the size budget (wc -l / token estimate), every `references/` file referenced by the body actually exists (no dangling links) and vice-versa, and the example Dockerfiles in references being syntactically valid (parseable by `docker build --check` / a Dockerfile linter such as hadolint if available, else manual structural review). The repo's eval harness does not cover this skill type, so validation is via a small checker (script or manual checklist) rather than the existing `suite.json`.
**Evidence:** No test files accompany existing skills (`ls .claude/skills/*/` shows only SKILL.md and the one references dir). `scripts/` are eval-runner utilities, not skill validators.
**Dependencies:** Optional external linters (hadolint, docker) — presence unconfirmed in this environment.
**Implicit contracts:** "Tested" for prose skills = structural/static validation, not behavioral execution.

## Q11: Are there reusable assets (example Dockerfiles, snippets, scripts) elsewhere in the repo the references could draw on or must stay consistent with?

**Answer:** NOT FOUND as reusable Dockerfile assets. The repo has no `Dockerfile` in source. The `.devcontainer/` directory exists (devcontainer config) and `docs/container-sandbox/` discusses container sandboxing at a design level (Kata/Firecracker, credential injection), but these are prose research docs about runtime sandboxing, not build-time Dockerfile examples to reuse. So the skill's example Dockerfiles will be authored fresh; there is no in-repo Dockerfile style to stay consistent with.

**Evidence:**

```
docs/container-sandbox/container-sandbox-prd.md
docs/container-sandbox/research/q01-kata-vs-firecracker.md
docs/container-sandbox/research/q09-credential-injection.md
```

— `grep -rli docker` (only docs/, no Dockerfiles); `.devcontainer/` is devcontainer config
**Dependencies:** None — examples are net-new.
**Implicit contracts:** None constrain Dockerfile style in-repo.

## Q12: How is skill performance or trigger accuracy measured and reported in this repo?

**Answer:** Via the eval harness: `scripts/run_eval.py` executes `evals/suite.json` cases over multiple trials (defaults: 3 trials, 120s timeout), `scripts/grade.py` scores assertions, `scripts/report.py` reports, with results landing under `results/`. `docs/eval-system.md` documents the system. However, all of this is scoped to QRSPI workflow phase prompts, not to a content skill's trigger accuracy. Trigger-accuracy/variance analysis for a description is a skill-creator (host-level) concern, not implemented in this repo's harness. So post-creation observability for writing-dockerfiles is limited to manual review plus any host-side skill-creator eval loop.

**Evidence:**

```
scripts/run_eval.py   scripts/grade.py   scripts/report.py   scripts/diagnose.py
"defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 }
```

— `evals/suite.json` defaults; `scripts/` listing; `docs/eval-system.md`
**Dependencies:** `run_eval.py` → `grade.py` → `report.py`; outputs to `results/`.
**Implicit contracts:** Eval results are per-phase artifact scores; no prose-skill quality metric exists in-repo.

---

## Discovered Patterns

- **Skill discovery is purely directory-based.** No manifest, no settings.json registration. Adding `.claude/skills/<name>/SKILL.md` is the entire registration step.
- **`name:` field == directory name, kebab-case, every time.** Hard invariant for discovery.
- **`description:` doubles as the trigger spec.** Every skill ends its description with "Use when…/Trigger on…" guidance. This is where triggering quality is won or lost.
- **Two distinct schemas coexist:** command-style skills (`.claude/skills/*/SKILL.md` with `command`/`argument-hint`/`allowed-tools`) and internal agents (`.claude/agents/*.md` with `model` + `claude.tools`). A content skill follows the skill schema and only strictly needs `name` + `description`.
- **References pattern is "load on demand":** body stays lean, deep topics live in `references/<topic>.md`, body says exactly when to read each. Only `qrspi-work` uses it today, so writing-dockerfiles will be the second example and should mirror its relative-path linking style.
- **No in-repo Dockerfiles** — examples are authored fresh; no existing style to match.

## Inconsistencies

- The project's stated convention "Agent prompt definitions live in `.qrspi/agents/`" (`.claude/CLAUDE.md`) does not match reality: agent definitions actually live in `.claude/agents/`, and `.qrspi/agents/` does not exist. Minor doc drift; does not affect this skill but worth noting if the skill is ever cross-referenced.
- The "SKILL.md body under 500 lines" target (ticket/agentskills.io) is already violated by `qrspi-work` (730 lines), so the repo does not enforce it. The new skill should still honor the target since it is an explicit acceptance criterion.
- The eval harness (`evals/`, `scripts/`) is QRSPI-phase-specific and provides no validation path for a content skill, despite the project's TDD directive. Validation for this skill must be defined newly (structural checks), not reused from the harness.
