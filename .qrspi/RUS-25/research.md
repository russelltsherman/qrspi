# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Q1: What is the on-disk layout of an existing skill that combines `SKILL.md` with `references/`, `scripts/`, and `assets/` subdirectories, and where do such skills live in this repo?

**Answer:** Skills live in `.claude/skills/<skill-name>/`, each containing a `SKILL.md`. There are 10 skills, all named `qrspi-*`. **No skill in this repo uses `scripts/` or `assets/` subdirectories.** The only skill with any subdirectory is `qrspi-work`, which has a single `references/` subdir containing one file (`review-cascade.md`). Every other skill is `SKILL.md`-only. So the repo has **no existing precedent for `assets/` or skill-local `scripts/`** — the ADR skill would be the first to introduce them. The closest precedent for the multi-file pattern is `qrspi-work/references/`.

**Evidence:**

```
.claude/skills/qrspi-work/:
SKILL.md
references
.claude/skills/qrspi-work/references:
review-cascade.md
```

— `.claude/skills/qrspi-work/` (directory listing; all other skill dirs contain only `SKILL.md`)

**Dependencies:** Skills are read by the Claude Code runtime from `.claude/skills/`. Phase skills are thin wrappers that delegate to agents in `.claude/agents/` (see Q5).
**Implicit contracts:** A skill is a directory named for the skill, containing a `SKILL.md`. Subdirectory layout (`references/`) is optional and used by only one skill. The agentskills.io `references/`/`scripts/`/`assets/` triad named in the question is an external convention, not one this repo currently exercises beyond `references/`.

## Q2: How are reference files under a skill referenced from the `SKILL.md` body (relative path convention, link format) so the ADR skill can point to its MADR/Nygard/Y-statement reference docs?

**Answer:** The single in-repo example references a file in `references/` using a **bare relative path wrapped in backticks**, not a Markdown link. In `qrspi-work/SKILL.md` the body says "see `references/review-cascade.md`". The path is relative to the skill's own directory (the directory containing `SKILL.md`). No `[text](path)` Markdown-link form is used for skill-local references anywhere in the repo.

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
here; a design-level change that invalidates plan/impl is handled by `reset`, not revise.
```

— `.claude/skills/qrspi-work/SKILL.md:282`

**Dependencies:** The runtime/agent reads `SKILL.md` and resolves the relative reference path against the skill directory.
**Implicit contracts:** Relative path from the skill root, in inline code formatting; the referenced file is loaded on-demand ("see X") rather than inlined, keeping the main `SKILL.md` smaller (progressive disclosure).

## Q3: What is the exact required `SKILL.md` frontmatter schema (field names such as name/description, required vs optional fields, formatting constraints) that the agentskills.io standard and this repo enforces?

**Answer:** Every in-repo `SKILL.md` uses YAML frontmatter delimited by `---` with these fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. `name` matches the directory name. `description` is a single string (sometimes double-quoted when it contains apostrophes/colons, e.g. `qrspi-work`). `command` is the slash-command form (`/qrspi-<name>`). `argument-hint` documents positional args (e.g. `<ticket-id>`). `allowed-tools` is a comma-separated tool allowlist that enforces per-skill capability lockdown. **There is no in-repo schema validator** that enforces this frontmatter — no parser checks field presence; the schema is enforced only by convention/consistency across the 10 files. The agentskills.io standard named in the question is external and not codified anywhere in this repo.

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

— `.claude/skills/qrspi-research/SKILL.md:1-6`

**Dependencies:** Claude Code runtime parses the frontmatter to register the slash command and apply the tool allowlist.
**Implicit contracts:** `name` == directory name; `command` == `/` + name; `description` doubles as the auto-invocation trigger text (it describes *when* to use the skill, in imperative "Use when…" phrasing); `allowed-tools` is the security firewall (e.g. questions skill omits Glob/Grep/Bash). Quote the description string when it contains YAML-special characters.

## Q4: How is the Anthropic skill builder (skill-creator) skill invoked, and what inputs and outputs does it produce when generating a new skill?

**Answer:** NOT FOUND inside the repo. `skill-creator` is referenced by name in `.claude/agents/qrspi-structure.md:40` ("invoking skill-creator") as a validation step, but **its definition does not exist anywhere under REPO_ROOT** — there is no `.claude/skills/skill-creator/` directory. It is a global/external skill outside the project scope, so its invocation contract, inputs, and outputs cannot be determined from this repo. Search queries attempted: `grep -rin 'skill-creator'` (only hits in `qrspi-structure.md` and the questions file), `find -name SKILL.md` (only the 10 `qrspi-*` skills). Per the project-scope firewall I did not read any global skill definitions outside REPO_ROOT.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

**Dependencies:** External — lives outside the project (e.g. global `~/.claude/skills/`, deliberately not read).
**Implicit contracts:** The repo treats `skill-creator` as an available external tool invoked during the validation step of a slice that authored skill files; it does not vendor or version it.

## Q5: How does the QRSPI workflow distinguish a skill's slash-command wrapper (in `.claude/skills/`) from its agent definition (in `.claude/agents/`), and which artifacts must be created for a new skill to be discoverable?

**Answer:** The repo uses a two-layer split, documented in `docs/qrspi_claude_code_guide.md`. **Agents** (`.claude/agents/qrspi-<phase>.md`) hold the heavy phase logic and per-phase tool lockdown; the orchestrator spawns them via the `Agent` tool with `subagent_type: qrspi-<phase>`. **Skills** (`.claude/skills/qrspi-<phase>/SKILL.md`) are thin slash-command wrappers that let a human invoke a single phase directly. Two skills are not phase wrappers: `qrspi-work` (the autonomous orchestrator) and `qrspi-ticket` (creates a Linear ticket). Note an asymmetry: there are **10 skills but only 8 agents** — `qrspi-work` and `qrspi-ticket` have skills with no matching agent (they are self-contained, not phase delegators). For discoverability, a skill needs a directory `.claude/skills/<name>/` with a `SKILL.md` carrying valid frontmatter; if the skill delegates phase work it also needs an agent at `.claude/agents/<name>.md`. A self-contained skill (like the ADR skill would likely be) needs only the `SKILL.md`.

**Evidence:**

```
- **Agents** (`.claude/agents/qrspi-<phase>.md`) hold the heavy phase logic and a per-phase tool lockdown. The orchestrator spawns them via the `Agent` tool with `subagent_type: qrspi-<phase>` ... it never reads the phase SKILL.md files or hand-engineers prompts. This is the agent-vs-skill split: the substance is in agents; skills are thin wrappers.
- **Skills** (`.claude/skills/qrspi-<phase>/SKILL.md`) are the slash-command wrappers ... They exist primarily for the orchestrator's surface area and for manual re-runs.
```

— `docs/qrspi_claude_code_guide.md` ("3. Agents and Skills" section)

**Dependencies:** Orchestrator (`qrspi-work`) → agents via `subagent_type`. Skills → agents via the `Agent` tool. Runtime → `.claude/skills/` and `.claude/agents/` directory scans.
**Implicit contracts:** Phase skills must NOT embed substance (the orchestrator never reads them); substance lives in the agent. A skill not tied to a phase (orchestrator, ticket creation) can be self-contained with no agent. `subagent_type` must match the agent filename stem.

## Q6: Are there existing conventions in the repo for where author-facing template/starter files (like the starter ADR in `assets/`) are stored versus reference documentation, and how is the distinction maintained?

**Answer:** Partially. The repo distinguishes **templates** from **reference docs** but at the project level, not the skill level. Output-format templates (the "single source of truth" for artifact shapes) live in `.qrspi/templates/` (10 files: design.md, plan.md, questions.md, research.md, structure.md, etc.). The README states "Templates as single source of truth. Output formats live in `.qrspi/templates/`. Skills reference templates rather than embedding formats inline." Reference documentation (loaded on-demand by a skill) lives in a skill-local `references/` dir — the sole example is `qrspi-work/references/review-cascade.md`. **There is no existing `assets/` convention** for starter/template files inside a skill; the analogous "starter" concept in this repo is the `.qrspi/templates/` directory, which is repo-global rather than skill-local.

**Evidence:**

```
**Templates as single source of truth.** Output formats live in `.qrspi/templates/`. Skills reference templates rather than embedding formats inline. Change the template, change every phase that uses it.
```

— `README.md:126`

**Dependencies:** Phase agents receive `TEMPLATE_PATH=…/templates/<artifact>.md` in their input contract (see `qrspi-work/SKILL.md:413-420`) and write artifacts matching that template.
**Implicit contracts:** Templates are reference-only and never written/mutated by agents (the templates dir is read-only input). Distinction is maintained by directory placement: `.qrspi/templates/` = output-shape templates; skill-local `references/` = explanatory reference material loaded on demand.

## Q7: What constraints does the skill tooling place on `SKILL.md` body size (the ticket requires under 500 lines / 5000 tokens), and is there a validator or eval that measures this?

**Answer:** There is a generic **`line_count(filename, max_lines)`** programmatic check in `scripts/grade.py` (registered in the check registry) that asserts a file's line count is `<= max_lines`. It is used in the eval suite, e.g. `evals/suite.json` asserts `line_count('design.md') <= 300`. **However, no check targets `SKILL.md` and no 500-line / 5000-token limit is enforced anywhere in the repo.** The line_count check measures lines only, not tokens; there is no token-counting validator in the repo. The 500-line/5000-token target named in the ticket would be a new constraint — the `line_count` check is the existing mechanism that could express the line half of it, but it is wired only into the eval-grading path (which is itself a placeholder pipeline — see Q10), not into any commit/lint gate.

**Evidence:**

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    ...
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:35-40`; registered at `scripts/grade.py:149` (`"line_count": line_count`); used at `evals/suite.json:242` (`line_count('design.md') <= 300`)

**Dependencies:** `grade.py` check registry ← invoked by the eval grading stage. No dependency from any git hook or skill loader.
**Implicit contracts:** Checks are addressed by string keys in suite assertions (`line_count('<file>') <= N`). There is no token-based check; "tokens" constraints have no existing enforcement.

## Q8: How do existing skills encode multi-state lifecycles or status enumerations (e.g., the QRSPI phase statuses), which the ADR skill must mirror for the `proposed → accepted → deprecated/superseded/rejected` lifecycle?

**Answer:** The QRSPI lifecycle is encoded in two places. (1) **Prose state tables** in the skill body: `qrspi-work/SKILL.md` has an action-dispatch table (`entry_blocked`, `run_design`, `advance`, `submit`, `wait`, `revise`, `reset`, `land`) and a Linear-status projection table mapping phase/event → status (`Selected` → `Design Review` → `Plan Review` → `Code Review` → `Done`). (2) **A code enumeration in the tested resolver**: `scripts/qrspi_resolve_state.py` defines `PHASES = ["design", "plan", "implementation"]` and an `_order()` helper, with each action documented in the module docstring. The pattern: a small ordered list of states in code (resolver) plus a human-readable transition table in the skill markdown. An ADR skill's `proposed → accepted → deprecated/superseded/rejected` lifecycle would mirror this by stating the states and transitions as a prose table/list in `SKILL.md` (the resolver-style code enum is QRSPI-internal and not required for a documentation skill).

**Evidence:**

```python
PHASES = ["design", "plan", "implementation"]

def _order(phase):
    return PHASES.index(phase)
```

— `scripts/qrspi_resolve_state.py:35-39`

```
| Active phase / event | Linear status to project |
| Design PR open / in review | `Design Review` |
| Plan PR open / in review | `Plan Review` |
| Implementation stack open / in review | `Code Review` |
| Stack landed | `Done` |
```

— `.claude/skills/qrspi-work/SKILL.md:383-389`

**Dependencies:** `qrspi-work` and `qrspi-batch.js` both call the resolver rather than re-deriving state. Linear projection is best-effort.
**Implicit contracts:** States are an ordered list; transitions are documented as a table keyed by event. Code that needs to act on state imports the resolver enum; documentation expresses it as a markdown table.

## Q9: Does the repo already contain a `docs/decisions/`, `docs/adr/`, or `architecture/decisions/` directory or any existing ADRs whose numbering and naming the new skill must remain consistent with?

**Answer:** NOT FOUND. There is **no** `docs/decisions/`, `docs/adr/`, `architecture/decisions/`, or any ADR directory anywhere under REPO_ROOT. Searches: `find -type d -name decisions|adr|architecture` (zero results); `grep -ril 'architecture decision'` matched only `.claude/skills/qrspi-ticket/SKILL.md`, `docs/qrspi_practical_application.md`, and the questions file itself — none are actual ADRs. The `docs/` tree contains only QRSPI workflow guides and design docs (e.g. `docs/qrspi-pr-gated-lifecycle-design.md`, `docs/eval-system.md`). **There is no existing ADR numbering/naming convention to remain consistent with** — the ADR skill defines the convention from scratch.

**Evidence:**

```
docs/delivery_summary.md
docs/eval-system.md
docs/qrspi-orientation.md
docs/qrspi-pr-gated-lifecycle-design.md
docs/qrspi_claude_code_guide.md
docs/qrspi_complete_guide.md
docs/qrspi_practical_application.md
docs/qrspi_quick_reference.md
docs/qrspi_working_example.md
```

— `docs/` full file listing (no decisions/adr subdirectory)

**Dependencies:** None.
**Implicit contracts:** None exist; the closest existing naming pattern for design-type docs is `docs/qrspi-<topic>-design.md` (hyphenated, lowercase, topic-descriptive), which the ADR skill could optionally echo.

## Q10: What is the established pattern for testing or evaluating a skill in this repo, given that the `evals/` harness is described as a non-functional placeholder?

**Answer:** Two distinct testing layers. (1) **Pure-logic unit tests**: stdlib-only `_test.py` siblings next to each script (`scripts/qrspi_resolve_state_test.py`, `qrspi_persist_test.py`, `qrspi_pr_state_test.py`, `qrspi_resolve_test.py`), run with `python3`. These are real and functional. (2) **The eval harness** (`scripts/run_eval.py` + `grade.py`/`report.py`/`diagnose.py`/`revise.py`, suites in `evals/`) is a **non-functional placeholder**: `run_eval.py`'s `execute_single()` returns empty output with an explicit "Placeholder for agent execution" comment and a docstring saying "In a real implementation, this would… This stub captures the structure for integration with the actual agent runtime." So the established, working way to verify a skill is: unit-test any pure logic it adds, and verify orchestration/behavior by manual end-to-end runs. The eval harness documents an *intended* 5-stage pipeline (run → grade → report → diagnose → revise, `docs/eval-system.md`) but does not actually execute the agent.

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

**Dependencies:** Unit tests depend only on Python stdlib. Eval harness would depend on an agent runtime that is not wired in.
**Implicit contracts:** Verify pure logic via `_test.py` unit tests; verify orchestration via manual e2e. Do not rely on `run_eval.py` to actually grade a skill — it produces empty results.

## Q11: How are skills currently verified for correct triggering and structure (e.g., description-matching tests, frontmatter checks) that the ADR skill should also satisfy?

**Answer:** There is **no automated verification of skill triggering or frontmatter structure** in the repo. No test parses `SKILL.md` frontmatter, validates required fields, or checks description-to-trigger matching. The eval suite (`evals/suite.json`) defines per-phase cases with assertions, but (a) those assertions test artifact *outputs* (e.g. `output_file_exists('questions.md')`, `line_count('design.md') <= 300`), not skill frontmatter or triggering, and (b) the runner that would execute them is the placeholder from Q10. The eval-system doc lists `evals/graphite-evals.json` as covering a skill's *behavior* (5 cases) but again via the non-functional runner. So correctness of triggering/structure is currently maintained by **convention and human review**, not by tooling. The available programmatic checks (in `grade.py`) are `output_file_exists`, `line_count`, section-presence, regex — none target frontmatter.

**Evidence:**

```
"check": "output_file_exists('questions.md')",
...
"check": "line_count('design.md') <= 300",
```

— `evals/suite.json:29,242` (assertions test outputs, not skill frontmatter/triggering)

**Dependencies:** None automated. Human reviewers + the (placeholder) eval suite.
**Implicit contracts:** A new skill is "verified" by matching the established frontmatter convention (Q3) and by manual review; there is no CI gate that would reject a malformed `SKILL.md`.

## Q12: How is a newly added skill surfaced to the agent at runtime (the available-skills listing), and what determines whether the ADR skill appears and auto-invokes correctly?

**Answer:** Surfacing is handled by the **Claude Code runtime**, not by any repo config. There is no plugin manifest, marketplace JSON, or settings entry that registers skills under REPO_ROOT (searched: no `plugin*.json`, `marketplace*.json`, and no committed `settings.json` enumerating skills). The mechanism is purely **convention-by-location**: dropping a directory `.claude/skills/<name>/SKILL.md` with valid frontmatter causes the runtime to list it as an available skill. What determines correct **auto-invocation** is the `description` field — it is the trigger text the agent matches against user intent (the docs/CLAUDE.md headers literally say "invoke with / or let Claude auto-invoke"). So for the ADR skill to appear and auto-invoke: place it at `.claude/skills/<name>/SKILL.md`, give it valid frontmatter, and write a `description` whose "Use when…" phrasing clearly enumerates the triggering situations (mirroring how `qrspi-work`'s description lists "work on <ticket-id>", "continue", "pick up" variants).

**Evidence:**

```
### Available skills (invoke with / or let Claude auto-invoke)
```

— `.claude/CLAUDE.md:43` and `docs/qrspi_claude_code_guide.md:136` (no config file backs this list; it is documentation of runtime-surfaced skills)

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>' ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (description-as-trigger pattern)

**Dependencies:** Claude Code runtime scans `.claude/skills/`. No repo-side registry.
**Implicit contracts:** Discoverability = correct directory + valid frontmatter. Auto-invocation quality = a `description` that explicitly describes *when* to use the skill, including concrete trigger phrasings. Keep the CLAUDE.md / README skill lists in sync manually (they are documentation, not the source of truth for surfacing).

---

## Discovered Patterns

- **Two-layer skill/agent split:** substance lives in `.claude/agents/qrspi-<phase>.md`; `.claude/skills/qrspi-<phase>/SKILL.md` is a thin slash-command wrapper. 10 skills, 8 agents — `qrspi-work` and `qrspi-ticket` are self-contained skills with no agent.
- **Per-skill tool lockdown (firewall):** the `allowed-tools` frontmatter field is the security boundary; e.g. questions omits Glob/Grep/Bash, research omits Linear/ticket access. This is the dominant security idiom.
- **`description`-as-trigger:** every `SKILL.md` description is written in imperative "Use when… / Trigger on…" form because the runtime matches it for auto-invocation.
- **Templates as single source of truth:** artifact shapes live once in `.qrspi/templates/` and are passed to agents as `TEMPLATE_PATH`; agents never embed formats inline and never mutate templates.
- **Progressive disclosure via `references/`:** large explanatory material is split into a skill-local `references/<file>.md` and referenced by bare relative path in backticks ("see `references/x.md`"), keeping `SKILL.md` lean.
- **Determinism via tested Python:** state logic lives in stdlib-only scripts (`scripts/qrspi_*.py`) with `_test.py` siblings; markdown skills delegate to them rather than re-deriving logic.
- **State expressed twice:** as an ordered list/enum in code (`PHASES`) and as a human-readable transition table in markdown.
- **Self-locating one-shot scripts:** orchestration scripts locate the repo root from their own path to survive cwd changes and weak-worker path mangling (see `qrspi_resolve.py`, `qrspi_persist.py`).

## Inconsistencies

- **`skill-creator` referenced but absent:** `.claude/agents/qrspi-structure.md:40` instructs "invoking skill-creator" as a validation step, but no such skill exists under REPO_ROOT. It is an external/global skill the repo assumes is present — an undocumented external dependency (Q4).
- **No `assets/` or skill-local `scripts/` precedent:** the questions (and the agentskills.io standard they cite) assume `references/`/`scripts/`/`assets/` are established; the repo only ever uses `references/` (once). `assets/` and skill-local `scripts/` would be net-new conventions (Q1, Q6).
- **Eval harness documented as functional, implemented as placeholder:** `docs/eval-system.md` describes a working 5-stage pipeline and `evals/suite.json` defines 15 weighted cases, but `scripts/run_eval.py:117-135` returns empty output (stub). The docs overstate the harness's current capability; CLAUDE.md correctly flags it as a "non-functional placeholder" — the two docs disagree on maturity (Q10, Q11).
- **No frontmatter/size validator despite a `line_count` check existing:** `grade.py` has a `line_count` check usable for the ticket's "under 500 lines" goal, but it is wired only to the (non-functional) eval grader and targets artifact outputs, never `SKILL.md`. The "5000 tokens" half has no token-counting mechanism at all (Q7).
- **Skill lists duplicated across files:** the available-skills list is maintained by hand in `.claude/CLAUDE.md`, `README.md`, and `docs/qrspi_claude_code_guide.md` with no single source of truth, so a new ADR skill must be added in multiple places to stay consistent (Q12).
- **Linear MCP tool naming drift:** root `.claude/CLAUDE.md` (project) says the MCP server is referenced by the fixed name `linear` (`mcp__linear__*`), but the skill frontmatter and `qrspi-work` body hard-code `mcp__linear-russelltsherman__*`. The two conventions disagree; a new skill needing Linear access faces an ambiguous tool name. (Observed comparing the project CLAUDE.md guidance to `.claude/skills/*/SKILL.md` frontmatter.)
