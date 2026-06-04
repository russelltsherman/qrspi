# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T11:53:10Z
**Status:** draft

> **Scope note that governs many answers below.** The `skill-creator` skill is **not present
> anywhere under REPO_ROOT** (`/workspaces/qrspi/.worktrees/RUS-29`). The only skills in this
> repo are the ten `qrspi-*` skills under `.claude/skills/`. `skill-creator` appears only as a
> *named, globally-available* Claude Code skill (it shows up in the harness skill list outside
> the repo and is referenced by user memory directives). Per the project-scope firewall, its
> internal SKILL.md, templates, and validation logic live outside REPO_ROOT and were **not
> read**. Questions that target skill-creator internals (Q1, Q3, Q7, Q9, Q10, Q12) are answered
> with what the repo itself establishes; the skill-creator-specific portions are marked
> **NOT FOUND — out of project scope**. Questions about *existing skills' conventions* (Q2, Q4,
> Q5, Q6, Q8, Q11) are fully answerable from the repo.

---

## Q1: What is the canonical on-disk layout the skill-creator skill produces for a new skill (SKILL.md plus the optional `references/`, `scripts/`, `assets/` subdirectories), and where does it place generated skills?

**Answer:** The skill-creator skill's own layout/output logic is **NOT FOUND — out of project
scope** (no `skill-creator/` directory exists under REPO_ROOT; `find .claude/skills -type d`
returns only the ten `qrspi-*` skills). What the *repo* demonstrates as the on-disk layout for a
skill is: a per-skill directory `.claude/skills/<name>/` containing a required `SKILL.md`, plus
an **optional** `references/` subdirectory holding supporting `.md` files. Only one skill in this
repo (`qrspi-work`) uses a subdirectory, and it is `references/` (not `scripts/` or `assets/`).
No skill in this repo ships a `scripts/` or `assets/` subdirectory, so those are unattested here.

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

— `find .claude/skills -type f` (full listing) — `.claude/skills/`

**Dependencies:** Skills are loaded by the Claude Code harness from `.claude/skills/<name>/SKILL.md`. No repo code reads these.
**Implicit contracts:** Each skill = one directory whose name matches the `name` frontmatter field; `SKILL.md` is mandatory; subdirectories (`references/`) are optional and only created when supporting material exists. Search queries attempted: `find .claude -type d -name skills`, `ls .claude/skills/skill-creator/` (no such dir), `grep -rl skill-creator . --include=*.md/*.json/*.py`.

## Q2: How do existing skills reference their `references/` material from the SKILL.md body — by relative path, by explicit instruction to read, or by some loader convention — so the dockerfile skill's language-specific reference files are discoverable?

**Answer:** By a **bare relative path embedded in prose**, with an implicit "go read it" instruction
(parenthetical "see ..."). There is no loader directive, no front-matter manifest, and no explicit
"Read the file at ..." imperative. The single example in the repo is `qrspi-work` referencing
`references/review-cascade.md`. The path is relative to the skill's own directory
(`.claude/skills/qrspi-work/references/review-cascade.md`). The referenced file is a normal Markdown
doc with its own headings; it is not auto-loaded — the agent is expected to open it when the prose
points there.

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
here; a design-level change that invalidates plan/impl is handled by `reset`, not revise.
```

— `.claude/skills/qrspi-work/SKILL.md:282-283`

**Dependencies:** The reference doc itself stands alone (review-cascade.md:1-30 is plain Markdown with `#` headings).
**Implicit contracts:** Reference path is relative to the skill directory; the reader (the agent) must follow the "see `references/...`" cue manually — there is no automatic inclusion. This is the only attested pattern, so a dockerfile skill should mirror it: cite `references/<lang>.md` inline with a "see" / "read" cue.

## Q3: What exact frontmatter fields does the agentskills.io / Anthropic skill standard require in SKILL.md (name, description, and any others), and what format/validation does the skill-creator enforce on them?

**Answer:** The skill-creator's *enforced* validation is **NOT FOUND — out of project scope**
(no skill-creator code in repo; no frontmatter validator/linter exists under REPO_ROOT — grep for
`settings*.json`, validation scripts returned nothing). The *de facto* frontmatter schema used by
every skill in this repo is observable empirically. Required-in-practice across all ten skills:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`. Every `qrspi-*` SKILL.md carries
exactly those five fields (no more, no fewer). Note these include QRSPI-specific slash-command fields
(`command`, `argument-hint`) that the generic agentskills standard does not mandate; the universal
minimum the standard requires is `name` + `description`, both present everywhere here.

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

**Dependencies:** Frontmatter is consumed by the Claude Code harness (skill loader), not by any in-repo script.
**Implicit contracts:** `name` must equal the directory name (Q5); `description` drives auto-invocation (Q4); `command` is the slash form `/<name>`; `argument-hint` documents positional args; `allowed-tools` is a comma-separated tool allowlist. No repo-side validator enforces any of this — it is convention only. Search queries attempted: `find . -name 'settings*.json'`, `grep -ri frontmatter/validate`, none found.

## Q4: How is a skill's description field written in existing skills to control auto-invocation triggering, and what length or phrasing constraints apply?

**Answer:** Two styles coexist. (1) **Short form** (8 of 10 skills): one or two sentences, typically
"`<what it does>`. Use after/when `<trigger condition>`." — e.g. qrspi-research, qrspi-design,
qrspi-plan. (2) **Long, trigger-dense form** (qrspi-work, and to a lesser degree qrspi-questions):
explicitly enumerates trigger phrases ("Trigger on any variant of: 'work on <ticket-id>',
'continue <ticket-id>', 'pick up <ticket-id>'..."). The long form is wrapped in double quotes in
YAML because it contains colons/commas; short forms are unquoted. No hard length limit is enforced
anywhere in the repo, but the observed convention is: lead with capability, then an explicit "Use
when..." trigger clause, optionally enumerate literal user phrasings to sharpen auto-invocation.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

```
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-questions/SKILL.md:3`

**Dependencies:** Read by the harness for auto-invocation matching.
**Implicit contracts:** Embed concrete trigger phrases for better matching; quote the YAML value when it contains `:` or `"`; keep capability-first. No numeric length cap is attested in-repo.

## Q5: Where should a newly authored skill physically live in this repo (`.claude/skills/<name>/`) and what naming convention applies to the directory versus the skill name field?

**Answer:** A new skill lives at `.claude/skills/<name>/SKILL.md`. The **directory name equals the
`name` frontmatter value verbatim** — both are the hyphenated, lowercase slug. There is no
"display name with spaces" variant anywhere: every skill's directory name and `name` field match
exactly (e.g. directory `qrspi-research/` ↔ `name: qrspi-research`). So a "writing dockerfiles"
skill would be directory `.claude/skills/writing-dockerfiles/` with `name: writing-dockerfiles` and
`command: /writing-dockerfiles`. The human-readable phrase ("writing dockerfiles") appears only in
the `description`, never as the `name`.

**Evidence:**

```
$ ls .claude/skills/
qrspi-design  qrspi-implement  qrspi-plan  qrspi-pr  qrspi-questions
qrspi-research  qrspi-structure  qrspi-ticket  qrspi-work  qrspi-worktree
```
Each directory's SKILL.md `name:` field equals the directory name (verified across all ten; e.g. `qrspi-worktree/SKILL.md:2` → `name: qrspi-worktree`).

— `.claude/skills/` directory listing + per-file frontmatter

**Dependencies:** Harness matches `command: /<name>` to the slash command the user types; mismatched dir/name would break invocation.
**Implicit contracts:** lowercase-hyphenated slug; `name` == directory == `command` (minus the leading `/`). No spaces, no capitals.

## Q6: Is there an index, manifest, or registration step that must be updated for a new skill to be listed and invokable, or are skills discovered purely by directory presence?

**Answer:** Discovery is **purely by directory presence** — there is no machine-read manifest or
registration file under REPO_ROOT. There is **no `.claude/settings.json` or `settings.local.json`
in this worktree** (`find . -name 'settings*.json'` → none). `.claude/CLAUDE.md` contains a
human-facing "Available skills" bullet list, but it is documentation, not a registry the harness
parses; it is the single source of truth *for humans* and would be **stale** if a new skill were
added without updating it. So: adding the directory + SKILL.md makes the skill invokable; updating
`.claude/CLAUDE.md`'s list (lines 43-53) is a documentation-hygiene step, not a functional gate.

**Evidence:**

```
### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-ticket <initial description>` — Create a Linear issue through guided conversation
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket (fetched from Linear)
...
```

— `.claude/CLAUDE.md:43-53` (prose list, ten entries, no skill-creator/dockerfiles)

**Dependencies:** Harness scans `.claude/skills/*/SKILL.md` directly (no in-repo loader code; this is harness behavior).
**Implicit contracts:** Directory presence = registration. The CLAUDE.md list and the skill-creator memory directives expect new skills to also be *documented* there, but nothing enforces it. Search queries attempted: `find . -name 'settings*.json'` (none), `grep -n skill .claude/CLAUDE.md` (only the doc list + the `.claude/skills/` location note at line 71).

## Q7: What does the skill-creator do when a SKILL.md body exceeds the size budget — is the under-500-lines / under-5000-tokens limit enforced anywhere, or only advisory?

**Answer:** **NOT FOUND — out of project scope** for the skill-creator's own size-budgeting logic
(no skill-creator code under REPO_ROOT). Within the repo there is **no size/token enforcement
mechanism at all** — no line counter, no token counter, no lint hook (grep for `token`, `lines`,
budget patterns in `scripts/` and `.claude/` returned nothing relevant). Empirically the existing
skills are well under any 500-line budget except `qrspi-work`, which is the outlier at **565 lines**
(`SKILL.md:565` is the last line). That single skill already exceeds a 500-line guideline with no
tooling objecting, which directly demonstrates the limit is **advisory, not enforced** in this repo.

**Evidence:**

```
$ wc -l .claude/skills/qrspi-work/SKILL.md  → 565 lines (last line is 565)
```
The file ends at line 565 (`SKILL.md:565`), well over a 500-line budget, with no validation present.

— `.claude/skills/qrspi-work/SKILL.md:565`

**Dependencies:** None in-repo.
**Implicit contracts:** None enforced. Budget is a guideline carried by skill-creator (external) and the ticket's acceptance criteria, not by repo tooling. Search queries attempted: `grep -rni 'token\|500 lines\|5000\|budget' scripts/ .claude/` (no enforcement code).

## Q8: How do existing skills that bundle `scripts/` handle the case where the dockerfile skill ships no executable scripts — is `scripts/` required, optional, or expected to be omitted entirely?

**Answer:** `scripts/` is **omitted entirely when not needed.** No skill in this repo ships a
`scripts/` subdirectory — the only skill subdirectory that exists anywhere is `qrspi-work/references/`.
Nine of ten skills are a lone `SKILL.md` with no subdirectory at all. This establishes the
convention: a skill bundles only the subdirectories it actually uses; a documentation-only skill
with no executables simply has no `scripts/` directory (and no empty placeholder). (Note: the
project's executable Python helpers live in the top-level `scripts/` dir — `scripts/qrspi_*.py` — and
belong to the orchestration harness, **not** to any skill. That is a separate concern from a skill's
own bundled `scripts/`.)

**Evidence:**

```
$ find .claude/skills -type d
.claude/skills
.claude/skills/qrspi-design   ... (each skill dir) ...
.claude/skills/qrspi-work
.claude/skills/qrspi-work/references     # <-- the ONLY skill subdirectory
```

— `find .claude/skills -type d` — `.claude/skills/`

**Dependencies:** Top-level `scripts/qrspi_*.py` are invoked by the orchestrator (qrspi-work SKILL.md:61) — unrelated to per-skill `scripts/`.
**Implicit contracts:** Include only the subdirectories you use; never an empty `scripts/`. A dockerfile (docs-only) skill should omit `scripts/` and `assets/`, keeping `SKILL.md` + `references/`.

## Q9: Does the skill-creator's eval loop require pre-existing eval fixtures, and what happens for a skill like this one where the evals/ harness is a non-functional placeholder?

**Answer:** The skill-creator eval loop's *internal* requirements are **NOT FOUND — out of project
scope**. What the repo establishes definitively: the in-repo `evals/` + `scripts/run_eval.py`
harness is a **confirmed non-functional placeholder/stub** — `execute_trial()` does not invoke any
model; it returns empty output (`result.output = ""`, `result.files = []`) behind a comment block
"`# ── Placeholder for agent execution ──`". The existing fixtures (`evals/fixtures/ticket_*.md`)
and `evals/suite.json` describe QRSPI *workflow* cases (questions/design/etc.), **not** skill
authoring, and `evals/golden/` is empty (`.gitkeep` only). So a new docs skill has **no pre-existing
fixtures** here and the harness could not score it even if it did. Per the project convention,
verification for such work falls back to unit tests + manual review, not the eval harness.

**Evidence:**

```python
    In a real implementation, this would:
    1. Spin up an isolated container/sandbox
    ...
    This stub captures the structure for integration with
    the actual agent runtime.
    """
    ...
        # ── Placeholder for agent execution ──
        ...
        result.output = ""
        result.files = []
```

— `scripts/run_eval.py:101-134`

**Dependencies:** `run_eval.py` loads `evals/suite.json` (run_eval.py:42-50) but never executes an agent.
**Implicit contracts:** Eval harness is inert; `.claude/CLAUDE.md` and project memory both declare it a "non-functional placeholder." Do not gate a skill on eval scores. Search queries attempted: `grep -n 'subprocess\|anthropic\|claude\|stub\|placeholder' scripts/run_eval.py`.

## Q10: What mechanism exists to validate a finished skill (frontmatter validity, body size, reference link integrity) before it is considered complete, and is it manual or scripted?

**Answer:** There is **no scripted validation of skills in this repo.** No frontmatter validator, no
body-size checker, no reference-link integrity check exists under REPO_ROOT. The scripted tests
present (`scripts/qrspi_*_test.py`) cover the Python orchestration helpers (resolver, persist, pr_state),
**not** skill SKILL.md files. `scripts/run_eval.py` is a stub (Q9) and would not validate authoring.
Therefore skill validation here is **manual** (human review of the SKILL.md). The skill-creator's own
validation/eval tooling is **NOT FOUND — out of project scope**. The repo's `.claude/agents/qrspi-structure.md:40`
even codifies that "invoking skill-creator" is itself the validation pass for skill-producing work —
i.e. validation is delegated to the (external) skill-creator + human review, not to in-repo scripts.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

```
$ ls scripts/qrspi_*_test.py   # tests target Python helpers, not SKILL.md files
```

— `scripts/` (e.g. `qrspi_resolve_test.py`, `qrspi_persist_test.py`)

**Dependencies:** None validate skills.
**Implicit contracts:** "Complete" = human-reviewed SKILL.md (+ optional skill-creator eval, external). No repo gate. Search queries attempted: `grep -ri 'frontmatter\|validate.*skill\|lint' scripts/ .claude/` — no skill-validation code.

## Q11: For documentation-only artifacts like a skill, what does the repo's "a coding task is never complete without tests" convention translate to — eval cases, lint checks, or none?

**Answer:** Evidence-based translation: for **logic** the repo demands stdlib-only `_test.py` unit
tests (`scripts/qrspi_*_test.py`), and for **orchestration** it demands manual end-to-end runs —
this is stated explicitly in `.claude/CLAUDE.md`. The eval harness is **excluded** as a verification
path because it is a placeholder (Q9). A documentation-only skill contains **no executable logic**,
so the unit-test convention has nothing to bind to; the existing skills bear this out — **none of the
ten `qrspi-*` skills has any sibling test or eval fixture of its own.** The de-facto convention for a
docs artifact is therefore: no unit tests (nothing to test), verification by human review +
(optionally) the external skill-creator eval loop. The "always run skill-creator eval" memory
directive is the closest thing to a test-equivalent for skills, but it lives outside the repo.

**Evidence:**

```
- All of the above have stdlib-only unit tests as `_test.py` siblings (`scripts/qrspi_*_test.py`, run with `python3`).
...
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions, the unit-test + placeholder bullets)

**Dependencies:** Unit tests bind only to Python helpers; skills have none.
**Implicit contracts:** Test the logic, manually verify orchestration/docs. No skill in the repo ships a test, so a docs skill following precedent ships none either — verification is review-based.

## Q12: How does the skill-creator surface progress, validation results, or errors during skill generation, so the author can confirm each acceptance criterion was met?

**Answer:** The skill-creator's own progress/output surface is **NOT FOUND — out of project scope**
(external skill, not under REPO_ROOT). For comparison, the repo's *own* harness surfaces progress via
**console prints from the orchestrator/scripts** and **JSON envelopes** from the deterministic Python
helpers (e.g. `qrspi_resolve.py` prints a one-line JSON `{ "ok": ..., "decision": {...} }`; phase
agents print one-line status messages; `run_eval.py` is the stub that *would* emit scores but does
not). There is no written progress-report file convention for skill authoring in this repo. So an
author confirming acceptance criteria for a dockerfile skill, within this repo's mechanisms, relies
on: console output + manual inspection of the produced `SKILL.md`/`references/` files — not an
automated score sheet.

**Evidence:**

```
It self-locates the repo root from its own location, ... It prints one JSON envelope:
   { "ok": true, "repoRoot": "…", "worktreeDir": "…",
     "existing": { "questions": false, … },
     "decision": { "action": "…", ... "reason": "…" } }
```

— `.claude/skills/qrspi-work/SKILL.md:64-72` (the repo's progress-surfacing pattern: JSON to stdout)

**Dependencies:** Orchestrator reads these prints to decide/dispatch (SKILL.md:77).
**Implicit contracts:** Progress = stdout (one-line status / JSON envelope); errors = printed verbatim then HARD STOP. No per-skill report artifact. skill-creator's internal surfacing is external and unverified here.

---

## Discovered Patterns

- **Skill = directory + SKILL.md, name-matched.** Every skill is `.claude/skills/<slug>/SKILL.md`
  where `<slug>` == `name` == `command` (minus `/`). Lowercase-hyphenated. Optional subdirectories
  only when used (`references/` is the only one attested).
- **Thin-wrapper skills.** Most QRSPI SKILL.md files are *thin slash-command wrappers* that just
  spawn a purpose-built agent from `.claude/agents/<name>.md` (e.g. qrspi-research/SKILL.md:9-26).
  The agent definition (in `.claude/agents/`) carries the real prompt. This SKILL-wrapper /
  agent-definition split is a strong codebase convention (documented at `.claude/CLAUDE.md:71`).
  A docs-only skill like writing-dockerfiles would NOT follow this split — it would be a
  self-contained SKILL.md with prose + `references/`, more like a standalone capability than a
  workflow phase.
- **Frontmatter schema (de facto):** `name`, `description`, `command`, `argument-hint`,
  `allowed-tools` — uniform across all ten skills, none enforced by tooling.
- **No enforcement layer for skills.** No settings.json in the worktree, no skill linter, no
  size/token gate, no skill-targeting tests. Skills are governed by convention + human review only.
- **Reference docs are followed by prose cue, not auto-loaded** (`see \`references/...\``).
- **The eval harness (`evals/` + `scripts/run_eval.py`) is an inert stub** — confirmed at
  run_eval.py:101-134; tests for real logic are stdlib `scripts/qrspi_*_test.py`.
- **Co-authorship trailer convention** for commits: `Co-Authored-By: Claude Opus 4.7 (1M context)`
  (qrspi-work/SKILL.md:176) — relevant if the skill ships any committed example.

## Inconsistencies

- **`qrspi-work/SKILL.md` is 565 lines**, exceeding a common ~500-line skill-body guideline, while
  every other skill is a short wrapper. Since no tooling enforces a budget (Q7), this outlier stands
  uncorrected — direct evidence the size limit is advisory in this repo.
- **`.claude/CLAUDE.md`'s "Available skills" list (lines 43-53) is a hand-maintained doc, not a
  registry.** A new skill is invokable by directory presence alone (Q6), so this list can silently
  drift out of sync with `.claude/skills/` — it currently lists exactly the ten qrspi skills and
  would not mention a new dockerfiles skill unless manually updated.
- **The `evals/suite.json` + fixtures describe QRSPI workflow phases, but the README/skill list
  promote evals as a verification path** — yet `run_eval.py` is a confirmed stub that returns empty
  output. The "run the eval loop" memory directive and the non-functional harness conflict for any
  in-repo skill; CLAUDE.md resolves this by declaring the harness a placeholder, but the tension
  remains for anyone expecting `run_eval.py` to actually score a skill.
- **`name`/`description` quoting is inconsistent:** long descriptions with `:` are double-quoted YAML
  (qrspi-work), short ones are bare (qrspi-research). Both parse, but there is no stated rule —
  authors must know to quote when the value contains YAML-significant characters.
- **Two `scripts/` meanings collide:** the top-level `scripts/` (orchestration Python) vs a skill's
  *own bundled* `scripts/` (none exist here). A reader could conflate them; the convention is that a
  skill bundles `scripts/` only for its own executables, which no current skill does.
