# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

> Scope note: REPO_ROOT is `/workspaces/qrspi/.worktrees/RUS-20`. The repo contains
> **only `qrspi-*` skills** under `.claude/skills/` — there is no `aws`/`aws-cli` skill
> and no `skill-creator` skill checked into this repo. The `skill-creator` skill referenced
> by several questions is a **harness-level (global) skill**, not present under REPO_ROOT, so
> any question targeting "the skill-creator skill definition" is answered NOT FOUND for
> in-repo content, with the closest in-repo evidence (the existing skill conventions) provided
> instead.

## Q1: What is the canonical on-disk layout that the agentskills.io standard prescribes (`SKILL.md` plus the optional `references/`, `scripts/`, `assets/` subdirectories), and where in this repo do existing skills place these files so the new aws-cli skill can mirror that convention?

**Answer:** No agentskills.io standard documentation exists under REPO_ROOT (searches for `agentskills`, `references/`, `assets/`, `scripts/` in `docs/` returned only QRSPI-workflow docs, none describing a skill directory standard). The *observable* in-repo convention: every skill is a directory under `.claude/skills/<skill-name>/` containing a `SKILL.md`. Of the 10 skills, **only `qrspi-work` uses a `references/` subdirectory** (`references/review-cascade.md`). **No skill in the repo ships a `scripts/` or `assets/` subdirectory** — those parts of the agentskills layout are unexercised here. So a new aws-cli skill mirroring the in-repo precedent would be `.claude/skills/aws-cli/SKILL.md` plus `.claude/skills/aws-cli/references/<topic>.md`.

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   <- only references/ dir in repo
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
... (each skill = one dir with a single SKILL.md; no scripts/ or assets/ anywhere)
```

— `.claude/skills/` (directory listing); `find .claude/skills -type f`
**Dependencies:** Skills are discovered by the Claude Code harness by directory name under `.claude/skills/`. No in-repo loader code references them.
**Implicit contracts:** Skill directory name == frontmatter `name` field (verified across all 10 skills). A skill is a directory, never a bare file. `references/` is sibling to `SKILL.md`.

## Q2: What required frontmatter fields (name, description, and any others) must `SKILL.md` carry for it to be valid, and what format/length constraints apply to each?

**Answer:** No validator or schema for SKILL.md frontmatter exists in the repo (no lint script checks frontmatter; `scripts/` has no skill-frontmatter validator). The *de facto* required fields, present in all 10 SKILL.md files, are: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. Every file uses YAML frontmatter delimited by `---` lines at the top. `description` is a single-line string (quoted with double quotes when it contains a colon or embedded quotes, as in `qrspi-work` and `qrspi-research`; bare otherwise). `allowed-tools` is a comma-separated tool allowlist, optionally with argument scoping like `Bash(pwd:*)` or specific MCP tools like `mcp__linear__get_issue`.

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
**Dependencies:** Frontmatter is consumed by the Claude Code harness (not by any in-repo script). `command`/`argument-hint` drive the slash-command wrapper UX.
**Implicit contracts:** `name` matches the directory name; `command` is `/<name>`; `argument-hint` documents positional args; descriptions starting with what the skill does and then "Use when…" (see Q4). Length constraints (500 lines / 5000 tokens) are NOT enforced anywhere in-repo — they are an external/acceptance-criteria convention.

## Q3: What inputs does the Anthropic skill builder (skill-creator) skill expect, and what outputs/files does it produce, so the ticket's "use the Anthropic skill builder skill to generate the skill" step can be executed concretely?

**Answer:** NOT FOUND — the `skill-creator` skill is a harness-level skill, not present under REPO_ROOT. Searches: `find . -iname "*skill-creator*"` (no files); `grep -rni "skill-creator"` in repo returns a single passing mention in `.claude/agents/qrspi-structure.md:40` ("Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice."). That line documents *when* to invoke skill-creator (as the final validation step of the slice that authored the skill), but not its inputs/outputs. Its full input/output contract lives outside the project scope and cannot be mapped here.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the
   final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`
**Dependencies:** The QRSPI structure phase treats skill-creator invocation as an in-slice validation step.
**Implicit contracts:** Skill creation/validation is folded into the producing slice, not split into its own vertical slice.

## Q4: How is the `description` field in `SKILL.md` used for trigger/discovery, and what phrasing patterns do existing skills use to encode when an agent should invoke them?

**Answer:** The `description` is what the harness surfaces in the available-skills list for auto-invocation/triggering (visible in the system reminder's skill list, where each entry is `name: description`). The repo-wide phrasing pattern: **a capability clause** ("Produce a design document…", "Generate atomic implementation steps…") **followed by a "Use when…/Use after…" trigger clause**, and for the most trigger-sensitive skill (`qrspi-work`) explicit example trigger phrases ("Trigger on any variant of: 'work on <ticket-id>'…"). Short single-phase skills use one or two sentences; `qrspi-work` uses a long quoted description packed with trigger variants.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the
user asks to 'work on' a ticket (e.g., 'work on RUS-42'). … Trigger on any variant of:
'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference
to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (frontmatter `description`)
**Dependencies:** Description text is the sole trigger signal the harness uses; there is no separate trigger config in-repo.
**Implicit contracts:** Pattern = "<what it does>. Use when/after <condition>. [Trigger on: <example phrases>]." Heavier trigger phrasing for skills that must fire on many natural-language variants.

## Q5: What is the SKILL.md body size budget the acceptance criteria require (under 500 lines / 5000 tokens), and how do existing repo skills split content between `SKILL.md` and `references/` to stay within that budget?

**Answer:** No in-repo mechanism enforces a 500-line/5000-token budget (no lint, no eval assertion on SKILL.md length). Observed body sizes: the single-phase wrapper skills are tiny (25–35 lines each); `qrspi-ticket` is 127 lines; `qrspi-work` is the largest at **565 lines** — already over a 500-line budget. The only example of splitting detail into `references/` is `qrspi-work`, which offloads the review-cascade logic to `references/review-cascade.md` (77 lines) and points to it inline ("see `references/review-cascade.md`"). So the in-repo precedent for staying lean is: keep procedural detail in `references/<topic>.md` and reference it by relative path from `SKILL.md`.

**Evidence:**

```
qrspi-work/SKILL.md            565 lines   (references review-cascade.md)
qrspi-ticket/SKILL.md          127 lines
qrspi-implement/SKILL.md        35 lines
qrspi-design/SKILL.md           28 lines
qrspi-pr/SKILL.md               28 lines
qrspi-questions/SKILL.md        26 lines
qrspi-research/SKILL.md         26 lines
qrspi-plan/SKILL.md             26 lines
qrspi-structure/SKILL.md        25 lines
qrspi-worktree/SKILL.md         25 lines
references/review-cascade.md    77 lines
```

— `wc -l .claude/skills/*/SKILL.md`
**Dependencies:** `qrspi-work/SKILL.md` depends on `references/review-cascade.md` (referenced by relative path).
**Implicit contracts:** `references/` files are referenced by **relative path** ("`references/review-cascade.md`") from the SKILL.md body. There is no in-repo size gate — the 500-line/5000-token budget is an external acceptance criterion, and `qrspi-work` already exceeds 500 lines.

## Q6: How should the `references/` material be partitioned across the three required topics (JMESPath patterns, common waiter commands, service-specific cheat sheets), and is there a precedent in existing skills for one reference file per topic versus a combined file?

**Answer:** The only precedent in the repo is a **single, single-topic reference file**: `qrspi-work/references/review-cascade.md` (one file = one cohesive topic, the review-cascade logic). There is no example of multiple reference files in one skill, so there is no in-repo precedent for either "one file per topic" or "combined file" with more than one topic. The closest signal is that the one existing reference file is scoped to a single coherent concern, which would favor one-file-per-topic (e.g. `references/jmespath.md`, `references/waiters.md`, `references/services.md`). No JMESPath/waiter/cheat-sheet content exists anywhere in the repo (grep for `jmespath`, `waiter`, `cloudformation` found nothing outside questions.md).

**Evidence:**

```
.claude/skills/qrspi-work/references/review-cascade.md   <- single topic: review cascade logic
(no other skill has a references/ dir; no multi-file references/ precedent exists)
```

— `find .claude/skills -path '*/references/*'`
**Dependencies:** None beyond the SKILL.md → references relative-path link.
**Implicit contracts:** One reference file = one cohesive topic (sole observed convention).

## Q7: How does the skill-creator workflow handle a skill that is documentation-only (no `scripts/` needed), and what is the minimal valid skill when the `scripts/` and `assets/` directories are omitted?

**Answer:** The skill-creator workflow itself is NOT FOUND in-repo (see Q3). However, the repo directly demonstrates the **minimal valid documentation-only skill**: a directory containing just `SKILL.md` with the five-field frontmatter and a markdown body, no `scripts/` and no `assets/`. Eight of the ten skills are exactly this (e.g. `qrspi-design`, `qrspi-plan` — 25–28 lines, frontmatter + body, no subdirectories). So omitting `scripts/`/`assets/` is the normal case in this repo, not an exception.

**Evidence:**

```
.claude/skills/qrspi-plan/
└── SKILL.md          (26 lines, frontmatter + body, no scripts/ or assets/)
```

— `find .claude/skills/qrspi-plan -type f`
**Dependencies:** None — a documentation-only skill has no executable artifacts.
**Implicit contracts:** Minimal valid skill = `<name>/SKILL.md` with `name`, `description`, `command`, `argument-hint`, `allowed-tools` frontmatter + a body. `references/` is optional; `scripts/`/`assets/` are never used in this repo.

## Q8: The ticket says "do not encode AWS account IDs, specific resource names, or region choices" — what existing convention or lint/eval check, if any, verifies a skill avoids embedding environment-specific values, and where would such a check live?

**Answer:** No check that scans skill content for embedded environment-specific values (account IDs, resource names, regions) exists in the repo. The only "scope" check is `scripts/check_scope.py`, which verifies the **implement agent only touched files listed in its session task list** — it diffs backtick-wrapped file paths in `impl-log.md` against those in the worktree-session manifest; it does **not** inspect file *content* for hard-coded secrets/values. Searches of `scripts/` and `evals/` found no secret/value linter. The relevant in-repo *convention* (not a check) is the harness's own portability principle: reviewers, team, and project are resolved from gitignored `.qrspi/config.json` rather than hard-coded (documented in `.claude/CLAUDE.md`), establishing a "no environment-specific values committed" norm — but it is enforced by review, not tooling.

**Evidence:**

```python
def check_scope(impl_log_path: str, worktree_session_path: str) -> dict:
    allowed = load_allowed_files(worktree_session_path)
    touched = extract_touched_files(impl_log_path)
    out_of_scope = touched - allowed   # compares FILE PATHS, not file content
```

— `scripts/check_scope.py:39-44`
**Dependencies:** `check_scope.py` is wired as a `script`-type eval assertion (per `docs/eval-system.md`), consuming `impl-log.md` and the worktree-session manifest.
**Implicit contracts:** "No environment-specific values" is enforced by human review / authoring discipline, not by any automated check. If such a check were added it would live in `scripts/` and be wired as a `script`-type assertion in `evals/suite.json`, mirroring `check_scope.py`.

## Q9: The ticket scopes out full IaC frameworks (Terraform, CDK, Pulumi) while keeping CloudFormation CLI commands in scope — where is the convention for documenting scope boundaries within a `SKILL.md`, and how do existing skills express "in scope / out of scope" guidance?

**Answer:** No SKILL.md in the repo uses a dedicated "In scope / Out of scope" heading. The closest in-repo convention for stating scope/non-goals is **the ticket template, not a skill**: `qrspi-ticket/SKILL.md` defines explicit `## Constraints` and `## Out of Scope` sections for *ticket bodies* (lines 93 and 96). Within SKILL.md bodies, scope/non-goal guidance is expressed **inline as imperative "Do NOT / Never" directives** rather than a section — heavily used in `qrspi-work` (e.g. "Do NOT touch downstream phases", "Never pass relative `.qrspi/...` paths", "Never guess the action") and via `### Project scope firewall` / `## Project scope restriction` subsections (lines 428, 434, 455, 461). So precedent points to either (a) inline "In scope / Out of scope" prose, or (b) a `## Scope` / firewall-style subsection modeled on qrspi-work.

**Evidence:**

```
.claude/skills/qrspi-ticket/SKILL.md:93:## Constraints
.claude/skills/qrspi-ticket/SKILL.md:96:## Out of Scope
.claude/skills/qrspi-work/SKILL.md:434:## Project scope restriction
.claude/skills/qrspi-work/SKILL.md:282: ... Do NOT touch downstream phases ...
```

— `grep -n '^#' .claude/skills/qrspi-ticket/SKILL.md`; `.claude/skills/qrspi-work/SKILL.md:434`
**Dependencies:** None.
**Implicit contracts:** Scope boundaries are conveyed either by `## Out of Scope` (ticket-template precedent) or inline `Do NOT/Never` imperatives (skill-body precedent). No standardized heading is enforced.

## Q10: How is a newly authored skill validated in this repo — what does the skill-creator eval/benchmark loop check, and how is it invoked to confirm the aws-cli skill's frontmatter, body length, and description triggering?

**Answer:** The repo's eval harness (`scripts/run_eval.py` + `scripts/grade.py`, `report.py`, `diagnose.py`, `revise.py`, suites in `evals/`) is **scoped to QRSPI workflow phase prompts only** — `evals/suite.json` defines 15 cases across questions/research/design/structure/plan/worktree/implement/pr, and `evals/graphite-evals.json` covers the Graphite CLI skill. **There is no eval case for skill-creation, frontmatter validation, body length, or description triggering.** Moreover `scripts/run_eval.py` is an explicit **non-functional placeholder**: `execute_single()` returns empty output and never invokes an agent (`result.output = ""` with a comment "Replace this block with actual agent invocation"). So there is no working automated validation loop in-repo for a newly authored skill's frontmatter/length/triggering.

**Evidence:**

```python
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
...
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:117-135`
**Dependencies:** `run_eval.py` loads a suite (`evals/suite.json`) and a skill prompt; downstream `grade.py`/`report.py` consume `results.json`. None of these target skill-authoring validation.
**Implicit contracts:** Eval cases are declared in `evals/suite.json` with weighted `programmatic`/`llm_judge`/`script` assertions; validating an aws-cli skill via this harness would require adding a new case there — but the executor is a stub, so it would not actually run.

## Q11: What manual end-to-end verification path exists for a documentation skill given that the `evals/` harness is described as a non-functional placeholder, and how have prior skills been confirmed working?

**Answer:** The repo's documented stance (`.claude/CLAUDE.md`, "Codebase conventions") is explicit: **"The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs."** For pure-logic Python helpers there are stdlib-only `_test.py` siblings (`scripts/qrspi_*_test.py`). For a *documentation skill* (no executable logic, hence no unit tests), the only verification path is **manual end-to-end invocation** — authoring the SKILL.md, then invoking the skill in a live Claude Code session and confirming it triggers and produces the intended guidance. There is no recorded golden-output corpus (`evals/golden/` contains only `.gitkeep`).

**Evidence:**

```
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` ("Codebase conventions"); corroborated by `scripts/run_eval.py:117-135` (stub) and `evals/golden/.gitkeep` (empty golden dir)
**Dependencies:** Manual verification depends on the live harness loading `.claude/skills/<name>/SKILL.md`.
**Implicit contracts:** Documentation skills (no scripts) ship without automated tests; correctness is established by manual end-to-end invocation, consistent with the project's stated verification policy.

## Q12: How is the creation or modification of a skill surfaced and tracked in this repo's workflow — what record (PR description, artifact, or status field) signals that the skill was built via the skill-creator skill and meets the acceptance criteria checklist?

**Answer:** Skill files are ordinary tracked files under `.claude/skills/`; their creation/modification is surfaced through the standard **QRSPI PR-gated lifecycle** — i.e. it lands as a slice PR in the ticket's Graphite stack, and the **PR review state is the authority** for acceptance (`.claude/CLAUDE.md` "Lifecycle — PR-gated"). The phase artifacts that record the work are persisted deterministically by `scripts/qrspi_persist.py`, which moves a staged file from `/tmp/phase-stage/<ticket>/<artifact>.md` to the canonical `.worktrees/<id>/.qrspi/<id>/<artifact>.md` (artifacts: questions, research, design, structure, plan, worktree). There is **no skill-specific status field or skill-creator provenance record** — nothing stamps "built via skill-creator". The acceptance-criteria checklist is verified via the PR description / review (the `qrspi-pr` phase maps acceptance criteria; per `docs/eval-system.md` case_013 covers "acceptance criteria mapping").

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)
ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]
```

— `scripts/qrspi_persist.py:43,58-62`
**Dependencies:** Persistence (`qrspi_persist.py`) → canonical `.qrspi/<id>/` artifacts → committed in slice PR → PR review state (`scripts/qrspi_resolve_state.py`) gates advancement.
**Implicit contracts:** The signal that work is "done and accepted" is **PR approval** (reviewDecision APPROVED + zero unresolved threads), not a Linear status or a skill-creator marker. `ARTIFACTS` does not include any skill-creation-specific artifact; a new skill is just a code change inside an implementation slice.

---

## Discovered Patterns

- **Skill = directory under `.claude/skills/<name>/` with a single `SKILL.md`.** Directory name == frontmatter `name` == `/command` (without slash). Verified across all 10 skills.
- **Five-field frontmatter convention** on every SKILL.md: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. No schema enforces it; it is consistent by convention.
- **Two-tier skill sizing:** thin slash-command wrappers (25–35 lines) that mostly spawn a sub-agent (`allowed-tools: Agent, Bash(pwd:*), …`), versus one fat orchestrator (`qrspi-work`, 565 lines) that offloads detail to `references/`.
- **`references/` is the only optional subdir actually used** (once, in `qrspi-work`); `scripts/` and `assets/` are never used in this repo.
- **Scope/non-goals are expressed inline as `Do NOT/Never` imperatives** within skill bodies, and as explicit `## Out of Scope` / `## Constraints` headings in the *ticket* template (`qrspi-ticket`), not in skill bodies.
- **Description = capability clause + "Use when/after" trigger clause (+ explicit trigger-phrase list for high-fire skills).**
- **Deterministic, self-locating Python helpers** (`qrspi_persist.py`, `qrspi_resolve.py`) derive REPO_ROOT from `__file__`, never from cwd/args, to dodge a weak worker model mangling the `qrspi` path token. Each has a stdlib-only `_test.py` sibling.
- **Acceptance/advancement authority is PR review state**, computed by `scripts/qrspi_resolve_state.py`; Linear status is a best-effort projection only.

## Inconsistencies

- **`qrspi-work/SKILL.md` is 565 lines** — already over the 500-line budget the questions cite as an acceptance criterion. The repo states the budget as a goal but does not enforce it and has a skill that violates it, so the budget is aspirational, not a hard repo invariant.
- **No `skill-creator` skill exists in this repo**, yet `.claude/agents/qrspi-structure.md:40` instructs agents to "invoke skill-creator" as a validation step. The instruction assumes a harness-level skill that is not part of REPO_ROOT — an in-repo reference to an out-of-repo dependency.
- **No automated validation for skills.** `docs/eval-system.md` describes a rich 5-stage eval pipeline with weighted assertions, but `scripts/run_eval.py:117-135` is an explicit stub that never invokes an agent (`result.output = ""`), and `evals/golden/` is empty (`.gitkeep` only). The documented eval system and the actual executable code diverge; `.claude/CLAUDE.md` candidly flags the harness as a "non-functional placeholder", contradicting the polished pipeline narrative in `docs/eval-system.md`.
- **`check_scope.py` checks file *paths*, not content.** Despite the questions assuming a check that prevents embedding environment-specific values, the only scope check verifies which files were touched, not what they contain — there is no secret/value content linter anywhere in `scripts/` or `evals/`.
