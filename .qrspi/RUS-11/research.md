# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

> Scope note: This repo (`qrspi`) contains **no `skill-creator` skill**, **no `deep-research`
> skill**, and **no agentskills.io / Anthropic skill-builder standard document**. Those are
> global/plugin skills that live outside `REPO_ROOT` and are intentionally not readable in this
> phase. Questions that target them are answered from the **observable in-repo evidence** (the
> ten `.claude/skills/qrspi-*/SKILL.md` files and their conventions); the out-of-scope portion
> is marked `NOT FOUND — outside project scope`. The repo's only authority on the standard is
> the convention encoded in its own SKILL.md files.

## Q1: What is the on-disk directory layout the agentskills.io standard expects for a skill, and how do `SKILL.md`, `references/`, `scripts/`, and `assets/` relate to one another?

**Answer:** The agentskills.io / Anthropic standard specification itself is **NOT FOUND in
REPO_ROOT** (no spec doc, no validator). The repo's *observed* convention is: each skill is a
directory under `.claude/skills/<skill-name>/` containing a `SKILL.md` file, with an optional
`references/` subdirectory for ancillary material. Of the ten skills in the repo, **only
`qrspi-work` uses a subdirectory** (`references/review-cascade.md`); none use `scripts/` or
`assets/`. So `references/` is the only one of the four with in-repo precedent. `scripts/` and
`assets/` have **no in-repo example** — their relationship to `SKILL.md` cannot be evidenced
from this codebase.

The observed layout:
```
.claude/skills/
  qrspi-work/
    SKILL.md
    references/
      review-cascade.md
  qrspi-questions/
    SKILL.md
  ... (8 more, each just SKILL.md)
```

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   <-- only subdir in any skill
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing; full tree confirmed via `find .claude/skills -type f`)

The `references/` file is a self-contained markdown document (cascade decision tables), not code:

```
# Review Cascade Logic (PR-gated)
Artifacts form a dependency chain, now split across **per-phase PR branches**:
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-5`

**Dependencies:** `SKILL.md` is the entry point; `references/*.md` are pulled in by reference
from the SKILL body (see Q2). No build step links them.
**Implicit contracts:** Skill name = directory name = frontmatter `name` field (all three match
for every skill). The directory is the unit; `SKILL.md` is mandatory; `references/` is optional.

## Q2: How is reference material in `references/` surfaced to an agent at runtime — is it loaded eagerly with `SKILL.md` or pulled on demand — and what does that imply for splitting the CLI reference, schema cheatsheet, lifecycle decision tree, and CI/CD examples across files?

**Answer:** **NOT FOUND in code** — there is no in-repo skill *loader* module (the harness that
loads skills lives outside REPO_ROOT). The loading mechanism cannot be evidenced from source.
What *is* observable is the **authoring convention** the repo uses to make on-demand loading
work: `references/review-cascade.md` is referenced by *relative path inside the SKILL.md body*
at the exact decision point where it is needed, which is the textbook progressive-disclosure
("pull on demand") pattern — the body stays small and points the agent to the reference only
when relevant.

**Evidence:**

```
Address feedback **within this phase only** — the cascade is bounded to the
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:281-283`

```
the cascade is bounded to the phase's own artifacts (see `references/review-cascade.md`).
```

— `.claude/skills/qrspi-work/SKILL.md` references the file by relative path 3 times
(`grep -c "references/" → 3`).

**Dependencies:** Runtime loading behavior is owned by the external Claude Code harness, not
this repo. Downstream: any new skill that splits content into `references/` must cite each file
by relative path from the body, as `qrspi-work` does.
**Implicit contracts:** A `references/<file>.md` is only useful if the SKILL body names it at
the relevant decision point; orphaned reference files would never be surfaced. Implication for
splitting CLI reference / schema cheatsheet / decision tree / CI-CD examples: each split-out
file needs an explicit `(see references/<name>.md)` pointer in the body for the same on-demand
behavior `qrspi-work` relies on.

## Q3: What fields are required vs optional in `SKILL.md` frontmatter for the agentskills.io standard, and what constraints (allowed characters, length, naming) apply to the `name` and `description` fields?

**Answer:** The **formal standard's field list and constraints are NOT FOUND** (no spec/validator
in REPO_ROOT). From the ten in-repo SKILL.md files, the **observed frontmatter schema** is a YAML
block delimited by `---` with these keys (present in all ten): `name`, `description`, `command`,
`argument-hint`, `allowed-tools`. No skill omits any of these five, so empirically all five are
treated as required by convention; there is no observed "optional" field. Constraints are not
declared anywhere in-repo, but observed values: `name` is always lowercase kebab-case and
exactly equals the directory name (e.g. `qrspi-research`); `description` is a single-line string
(quoted when it contains commas/colons, e.g. `qrspi-work`), phrased with a "what + when to use"
trigger pattern (see Q8).

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

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (multi-clause descriptions are double-quoted)

**Dependencies:** Frontmatter is consumed by the external harness (out of scope). 
**Implicit contracts:** `name` MUST equal the directory name (invariant across all ten). 
`allowed-tools` is a comma-separated tool allowlist and is where tool lockdown lives (e.g.
research = `Agent, Bash(pwd:*)`; ticket = `Read, Glob, Grep, Write, Bash, mcp__...save_issue`).
`command` is the slash-command string (`/<name>`); `argument-hint` documents positional args.

## Q4: What does the skill-creator skill's authoring workflow require as inputs and produce as outputs (scaffolding, eval loop, packaging), and which of its steps are mandatory per the ticket's "Built using the Anthropic skill builder skill" criterion?

**Answer:** **NOT FOUND — outside project scope.** The `skill-creator` skill is a global/plugin
skill; it does not exist under `.claude/skills/` in REPO_ROOT (confirmed: the ten skills present
are all `qrspi-*`). Its inputs, outputs, scaffolding, eval loop, and packaging steps cannot be
evidenced from this repo. The only in-repo references to "skill-creator" are textual mentions in
`.claude/agents/qrspi-structure.md` and the questions artifact — neither defines the workflow.

**Evidence:**

```
.claude/agents/qrspi-structure.md   (mentions the string "skill-creator")
.qrspi/RUS-11/questions.md
```

— `grep -rl "skill-creator" .` (only these two files; neither is the skill definition)

Searched: `find .claude/skills -name SKILL.md` (ten results, all `qrspi-*`);
`grep -rl "skill-creator"` (no SKILL.md hit).
**Dependencies:** N/A — out of scope.
**Implicit contracts:** N/A — out of scope.

## Q5: Where do new skills live in this repo (`.claude/skills/` vs `.claude/agents/`), and what is the relationship between a skill definition and its slash-command wrapper per the project conventions?

**Answer:** Skills live in `.claude/skills/<name>/SKILL.md`; agents live in
`.claude/agents/<name>.md`. The documented convention: **"Phase agent definitions live in
`.claude/agents/`; their slash-command wrappers live in `.claude/skills/`."** The pattern is a
**thin wrapper**: the `SKILL.md` is a minimal slash-command shim that parses arguments and
spawns the matching agent via the `Agent` tool (`subagent_type: <name>`); **all prompt content
lives in the agent file**. Eight of the ten skills follow this (the eight phase wrappers).
`qrspi-ticket` (119 lines) and `qrspi-work` (565 lines) are exceptions — they hold their logic
directly in SKILL.md and have **no** sibling agent in `.claude/agents/` (agents dir contains 8
files: design, implement, plan, pr, questions, research, structure, worktree — no ticket, no work).

**Evidence:**

```
- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
```

— `.claude/CLAUDE.md` (Codebase conventions section)

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:11`

**Dependencies:** Wrapper SKILL.md → agent file via `subagent_type`. A non-thin skill (ticket,
work) has no agent dependency. 
**Implicit contracts:** Thin wrappers verify the output artifact exists and is non-empty after
the agent returns, then stop on failure (`SKILL.md:25` research). `name` ties the skill, command,
and (for thin wrappers) the agent together.

## Q6: How are the `SKILL.md` body size limits (under 500 lines / 5000 tokens) measured and enforced in this repo, and is there an existing check or convention for keeping bodies within budget?

**Answer:** **NOT FOUND** — there is **no SKILL.md size-check tooling and no enforcement** in
this repo. Searched `scripts/`, `.claude/`, and `README.md` for `5000`, `500 lines`, `max_lines`,
`wc -l`, `token` (against SKILL.md): the only `max_lines`/`line_count` hit is `grade.py`, which
checks **phase artifacts** (questions.md, etc.) inside the eval harness, not SKILL.md bodies — and
that harness is a non-functional placeholder (see Q10). The convention is purely cultural ("thin
wrapper"), evidenced by the actual line counts. Notably, **`qrspi-work/SKILL.md` is 565 lines —
it exceeds the 500-line guideline the ticket references**, with nothing in the repo flagging it
(see Inconsistencies).

**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
   26 .claude/skills/qrspi-questions/SKILL.md
   26 .claude/skills/qrspi-research/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  565 .claude/skills/qrspi-work/SKILL.md      <-- over 500
```

— `wc -l .claude/skills/*/SKILL.md`

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    count = len(output.splitlines())
    ok = count <= max_lines
```

— `scripts/grade.py:35-40` (applies to eval artifact output, not SKILL.md; placeholder harness)

**Dependencies:** None — no validator imports SKILL.md.
**Implicit contracts:** The "thin wrapper" convention keeps the eight phase skills at ~25-35
lines; budget compliance is by author discipline, not tooling.

## Q7: How does the standard pattern handle a skill that needs both a concise body and large reference appendices without exceeding the body budget — what is the precedent for what stays in `SKILL.md` vs what moves to `references/`?

**Answer:** The single in-repo precedent is **`qrspi-work`**. The pattern: the **operational
state machine, dispatch table, and per-action handlers stay in `SKILL.md`**, while a **bounded,
self-contained decision document** (the cascade rules) was moved to
`references/review-cascade.md` and cited from the body at the one place it is needed (the
`revise` action). The body keeps the *control flow*; the reference holds a *detailed lookup
table* the agent only consults in a specific branch. Note this precedent is imperfect: even
after moving the cascade out, `qrspi-work/SKILL.md` is still 565 lines (Q6) — so the repo's one
example shows the pattern but does **not** demonstrate keeping the body under the 500-line budget.
(`deep-research`, named in the question, is **NOT FOUND — outside project scope**.)

**Evidence:**

```
Address feedback **within this phase only** — the cascade is bounded to the
phase's own artifacts (see `references/review-cascade.md`).
```

— `.claude/skills/qrspi-work/SKILL.md:281-283` (body cites the reference at the decision point)

```
# Review Cascade Logic (PR-gated)
## 1. Within-phase cascade — the manual `revise` path
## 2. Cross-phase change — the automatic `reset` path (NOT a patch)
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1,15,57` (the moved-out detail tables)

**Dependencies:** Body → reference by relative path.
**Implicit contracts:** What moves out is a topic the agent needs **conditionally**; what stays
is the always-needed dispatch/control flow. The reference must be cited or it is dead.

## Q8: What is the established convention for the `description` triggering field so the new skill auto-invokes on devcontainer requests without over-triggering on general Docker work that is out of scope?

**Answer:** The observed convention is a **two-part description**: (1) a clause stating *what the
skill does*, then (2) explicit *"Use when…"* / *"Trigger on…"* phrasing enumerating concrete
invocation phrases. The strongest example is `qrspi-work`, which lists exact trigger variants
(`'work on <ticket-id>'`, `'continue <ticket-id>'`, `'pick up <ticket-id>'`). Thin phase skills
use a terser "Use after X is approved" / "Use when starting…" form. **No in-repo description uses
explicit "when NOT to use / skip" negative phrasing** — there is no precedent for an anti-trigger
clause to suppress over-triggering, so the established mechanism for scoping is *specificity of
positive triggers*, not exclusion clauses. (The richer when-to-skip guidance lives in the global
`skill-creator`/`update-config` skills, which are **outside project scope**.)

**Evidence:**

```
description: "... Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ...
Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

```
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-questions/SKILL.md:3`

**Dependencies:** Consumed by the external harness's skill router.
**Implicit contracts:** Descriptions are single-line; quote the value when it contains
commas/colons. Specific quoted trigger phrases narrow invocation; there is no negative-clause
precedent in this repo.

## Q9: Does this repo's `.devcontainer/devcontainer.json` exist and what patterns does it already use (image vs build, remoteUser, features, lifecycle hooks)?

**Answer:** **Yes — it exists** at `.devcontainer/devcontainer.json` (93 lines, plus a sibling
`Dockerfile`, `config/`, `etc/`, and `protected-paths`). Patterns it uses:
- **build, not image:** `"build": { "dockerfile": "Dockerfile" }` (no `image` key; no `features`).
- **remoteUser:** `vscode`.
- **No `features` block** — everything is in the Dockerfile.
- **All four lifecycle hooks present**, each delegating to a script under `.devcontainer/config/`:
  `initializeCommand` → `initialize.sh`, `postCreateCommand` → `post-create.sh`,
  `postStartCommand` → `post-start.sh`. (`onCreateCommand`/`updateContentCommand` are absent;
  `initializeCommand` is present, which is unusual.)
- **Security hardening:** `capAdd: [NET_ADMIN, SYS_ADMIN]`, a custom hardened seccomp profile via
  `runArgs`, `--add-host=host.docker.internal:host-gateway`, bind `mounts` for host config repos,
  and a `protected-paths` shadowing mechanism.
- **containerEnv:** forwards OMLX_* and OLLAMA_* local-model-server vars from `localEnv`.
- **workspaceFolder/workspaceMount:** explicit, cached consistency.

**Evidence:**

```
"build": { "dockerfile": "Dockerfile" },
...
"initializeCommand": "bash .devcontainer/config/initialize.sh",
...
"postCreateCommand": "bash .devcontainer/config/post-create.sh",
"postStartCommand": "bash .devcontainer/config/post-start.sh",
"remoteUser": "vscode",
```

— `.devcontainer/devcontainer.json:4-6, 35, 85-88`

```
"capAdd": ["NET_ADMIN", "SYS_ADMIN"],
"runArgs": ["--security-opt", "seccomp=${localWorkspaceFolder}/.devcontainer/etc/seccomp/hardened.json",
            "--add-host=host.docker.internal:host-gateway"],
```

— `.devcontainer/devcontainer.json:70, 80-83`

**Dependencies:** References `Dockerfile`, `config/{initialize,post-create,post-start}.sh`,
`etc/seccomp/hardened.json`, `protected-paths`, `etc/sudoers.d/vscode` (per comments).
**Implicit contracts:** This repo's own devcontainer is a **build-based, hardened, lifecycle-script
-driven** setup — opinionated defaults a new skill recommends (e.g. "prefer `image` over `build`,
use `features`") would *contradict* the repo's own working example. Lifecycle work is delegated
to scripts, not inlined in JSON.

## Q10: What mechanism exists to test or eval a skill in this repo, and is the skill-creator eval loop functional here or is it covered by the "non-functional placeholder" note?

**Answer:** Two distinct things exist: (1) **unit tests** — `scripts/qrspi_*_test.py`, stdlib-only,
run with `python3`, covering the pure logic (resolver, persist, pr_state); these are real and
functional. (2) The **`evals/` + `scripts/run_eval.py` + `scripts/grade.py` harness** — this is
the **non-functional placeholder** explicitly called out in the project conventions. `run_eval.py`
`execute_single()` has a stubbed agent-execution block that returns empty output (`result.output
= ""`); `grade.py`'s `run_llm_judge`/`run_script_check` return `passed: None` ("not yet
integrated"). So **there is no functional way to runtime-eval a skill in this repo**; verification
of pure logic is via the `_test.py` unit tests, and orchestration via manual end-to-end runs. The
**skill-creator eval loop is NOT FOUND — outside project scope** (skill-creator is a global skill).

**Evidence:**

```
The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions section)

```
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
...
result.output = ""
result.files = []
```

— `scripts/run_eval.py:117-135`

```
"evidence": "LLM judge not yet integrated — requires model API",
```

— `scripts/grade.py:226`

**Dependencies:** Unit tests: stdlib only. Harness: `run_eval.py` → `suite.json` + skill file;
`grade.py` → `results.json` + `suite.json`.
**Implicit contracts:** Real verification = `_test.py` siblings + manual e2e. The eval harness
JSON schema is defined but un-executed.

## Q11: What format do existing skill evals use for triggering and behavior assertions, so acceptance criteria can be verified rather than assumed?

**Answer:** Eval cases live in `evals/suite.json` (and `evals/graphite-evals.json`). A case is a
JSON object with `id`, `name`, `phase`, `prompt`, `context` (fixture `files`,
`conversation_history`, `user_preferences`), and an `assertions` array, plus `tags`,
`difficulty`, and `split` (train/test). Each assertion has a `type` — **`programmatic`** (a
`check` string naming a registered function with args, e.g.
`"question_count('questions.md') >= 8"`), **`llm_judge`** (a `criteria` string), or **`script`** —
and a numeric `weight`. The registered programmatic checks live in `scripts/grade.py`'s `CHECKS`
dict (e.g. `output_file_exists`, `has_section`, `no_solution_language`, `all_questions_have_target`,
`all_evidence_has_file_citations`, `all_slices_have_verification`). **There is no "triggering"
assertion type** — these cases test *behavior given a prompt*, not auto-invocation/routing. So
acceptance criteria expressible as text-pattern checks (sections present, counts, citations) map
to `programmatic` checks; subjective ones map to `llm_judge` (which is non-functional, Q10).
Fixtures are markdown tickets in `evals/fixtures/`. **Skill-creator's own eval fixtures: NOT
FOUND — outside project scope.**

**Evidence:**

```
{ "type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0 },
{ "type": "programmatic", "check": "no_solution_language('questions.md')", "weight": 2.0 },
{ "type": "llm_judge", "criteria": "Questions are specific and answerable by reading code...", "weight": 2.0 }
```

— `evals/suite.json:38-71`

```
CHECKS = { "output_file_exists":..., "has_section":..., "no_solution_language":...,
           "all_questions_have_target":..., "all_evidence_has_file_citations":... }
```

— `scripts/grade.py:146-157`

Note: `suite.json` references checks not in the registry (`section_count`,
`section_question_count`) — see Inconsistencies.
**Dependencies:** `suite.json` `check` strings must resolve to `grade.py` `CHECKS` functions;
`context.files` must resolve to `evals/fixtures/*`.
**Implicit contracts:** Assertions are weighted; `split` partitions train/test; a `check` string
naming an unregistered function is silently scored `passed: None` (`grade.py:196-197`).

## Q12: How does the skill loader report a malformed or oversized skill (frontmatter errors, missing required fields, body over budget) — where would such errors surface so authoring failures are visible?

**Answer:** **NOT FOUND in REPO_ROOT.** There is no in-repo skill loader, frontmatter parser, or
SKILL.md validator — that machinery is in the external Claude Code harness, outside project scope.
Consequently, **frontmatter errors / missing-field / over-budget conditions for a SKILL.md have
no in-repo surfacing point and no enforcement** (consistent with Q6: no size check exists). The
nearest analogues are: (a) the **eval-suite** loader `load_suite()` in `run_eval.py`, which
raises `ValueError` on missing required keys for *suite/case JSON* (not SKILL.md); and (b) the
**persistence gate** `qrspi_persist.py`, which verifies a staged artifact is non-empty and fails
the phase otherwise — again, for phase artifacts, not skills. Authoring failures of a SKILL.md
would only surface at *load time in the live harness*, which this repo does not contain.

**Evidence:**

```
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
```

— `scripts/run_eval.py:47-50` (validates eval-suite JSON, NOT SKILL.md)

Searched: `grep -rn "frontmatter\|SKILL.md\|yaml" scripts/` → no SKILL.md parser/validator.
**Dependencies:** Skill loading/validation = external harness (out of scope).
**Implicit contracts:** Because nothing in-repo validates SKILL.md, correctness of a new skill's
frontmatter and body budget is the author's responsibility and is only checked by the live agent
runtime.

---

## Discovered Patterns

- **Thin-wrapper skill pattern (dominant).** 8 of 10 skills are ~25-35 line shims whose body is
  one sentence ("Thin wrapper that spawns the `<name>` agent. All prompt content lives in
  `.claude/agents/<name>.md`.") plus a numbered Steps list that parses `$ARGUMENTS`, resolves
  `REPO_ROOT` from `pwd`, spawns via `Agent` (`subagent_type`), then verifies the artifact is
  non-empty. (`.claude/skills/qrspi-research/SKILL.md:9-26`)
- **Frontmatter is the tool-lockdown mechanism.** `allowed-tools` differs sharply per skill —
  research has only `Agent, Bash(pwd:*)`; ticket has `Read, Glob, Grep, Write, Bash, mcp__...`.
  Per-phase least privilege is enforced in frontmatter, not code.
- **`name` == directory name == command basename** is invariant across all ten skills.
- **References are cited by relative path at the decision point**, never preloaded
  (`qrspi-work/SKILL.md:281`). Single precedent, but consistent with progressive disclosure.
- **Verification = unit tests + manual e2e, not the eval harness.** The repo repeatedly states
  the `evals/` harness is a placeholder; real assurance is `scripts/qrspi_*_test.py`.
- **Self-locating one-shot scripts** (`qrspi_resolve.py`, `qrspi_persist.py`) and **token-free
  staging paths** are a deliberate pattern to defend against a weak local worker model mangling
  the `qrspi` token in long paths (`.claude/CLAUDE.md` conventions; `scripts/qrspi_persist.py:8-22`).
- **The repo's own devcontainer is build-based + heavily hardened** (seccomp, capAdd, protected
  paths, lifecycle scripts) — an opinionated reference any devcontainer-advice skill must respect.

## Inconsistencies

- **`qrspi-work/SKILL.md` is 565 lines — over the 500-line guideline** referenced by the ticket,
  even after moving the cascade tables to `references/`. The repo's only "large skill with
  references" precedent does not itself meet the body budget, and nothing flags it. (`wc -l`)
- **`suite.json` references unregistered check functions.** It uses
  `section_count('questions.md', '## ') >= 5` (`evals/suite.json:34`) and `section_question_count`
  (`:64`), but `grade.py`'s `CHECKS` registry (`scripts/grade.py:146-157`) defines neither. Such
  checks are scored `passed: None` (silently skipped) rather than erroring (`grade.py:196-197`).
- **`grade.py` check signatures vs `suite.json` call strings can mismatch.** `parse_check_call`
  (`grade.py:160-174`) only extracts string/number literals and ignores operators like `>= 5` /
  `<= 15` in the suite's check strings — the comparison is dropped, so e.g.
  `question_count(...) >= 8` would call `question_count('questions.md')` and treat its numeric
  return as `passed: True` regardless of the threshold (`grade.py:188-190`). The eval DSL in the
  suite is more expressive than the grader implements (further evidence the harness is a placeholder).
- **Two skills (`qrspi-ticket`, `qrspi-work`) break the thin-wrapper convention** — they hold full
  logic in SKILL.md and have no sibling agent in `.claude/agents/`, unlike the documented "wrappers
  in skills, logic in agents" rule (`.claude/CLAUDE.md`). The convention is real but not universal.
- **agentskills.io / Anthropic skill-builder standard is referenced by the ticket but absent
  from the repo.** No spec, validator, or `skill-creator` skill exists in REPO_ROOT; the only
  available authority on the standard is the implicit convention encoded in the ten SKILL.md files.
