# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

> **Scope finding (read first).** The majority of these questions target the **Anthropic
> skill-creator skill** and **kustomize CLI reference content**. Neither exists inside
> `REPO_ROOT` (`/workspaces/qrspi/.worktrees/RUS-16`). `skill-creator` is a **global plugin
> skill** (it appears in the harness's available-skills list but has no files under the repo),
> and there is **zero kustomize content** anywhere in the repo (`grep -rli kustomize` matches
> only `questions.md` itself). Per the project-scope firewall, those questions are answered
> **NOT FOUND — outside project scope**, with the search queries recorded. What the repo *does*
> contain — and what is answerable — is a set of **in-repo skill examples** (`.claude/skills/*/SKILL.md`),
> their authoring conventions, and an **eval harness** (`evals/` + `scripts/`) that the project
> documents as a non-functional placeholder. Those facts are mapped below as the concrete,
> in-scope analogs.

## Q1: What is the canonical on-disk directory structure for an agentskills.io-standard skill (the `SKILL.md` plus `references/`, `scripts/`, `assets/` layout), and where in this repo are skills expected to live?

**Answer:** The canonical agentskills.io structure itself is defined in the global
`skill-creator` skill, which is **NOT in scope**. What IS in the repo: skills live under
`.claude/skills/<skill-name>/`, each containing a `SKILL.md`. The skill→agent split convention
is documented in `.claude/CLAUDE.md`: *"Phase agent definitions live in `.claude/agents/`; their
slash-command wrappers live in `.claude/skills/`."* Of the 10 in-repo skills, only `qrspi-work`
uses a `references/` subdirectory; **no skill uses `scripts/` or `assets/` subdirectories** (none
exist anywhere under `.claude/skills/`). Observed layout:

**Evidence:**

```
.claude/skills/
  qrspi-work/
    SKILL.md
    references/
      review-cascade.md      # the only references/ dir in the repo
  qrspi-research/
    SKILL.md                 # all other skills: SKILL.md only, no subdirs
  ... (8 more *-only skills)
.claude/agents/
  qrspi-research.md          # the agent body the thin skill wrapper spawns
  ... (7 more)
```

— `.claude/skills/` (directory listing); `.claude/skills/qrspi-work/references/review-cascade.md`
— `.claude/CLAUDE.md` (Codebase conventions: skills vs agents split)
**Dependencies:** skill wrappers (`.claude/skills/*/SKILL.md`) depend downstream on agent bodies (`.claude/agents/*.md`) via `subagent_type`.
**Implicit contracts:** A skill directory is named for the skill; its entry file is exactly `SKILL.md`; `references/` files are siblings of `SKILL.md` and referenced by relative path (`references/<file>.md`). No in-repo skill demonstrates `scripts/` or `assets/`.

## Q2: How does the Anthropic skill-builder skill ingest a specification and emit the generated skill files — what inputs does it read and what files does it produce on disk?

**Answer:** **NOT FOUND — the question targets a resource outside the project scope.** The
`skill-creator`/`skill-builder` skill is a global plugin skill; no copy of it exists under
`REPO_ROOT`. The only in-repo references to it are textual mentions, not the skill's
implementation: `questions.md` and `.claude/agents/qrspi-structure.md:40` (which merely says
*"Validation passes (linting, running a review tool, invoking skill-creator) are the final step
of the slice…"*). Searches run: `find . -iname '*skill-creator*'` (no hits), `grep -rli
'skill-creator\|skill-builder'` (hits only in `questions.md` and `qrspi-structure.md`).
**Dependencies:** N/A (out of scope).
**Implicit contracts:** N/A.

## Q3: How are `references/` files referenced from a `SKILL.md` body so an agent loads them on demand rather than inline (the progressive-disclosure mechanism)?

**Answer:** The repo demonstrates the on-demand reference pattern in exactly one place:
`qrspi-work/SKILL.md` points the agent to a sibling reference file by **relative path inside
prose**, so the file is only opened when that code path is reached (progressive disclosure by
convention, not by an enforced loader). There is no in-repo loader/validator that parses these
links — the mechanism is purely the agent following the instruction to read the named file.

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`
**Dependencies:** `qrspi-work/SKILL.md` → `qrspi-work/references/review-cascade.md` (the referenced file exists).
**Implicit contracts:** The reference is a relative path (`references/<name>.md`) resolved against the skill directory; the body names the file in context ("see `references/…`") rather than inlining its content. No automated check verifies the link target exists.

## Q4: What frontmatter fields does a valid `SKILL.md` require (name, description, and any others), and what are the format constraints on each?

**Answer:** The formal field spec lives in the out-of-scope `skill-creator`. **In-repo
observation:** all 10 `SKILL.md` files use an identical YAML frontmatter field set —
`name`, `description`, `command`, `argument-hint`, `allowed-tools` (each appears in 10/10
files). `description` may be a bare scalar or a double-quoted string (quoted when it contains
trigger-phrase punctuation, e.g. `qrspi-work`). `allowed-tools` is a comma-separated tool list,
sometimes scoped (e.g. `Bash(pwd:*)`).

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
**Dependencies:** `command` value (e.g. `/qrspi-research`) is the slash-command alias; `name` matches the directory and the `subagent_type` the wrapper spawns.
**Implicit contracts:** Frontmatter is delimited by `---` lines; `name` equals the containing directory name; `command` is `/<name>`; `argument-hint` describes positional args; `allowed-tools` gates the wrapper's tool access (the `qrspi-work` body relies on `allowed-tools` including the Linear MCP tools it calls). The repo's wrappers are thin and consistently use these five fields — additional standard fields the global skill-creator may require are not represented here.

## Q5: What is the enforced size limit for a `SKILL.md` body, and how is the "under 500 lines / 5000 tokens" acceptance criterion measured or validated in this repo?

**Answer:** **No in-repo mechanism enforces a SKILL.md size limit.** Searches for a skill-size
validator (`grep -rli '500 lines\|5000 token\|wc -l'` in `scripts/`) found only `scripts/grade.py`,
whose `line_count()` check applies to **QRSPI workflow artifacts** (e.g. `design.md <= 300`), not
to `SKILL.md`. The "under 500 lines / 5000 tokens" rule is a convention from the out-of-scope
skill-creator. For reference, current in-repo SKILL.md sizes: nine are 25–35 lines; `qrspi-ticket`
is 127; `qrspi-work` is **565 lines** — already over a 500-line guideline, with no check flagging it.

**Evidence:**

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    ...
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:35-40` (used by eval `case_005`: `line_count('design.md') <= 300`, not SKILL.md)
— SKILL.md line counts: `wc -l .claude/skills/*/SKILL.md` → qrspi-work 565, qrspi-ticket 127, rest 25–35
**Dependencies:** `grade.py` is consumed by the eval harness (`evals/suite.json` assertions of type `programmatic`).
**Implicit contracts:** Size limits on SKILL bodies are unenforced here; the only line-count gate is on phase artifacts via the placeholder eval harness (see Q12).

## Q6: How is the `description` field used to trigger auto-invocation of a skill, and what wording patterns make a skill reliably trigger versus not?

**Answer:** The triggering/auto-invocation machinery is the harness's, not the repo's — and the
description-optimization guidance lives in the out-of-scope skill-creator (**NOT FOUND** for the
guidance itself). **In-repo evidence of the pattern in use:** the most trigger-engineered
description in the repo is `qrspi-work`'s, which encodes (a) a capability summary, (b) an explicit
"Use when…" clause, and (c) literal example phrasings the user might type. This is the observable
"reliable trigger" wording pattern the repo models, but nothing in the repo *measures* trigger reliability.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user
asks to 'work on' a ticket (e.g., 'work on RUS-42'). … Trigger on any variant of:
'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to
progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`
**Dependencies:** Auto-invocation is resolved by the Claude Code harness (external); the repo only supplies the `description` text.
**Implicit contracts:** Effective descriptions pair a "Use when…/Trigger on…" clause with concrete example user phrasings; quoting is used when the description embeds such phrases.

## Q7: Are example asset files stored under `assets/` and copied verbatim, or rendered/templated at skill-build time?

**Answer:** **No `assets/` directory exists anywhere in the repo** (`find . -type d -name assets`
returns nothing). The repo therefore has no in-scope example of asset handling — verbatim-copy vs.
templated is a property of the out-of-scope skill-creator. The closest in-repo analog is the
QRSPI **template** mechanism: artifact templates live in `.qrspi/templates/` and are documented as
"reference only — not written locally" — i.e. read as scaffolding, not copied into the deliverable.
That is template *reading*, not skill-asset bundling. **NOT FOUND** for the asset-handling answer proper.

— `.qrspi/templates/` (templates exist, e.g. `research.md`); `.claude/CLAUDE.md` ("Artifact templates live in `.qrspi/templates/` (reference only — not written locally)")
— `find . -type d -name assets` → (no results)
**Dependencies:** N/A.
**Implicit contracts:** N/A (no asset bundling pattern present).

## Q8: How should the skill encode deprecation awareness (`vars` → `replacements`, `patchesStrategicMerge`/`patchesJson6902` → `patches:`) so an agent prefers the current field without breaking on legacy repos?

**Answer:** **NOT FOUND — the question targets a resource outside the project scope.** This is
kustomize reference content; no kustomize material exists in the repo. Search: `grep -rli
'kustomize\|replacements\|patchesStrategicMerge'` → matches only `questions.md`.
**Dependencies:** N/A. **Implicit contracts:** N/A.

## Q9: How is a `secretGenerator` referencing uncommitted `.env` files represented in skill examples without leaking secrets or committing the `.env` files?

**Answer:** **NOT FOUND — outside project scope** for the kustomize `secretGenerator` content.
**Tangentially relevant in-repo fact:** the repo already follows the "config in a gitignored file,
ship an example template" pattern that the kustomize answer would mirror — `.qrspi/config.json` is
gitignored and a committed `.qrspi/config.example.json` documents its shape (per `.claude/CLAUDE.md`
"Codebase conventions": *"Source: `.qrspi/config.json` (gitignored; see `.qrspi/config.example.json`)"*).
The same `.gitignore` + `*.example` convention is the in-repo precedent for representing
secret-bearing config without committing it. The kustomize-specific representation itself is out of scope.

— `.claude/CLAUDE.md` (config.json gitignored, config.example.json committed); `git status` shows `.qrspi/config.example.json` tracked and `.env` present-but-not-the-template
**Dependencies:** N/A to kustomize. **Implicit contracts:** repo precedent = gitignore the real secret-bearing file, commit a `*.example` sibling.

## Q10: What does the skill prescribe when `commonLabels` would inject into a Deployment selector and break a rolling update — the transformer-vs-commonLabels decision boundary?

**Answer:** **NOT FOUND — outside project scope.** Kustomize transformer/commonLabels content does
not exist in the repo. Search: `grep -rli 'commonLabels\|transformer\|rolling update'` → no hits
outside `questions.md`.
**Dependencies:** N/A. **Implicit contracts:** N/A.

## Q11: How should the decision framework distinguish strategic merge patch from JSON 6902 patch for ambiguous cases (removing a field, replacing an array item by index)?

**Answer:** **NOT FOUND — outside project scope.** Kustomize patch-type content does not exist in
the repo. Search: `grep -rli 'JSON 6902\|strategic merge\|patchesJson6902'` → no hits outside
`questions.md`.
**Dependencies:** N/A. **Implicit contracts:** N/A.

## Q12: How are skills validated or evaluated in this repo (does the skill-creator eval loop apply), and what constitutes a passing check?

**Answer:** The repo has an eval harness — `evals/suite.json` (15 cases) + `scripts/run_eval.py`
(runner) + `scripts/grade.py` (assertion checks) — BUT it is a **documented non-functional
placeholder**: `run_eval.py`'s `execute_single()` does not invoke any agent; it returns empty
output and notes *"This stub captures the structure for integration with the actual agent runtime."*
`.claude/CLAUDE.md` states this explicitly: *"The `evals/` + `scripts/run_eval.py` harness is a
**non-functional placeholder** — verify pure logic with the unit tests and orchestration changes
with manual end-to-end runs."* Notably, **every eval case targets a QRSPI phase** (`questions`,
`research`, `design`, `structure`, `plan`, `worktree`, `implement`, `pr`) — there is **no eval case
for a generic/new skill**, and the skill-creator eval loop is out of scope (not in repo). A "passing
check" is therefore defined only for QRSPI phase artifacts, via weighted `programmatic`/`script`/
`llm_judge` assertions in `suite.json` graded by `grade.py`.

**Evidence:**

```python
    """Execute a single trial of a single test case.
    In a real implementation, this would:
    1. Spin up an isolated container/sandbox
    ...
    This stub captures the structure for integration with
    the actual agent runtime.
    """
    ...
        # ── Placeholder for agent execution ──
        result.output = ""
        result.files = []
```

— `scripts/run_eval.py:99-134`; `evals/suite.json` (15 cases, all QRSPI phases); `scripts/grade.py:21-90`
— `.claude/CLAUDE.md` (eval harness = non-functional placeholder)
**Dependencies:** `suite.json` assertions → `grade.py` check functions; `run_eval.py` → `load_suite()`/`load_skill()`/`build_messages()` (real) but `execute_single()` (stub).
**Implicit contracts:** Validation of *this repo's* skills is done via stdlib `_test.py` unit tests (`scripts/qrspi_*_test.py`) for pure logic + manual e2e runs, NOT via the eval harness. The skill-creator eval loop the question references is external.

## Q13: What CI validation patterns for kustomize output (`kustomize build` per overlay, `kubeconform`, `conftest`/OPA) should the references document, and is there an existing pipeline format to mirror?

**Answer:** **NOT FOUND — outside project scope** for the kustomize CI content. **In-repo CI
artifacts:** there is **no `.github/workflows/` directory** and no `kubeconform`/`conftest`
reference. The only "pipeline-like" runnable in the repo is `run_loop.sh` (a top-level shell driver)
and the placeholder eval harness; neither is a kustomize CI example to mirror. Search:
`grep -rli 'kubeconform\|conftest\|kustomize build'` → no hits outside `questions.md`; `find .
-path '*/.github/workflows/*'` → none.
**Dependencies:** N/A to kustomize. **Implicit contracts:** N/A.

## Q14: What signals should the skill instruct an agent to surface when `kustomize build` fails on an overlay so failures are diagnosable in CI logs?

**Answer:** **NOT FOUND — outside project scope** for the kustomize build-failure content.
**Relevant in-repo failure-reporting precedent** (the pattern such content would mirror): the
repo's agents are governed by a strict **"surface the exact error verbatim and STOP"** doctrine —
`.claude/skills/qrspi-work/SKILL.md:547-564` ("HARD STOP: Infrastructure Errors Are Not Puzzles To
Solve") mandates printing *"the exact error verbatim — the failing command and full output,
unmodified"*; and `scripts/diagnose.py` exists as a diagnostic helper. So the in-repo norm for
"diagnosable failure signals" is: identify the failing command + its full stderr, do not paraphrase,
do not work around. The kustomize-specific signal list (which overlay/resource/stderr) is itself out of scope.

**Evidence:**

```
2. **Print the exact error verbatim** — the failing command and full output, unmodified.
```

— `.claude/skills/qrspi-work/SKILL.md:554`; `scripts/diagnose.py` (present)
**Dependencies:** N/A to kustomize. **Implicit contracts:** repo-wide error doctrine = verbatim command + full stderr, then stop.

---

## Discovered Patterns

- **Skill = thin wrapper + heavy agent body.** Each `.claude/skills/<name>/SKILL.md` is a thin
  slash-command shell that spawns a `subagent_type` of the same name; the real prompt lives in
  `.claude/agents/<name>.md`. `qrspi-research/SKILL.md:9-11` states this verbatim ("Thin wrapper
  that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`").
  Exception: `qrspi-work` carries its full logic in the SKILL.md itself (565 lines, no separate agent body).
- **Uniform five-field frontmatter** across all 10 skills (`name`, `description`, `command`,
  `argument-hint`, `allowed-tools`) — a strong house convention for any new skill to follow.
- **Config-by-gitignored-file + committed `*.example`.** `.qrspi/config.json` (gitignored) ↔
  `.qrspi/config.example.json` (committed). This is the repo's secret/config handling precedent
  (relevant to Q9's secretGenerator analog).
- **Determinism + staging doctrine.** Phase artifacts are written to a token-free staging path and
  moved deterministically by `scripts/qrspi_persist.py` (Fix A); orchestration logic is centralized
  in self-locating Python scripts with stdlib `_test.py` siblings. New automation in this repo is
  expected to be a tested, self-locating script, not inline shell.
- **Verbatim-error / HARD-STOP doctrine** is repeated across agents (`qrspi-work/SKILL.md` and this
  research agent's own prompt): infrastructure errors are never "solved" with workarounds.
- **Eval harness is structurally complete but inert.** `suite.json` + `grade.py` are real and
  detailed; `run_eval.py::execute_single` is an explicit stub. Real verification = unit tests + manual e2e.

## Inconsistencies

- **Documentation vs. code (size convention):** the skill-authoring convention referenced by the
  questions ("SKILL.md under 500 lines") is contradicted in-repo — `qrspi-work/SKILL.md` is **565
  lines**, with no validator catching it. The repo has no enforcement of any SKILL.md size limit
  (the only `line_count` gate in `grade.py` targets `design.md <= 300`, an unrelated artifact).
- **Question targets vs. repo contents:** Q2–Q14 target the `skill-creator` skill and kustomize
  reference content as if they were in-repo modules; 6 of them (Q2, Q8, Q9, Q10, Q11, Q13, partially
  Q14, Q7) resolve to material that does not exist under `REPO_ROOT`. The `skill-creator` skill is
  available to the harness as a **global plugin** but is intentionally **outside the project scope**
  this research is allowed to read.
- **`references/` convention is asserted but barely exercised:** the skill→references progressive-disclosure
  pattern (Q3) appears in exactly **one** file (`qrspi-work/references/review-cascade.md`); 9 of 10
  skills have no `references/` at all, so the repo provides a single, thin example rather than an
  established multi-skill convention. `scripts/`- and `assets/`-style skill subdirectories have **zero**
  in-repo examples.
- **Eval harness scope gap:** `evals/suite.json` covers only the 8 QRSPI phases; there is no eval
  case (and no grading support in `grade.py`) for a generic/new skill such as a kustomize-CLI skill,
  so "validate the new skill via the eval loop" (Q12) has no working path in this repo today.
