# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

> Scope note: This repo's `.claude/skills/` contains ONLY the 10 QRSPI slash-command
> wrapper skills. The Anthropic authoring skills referenced in several questions
> (`skill-creator`, `using-graphite-cli`, `writing-bash-scripts`) are NOT vendored
> in the repo — they are global skills outside `REPO_ROOT` and therefore out of
> research scope. Where a question targets one of those, the answer is bounded to
> what the in-repo skills demonstrate plus an explicit out-of-scope gap.

## Q1: How does an existing skill in this repo lay out the flow from `SKILL.md` body to its `references/`, `scripts/`, and `assets/` subdirectories — what relative-path conventions link the body to reference material?

**Answer:** Exactly one in-repo skill uses a subdirectory: `qrspi-work` has a
`references/` directory holding `review-cascade.md`. The `SKILL.md` body links to it
with a **bare relative path** (`references/review-cascade.md`), relative to the skill's
own directory — not an absolute or worktree-prefixed path. No in-repo skill uses a
`scripts/` or `assets/` subdirectory (`find .claude/skills -type d` returns only the 10
skill dirs plus `qrspi-work/references`). The body references the file twice as
inline prose pointers, never as a tool-loaded include.

**Evidence:**

```
## action: revise
... Address feedback **within this phase only** — the cascade is bounded to the
phase's own artifacts (see `references/review-cascade.md`). ...

> ... Stay on the phase branch. ... See `docs/qrspi-pr-gated-lifecycle-design.md` §4
```

— `.claude/skills/qrspi-work/SKILL.md:280-283` (and `:67`)
Directory listing — `.claude/skills/qrspi-work/references/review-cascade.md` is the
only reference file; tree confirmed via `find .claude/skills -type d`.

**Dependencies:** `qrspi-work/SKILL.md` → `references/review-cascade.md` (intra-skill);
both also point outward to `docs/qrspi-pr-gated-lifecycle-design.md` for rationale.
**Implicit contracts:** Reference paths are relative to the skill directory root and
written bare (no leading `./`, no `.claude/skills/...` prefix). The body cites them as
prose ("see `references/...`"), implying the agent reads them on demand, not eagerly.

## Q2: What does the Anthropic skill-builder skill produce as output, and where does it write the generated skill files — does it scaffold the directory structure or only the `SKILL.md`?

**Answer:** NOT FOUND — the question targets a resource outside the project scope.
The `skill-creator` / skill-builder skill is a global Anthropic skill, not vendored in
this repo. Searches (`grep -rli "skill-creator|skill-builder|skill_creator"`) returned
only two incidental textual mentions inside QRSPI artifacts, neither of which is the
skill's definition: `.claude/agents/qrspi-structure.md:40` lists "invoking skill-creator"
as an example of a validation pass, and the questions artifact itself. No skill-creator
module, scaffold script, or output spec exists under `REPO_ROOT`.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the
   final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

**Dependencies:** None in-repo.
**Implicit contracts:** The only in-repo signal is that qrspi-structure treats
"invoking skill-creator" as a normal validation step folded into the producing slice,
not a standalone phase.

## Q3: What is the exact required frontmatter schema (field names, allowed values, name/description constraints) for a `SKILL.md` in this repo's skills, and is there a validator that enforces it?

**Answer:** There is **no validator** in the repo (`grep -rli "frontmatter|validate"`
across `scripts/` matched only `run_eval.py`, which validates eval-suite JSON, not skill
frontmatter). The schema is therefore conventional, inferred from the 10 existing
`SKILL.md` files, which are 100% consistent on five fields, all present in YAML
frontmatter delimited by `---`:

- `name` — matches the skill directory name exactly (e.g. `qrspi-research`).
- `description` — natural-language trigger text; quoted when it contains commas/colons
  (only `qrspi-work` quotes it). Others are bare scalars.
- `command` — the slash command, `/<name>` (always equals `/` + `name`).
- `argument-hint` — placeholder like `<ticket-id>` or `<ticket-id> <slice-number>`.
- `allowed-tools` — comma-separated tool allowlist; supports scoped forms like
  `Bash(pwd:*)` and fully-qualified MCP tool names.

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

**Dependencies:** None — no schema file, no JSON-schema, no lint step references skill
frontmatter.
**Implicit contracts:** `name` == directory name == `command` minus the leading `/`.
`allowed-tools` is the security surface (wrapper skills grant only `Agent`,
`Bash(pwd:*)`, and the specific Linear MCP tools they need). Note the agent definitions
in `.claude/agents/*.md` use a DIFFERENT frontmatter shape (`claude: { tools: ... }` —
see `.claude/agents/qrspi-research.md:1-6`), so the two file families are not interchangeable.

## Q4: How are skills registered and surfaced to agents (auto-invocation vs. slash-command wrapper) — what file or manifest declares a skill's trigger description and name?

**Answer:** There is **no manifest**. Registration is by **directory convention**: a
skill exists because a `<name>/SKILL.md` directory lives under `.claude/skills/`. The
`description` frontmatter field is what surfaces the skill for auto-invocation; the
`command` field declares the slash-command form. The repo's two-tier split is explicit
in the README: `.claude/agents/<phase>.md` holds the real agent prompt; `.claude/skills/<phase>/SKILL.md`
is a thin slash-command **wrapper** that spawns that agent via the `Agent` tool.

**Evidence:**

```
agents/                # phase agent prompts
    qrspi-research.md
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-research/
    ...
    qrspi-work/        # Autonomous orchestrator (PR-gated state machine)
```

— `README.md:78-96`

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in
`.claude/agents/qrspi-research.md`.
... Spawn the agent via the `Agent` tool: subagent_type: qrspi-research
```

— `.claude/skills/qrspi-research/SKILL.md:11-18`

**Dependencies:** wrapper `SKILL.md` → agent `.claude/agents/<name>.md` via the `Agent`
tool (`subagent_type: <name>`). No central registry file.
**Implicit contracts:** A skill's trigger text is its `description`; discovery is purely
filesystem-location-based (presence of `SKILL.md` in a dir under `.claude/skills/`).
qrspi-work is the exception that carries its full prompt inline rather than delegating.

## Q5: Where do skill assets and reference files physically live relative to the worktree, and how is the kubectl skill expected to be persisted given the staging-plus-deterministic-move artifact convention (`/tmp/phase-stage/` → `.qrspi/`)?

**Answer:** Skill files live at `<REPO_ROOT>/.claude/skills/<name>/` (with optional
`references/` subdir), and `<REPO_ROOT>/.claude/agents/<name>.md` for the agent half.
The staging-plus-move convention in `qrspi_persist.py` does **NOT** cover skill files —
it is hard-coded to QRSPI **phase artifacts** only. `ARTIFACTS` is a closed list
(`questions, research, design, structure, plan, worktree`) and `dest_path()` always
moves into `.worktrees/<ticket>/.qrspi/<ticket>/<artifact>.md`. A kubectl skill, being
source code under `.claude/skills/`, would be created directly in the worktree by the
implement agent and committed like any other code file — not routed through
`qrspi_persist.py`.

**Evidence:**

```python
ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]
...
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)
```

— `scripts/qrspi_persist.py:43,58-62`

**Dependencies:** `qrspi_persist.py` is invoked only for the six phase artifacts (the
`stg()` helper + `--artifact` choices). Skill source files have no persistence helper.
**Implicit contracts:** Anything that is not one of the six phase artifacts is a normal
working-tree file; it is staged/committed by the orchestrator's git steps (the implement
flow's `git add <every file shown>`), not by the persist script.

## Q6: Is there an existing CLI-tool agent skill in the repo whose structure (multi-file references, copy-pasteable command patterns) can serve as the structural reference for the kubectl skill?

**Answer:** Among in-repo skills, `qrspi-work/SKILL.md` is the closest structural
analog: it is a 565-line skill with heavy copy-pasteable `bash` command blocks (git/gt/gh),
a destructive-operation "HARD STOP" guardrail section, action-dispatch tables, and a
`references/` subdirectory — the exact multi-file + command-pattern shape a kubectl
skill would mirror. The external `using-graphite-cli` and `writing-bash-scripts` skills
named in the question are NOT in the repo (out of scope), so qrspi-work is the only
available in-repo reference.

**Evidence:**

```
gt rename <branch>-stale --no-interactive   # detaches the dead PR
gt rename <branch>        --no-interactive   # restores the canonical name
gt info <branch> --no-interactive            # confirm no "(Closed)/(Merged)" PR line remains
gt submit --publish --force --no-edit --no-interactive # creates a brand-new PR
```

— `.claude/skills/qrspi-work/SKILL.md:513-516` (one of many copy-pasteable blocks)
Line counts — `qrspi-work/SKILL.md` = 565 lines; next largest is `qrspi-ticket` = 119.

**Dependencies:** qrspi-work → `references/review-cascade.md`, `docs/qrspi-pr-gated-lifecycle-design.md`.
**Implicit contracts:** Command blocks use fenced ```bash, placeholder tokens in
`<angle-brackets>`, inline `# comments` explaining each line, and `--no-interactive`
flags throughout — the established command-pattern style for an automatable CLI skill.

## Q7: How do existing skills enforce or document a body-size budget — is the "under 500 lines / 5000 tokens" constraint on `SKILL.md` checked anywhere, and what happens when content exceeds it?

**Answer:** NOT FOUND — there is **no body-size budget check** anywhere in the repo for
`SKILL.md`. No script, eval assertion, or doc references a "500 line / 5000 token" limit
for skills. (`grep` for line-count/budget logic in `scripts/` found only `run_eval.py`,
which counts nothing about skill bodies.) Notably, the longest existing skill,
`qrspi-work/SKILL.md`, is **565 lines** — already over the 500-line figure cited in the
question — and nothing flags it, confirming the budget is unenforced in this codebase.
The only analogous budget that IS documented is for **ticket bodies** (500 words, in the
ticket skill/template), not skill bodies.

**Evidence:**

```
   565 .claude/skills/qrspi-work/SKILL.md   (wc -l)
```

```
- **Description** — three focused sections, 500 words max for the entire ticket body:
```

— `.claude/skills/qrspi-ticket/SKILL.md:33` (the 500-word budget that DOES exist, for tickets)

**Dependencies:** None — no enforcement path.
**Implicit contracts:** Body length is governed only by convention; the wrapper skills
stay terse (25–35 lines) by design ("All prompt content lives in
`.claude/agents/...`" — `qrspi-research/SKILL.md:11`), while qrspi-work, which carries
its prompt inline, runs long without any guard.

## Q8: How do existing skills encode prominently-placed safety guardrails (e.g. destructive-operation warnings) within `SKILL.md` — what formatting or section convention signals a guardrail versus normal guidance?

**Answer:** The established convention (from `qrspi-work`) signals a guardrail with: a
dedicated `###`/`##` heading naming the hazard, ALL-CAPS imperative emphasis, bolded
absolute language, and an enumerated stop-procedure. The canonical example is the
"HARD STOP: Infrastructure Errors Are Not Puzzles To Solve" section and the inline
"CRITICAL —" callout. Destructive-flag guidance (e.g. "Staging — NEVER use `-a`") uses
a heading with the prohibition in the title plus a one-line rationale.

**Evidence:**

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve

Non-negotiable, no exceptions. When ANY operation fails due to permissions, ...

1. **STOP. Do not execute another command.** Not "one more try."
2. **Print the exact error verbatim** ...
**Explicitly forbidden:** `chmod`/`chown`; ... `sudo`/escalation; ...
```

— `.claude/skills/qrspi-work/SKILL.md:547-560` (also `### Staging — NEVER use -a` at :498;
`**CRITICAL — sub-agents do NOT inherit your cwd.**` at :126)

**Dependencies:** None — purely a formatting convention.
**Implicit contracts:** Guardrails are visually distinct (CAPS + bold + dedicated
heading), state the rule as absolute ("Non-negotiable, no exceptions"), enumerate the
required behavior, and often include an "Explicitly forbidden" list of tempting
workarounds. A kubectl skill's destructive-command warnings (delete/apply/scale) would
mirror this shape.

## Q9: What is the repo's convention for an in-scope/out-of-scope or "judgment call" section inside a skill, and do any existing skills demonstrate scope boundaries the kubectl skill can mirror?

**Answer:** The dominant scope-boundary convention is the reusable **"Project scope
restriction / firewall"** block defined in `qrspi-work` and appended to the research and
implement agent prompts. It states a hard root boundary ("ALL file reads must be inside
... REPO_ROOT/"), a pre-action validation rule, an explicit "DO NOT read/modify" list,
and a refusal directive when scope is exceeded. Phase isolation itself is also documented
as a design principle in the README ("Each phase sees only the artifacts it needs").
There is no single named "judgment call" heading convention; scope is expressed as
enumerated DO/DON'T lists and firewall blocks.

**Evidence:**

```
## Project scope restriction

You are researching the codebase for a specific ticket. ALL file reads must be inside
the project repository at REPO_ROOT_VALUE/.

BEFORE reading ANY file, validate its path starts with REPO_ROOT_VALUE/. ...
DO NOT read:
- ~/.claude/, ~/.config/, ~/ (home directory)
- System config files (/etc/, /usr/, /var/)
- Global skill definitions outside the repo
```

— `.claude/skills/qrspi-work/SKILL.md:434-445` (implement variant at :460-476)

**Dependencies:** The firewall block is authored once in qrspi-work and re-emitted into
spawned agent prompts (research, implement).
**Implicit contracts:** Scope sections use a `##`/`###` heading, an enumerated bulleted
"DO NOT" list, a pre-action validation gate, and a "report and STOP / note the gap"
fallback. A kubectl skill would mirror this for cluster/namespace scoping.

## Q10: How are skills verified in this repo given that the `evals/` + `scripts/run_eval.py` harness is documented as a non-functional placeholder — what is the actual accepted verification path for a new skill?

**Answer:** `scripts/run_eval.py` is confirmed a **stub**: `execute_single()` returns
empty output with an inline comment "Placeholder for agent execution / Replace this block
with actual agent invocation" and no agent is ever invoked. The project CLAUDE.md states
the harness is "a **non-functional placeholder**" and that the accepted verification path
is: **stdlib-only unit tests** (`scripts/qrspi_*_test.py`, run with `python3`) for pure
logic, and **manual end-to-end runs** for orchestration. Skills (which are prompts, not
pure logic) therefore have no automated test in-repo — they are verified by manual e2e
runs. `evals/suite.json` defines cases but they are not executable end-to-end.

**Evidence:**

```python
try:
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    ...
    result.output = ""
    result.files = []
```

— `scripts/run_eval.py:116-134`

```
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** —
  verify pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions, final bullet)

**Dependencies:** `run_eval.py` → `grade.py` → `report.py` → `diagnose.py` → `revise.py`
is the *intended* 5-stage pipeline (`docs/eval-system.md:1-12`), but stage 1 is stubbed,
so the whole pipeline is non-functional for live skill execution.
**Implicit contracts:** A new skill ships with manual e2e verification; any *pure-logic*
helper it adds (e.g. a Python script) is expected to carry a `_test.py` sibling using
stdlib `unittest` only.

## Q11: What naming and directory conventions must a new skill directory satisfy to be discovered (directory name vs. frontmatter `name`, location under `.claude/skills/`)?

**Answer:** A skill is discovered by placing `<name>/SKILL.md` under `.claude/skills/`,
where across all 10 existing skills the directory name is **identical** to the frontmatter
`name`, which is **identical** to `command` minus the leading `/`. The agent half (when
the wrapper delegates) lives at `.claude/agents/<name>.md` with a matching `name`. So a
kubectl skill would be `.claude/skills/<dir>/SKILL.md` with frontmatter `name: <dir>` and
`command: /<dir>`. There is no discovery script — discovery is filesystem-convention based
(verified: no skill-discovery logic in `scripts/`).

**Evidence:**

```
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/
    qrspi-questions/
    ...
    qrspi-work/
```

— `README.md:86-96`; all dirs match their `SKILL.md` `name`/`command` (Q3 evidence).

**Dependencies:** None — convention only.
**Implicit contracts:** Triple-identity invariant: `directory name` == frontmatter
`name` == `command` without `/`. The wrapper's agent (if any) is `.claude/agents/<name>.md`
with the same `name`.

## Q12: How is a skill's invocation or triggering surfaced/logged — is there any mechanism that records when a skill fires, which would let an author confirm the kubectl skill's description triggers correctly?

**Answer:** NOT FOUND in-repo. There is **no hook, logging, or invocation-recording
mechanism for skills inside `REPO_ROOT`**: no `hooks/` directory, no `settings.json` /
`settings.local.json` (`find` for both returned nothing committed), and no logging code
tied to skill firing. The question's target, `~/.agents/hooks/`, is **outside the project
scope** and was not read. The closest in-repo observability is the orchestrator's own
runtime printing — qrspi-work instructs printing the resolved decision and phase status
to stdout (e.g. "Print the decision (`action` + `reason`)") — but that surfaces
orchestrator actions, not skill-trigger events.

**Evidence:**

```
4. **Print the decision** (`action` + `reason`) so the operator can observe.
```

— `.claude/skills/qrspi-work/SKILL.md:77` (orchestrator-level observability, not skill triggering)
`find . -name "settings*.json" -not -path "./.git/*"` → no results; no `hooks/` dir in repo.

**Dependencies:** None in-repo. Any skill-trigger logging would live in the harness
(`settings.json` hooks) or `~/.agents/hooks/`, both outside `REPO_ROOT`.
**Implicit contracts:** Within this repo, the only confirmation that a description
"triggers" is manual end-to-end observation (consistent with Q10's manual-verification
path); there is no automated trigger log to inspect.

---

## Discovered Patterns

- **Two-tier skill architecture.** Phase skills are split: a thin slash-command
  **wrapper** in `.claude/skills/<name>/SKILL.md` (25–35 lines, frontmatter +
  "spawn the agent" steps) and the real prompt in `.claude/agents/<name>.md`. The two
  file families use *different* frontmatter shapes — wrappers use
  `name/description/command/argument-hint/allowed-tools`; agents use `name/description`
  plus a `claude: { tools: ... }` block (`.claude/agents/qrspi-research.md:1-6`).
- **qrspi-work is the monolith exception.** It carries its full state-machine prompt
  inline (565 lines, the only skill with a `references/` subdir), rather than delegating
  to an agent file. It is the de-facto template for a long, command-heavy CLI skill.
- **Convention over enforcement.** Triple-identity naming (dir == `name` == `command`
  sans `/`), reference-path style, body length, and guardrail formatting are all
  enforced only by example consistency — no validator, linter, or schema exists in-repo.
- **Self-locating deterministic scripts.** `qrspi_persist.py` and `qrspi_resolve.py`
  derive `REPO_ROOT` from `__file__` (two levels up) specifically to keep the corruptible
  `qrspi` path out of a weak worker model's hands (`qrspi_persist.py:37-41`).
- **Firewall-block reuse.** Scope boundaries and the research/ticket firewalls are
  authored once in qrspi-work and re-emitted into spawned sub-agent prompts (defense in
  depth), rather than relying on tool allowlists alone.
- **Templates are the single source of truth** for output formats (`.qrspi/templates/`,
  `README.md:126`) — skills reference templates rather than embedding formats. (Note:
  this applies to phase *artifacts*, not to SKILL.md authoring, for which no template exists.)

## Inconsistencies

- **Body budget exceeded with no flag (Q7).** If a 500-line `SKILL.md` budget were a
  real constraint, `qrspi-work/SKILL.md` (565 lines) already violates it, yet nothing in
  the repo checks or warns — the only enforced 500-unit budget is the ticket-body
  *word* limit (`qrspi-ticket/SKILL.md:33`), a different thing entirely.
- **Eval system documented as real but stubbed (Q10).** `docs/eval-system.md:1-12`
  describes a working 5-stage eval pipeline ("Execute test cases against a skill prompt,
  multi-trial, parallel"), but `scripts/run_eval.py:116-134` never invokes an agent —
  the executor is an empty placeholder. CLAUDE.md correctly labels it non-functional, so
  the doc and the conventions file disagree on the harness's real status.
- **Frontmatter quoting is inconsistent (Q3).** Only `qrspi-work` quotes its
  `description` scalar (because it contains commas/colons); the other nine leave it bare.
  This is YAML-valid in both cases but stylistically divergent and a likely trip-hazard
  for a hand-authored kubectl description containing punctuation.
- **`scripts/` subdirectory convention undefined (Q1).** The question presumes a
  `scripts/` and `assets/` subdir convention for skills, but no in-repo skill has either —
  only `qrspi-work/references/` exists, so the repo provides a `references/` precedent and
  zero precedent for `scripts/` or `assets/` inside a skill.
