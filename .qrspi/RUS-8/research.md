# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Q1: How does an existing SKILL.md in this repo reference and load its supporting material at runtime (e.g., relative paths into `references/`, `scripts/`, `assets/`), and what path conventions do those references use?

**Answer:** Only one skill in this repo has a `references/` directory: `qrspi-work`. Its SKILL.md references the supporting file via a **skill-root-relative path** (no leading `./`, no absolute path): `references/review-cascade.md`. There is no `assets/` directory anywhere in the repo, and no skill contains its own `scripts/` subdirectory. Skills that need executable logic reference the **repo-level** `scripts/` directory by a repo-root-relative path (e.g. `scripts/qrspi_resolve.py`), not a per-skill `scripts/` dir. So two distinct path conventions coexist: (a) within-skill supporting prose lives in `references/<file>.md` and is cited skill-root-relative; (b) shared executable scripts live in the repo-level `scripts/` and are cited/invoked repo-root-relative.

**Evidence:**

```
Address feedback **within this phase only** — the cascade is bounded to the
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:281-283`

```
python3 scripts/qrspi_resolve.py --ticket "<ticket-id>" \
  $( [ "<assigned>" = "true" ] && echo --assigned ) \
  --linear-status "<status>"
```

— `.claude/skills/qrspi-work/SKILL.md:61-64`

**Dependencies:** `qrspi-work` SKILL.md → `references/review-cascade.md` (sibling) and → repo-level `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`, `scripts/qrspi_pr_state.py`.
**Implicit contracts:** Reference files are cited relative to the skill's own directory; shared scripts are cited relative to the repo root and invoked with `python3 scripts/...` after a `cd` into the worktree/repo root.

## Q2: How does the skill-creator skill expect inputs and where does it emit the generated skill directory (target path, naming, frontmatter scaffolding)?

**Answer:** NOT FOUND in-repo. The `skill-creator` skill is referenced twice but is **not defined inside the project** — it is a global/harness skill outside `REPO_ROOT`. Searches across `.md/.py/.js` returned only two mentions, both of which merely point at it as an external validation step, neither defines its inputs, output path, naming, or frontmatter scaffolding. Per the project-scope firewall, the skill-creator definition lives outside `REPO_ROOT` and cannot be inspected here.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40` (the only repo reference besides `questions.md` itself)

Searches attempted: `grep -rl "skill-creator" . --include=*.md --include=*.py --include=*.js` → only `.claude/agents/qrspi-structure.md` and `.qrspi/RUS-8/questions.md`. No `skill-creator/` directory under `.claude/skills/`.
**Dependencies:** External to the repo.
**Implicit contracts:** The repo treats `skill-creator` as an externally-provided validation/authoring tool to be invoked as the final step of a skill-producing slice; the repo does not vendor or wrap it.

## Q3: What is the exact required frontmatter schema for a SKILL.md in this repo (required keys such as name/description, allowed values, naming format), and is there a validator that enforces it?

**Answer:** There is **no validator** in the repo that enforces SKILL.md frontmatter (no schema file, no lint script; the `scripts/` dir contains only the QRSPI resolver/persist/PR-state logic and the eval-harness scripts). The schema is therefore a **convention derived from the 10 existing files**, which are 100% consistent on these keys: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. Observed conventions:
- `name`: matches the skill directory name exactly (e.g. `qrspi-research` in `.claude/skills/qrspi-research/`); kebab-case.
- `description`: a single sentence-to-paragraph; usually unquoted, but quoted with `"..."` when it contains special characters/colons (only `qrspi-work` is quoted). Typically includes a "Use when…" trigger clause.
- `command`: `/<name>` (slash + the same name).
- `argument-hint`: `<ticket-id>` for phase skills; `<initial description>` for ticket; `<ticket-id> <slice-number>` for implement.
- `allowed-tools`: comma-separated tool list. Phase wrappers use `Agent, Bash(pwd:*)` (plus a Linear MCP tool when they fetch the ticket); `qrspi-ticket` and `qrspi-work` use broader sets.

Note: the **agent** definitions in `.claude/agents/` use a *different* frontmatter shape — `name` + `description` + a nested `claude: { tools: ... }` block (see `qrspi-research.md:1-6`), not the SKILL.md `command`/`allowed-tools` shape.

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

**Dependencies:** None (convention, not code-enforced).
**Implicit contracts:** `name` == directory name; `command` == `/<name>`; quote `description` only if it contains YAML-special chars; restrict `allowed-tools` to the minimum the skill needs.

## Q4: What invocation surface do skills expose here — slash-command wrappers vs. agent definitions — and which file(s) must exist for the new skill to be discoverable/triggerable?

**Answer:** Two distinct artifact types exist:
1. **Slash-command wrappers** at `.claude/skills/<name>/SKILL.md` — these are the triggerable surface (auto-invoke by `description` or explicit `/<name>`). All 10 skills have one.
2. **Phase agent definitions** at `.claude/agents/qrspi-<phase>.md` — these are NOT directly triggerable; they are spawned via the `Agent` tool (`subagent_type: qrspi-<phase>`) by a wrapper or by the `qrspi-work` orchestrator. There are 8 agent files (questions, research, design, structure, plan, worktree, implement, pr).

Crucially, **not every skill needs an agent**: `qrspi-ticket` and `qrspi-work` are skills with NO corresponding agent — their full logic lives in the SKILL.md itself. So the *minimum* file required for a new skill to be discoverable/triggerable is exactly one: `.claude/skills/<name>/SKILL.md` with valid frontmatter. An agent definition is only needed if the skill delegates to a fresh-context sub-agent.

**Evidence:**

```
- **`.claude/skills/qrspi-<phase>/SKILL.md`** are the slash-command wrappers that invoke the phase agents. `/qrspi-ticket` and `/qrspi-work` are skills with no corresponding phase agent (ticket creation is a guided conversation; `/qrspi-work` is the orchestrator).
```

— `docs/qrspi-orientation.md:85`

```
- Each phase's logic lives in a purpose-built agent at `.claude/agents/qrspi-<phase>.md` ... Slash-command wrappers live at `.claude/skills/qrspi-<phase>/SKILL.md`.
```

— `docs/qrspi_complete_guide.md:229`

**Dependencies:** Wrapper SKILL.md → (optionally) agent definition via the `Agent` tool's `subagent_type`.
**Implicit contracts:** Discovery is directory-convention-based — a `SKILL.md` placed under `.claude/skills/<name>/` is auto-discovered; no registration step. A self-contained skill (like a CLI helper) can ship as a single SKILL.md with no agent.

## Q5: Where do skill artifacts physically live relative to the worktree/repo root, and how is the new skill directory expected to be registered or auto-discovered (no manifest vs. an index file)?

**Answer:** Skills live at `<repo-root>/.claude/skills/<name>/SKILL.md` (and within a ticket worktree, at `<worktree>/.claude/skills/...`, since the worktree is a full checkout). There is **no manifest and no index file** — discovery is purely directory-convention. No file in the repo lists or registers the set of skills; the harness scans `.claude/skills/*/SKILL.md`. (The only "lock"/registry-like file in `.claude/` is `.claude/scheduled_tasks.lock`, which is gitignored and unrelated to skills.)

**Evidence:**

```
.claude/skills/            ← slash-command wrappers (incl. /qrspi-ticket, /qrspi-work)
```

— `docs/qrspi-orientation.md:65`

```
.claude/scheduled_tasks.lock
```

— `.gitignore:3` (the only `.claude/`-level state file; not a skill manifest)

Directory listing confirms each skill is a self-contained dir with a `SKILL.md`; no top-level `index.*`, `manifest.*`, or registry file exists under `.claude/`.
**Dependencies:** None — no registry to update.
**Implicit contracts:** Adding a new skill = creating `.claude/skills/<name>/SKILL.md`; no other file must be edited for discovery.

## Q6: Is there an enforced line/token budget mechanism for SKILL.md bodies (the acceptance criteria require under 500 lines / 5000 tokens), and where would such a limit be checked or measured?

**Answer:** NOT FOUND — there is **no line/token budget mechanism for SKILL.md in this repo** (no checker, no documented SKILL.md limit). Greps for "500 line", "5000 token", "line budget", "token budget" returned no SKILL.md-related hits. The only budget conventions found apply to *other* artifacts: a design-document budget ("~200-line design document (hard max 300 lines)") in `docs/qrspi-orientation.md:310`, a 200-line budget for project `MEMORY.md` (in global instructions, outside repo), and a "max 20 lines" code-snippet guideline in `.qrspi/templates/research.md`. The 500-line/5000-token figure in the question is not enforced or measured anywhere in `REPO_ROOT`. If such a check were desired, the natural homes given existing structure would be (a) a new repo-level script under `scripts/` (mirroring `check_scope.py`), or (b) a programmatic check inside the eval grader `scripts/grade.py`.

**Evidence:**

```
A ~200-line design document (hard max 300 lines) in prose and tables — no code blocks.
```

— `docs/qrspi-orientation.md:310` (a *design* budget, not a SKILL.md budget)

Searches attempted (all empty for SKILL.md): `grep -rni "5000 token\|500 line\|line budget\|token budget\|max.*line" . --include=*.md`.
**Dependencies:** None.
**Implicit contracts:** SKILL.md length is currently governed by author discipline, not tooling. Existing skill bodies range from very short wrappers (~26 lines, `qrspi-research/SKILL.md`) to the large orchestrator (`qrspi-work/SKILL.md`, 565 lines) — so even the in-repo files exceed a 500-line limit, confirming no enforcement.

## Q7: How do existing skills handle the split between the SKILL.md body and `references/` content — what determines what belongs inline vs. in a reference file, and are there examples of multi-reference skills to model the argocd reference set after?

**Answer:** Only one skill demonstrates the split: `qrspi-work`, which keeps the state-machine algorithm inline in SKILL.md and factors out the detailed **review-cascade decision logic** into `references/review-cascade.md`. The observed determinant: the SKILL.md body holds the always-needed control flow and dispatch, while a `references/` file holds **deep, conditionally-needed reference material** that the agent consults only in a specific branch (here, when handling review feedback). It is loaded on demand ("see `references/review-cascade.md`"), not eagerly. There are **no multi-reference (2+) skills** in the repo to copy — `qrspi-work` has exactly one reference file. The structure to model after: SKILL.md = procedure + when-to-consult pointers; `references/<topic>.md` = the detailed knowledge for one topic, with its own `#` headings and code-fence diagrams.

**Evidence:**

```
=== qrspi-work/references ===
.claude/skills/qrspi-work/references/review-cascade.md   (the only reference file in the repo)
```

— directory listing

```
# Review Cascade Logic (PR-gated)

Artifacts form a dependency chain, now split across **per-phase PR branches**:
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-3`

**Dependencies:** SKILL.md → `references/review-cascade.md` (on-demand).
**Implicit contracts:** Reference files are topic-scoped, self-titled with an H1, and cited inline at the decision point where they are needed; the body stays focused on procedure. For a multi-reference argocd skill, model each reference as a single topic file under `references/` and cite each from the relevant body section.

## Q8: How are `scripts/` and `assets/` subdirectories within a skill expected to be structured, named, and made executable, for cases where the argocd skill ships helper scripts?

**Answer:** NOT FOUND as a per-skill convention — **no skill in this repo contains its own `scripts/` or `assets/` subdirectory**, and there is no `assets/` directory anywhere in the repo. The only analog is the **repo-level** `scripts/` directory. Its observable conventions for shipped helper scripts:
- **Naming:** `snake_case.py`; user-facing/CLI scripts are plainly named (`check_scope.py`, `grade.py`, `run_eval.py`, `diagnose.py`, `report.py`, `revise.py`), while the QRSPI internal helpers are `qrspi_*` prefixed (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_state.py`).
- **Executable bit + shebang:** CLI entrypoints are `chmod +x` (`-rwxr-xr-x`) and start with `#!/usr/bin/env python3` (e.g. `check_scope.py`, `grade.py`, `run_eval.py`, `report.py`, `revise.py`, `diagnose.py`). Library/helper modules invoked via `python3 <path>` are NOT executable (`-rw-r--r--`) — the `qrspi_*.py` modules.
- **Tests:** every internal helper has a stdlib-only `_test.py` sibling (`qrspi_*_test.py`), run with `python3`.
- **Invocation from a skill:** `python3 scripts/<name>.py ...` (repo-root-relative), e.g. `.claude/skills/qrspi-work/SKILL.md:61`.

If the argocd skill ships scripts, the established pattern is either a repo-level `scripts/` entry or (new pattern) a per-skill `scripts/` dir — the latter has no precedent here.

**Evidence:**

```
-rwxr-xr-x scripts/check_scope.py        #!/usr/bin/env python3
-rwxr-xr-x scripts/run_eval.py           #!/usr/bin/env python3
-rw-r--r-- scripts/qrspi_resolve.py      (invoked via `python3 scripts/...`)
-rw-r--r-- scripts/qrspi_persist.py
```

— `ls -l scripts/*.py` + `head -1` shebang check

**Dependencies:** Skills → repo-level `scripts/`; helper modules → their `_test.py` siblings.
**Implicit contracts:** CLI scripts get `+x` and a `python3` shebang; importable helpers stay non-executable and are run as `python3 scripts/x.py`; every helper carries a stdlib-only `_test.py`. No per-skill `scripts/`/`assets/` precedent exists — using one would introduce a new pattern.

## Q9: How are skills verified in this repo — is there an eval harness, unit-test pattern, or manual checklist used to confirm a SKILL.md is valid and triggers correctly?

**Answer:** Three verification surfaces exist, with an explicit caveat:
1. **Eval harness** — a 5-stage pipeline under `scripts/`: `run_eval.py` (execute) → `grade.py` (score) → `report.py` (compare) → `diagnose.py` (categorize failures) → `revise.py` (propose edits), driven by suites in `evals/` (`evals/suite.json` = 15 cases across QRSPI phases; `evals/graphite-evals.json` = a separate 5-case eval for the **Graphite CLI skill**, which is the closest precedent to a non-QRSPI CLI skill eval). **However, the harness is a non-functional placeholder**: `run_eval.py` contains a stub where real agent execution would go, returning empty output.
2. **Unit tests** — stdlib-only `scripts/qrspi_*_test.py` for the deterministic Python logic (resolver, persist, pr-state). These verify *scripts*, not SKILL.md prose.
3. **Manual end-to-end** — the documented fallback per `CLAUDE.md`: "verify pure logic with the unit tests and orchestration changes with manual end-to-end runs."

There is **no automated SKILL.md validity check** (no frontmatter linter, no trigger test that actually runs).

**Evidence:**

```
This stub captures the structure for integration with
the actual agent runtime.
...
        # ── Placeholder for agent execution ──
```

— `scripts/run_eval.py:107-117`

```
`evals/graphite-evals.json` is a separate eval for the Graphite CLI skill (5 cases covering commit, submit, log, move, sync).
```

— `docs/eval-system.md` (Suite Definition section)

**Dependencies:** `run_eval.py` → `grade.py` → `report.py` → `diagnose.py` → `revise.py`; all → `evals/*.json` suites.
**Implicit contracts:** Logic correctness is proven by `_test.py` unit tests; prompt/skill behavior is (intended to be) measured by the eval suite, but that path is currently a placeholder — practical verification is manual e2e plus (per global memory) the external skill-creator eval loop.

## Q10: What naming, formatting, and Markdown conventions do existing SKILL.md files follow (heading structure, section ordering, code-fence style) that the new argocd skill must match?

**Answer:** Observed conventions across all 10 SKILL.md files:
- **Directory + name:** `.claude/skills/<kebab-name>/SKILL.md`; frontmatter `name` matches the directory.
- **Frontmatter first:** YAML block delimited by `---` with keys in the order `name`, `description`, `command`, `argument-hint`, `allowed-tools` (consistent across all files).
- **Body H1:** thin wrappers use `# /<command>` (e.g. `# /qrspi-research`) as the first heading; richer skills use a descriptive H1 (e.g. `# QRSPI Work Orchestrator (PR-gated)`, `# Ticket Phase (T)`).
- **Section structure:** wrappers use a single `## Steps` ordered list; complex skills use multiple `##` sections (e.g. `## Lifecycle`, `## Entry Point`, `## action: ...`, tables for dispatch). Headings are sentence/Title case.
- **Code fences:** triple-backtick fenced blocks; `bash` language tag for shell, plain fences for tree/JSON diagrams. Inline code in backticks for paths, commands, identifiers.
- **Emphasis:** `**bold**` for key terms/rules; em-dashes used liberally in prose.

The new argocd skill must reproduce: kebab dir/name, the 5-key frontmatter in that order, a leading H1, and bash-tagged fenced command examples.

**Evidence:**

```
# /qrspi-questions

## Steps
```

— `.claude/skills/qrspi-questions/SKILL.md:9,13` (thin-wrapper pattern)

```
# QRSPI Work Orchestrator (PR-gated)
...
## Entry Point
```

— `.claude/skills/qrspi-work/SKILL.md:9,49` (rich-skill pattern)

**Dependencies:** None.
**Implicit contracts:** Wrapper-style skills = `# /<command>` + `## Steps`; self-contained/CLI skills = descriptive H1 + topical `##` sections + bash-fenced examples. A CLI helper like argocd most resembles the self-contained pattern (the Graphite CLI skill is the nearest model, though its SKILL.md is outside `REPO_ROOT`).

## Q11: How is skill triggering/selection surfaced or logged when an agent chooses a skill (what signal indicates the description field is correctly scoped), and where is that triggering behavior measured?

**Answer:** NOT FOUND in-repo as instrumentation. There is **no logging or surfacing mechanism in the repo** that records skill selection, and no triggering-accuracy measurement that is functional. Two relevant facts:
1. The intended measurement vehicle is the eval harness (`scripts/run_eval.py` + `grade.py` + `evals/suite.json`), but `run_eval.py`'s agent-execution step is a placeholder (Q9), so no real trigger data is captured today.
2. The **description-optimization / triggering-accuracy tooling named in the question is the external `skill-creator` skill's eval loop** (referenced in `.claude/agents/qrspi-structure.md:40` and in the project global memory as "the skill-creator eval loop"), which lives outside `REPO_ROOT` and cannot be inspected here.

The only in-repo signal that a `description` is "correctly scoped" is the convention itself: descriptions include an explicit "Use when…/Trigger on…" clause enumerating trigger phrases (most elaborately in `qrspi-work`), which is what the harness/skill-creator would test against. No code in `REPO_ROOT` logs or scores actual selection events.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (trigger phrases embedded in `description` — the scoping signal)

Searches attempted: grep for `discover|register|index.*skill` in `docs/`+`README.md` (only directory-layout descriptions, no logging); no `log`/telemetry file for selection in repo.
**Dependencies:** Triggering measurement → external skill-creator eval loop (outside repo) and the (placeholder) in-repo eval harness.
**Implicit contracts:** A well-scoped `description` carries explicit "Use when / Trigger on" phrasing; correctness is judged externally (skill-creator eval loop) rather than logged at runtime in this repo.

---

## Discovered Patterns

- **Two-layer skill architecture.** Triggerable wrappers (`.claude/skills/<name>/SKILL.md`) sit above optional fresh-context agents (`.claude/agents/qrspi-<phase>.md`, spawned by `subagent_type`). Self-contained skills (`qrspi-ticket`, `qrspi-work`) skip the agent layer — a single SKILL.md is sufficient and is the minimal deliverable for discoverability.
- **Convention over configuration for discovery.** No manifest, index, or registry — a directory under `.claude/skills/` with a valid-frontmatter `SKILL.md` is auto-discovered. Adding a skill edits no other file.
- **Consistent 5-key frontmatter** (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) in that order across all 10 SKILL.md files; `name` == directory == `command` minus the slash; `allowed-tools` is minimized per skill.
- **Two body templates:** thin wrapper (`# /<command>` + `## Steps`) vs. rich self-contained (descriptive H1 + topical `##` sections + dispatch tables + bash-fenced examples). A CLI-helper skill (argocd) fits the self-contained template; the out-of-repo Graphite CLI skill is the nearest conceptual model.
- **On-demand reference splitting.** Deep, branch-specific knowledge moves to `references/<topic>.md` (only `qrspi-work` does this, with one file) and is cited inline at the decision point; the body keeps the always-needed procedure.
- **Repo-level `scripts/` discipline.** CLI entrypoints get `#!/usr/bin/env python3` + executable bit; importable helpers stay non-executable and run via `python3 scripts/x.py`; every helper ships a stdlib-only `_test.py` sibling. No per-skill `scripts/`/`assets/` precedent exists.
- **Strong project-scope firewalls** are a recurring theme (research and implement agents both forbid escaping `REPO_ROOT`; global skills are explicitly out of bounds) — relevant because skill-creator and the triggering eval loop live outside the repo.

## Inconsistencies

- **No SKILL.md size enforcement despite an apparent expectation.** The question's 500-line/5000-token budget is not implemented anywhere, and the existing `qrspi-work/SKILL.md` (565 lines) already exceeds 500 lines — so there is neither tooling nor adherence to that limit in-repo. The only documented length budget (300 lines) targets the *design* artifact, not SKILL.md.
- **Eval harness documented as functional but is a stub.** `docs/eval-system.md` describes a 5-stage pipeline with 15 cases and metrics, while `scripts/run_eval.py:107-133` is an explicit placeholder returning empty output. `CLAUDE.md` reconciles this ("`evals/` ... is a **non-functional placeholder**"), so the doc and the code disagree on operability — verification is actually manual + unit tests.
- **Frontmatter `description` quoting is inconsistent** — 9 of 10 skills leave `description` unquoted; only `qrspi-work` quotes it (because it contains colons/quotes). Not a defect, but the new skill must quote its `description` if it contains YAML-special characters.
- **Two frontmatter dialects.** Skill wrappers use `command`/`argument-hint`/`allowed-tools`; agent definitions (`.claude/agents/*.md`) use a nested `claude: { tools: ... }` block instead. A new agent (if one is created) must use the agent dialect, not the SKILL dialect.
- **skill-creator and the triggering-accuracy eval loop are referenced but not vendored.** They are invoked as the canonical authoring/validation path yet live outside `REPO_ROOT`, so their input/output/scaffolding contracts are unverifiable from within the project.
