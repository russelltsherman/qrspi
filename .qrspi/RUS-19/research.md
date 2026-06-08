# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

> Scope note: The `skill-creator` and `writing-bash-scripts` skills referenced by several
> questions are NOT present inside `REPO_ROOT` (`/workspaces/qrspi/.worktrees/RUS-19`). They
> are global/plugin skills installed outside the project tree (e.g. under `~/.claude/`), which
> this phase is forbidden to read. Where a question targets only those skills, the answer is
> marked **NOT FOUND — outside project scope**. Where a question also targets in-repo skills,
> the in-repo facts are reported and the out-of-scope portion is flagged.

## Q1: What is the required `SKILL.md` frontmatter schema (field names, order, allowed values) that existing skills in this repo use, and does it match the agentskills.io standard the ticket references?

**Answer:** Every in-repo skill is a single `SKILL.md` file at `.claude/skills/<name>/SKILL.md`
with YAML frontmatter delimited by `---`. The observed field set, in consistent order, is:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`. Field details:

- `name` (string): exactly matches the directory name and the `subagent_type` spawned (e.g. `qrspi-design`).
- `description` (string): one-to-three sentences; for `qrspi-work` it is quoted and contains embedded trigger phrases.
- `command` (string): the slash command, e.g. `/qrspi-design`.
- `argument-hint` (string): e.g. `<ticket-id>` or `<ticket-id> <slice-number>`.
- `allowed-tools` (string, comma-separated): tool allowlist with scoped Bash, e.g. `Agent, Bash(pwd:*), mcp__linear__get_issue`.

All 10 in-repo skills follow this schema. There is **no** in-repo schema validator, JSON Schema,
or linter that enforces frontmatter; the schema is conventional only (observed, not enforced).
The agentskills.io standard the ticket references is **NOT FOUND** in-repo — no file mentions
"agentskills", so conformance cannot be verified from this repo. The standard fields `name` and
`description` are present; `command`/`argument-hint`/`allowed-tools` are Claude Code-specific
additions.

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

```
---
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation. ...
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear__save_issue, mcp__linear__list_teams
---
```

— `.claude/skills/qrspi-ticket/SKILL.md:1-7`

**Dependencies:** Claude Code skill loader reads this frontmatter; `name` must equal both the
directory name and the agent `subagent_type` in `.claude/agents/<name>.md`.
**Implicit contracts:** field order is consistent across all skills; `name` == dir name == agent
subagent_type; `allowed-tools` scopes Bash with `Bash(pwd:*)` rather than bare `Bash` for the
thin wrappers. No enforcement exists, so a new skill must self-conform.

## Q2: How does the skill-builder/skill-creator skill expect content to be split between the `SKILL.md` body and the `references/`, `scripts/`, and `assets/` subdirectories, and how is reference material loaded on demand?

**Answer:** The `skill-creator` skill itself is **NOT FOUND — outside project scope** (not under
`REPO_ROOT`). However, the repo demonstrates the split convention in practice: `qrspi-work` is the
only in-repo skill with a `references/` subdirectory. The pattern observed: the `SKILL.md` body
holds the primary instructions, and detailed/secondary logic is offloaded to a `references/*.md`
file that the body points to by relative path, to be loaded on demand ("progressive disclosure").
No in-repo skill ships `scripts/` or `assets/` subdirectories (none exist anywhere under
`.claude/skills/`).

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282` (the only on-demand reference pointer in any in-repo skill)

Directory layout confirming only `qrspi-work` has `references/` and no skill has `scripts/`/`assets/`:

```
.claude/skills/qrspi-work/references/review-cascade.md   (only references/ dir under skills)
# `find .claude -type d \( -name references -o -name scripts -o -name assets \)`
#   → .claude/skills/qrspi-work/references   (sole result)
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1` (file exists, 4158 bytes)

**Dependencies:** the `references/` file lives beside `SKILL.md` and is referenced by a path
relative to the skill directory.
**Implicit contracts:** the body links to the reference by a bare relative path
(`references/<file>.md`) inside prose, not a markdown link; the agent loads it only when the body
instructs. No `scripts/`/`assets/` convention is exercised in this repo — a new skill bundling
them would be the first instance.

## Q3: What is the canonical on-disk directory layout for a skill in this repo, and where must the new atmos skill be created?

**Answer:** Skills live at `.claude/skills/<skill-name>/SKILL.md`. The skill name is the directory
name; the entrypoint file is always named `SKILL.md` (uppercase). Optional `references/` sits
inside the skill directory. The README documents this layout explicitly. A new skill (the
atmos skill) would be created as `.claude/skills/<atmos-skill-name>/SKILL.md` with optional
`references/`, `scripts/`, `assets/` subdirectories alongside it.

**Evidence:**

```
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/
    qrspi-questions/
    ...
    qrspi-work/        # Autonomous orchestrator (PR-gated state machine)
```

— `README.md:86-96`

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
```

— directory listing of `.claude/skills/` (10 skill dirs, each with `SKILL.md`)

**Dependencies:** Claude Code discovers skills by scanning `.claude/skills/*/SKILL.md`.
**Implicit contracts:** dir name == frontmatter `name`; entrypoint filename is exactly `SKILL.md`;
the atmos skill must be a new sibling directory under `.claude/skills/`.

## Q4: What naming convention and `name`/`description` triggering pattern do existing skills use, and what does the skill-creator skill recommend for the new atmos skill's description?

**Answer:** Naming convention: lowercase, hyphen-separated, project-prefixed (`qrspi-<phase>`).
For triggering, most skills use a short imperative `description` ("Use after X is approved").
The autonomous orchestrator `qrspi-work` uses a richer, quoted `description` that embeds explicit
trigger phrases and an em-dash list of variants, which is the in-repo template for controlling
auto-invocation. The skill-creator's specific recommendation is **NOT FOUND — outside project
scope**, but the in-repo exemplar is `qrspi-work`.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user
asks to 'work on' a ticket (e.g., 'work on RUS-42'). Reads PR review state ... Trigger on any
variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any
reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (condensed)

```
description: Produce a design document ... Use after research is approved. This is the brain-surgery phase.
```

— `.claude/skills/qrspi-design/SKILL.md:3` (terse-imperative style used by all phase wrappers)

**Dependencies:** the loader matches user intent against `description`; richer descriptions improve
auto-invocation precision.
**Implicit contracts:** descriptions name *when* to use the skill, not just what it does; for an
auto-invoked tool-CLI skill, the `qrspi-work` quoted-with-trigger-phrases pattern is the precedent.

## Q5: Does the skill-creator skill enforce or measure the SKILL.md body limits (under 500 lines / 5000 tokens), and what mechanism reports those counts?

**Answer:** **NOT FOUND — outside project scope** for the skill-creator's own enforcement. Within
`REPO_ROOT` there is **no** mechanism that measures or enforces a 500-line / 5000-token SKILL.md
budget — grep for "500 line", "5000 token", "agentskills", "progressive disclosure" returns zero
in-repo hits (excluding the questions artifact). The repo has no skill-linting tool. For reference,
the largest in-repo skill body is `qrspi-work` SKILL.md; all others are well under 100 lines. The
budget named in the acceptance criteria is therefore a ticket-supplied constraint, not a repo-enforced one.

**Evidence:**

```
# grep -rn "500 line\|5000 token\|agentskills\|progressive disclosure" . --include="*.md"
#   (excluding .qrspi/RUS-19/questions.md) → no results
```

— search performed against all `*.md` under `REPO_ROOT`; no enforcement code found.

**Dependencies:** none in-repo.
**Implicit contracts:** none enforced; any line/token budget for the atmos skill must be checked
manually or by the out-of-scope skill-creator tooling.

## Q6: How are `references/` files referenced from within `SKILL.md` (relative paths, link format, progressive disclosure markers)?

**Answer:** In the single in-repo example, the reference is cited inline in prose as a bare relative
path in backticks — `references/review-cascade.md` — not as a markdown hyperlink, and not with any
special progressive-disclosure marker syntax. The body instructs the agent to "see" the file at the
point where the deeper logic is needed; loading is implicit/on-demand by the agent following that
instruction. No frontmatter field lists references; there is no manifest. The five named reference
docs in the acceptance criteria (stack-YAML-schema, vendoring, workflow, CLI, troubleshooting) do
not exist in-repo — they are to be authored.

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`

**Dependencies:** path is resolved relative to the skill directory (`.claude/skills/qrspi-work/`).
**Implicit contracts:** reference = backticked relative path inside an instruction sentence; agent
loads it when the body tells it to; no manifest/marker convention exists, so the atmos skill follows
the same prose-pointer style.

## Q7: What does the skill-creator eval loop require before a skill is considered shippable, and what failure modes does that loop check for?

**Answer:** **NOT FOUND — outside project scope.** The skill-creator skill and its eval loop are not
under `REPO_ROOT` and cannot be read in this phase. The repo records the *policy* that one must
"never ship a SKILL.md ad-hoc" only via the global memory index reference (in CLAUDE.md/global
memory), but the loop's concrete requirements and failure modes live in the out-of-scope skill
definition. The in-repo eval harness (`scripts/run_eval.py`, `evals/`) is unrelated and is a
placeholder (see Q10).

**Evidence:** No skill-creator files exist under `REPO_ROOT`; `grep -rl "skill-creator"` returns only
`.claude/agents/qrspi-structure.md` and the questions artifact, neither of which defines an eval loop.

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step
   of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40` (mentions invoking skill-creator as a validation step, but does not define its loop)

**Dependencies:** the out-of-scope skill-creator skill.
**Implicit contracts:** repo convention treats skill-creator validation as the final step of the
slice that creates the skill files (per the structure agent), not a separate slice.

## Q8: Are there existing skills in this repo that contain executable `scripts/` or `assets/`, and what conventions must any bundled scripts follow?

**Answer:** **No in-repo skill bundles `scripts/` or `assets/`** — `find .claude/skills -name "*.sh"`
and the dir search for `scripts`/`assets` return nothing. So there is no skill-local script
precedent. The repo-wide script convention lives in `scripts/`: Python `*.py` modules, several with
executable bit and `#!/usr/bin/env python3` shebangs (e.g. `check_scope.py`, `run_eval.py`,
`grade.py`), each with a stdlib-only `*_test.py` sibling. The `writing-bash-scripts` skill named by
the question (ShellCheck conventions) is **NOT FOUND — outside project scope**, and no in-repo file
mentions ShellCheck. So bash conventions for a bundled script are not specified in-repo; the repo's
own executable scripts are Python with shebang + executable bit + stdlib-only unit-test sibling.

**Evidence:**

```
-rwxr-xr-x  scripts/check_scope.py
-rwxr-xr-x  scripts/run_eval.py
-rw-r--r--  scripts/qrspi_resolve.py        (importable module, no exec bit)
-rw-r--r--  scripts/qrspi_resolve_test.py   (stdlib-only test sibling)
```

— `scripts/` listing (exec bit set on CLI entrypoints, cleared on import-only modules)

```
#!/usr/bin/env python3
"""Execute an eval suite against a skill/agent prompt version. ..."""
```

— `scripts/run_eval.py:1-5`

**Dependencies:** repo CI/tests run `python3` on the `_test.py` siblings.
**Implicit contracts:** executable entrypoints carry `#!/usr/bin/env python3` + the exec bit;
every script has a stdlib-only `*_test.py` sibling. There is no in-repo bash/ShellCheck convention
to inherit; the global memory directive ("Use skill-creator for skills") and TDD directive still apply.

## Q9: Does the repo place any constraint on whether a new skill must also have a matching slash-command wrapper, and where would such a wrapper for the atmos skill live versus the skill definition itself?

**Answer:** The repo's documented convention (CLAUDE.md "Codebase conventions") is a **two-file split
for the QRSPI phase skills**: the agent *definition* lives in `.claude/agents/<name>.md` and a thin
slash-command *wrapper* lives in `.claude/skills/<name>/SKILL.md`. However, this split is specific to
the QRSPI Agent-spawning phases — those wrappers carry `allowed-tools: Agent` and exist to spawn a
subagent. Not every skill follows it: `qrspi-ticket` and `qrspi-work` are self-contained `SKILL.md`
files with **no** matching `.claude/agents/` definition (there are 8 agent files vs 10 skills). So
there is no hard constraint that a new skill must spawn an agent or have a separate wrapper; a skill
can be a single self-contained `SKILL.md`. A new atmos skill that does its own work (a CLI helper,
not a subagent spawner) follows the `qrspi-ticket`/`qrspi-work` self-contained pattern: just
`.claude/skills/<name>/SKILL.md`, no `.claude/agents/` file.

**Evidence:**

```
- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
```

— `.claude/CLAUDE.md` "Codebase conventions"

Agents present (8): qrspi-design, implement, plan, pr, questions, research, structure, worktree.
Skills present (10): the above + `qrspi-ticket` and `qrspi-work` — the two skills with **no** agent file:

```
.claude/agents/  → qrspi-{design,implement,plan,pr,questions,research,structure,worktree}.md
.claude/skills/  → + qrspi-ticket/, qrspi-work/   (self-contained, no agents/ counterpart)
```

— directory listings of `.claude/agents/` and `.claude/skills/`

**Dependencies:** wrapper skills declare `allowed-tools: Agent` and call `subagent_type: <name>`;
self-contained skills declare their own tool allowlist (e.g. `qrspi-ticket`: Read, Glob, Grep, Write, Bash).
**Implicit contracts:** the agent/wrapper split is for subagent-spawning phases only; a self-contained
skill needs no `.claude/agents/` file. The atmos skill, if it executes directly, is self-contained.

## Q10: How are skills validated or tested in this repo today, and which mechanisms are real versus placeholder?

**Answer:** Two mechanisms exist; only one is real.

1. **Real — stdlib-only Python unit tests** for the deterministic orchestration scripts:
   `scripts/qrspi_*_test.py` (resolve_state, pr_state, persist, resolve) run with `python3`. These
   test pure logic, not skill prose.
2. **Placeholder — the eval harness** `scripts/run_eval.py` + `evals/suite.json`. `execute_single()`
   never actually runs an agent; it returns empty output and is explicitly a stub. CLAUDE.md and the
   project memory both label `evals/` + `run_eval.py` "a non-functional placeholder."

There is **no** skill-specific validator (no frontmatter linter, no line/token checker). Skill prose
quality is verified by manual end-to-end runs and (per global memory) the out-of-scope skill-creator
eval loop. So for the atmos skill, mechanical in-repo validation is limited to any Python tests one
writes; skill behavior itself is verified manually / via the external skill-creator.

**Evidence:**

```
    try:
        # ── Placeholder for agent execution ──
        # Replace this block with actual agent invocation:
        ...
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py` (`execute_single`, the stub body returns empty results)

```
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` "Codebase conventions"

**Dependencies:** `python3` for the `_test.py` siblings; the eval harness depends on a real agent
runtime that is not wired up.
**Implicit contracts:** real verification = stdlib unit tests on pure logic + manual e2e; eval scores
from `run_eval.py` are meaningless (empty outputs). Do not rely on it to validate the atmos skill.

## Q11: What concrete acceptance-criteria checks (frontmatter validity, line/token budget, presence of the five named reference docs) can be verified mechanically, and what tooling performs that check?

**Answer:** **No in-repo tooling performs any of these checks.** There is no frontmatter validator, no
line/token budget checker, and no reference-doc-presence checker anywhere under `REPO_ROOT`. Each
check would have to be done either manually or by new tooling/the out-of-scope skill-creator:

- *Frontmatter validity*: verifiable by comparison against the observed schema in Q1, but no linter exists.
- *Line/token budget*: no checker exists (Q5); a line count is trivial via shell but unimplemented.
- *Presence of the five named reference docs*: would be a filesystem existence check
  (`.claude/skills/<atmos>/references/*.md`), but no such check is automated; the docs do not yet exist.

The only adjacent precedent is `scripts/check_scope.py` (a Python scope checker, 2081 bytes), which
checks path scope, not skill structure — so it is not reusable for these criteria as-is.

**Evidence:** searches for any line/token/frontmatter validator returned nothing; the only validation
tooling in `scripts/` is the unit-test suite and the placeholder eval harness (Q10).

```
-rwxr-xr-x  scripts/check_scope.py   # path-scope checker, NOT a skill-structure validator
```

— `scripts/` listing

**Dependencies:** none in-repo for these specific checks.
**Implicit contracts:** acceptance-criteria checks for the atmos skill are currently manual or must be
newly built; the repo's TDD directive implies any new mechanical checker should ship with a
stdlib-only `_test.py` sibling.

## Q12: When a skill fails to trigger or under-performs, what signal does the skill-creator eval/benchmark surface, and where is that output recorded?

**Answer:** The skill-creator's benchmark/variance/triggering-accuracy output is **NOT FOUND —
outside project scope** (the skill is not under `REPO_ROOT`). The in-repo eval harness does have an
*output-recording structure* but produces no meaningful signal because it is a stub: `run_suite()`
writes a results JSON keyed by a `skill_hash` (sha256 of the skill text) into the configured output
directory, with per-case/per-trial `ExecutionResult` records (output, files, tokens, tool_calls,
transcript, duration_ms, error). With the placeholder executor those fields are empty/zero, so no
triggering-accuracy or variance signal is actually emitted in-repo. `results/` and `evals/golden/`
exist as output/golden locations but the harness does not populate them with real scores.

**Evidence:**

```
@dataclass
class ExecutionResult:
    case_id: str
    trial_id: int
    output: str = ""
    duration_ms: float = 0.0
    tokens: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
    error: Optional[str] = None
```

— `scripts/run_eval.py` (`ExecutionResult` — the recorded shape, populated empty by the stub)

```
    skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]
    ... output = {"skill_hash": skill_hash, "skill_path": ..., "suite": suite["name"], ...
```

— `scripts/run_eval.py` (`run_suite` writes results keyed by skill hash)

**Dependencies:** real signal depends on the out-of-scope skill-creator benchmark; the in-repo harness
needs a wired agent runtime it lacks.
**Implicit contracts:** in-repo, observability of skill quality is effectively manual; the
skill-creator's scores/variance/triggering-accuracy live outside this repo.

---

## Discovered Patterns

- **Skill = `.claude/skills/<name>/SKILL.md`** with `---`-delimited YAML frontmatter; fields in a
  consistent order: `name, description, command, argument-hint, allowed-tools`. (`.claude/skills/*/SKILL.md`)
- **Two skill archetypes coexist:** (a) *thin wrapper* skills (8 of them) that only spawn a matching
  `.claude/agents/<name>.md` agent via `allowed-tools: Agent` + `subagent_type`; (b) *self-contained*
  skills (`qrspi-ticket`, `qrspi-work`) that carry all logic in the `SKILL.md` body and have no agent file.
- **`name` is a triple-identity key:** dir name == frontmatter `name` == agent `subagent_type`.
- **Progressive disclosure via prose pointer:** deeper logic offloaded to `references/<file>.md`,
  cited as a backticked relative path inside an instruction sentence (only `qrspi-work` does this).
- **No `scripts/` or `assets/` precedent** inside any skill; repo-level scripts are Python in `scripts/`
  with `#!/usr/bin/env python3`, exec bit on entrypoints, and a stdlib-only `*_test.py` sibling each.
- **Templates as single source of truth:** output formats live in `.qrspi/templates/`; skills/agents
  reference templates rather than embedding them (`README.md:126`).
- **Real validation = stdlib unit tests + manual e2e; the eval harness is a labeled placeholder.**
- **Scoped Bash permissions:** wrappers use `Bash(pwd:*)` rather than bare `Bash` to minimize tool surface.

## Inconsistencies

- **CLAUDE.md convention vs. reality:** CLAUDE.md states "Phase agent definitions live in
  `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`" — implying a 1:1 split —
  but `qrspi-ticket` and `qrspi-work` are skills with **no** `.claude/agents/` counterpart (10 skills,
  8 agents). The convention describes the phase wrappers, not all skills.
- **`description` style is not uniform:** phase wrappers use terse imperative descriptions, while
  `qrspi-work` uses a long quoted description with explicit trigger phrases — two different conventions
  for the same field, with no documented rule on when to use which.
- **Out-of-scope dependency:** multiple questions target `skill-creator` / `writing-bash-scripts`
  skills and an "agentskills.io" standard that are referenced by repo memory/conventions but do not
  exist inside `REPO_ROOT`. The repo's stated policy ("never ship a SKILL.md ad-hoc", "invoke
  skill-creator") thus depends on tooling that cannot be inspected or enforced from within the project.
- **Eval harness comment vs. behavior:** `run_eval.py`'s docstring describes "Runs each test case
  multiple trials in isolated environments, capturing full transcripts, outputs, and metrics," but the
  executor is an explicit stub returning empty outputs — the docstring overstates current capability
  (CLAUDE.md correctly labels it a placeholder).
