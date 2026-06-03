# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T12:52:33Z
**Status:** draft

> Scope note: The `skill-creator` skill is installed **globally** (it appears in this
> session's available-skills list) but its definition files live under `~/.claude/skills/`,
> **outside REPO_ROOT** (`/workspaces/qrspi/.worktrees/RUS-14`). Per the research firewall,
> files outside the project were not read. Questions that depend solely on the skill-creator
> internals (Q1 inputs, Q4 description-optimization internals, Q6 eval loop, Q10 validation
> step, Q12 trigger logging) are answered "NOT FOUND — outside project scope" where the repo
> holds no evidence. The repo DOES contain ten production SKILL.md files that serve as
> concrete, authoritative examples for layout, frontmatter, cross-references, scope, and size.

## Q1: How does the Anthropic skill builder skill (skill-creator) consume an initial description and produce a SKILL.md plus supporting directories, and what inputs does it require to run?

**Answer:** NOT FOUND — outside project scope. `skill-creator` is a globally-installed skill
whose definition is not present under REPO_ROOT. Searches performed (all rooted at REPO_ROOT):
`find . -ipath "*skill-creator*"` → no matches; `grep -rln "skill-creator\|skill_creator"
--include=*.md --include=*.py --include=*.js` → matched only `.claude/agents/qrspi-structure.md`
and the questions file (see below), not a skill-creator definition.

The only in-repo reference to skill-creator is an instruction to *invoke* it as a validation
pass, not a definition of its inputs/outputs:

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the
   final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

**Dependencies:** skill-creator is referenced as an external/global tool the workflow may call; no repo module imports or wraps it.
**Implicit contracts:** The repo treats skill-creator as a black-box validation/authoring tool available in the harness, not a versioned in-repo asset.

## Q2: What is the canonical on-disk layout for an agentskills.io-style skill in this repo (SKILL.md + references/ + scripts/ + assets/), and where do new skills get placed?

**Answer:** Skills live at `.claude/skills/<skill-name>/SKILL.md`. Each skill is a directory
named after the skill, containing a required `SKILL.md`. Supporting material goes in
sibling subdirectories. The repo demonstrates `references/` (a `scripts/`/`assets/` convention
is named in the questions but only `references/` is actually present in-repo). New skills are
placed as a new directory under `.claude/skills/`. The matching agent prompt (for wrapper-style
skills) lives at `.claude/agents/<skill-name>.md`.

Observed directory tree:

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
.claude/skills/qrspi-work/references/review-cascade.md   <- only multi-file skill
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing)

README confirms the split:

```
skills/              # Slash-command wrappers that invoke the phase agents
```

— `README.md:86`

**Dependencies:** Wrapper SKILL.md files depend on the corresponding `.claude/agents/<name>.md`
prompt (10 agents present except `qrspi-ticket` and `qrspi-work`, which are self-contained).
Templates referenced by skills live in `.qrspi/templates/`.
**Implicit contracts:** Skill directory name == frontmatter `name` == agent filename (for
wrappers). No `scripts/` or `assets/` subdir exists in any skill today; only `references/` is
in use, so that is the only directory convention with a live precedent.

## Q3: What exact frontmatter fields and value formats are required and accepted in a valid SKILL.md (name, description, triggers, allowed-tools, etc.)?

**Answer:** Every in-repo SKILL.md uses YAML frontmatter delimited by `---` with these fields:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`. There is no separate
`triggers` field — triggering is encoded inside `description`. `allowed-tools` is a
comma-separated list; entries can be bare tool names (`Agent`, `Read`), scoped Bash
(`Bash(pwd:*)`), or fully-qualified MCP tool names
(`mcp__linear-russelltsherman__get_issue`). `description` may be a bare scalar or a
double-quoted string when it contains commas/colons (see qrspi-work).

```yaml
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-6`

Quoted form for descriptions with punctuation:

```yaml
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42')..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

**Dependencies:** Field names consumed by the Claude Code harness skill loader (external to repo).
**Implicit contracts:** `command` always begins with `/`; `argument-hint` is angle-bracketed
positional hints; `name` matches the directory; the set {name, description, command,
argument-hint, allowed-tools} is consistent across all 10 files (a de-facto required set in this repo). No repo schema file enforces this — it is convention only.

## Q4: How is a skill's `description`/trigger phrasing structured so the harness auto-invokes it correctly, and what conventions does skill-creator enforce for triggering accuracy?

**Answer:** The skill-creator's enforced conventions are NOT FOUND (outside project scope).
The observable in-repo convention: `description` is two-to-three sentences combining (1) what
the skill produces and (2) explicit "Use when…" trigger phrasing, sometimes enumerating
literal invocation variants. The richest example is qrspi-work, which lists trigger phrasings
verbatim:

```
description: "Single entry point for autonomous QRSPI feature development. Use when the
user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of:
'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to
progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

Simpler skills use a "<what it does>. Use <when> / after <prior phase> approved." shape:

```
description: Define vertical slices, types, and contracts from the approved design. Use after design is approved.
```

— `.claude/skills/qrspi-structure/SKILL.md:3`

**Dependencies:** Consumed by the harness's auto-invocation matcher (external).
**Implicit contracts:** Sequencing skills state their precondition ("Use after X is
approved"); the discoverable pattern is action + explicit "Use when/after" clause, with
literal trigger phrases for high-ambiguity skills.

## Q5: How are `references/`, `scripts/`, and `assets/` files referenced from within SKILL.md so the agent loads them on demand rather than inline?

**Answer:** The only in-repo precedent is `references/`: SKILL.md mentions the relative path
in prose so the agent reads it on demand rather than inlining the content. qrspi-work keeps a
77-line cascade doc out of its main body and points to it:

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282` (referencing `.claude/skills/qrspi-work/references/review-cascade.md`, 77 lines)

A second cross-reference style is invoking repo scripts by path from inside a SKILL.md:

```
folded into a single script (`scripts/qrspi_resolve.py`). Run it verbatim — do **not** ...
python3 scripts/qrspi_resolve.py --ticket "<ticket-id>" \
```

— `.claude/skills/qrspi-work/SKILL.md:58,61`

Wrapper skills similarly reference external content by path (the agent prompt and templates):

```
All prompt content lives in `.claude/agents/qrspi-design.md`.
```

— `.claude/skills/qrspi-design/SKILL.md:11`

**Dependencies:** `references/review-cascade.md`, `scripts/qrspi_resolve.py`, `.claude/agents/*.md`, `.qrspi/templates/*`.
**Implicit contracts:** On-demand loading is achieved by naming the relative path in prose
(backtick-quoted) and instructing the agent to read/run it; content is NOT pasted inline. Paths
are repo-root-relative (e.g. `scripts/...`) or skill-dir-relative (e.g. `references/...`). There is no `assets/` example in-repo.

## Q6: What process does skill-creator define for its eval loop, and where are eval cases and results stored when iterating on a new skill?

**Answer:** skill-creator's own eval-loop definition is NOT FOUND (outside project scope).
However, the repo has its OWN eval harness (a documented placeholder) that stores cases and
results, which is the in-repo analogue:

- Cases: `evals/suite.json` (15 cases spanning all QRSPI phases) and
  `evals/graphite-evals.json` (5 cases for the Graphite skill). Fixtures in `evals/fixtures/`,
  expected outputs in `evals/golden/`.
- Results destination is a configurable `output_dir` (see `EvalConfig` in run_eval.py).
- Pipeline: run_eval → grade → report → diagnose → revise.

```
1. `scripts/run_eval.py` — Execute test cases against a skill prompt (multi-trial, parallel)
2. `scripts/grade.py` — Score results using programmatic checks + LLM judges
3. `scripts/report.py` — Compare versions, detect regressions/plateaus/overfitting
4. `scripts/diagnose.py` — Categorize failures into root causes (8 categories)
5. `scripts/revise.py` — Propose and apply targeted prompt edits
```

— `docs/eval-system.md:5-9`

**Dependencies:** `evals/suite.json`, `evals/graphite-evals.json`, `evals/fixtures/`, `evals/golden/`, `scripts/run_eval.py`.
**Implicit contracts:** Cases use a 65/35 train/test split (seed 42); defaults 3 trials, 120s
timeout (`docs/eval-system.md`). CRITICAL caveat — this harness does not actually execute
agents (see Q11/Inconsistencies); it is a placeholder.

## Q7: How is the SKILL.md body size constraint (under 500 lines / 5000 tokens) measured and validated, and what existing skills sit near that boundary?

**Answer:** No in-repo tooling measures or enforces a SKILL.md size/token budget — searches
for a validator returned nothing (`grep -rln -i "frontmatter\|allowed-tools\|argument-hint"
scripts/` → no matches; no 500-line/5000-token check anywhere in `docs/` or `README.md`). The
constraint is therefore unenforced convention. Current line counts:

```
   28 .claude/skills/qrspi-design/SKILL.md
   35 .claude/skills/qrspi-implement/SKILL.md
   26 .claude/skills/qrspi-plan/SKILL.md
   28 .claude/skills/qrspi-pr/SKILL.md
   26 .claude/skills/qrspi-questions/SKILL.md
   26 .claude/skills/qrspi-research/SKILL.md
   25 .claude/skills/qrspi-structure/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  565 .claude/skills/qrspi-work/SKILL.md   <- exceeds the 500-line guideline
   25 .claude/skills/qrspi-worktree/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`

**Dependencies:** None (no validator).
**Implicit contracts:** Wrapper skills stay ~25–35 lines by delegating to agent files;
self-contained skills (qrspi-ticket 119, qrspi-work 565) are larger. qrspi-work already sits
**over** the 500-line guideline and offloads detail to `references/review-cascade.md` — the
in-repo precedent for staying under budget is "move detail into references/," not an automated check.

## Q8: How do existing skills delineate in-scope vs out-of-scope material within SKILL.md so scope boundaries (kubectl/kustomize, Helmfile, GitOps reconcilers) are expressed consistently?

**Answer:** Two consistent in-repo patterns express scope boundaries: (1) an explicit
"Out of Scope" / anti-pattern section, and (2) inline "do NOT" directives that defer related
work to a sibling skill/phase. qrspi-ticket has a dedicated anti-pattern list; qrspi-work
defers cross-phase concerns explicitly.

Dedicated negative-scope section:

```
### Anti-patterns — do NOT include in the ticket body
Before drafting, verify the ticket contains NONE of these:
- Specific technical approaches, tool choices, or library recommendations
- Code patterns, CLI commands, API calls, or configuration examples
...
If any appear, strip them. They belong in Design, Structure, or Plan phases.
```

— `.claude/skills/qrspi-ticket/SKILL.md:50-59`

Deferral to a sibling mechanism rather than handling inline:

```
here; a design-level change that invalidates plan/impl is handled by `reset`, not revise.
```

— `.claude/skills/qrspi-work/SKILL.md:283`

**Dependencies:** Scope deferrals point to other phases/skills (Design/Structure/Plan; reset).
**Implicit contracts:** The convention is "name the excluded topic explicitly and say which
other skill/phase owns it" — directly applicable to a helm skill deferring kubectl/kustomize/
Helmfile/GitOps to separate skills.

## Q9: How do existing skills handle version-specific guidance where defaults differ across tool versions (analogous to Helm 3 vs Helm 4), and is there a convention for noting compatibility caveats?

**Answer:** NOT FOUND — there is no in-repo precedent for version-specific/compatibility-caveat
guidance inside a SKILL.md. A search for version/compat markers across all skills and agents
(`grep -rln -i "helm 3\|helm 4\|version\|3.x\|deprecat\|compat" .claude/skills .claude/agents`)
matched only `.claude/skills/qrspi-ticket/SKILL.md`, and that hit is the word "version" in an
unrelated VCS context, not a tool-version compatibility note. No skill encodes
version-conditional defaults, so there is no established convention to mirror.

**Dependencies:** None.
**Implicit contracts:** None established; a helm skill would be introducing this pattern, not
following an existing one.

## Q10: When skill-creator generates a skill, how are failure cases surfaced if required frontmatter is missing or the directory structure is invalid?

**Answer:** NOT FOUND — outside project scope. skill-creator's validation/failure behavior is
not defined in any file under REPO_ROOT (no frontmatter/structure validator exists in
`scripts/`; see Q7). The closest in-repo failure-surfacing convention is the general
"hard stop, print exact error, do not work around" pattern used by the QRSPI skills
themselves, e.g.:

```
2. If `save_issue` fails, report the error to the user and STOP. Do not create a local
   directory or fall back to local files.
```

— `.claude/skills/qrspi-ticket/SKILL.md:113`

```
— if the retry fails, this is a **hard stop** — print the exact error and exit.
```

— `.claude/skills/qrspi-work/SKILL.md:53-54`

**Dependencies:** None for skill-creator validation (external).
**Implicit contracts:** Repo convention for failures is fail-loud / no silent workaround; if a
helm skill needs structural validation it would adopt this convention, but no automated
structure check exists to invoke.

## Q11: How are skills verified in this repo given the eval harness is a non-functional placeholder, and what manual/unit-test path confirms a new skill is well-formed?

**Answer:** Verification is by (1) stdlib-only Python unit tests for the deterministic logic
(`scripts/qrspi_*_test.py`) and (2) manual end-to-end runs — NOT by the eval harness, which is
an explicit placeholder. `scripts/run_eval.py` does not actually execute an agent; its core
function is a stub:

```
This stub captures the structure for integration with
the actual agent runtime.
...
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
...
result.output = ""
result.files = []
```

— `scripts/run_eval.py:107-134`

Project convention confirms this:

```
The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions)

A SKILL.md itself has no unit test in-repo — well-formedness is confirmed by manual review
against the existing 10 SKILL.md examples plus (per the workflow) invoking skill-creator as the
authoring/validation pass (Q1/Q10 caveats apply).

**Dependencies:** `scripts/qrspi_*_test.py` (run with `python3`); manual e2e.
**Implicit contracts:** Pure-logic code gets `_test.py` siblings; prose skill files are
verified by review/manual run, not automated tests.

## Q12: How does the harness report which skill was invoked and whether its trigger matched, so authors can confirm the new helm skill activates on the intended requests?

**Answer:** NOT FOUND — outside project scope. Skill invocation/trigger logging is a Claude
Code harness feature, not implemented in any file under REPO_ROOT. No repo module logs skill
selection or trigger matches (no matches for skill-invocation logging in `scripts/`,
`.claude/`, or `docs/`). The repo's only related capability is the (placeholder) eval harness,
which is designed to capture `tool_calls`/`transcript` per case but currently records nothing
(`result.output = ""`, `scripts/run_eval.py:133`). Trigger-match confirmation in practice would
rely on the harness UI/logs, which are external to this project.

**Dependencies:** External harness.
**Implicit contracts:** None in-repo.

---

## Discovered Patterns

- **Two skill archetypes.** (a) Thin wrappers (~25–35 lines) whose SKILL.md only parses
  `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, and spawns a `subagent_type` agent — all real
  content lives in `.claude/agents/<name>.md` (e.g. qrspi-design/plan/research/structure/
  worktree/pr/implement/questions). (b) Self-contained skills whose full prompt lives in
  SKILL.md (qrspi-ticket, qrspi-work). A helm skill would be archetype (b).
- **Frontmatter is a stable 5-field set** across all 10 files: name, description, command,
  argument-hint, allowed-tools. `name` == directory == agent filename.
- **Description = action + explicit "Use when/after" trigger clause**, with literal trigger
  phrases enumerated for high-ambiguity skills (qrspi-work).
- **On-demand loading via path-naming, not inlining:** backtick-quoted relative paths to
  `references/`, `scripts/`, `.claude/agents/`, `.qrspi/templates/`.
- **Fail-loud convention:** hard stop + print exact error + no silent fallback (qrspi-ticket:113,
  qrspi-work:53). This aligns with the user's global "error surfacing over workarounds" directive.
- **Templates as single source of truth** for output formats, in `.qrspi/templates/`
  (README.md:126) — skills reference templates rather than embedding them.
- **No automated skill validation exists** — no frontmatter linter, no size/token checker, no
  structure validator anywhere in the repo.

## Inconsistencies

- **qrspi-work SKILL.md is 565 lines**, exceeding the 500-line guideline cited in Q7, while
  every other SKILL.md is ≤119. It partially mitigates by offloading to
  `references/review-cascade.md`, but the main body still overshoots. (`wc -l`)
- **Eval harness documented as a real 5-stage pipeline vs. actually a stub.** `docs/eval-system.md`
  describes run_eval.py as "Execute test cases against a skill prompt," but the code is an
  explicit placeholder that returns empty output (`scripts/run_eval.py:107-134`) — matching the
  `.claude/CLAUDE.md` "non-functional placeholder" note but contradicting the eval-system doc's
  affirmative phrasing.
- **`scripts/` and `assets/` skill subdirectories are named in the questions' assumed layout but
  do not exist in any skill** — only `references/` has a live precedent (one occurrence,
  qrspi-work). A new skill using `scripts/`/`assets/` would be establishing, not following, that
  convention.
- **skill-creator is invoked by the workflow (qrspi-structure.md:40) but its definition is not
  vendored into the repo** — the project depends on a globally-installed skill that is invisible
  to repo-scoped tooling and review.
