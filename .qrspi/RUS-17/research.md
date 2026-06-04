# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

> Scope note: Several questions reference the **skill-creator** skill and the
> "agentskills.io / Anthropic skill-builder" directory pattern. There is **no
> `skill-creator` skill, `skill-builder`, or any `agentskills` reference anywhere
> under REPO_ROOT** (`grep -rni "skill-builder\|agentskills\|skill-creator" .claude
> docs` returns nothing). The skill-creator skill is a global/built-in skill that
> lives outside `/workspaces/qrspi/.worktrees/RUS-17`, so its definition cannot be
> read under this phase's project-scope firewall. Questions that depend on its
> internals are answered with what IS observable in-repo plus an explicit
> out-of-scope gap. Where a question asks "how do existing skills do X," that IS
> in scope and is answered fully from `.claude/skills/`.

## Q1: What is the directory layout the agentskills.io / Anthropic skill-builder pattern produces (SKILL.md plus references/, scripts/, assets/), and where in this repo are existing skills stored that the new Obsidian skill must sit alongside?

**Answer:** Existing skills live under `.claude/skills/<skill-name>/SKILL.md`. There are
10 skills, all named `qrspi-*` (design, implement, plan, pr, questions, research,
structure, ticket, work, worktree). Each skill is its own directory containing a single
`SKILL.md`. Only **one** skill uses the multi-file pattern: `qrspi-work/` has a
`references/` subdirectory (`references/review-cascade.md`). **No skill in the repo has a
`scripts/` or `assets/` directory** (`find .claude/skills -type d \( -name scripts -o
-name assets \)` returns nothing). So the observed in-repo layout is `SKILL.md`
(mandatory) + optional `references/*.md` (one precedent). The new Obsidian skill must sit
as a sibling directory under `.claude/skills/`. The "agentskills.io / Anthropic
skill-builder" canonical layout named in the question (references/, scripts/, assets/) is
NOT documented anywhere in this repo — only `references/` has an in-repo precedent.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   <- only multi-file skill
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing); `.claude/skills/qrspi-work/references/review-cascade.md:1`
**Dependencies:** Skills are paired with agent definitions in `.claude/agents/qrspi-<phase>.md` (8 agent files; ticket and work have no separate agent file — they are self-contained skills). The slash-command wrapper convention is documented in `.claude/CLAUDE.md` ("Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`").
**Implicit contracts:** A skill = a directory whose name equals the frontmatter `name`, containing `SKILL.md`. `references/` is an established sub-bundle pattern; `scripts/`/`assets/` are unestablished in this repo.

## Q2: How does the skill-creator skill expect the new skill to be scaffolded and invoked (inputs, generated files, output location), so the build can be driven through it as the acceptance criteria require?

**Answer:** NOT FOUND — out of project scope. The `skill-creator` skill is not present
under REPO_ROOT (searched: `grep -rni "skill-creator" .claude docs scripts`,
`find . -iname "*skill-creator*"` — both empty). It is a global/built-in skill outside
`/workspaces/qrspi/.worktrees/RUS-17`, and the project-scope firewall forbids reading it.
What IS observable in-repo about scaffolding a skill: a skill is created by adding a
directory `.claude/skills/<name>/` with a `SKILL.md` carrying the frontmatter contract in
Q3, optionally with a `references/` subdir (Q1, Q4). No in-repo tool generates skills;
skills here were authored by hand (no generator script exists under `scripts/`).
**Search queries attempted:** `grep -rni "skill-creator"`, `find -iname "*skill-creator*"`, `grep -rni "skill-builder\|agentskills"` — all empty within REPO_ROOT.
**Dependencies:** none in-repo.
**Implicit contracts:** Cannot characterize the skill-creator's inputs/outputs from within the project scope.

## Q3: What fields, format, and length constraints does the SKILL.md frontmatter require (name, description, and any other keys), and what triggers the "body under 500 lines / 5000 tokens" limit named in the acceptance criteria?

**Answer:** Every in-repo `SKILL.md` uses YAML frontmatter (delimited by `---`) with these
keys, in this order: `name`, `description`, `command`, `argument-hint`, `allowed-tools`.
`name` matches the directory name (e.g. `qrspi-research`). `description` is a single-line
string (one skill, `qrspi-work`, quotes it because it contains a colon/embedded quotes).
`command` is the slash invocation (e.g. `/qrspi-research`). `argument-hint` describes
positional args (e.g. `<ticket-id>`, or `<ticket-id> <slice-number>` for implement).
`allowed-tools` is a comma-separated tool allowlist (e.g. `Agent, Bash(pwd:*)`, or with
scoped MCP tools `mcp__linear__get_issue`). **No explicit line/token limit is encoded
anywhere in the repo's skill frontmatter or docs** — the "500 lines / 5000 tokens" limit
named in the AC is an external skill-authoring convention, not enforced or referenced
in-repo. Observed body sizes: 25–35 lines for thin wrapper skills, 127 lines (qrspi-ticket),
565 lines (qrspi-work, the largest). So qrspi-work already exceeds 500 lines, which means
the ~500-line rule is NOT applied to existing skills here.

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
**Dependencies:** `allowed-tools` gates which tools the skill/agent may call (e.g. the questions firewall excludes Glob/Grep/Bash; the research firewall excludes Linear MCP).
**Implicit contracts:** `name` MUST equal the directory name. `description` is the trigger surface (Q11). Body length is unconstrained in practice (565-line counterexample). The 500-line/5000-token cap is an external convention with no in-repo enforcement.

## Q4: How do existing skills in this repo split content between the SKILL.md body and a `references/` directory, so the Obsidian CLI command reference, URI protocol, and Dataview syntax can be placed correctly?

**Answer:** Exactly one skill demonstrates the split: `qrspi-work`. Its `SKILL.md`
(565 lines) holds the orchestrator's primary state-machine logic and inlines a pointer to
the reference file for a bounded sub-topic. The detailed, self-contained "review cascade"
logic (77 lines) is factored out to `references/review-cascade.md`. The body references it
by relative path inline: `(see references/review-cascade.md)`. The reference file is a
standalone explainer with its own headings, ASCII diagram, and decision tables — content
that is consulted situationally, not on every invocation. This is the in-repo precedent for
placing situational lookup material (CLI command reference, URI protocol, Dataview syntax)
into `references/*.md` while keeping the decision/trigger logic in `SKILL.md`.

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282` (the inline relative-path reference); body of `.claude/skills/qrspi-work/references/review-cascade.md:1-78`
**Dependencies:** The reference is loaded on demand by the agent reading `SKILL.md`; it is a plain relative-path doc link, not a manifest entry.
**Implicit contracts:** Reference files are addressed by relative path (`references/<file>.md`) from within `SKILL.md`. They are prose+tables, no frontmatter. Split criterion observed: keep core/always-needed logic inline; move bounded, situationally-consulted detail to `references/`.

## Q5: How are skills registered and discovered so a newly added skill becomes available (directory naming, manifest, or auto-discovery), and is any index or config update needed when adding the Obsidian skill?

**Answer:** Discovery is by **directory auto-discovery** — there is no manifest, registry,
or index file. `.claude/` contains only `CLAUDE.md`, `agents/`, `skills/`, `workflows/`
(no `skills.json`, no `plugin.json`, no marketplace/settings file registering skills). A
skill becomes available simply by existing as `.claude/skills/<name>/SKILL.md` with valid
frontmatter. The only in-repo place that lists skills by name is the **human-facing prose**
in `.claude/CLAUDE.md` ("Available skills" section) — that is documentation, not a load-bearing
registry, but it should be updated for consistency when adding the Obsidian skill. No code
reads that list. Therefore adding the Obsidian skill needs: the new directory + SKILL.md
(required for it to load) and, optionally for docs consistency, an entry in the
`.claude/CLAUDE.md` "Available skills" list.

**Evidence:**

```
total 8
drwxr-xr-x  CLAUDE.md
drwxr-xr-x  agents
drwxr-xr-x  skills
drwxr-xr-x  workflows
```

— `.claude/` directory listing (no manifest/registry file); skill list as prose at `.claude/CLAUDE.md` "Available skills" section
**Dependencies:** The harness/agent runtime discovers skills from the `.claude/skills/` tree (external to repo code). No repo script enumerates skills.
**Implicit contracts:** Directory name = skill name = invocation basis. No registration step beyond creating the directory. Doc list in CLAUDE.md is descriptive, not authoritative.

## Q6: What naming convention governs skill directory and skill `name` values in this repo, and what must the Obsidian skill be named to remain consistent?

**Answer:** All 10 skill directories are lowercase, hyphenated, and share the project
prefix `qrspi-`: `qrspi-design`, `qrspi-implement`, `qrspi-plan`, `qrspi-pr`,
`qrspi-questions`, `qrspi-research`, `qrspi-structure`, `qrspi-ticket`, `qrspi-work`,
`qrspi-worktree`. The frontmatter `name` value is identical to the directory name in every
case, and `command` is `/` + that name. The convention is therefore: lowercase
kebab-case, directory == frontmatter `name` == command (minus slash). All existing names
encode the QRSPI workflow phase. An Obsidian skill is a NEW capability unrelated to the
QRSPI phase pipeline, so the only firm in-repo rule it must follow is lowercase
kebab-case with directory==name==command; whether it carries the `qrspi-` prefix is a
judgement call not dictated by any existing non-qrspi skill (there are none in-repo to
serve as precedent).

**Evidence:**

```
name: qrspi-research        command: /qrspi-research   (dir: qrspi-research)
name: qrspi-work            command: /qrspi-work       (dir: qrspi-work)
name: qrspi-ticket          command: /qrspi-ticket     (dir: qrspi-ticket)
```

— frontmatter across `.claude/skills/*/SKILL.md:2` and `:4`
**Dependencies:** Q5 (directory name is the discovery key).
**Implicit contracts:** kebab-case; directory name MUST equal `name` MUST equal `command` without the leading slash. Every existing skill is `qrspi-`-prefixed (no counterexample in-repo).

## Q7: How do existing skills document error-handling and failure-mode guidance, so the Obsidian skill can encode the required cases (Obsidian not running, malformed YAML frontmatter, link collisions) in a consistent style?

**Answer:** The richest in-repo precedent is `qrspi-work`, which has a dedicated
`## Error Handling` section (a bullet list mapping each failure class to a response) plus a
hard-stop subsection with imperative numbered steps and an explicit "Explicitly forbidden"
list. The pattern: (1) a bullet list of `<failure condition> → <action>`; (2) a strong,
named "HARD STOP" subsection for infrastructure/auth/config errors with numbered
imperative steps ("STOP", "Print the exact error verbatim", "Exit"); (3) an explicitly
forbidden-actions enumeration; (4) a "Why absolute" rationale paragraph. `qrspi-ticket`
shows a lighter inline pattern: at each failure point it states "report the error and STOP.
Do not <fallback>" (e.g. step 3 on `save_issue` failure). Style is imperative, second
person, with capitalized STOP and explicit "do not <X>" negative guidance.

**Evidence:**

```
## Error Handling
- Sub-agent fails or its artifact is missing → print the error, STOP, no Linear write.
- A `gt`/`git`/`gh` command fails for non-infrastructure reasons → print command + error, STOP.
...
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve
1. **STOP. Do not execute another command.** Not "one more try."
2. **Print the exact error verbatim** ...
**Explicitly forbidden:** `chmod`/`chown`; routing around config via env vars ...
```

— `.claude/skills/qrspi-work/SKILL.md:539-564`; lighter inline form at `.claude/skills/qrspi-ticket/SKILL.md:121`
**Dependencies:** none.
**Implicit contracts:** Failure modes are documented as `condition → STOP/action` bullets; infrastructure/auth errors get a distinct, emphatic "do not work around it" block; negative guidance ("do not <fallback>") is explicit at each failure point.

## Q8: How do existing skills express "prefer tool X over fallback Y" decision guidance, so the CLI-vs-URI-vs-filesystem and idempotency guidance in this ticket can follow the same pattern?

**Answer:** Two in-repo patterns. (1) **Decision tables**: `qrspi-work` dispatches on an
`action` value via a Markdown table mapping value→handler, and `references/review-cascade.md`
uses "Change type → Cascade? (Yes/No)" tables to encode conditional behavior. (2) **Imperative
prefer/forbid prose with rationale**: e.g. the staging guidance "Staging — NEVER use `-a`"
states the preferred action, the forbidden alternative, and WHY ("`-a` stages unrelated
untracked files and makes `gt undo` destroy them. Stage specific files."). Similarly
"Do NOT use `gt create`: the branch already exists, so `gt create` fails. ... use `gt modify -c`"
encodes "prefer X over Y, because Y fails in state Z." `qrspi-ticket` uses the same
prefer/redirect style for conversation behavior. So the established style for "prefer CLI
over URI over filesystem" is: a decision table for the selection plus imperative
"prefer X; do NOT use Y because <consequence>" sentences, each justified.

**Evidence:**

```
### Staging — NEVER use `-a`
`-a` stages unrelated untracked files and makes `gt undo` destroy them. Stage specific files.
```

— `.claude/skills/qrspi-work/SKILL.md:498-499`; action dispatch table at `:80-89`; `gt modify -c` vs `gt create` rationale at `:168-178`; Yes/No cascade tables at `.claude/skills/qrspi-work/references/review-cascade.md:38-46`
**Dependencies:** none.
**Implicit contracts:** Tool-preference is expressed as (a) a selection table when there are >2 discrete cases, and (b) imperative "prefer X / do NOT Y because <consequence>" sentences. Every preference carries a stated reason.

## Q9: Do any skills in this repo include runnable scripts or assets, and how are file permissions, shebangs, and invocation paths handled, in case the Obsidian skill needs a `scripts/` directory?

**Answer:** NO skill in `.claude/skills/` contains a `scripts/` or `assets/` directory, and
no skill file is executable (`find .claude/skills -type f -perm -u+x` is empty). There is
no in-repo precedent for a skill bundling runnable scripts. The repo DOES have a
top-level `scripts/` directory (separate from skills) whose Python files demonstrate the
project's script conventions: a shebang `#!/usr/bin/env python3`, executable bit set on
some (e.g. `run_eval.py`, `check_scope.py`, `diagnose.py`, `grade.py`, `report.py`,
`revise.py` are `-rwxr-xr-x`), stdlib-only, and self-locating from their own path (per
`.claude/CLAUDE.md`: `qrspi_resolve.py`/`qrspi_persist.py` "self-locate the repo root from
its own path"). Note some `scripts/qrspi_*.py` modules are `-rw-r--r--` (not executable) —
they are imported/run via `python3 <file>`, not invoked directly. So the project-level
convention for runnable scripts is: `#!/usr/bin/env python3` shebang, stdlib-only,
self-locating paths, executable bit for entry-point scripts, and a `_test.py` sibling.

**Evidence:**

```
-rwxr-xr-x  scripts/run_eval.py
-rwxr-xr-x  scripts/check_scope.py
-rw-r--r--  scripts/qrspi_resolve.py        <- run via `python3`, not executable
```

— `scripts/` directory listing; shebang at `scripts/run_eval.py:1` (`#!/usr/bin/env python3`); self-locating convention documented in `.claude/CLAUDE.md`
**Dependencies:** top-level `scripts/` is the conventions reference; no skill currently bundles scripts.
**Implicit contracts:** Scripts use `#!/usr/bin/env python3`, are stdlib-only, self-locate the repo root, ship a `_test.py` sibling, and set the executable bit when they are direct entry points. There is NO precedent for a per-skill `scripts/` dir.

## Q10: How is a skill verified or evaluated in this repo (the skill-creator eval loop and the `evals/` + `scripts/run_eval.py` harness), and which of these is functional versus placeholder for validating the Obsidian skill?

**Answer:** `scripts/run_eval.py` + `evals/` is a **non-functional placeholder**. The
script's `execute_single()` does NOT run any agent — its docstring says "In a real
implementation, this would: spin up an isolated container... This stub captures the
structure" and the body sets `result.output = ""` / `result.tool_calls = []` with the
actual agent invocation commented out. The repo's own `.claude/CLAUDE.md` confirms: "The
`evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify pure
logic with the unit tests and orchestration changes with manual end-to-end runs." So the
functional verification mechanisms in-repo are: (1) **stdlib-only unit tests** as `_test.py`
siblings under `scripts/` (`qrspi_resolve_test.py`, `qrspi_persist_test.py`,
`qrspi_pr_state_test.py`, `qrspi_resolve_state_test.py`), run with `python3`; and (2)
manual end-to-end runs. The "skill-creator eval loop" referenced by the question lives in
the out-of-scope global skill-creator skill and cannot be inspected from REPO_ROOT — NOT
FOUND in project scope. There is no automated eval that would meaningfully validate a prose
Obsidian skill in-repo today.

**Evidence:**

```
def execute_single(...):
    """... This stub captures the structure for integration with the actual agent runtime."""
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    result.output = ""
    result.tool_calls = []
```

— `scripts/run_eval.py:93-137`; placeholder status asserted in `.claude/CLAUDE.md`; unit-test convention also in `.claude/CLAUDE.md`
**Dependencies:** `run_eval.py` reads `evals/suite.json` (`load_suite` requires `name`+`cases`) and a `--skill` prompt file, but never executes them. `scripts/grade.py`/`report.py`/`diagnose.py` are the grading/reporting siblings (also part of the placeholder harness).
**Implicit contracts:** Real verification = `_test.py` unit tests for pure logic + manual e2e. The eval harness is structural scaffolding only. skill-creator's eval loop is out of project scope.

## Q11: How does a skill's `description` field surface the skill for triggering/auto-invocation, and what wording pattern do existing skill descriptions use so the Obsidian skill is discoverable when an agent works with vaults and notes?

**Answer:** The `description` frontmatter is the trigger surface — it is the text an agent
matches against to decide whether to auto-invoke. The in-repo wording pattern is two parts:
(1) a capability statement ("what this does"), then (2) an explicit **"Use when..."**
trigger clause. Examples: qrspi-research = "Map codebase facts... **Use after** questions
are approved."; qrspi-questions = "Generate 8-15 targeted technical questions... **Use when**
starting a new QRSPI feature workflow **or when the user says** 'questions for' a ticket."
The most elaborate, `qrspi-work`, additionally enumerates literal trigger phrases:
"**Trigger on any variant of:** 'work on <ticket-id>', 'continue <ticket-id>', 'pick up
<ticket-id>'...". Descriptions are single-line; lengths range 73–488 chars (qrspi-worktree
shortest at 73, qrspi-work longest at 488). For the Obsidian skill to be discoverable when
an agent works with vaults/notes, it should follow the capability + "Use when..." +
explicit trigger-phrase pattern, naming concrete nouns (vault, note, frontmatter,
Dataview, backlink) the agent would encounter.

**Evidence:**

```
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-questions/SKILL.md:3`; trigger-phrase enumeration at `.claude/skills/qrspi-work/SKILL.md:3`; description char lengths measured across `.claude/skills/*/SKILL.md` (73–488)
**Dependencies:** Auto-invocation matching is performed by the harness/agent runtime against this field (external to repo code); Q5 (no other registry feeds discovery).
**Implicit contracts:** `description` = single line, capability statement + "Use when/after..." trigger clause, optionally explicit literal trigger phrases. Concrete domain nouns improve match precision.

---

## Discovered Patterns

- **Skill = directory with SKILL.md; agent logic factored out.** Phase skills are thin
  wrappers (25–35 lines) whose body just parses `$ARGUMENTS`, resolves paths, and spawns a
  `subagent_type: qrspi-<phase>` agent defined in `.claude/agents/`. Two skills are
  self-contained (no agent file): `qrspi-ticket` (127 lines) and `qrspi-work` (565 lines).
  (`.claude/skills/qrspi-research/SKILL.md:9-26`; `.claude/agents/` listing.)
- **Five-key frontmatter, fixed order:** `name`, `description`, `command`, `argument-hint`,
  `allowed-tools` — uniform across all 10 skills. `allowed-tools` doubles as a security
  firewall (questions excludes Glob/Grep/Bash; research excludes Linear MCP).
- **Only `references/` is an established multi-file bundle pattern** (1 precedent). No
  `scripts/` or `assets/` exists in any skill.
- **Path/repo-root self-location** is a strong project convention for scripts
  (`qrspi_resolve.py`/`qrspi_persist.py` self-locate from their own path); scripts are
  stdlib-only with `_test.py` siblings.
- **Discovery is filesystem auto-discovery**, no manifest. The CLAUDE.md "Available skills"
  list is human documentation, not a registry.
- **Imperative, second-person, STOP-emphatic style** for failure modes; preferences encoded
  as decision tables + "prefer X / do NOT Y because <consequence>" sentences with rationale.

## Inconsistencies

- **The "body under 500 lines / 5000 tokens" limit named in the AC is not enforced or even
  mentioned in-repo, and `qrspi-work/SKILL.md` is 565 lines** — already over the named
  500-line bound. Existing skills do not honor that cap, so it is an external authoring
  convention rather than an established repo rule.
- **The questions assume a `skill-creator` skill and an "agentskills.io / skill-builder"
  directory pattern (references/, scripts/, assets/) exist to model against. Neither is
  present anywhere under REPO_ROOT.** Only `references/` has an in-repo precedent;
  `scripts/`/`assets/` for skills do not. The skill-creator skill itself is global/built-in
  and outside project scope (Q2, Q10 partially unanswerable).
- **`scripts/run_eval.py` reads like a working harness** (full argparse, ThreadPoolExecutor,
  results.json output) **but does nothing** — `execute_single` is a stub returning empty
  output. The docstring and `.claude/CLAUDE.md` both flag this, but the code's surface
  completeness could mislead a reader into thinking it validates skills.
- **Executable-bit inconsistency under `scripts/`:** entry-point scripts
  (`run_eval.py`, `check_scope.py`, etc.) are `-rwxr-xr-x`, while the `qrspi_*.py` library
  modules are `-rw-r--r--` and run via `python3 <file>`. No single rule covers both.
- **CLAUDE.md "Available skills" list omits `skill-creator`** and all the built-in/global
  skills, confirming that list documents only the repo's own qrspi-* skills and is not a
  complete registry.
