# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

> Scope note: `skill-creator` and the `agentskills.io` standard referenced by several
> questions are **global** Claude Code assets installed outside `REPO_ROOT`
> (`/workspaces/qrspi/.worktrees/RUS-26`). Per the research firewall they are out of scope
> and were not read. Where a question targets them, the answer reports what the **repo's own
> skills** demonstrate as the de-facto local convention instead, and flags the global
> resource as NOT FOUND in-repo.

## Q1: What inputs does the skill-creator skill expect (skill name, description, target directory) and what files does it emit when generating a new skill?

**Answer:** NOT FOUND in-repo. There is no `skill-creator` skill anywhere under `REPO_ROOT`.
`find . -iname "*skill-creator*"` returns nothing; the only skills present are the ten
`qrspi-*` skills under `.claude/skills/`. `skill-creator` is a global Claude Code skill
installed outside the repo (e.g. `~/.claude/skills/`), which the firewall forbids reading.

What the repo *does* show is the on-disk shape every generated skill must take (see Q2): a
directory `.claude/skills/<name>/` whose required file is `SKILL.md`, optionally with a
`references/` subdirectory. No repo code generates skills; they are authored by hand.
**Evidence:**

```
$ find .claude/skills -maxdepth 3 -type f
.claude/skills/qrspi-design/SKILL.md
...
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing)
**Dependencies:** none in-repo; the generator lives in the global Claude Code install.
**Implicit contracts:** a skill = a directory named for the skill containing a `SKILL.md`.

## Q2: Where do existing skills in this repo place their generated SKILL.md and supporting directories, and what is the on-disk layout the new PRD skill must match?

**Answer:** Each skill lives at `.claude/skills/<skill-name>/SKILL.md`. The directory name
equals the skill's `name` frontmatter field. Only `SKILL.md` is required; supporting content
goes in a `references/` subdirectory. In this repo **only** `qrspi-work` uses a supporting
dir (`references/review-cascade.md`); no skill currently uses `scripts/` or `assets/`
subdirectories — those are part of the broader agentskills layout but are unused here.
Phase agent *prompt bodies* live separately under `.claude/agents/qrspi-<phase>.md`, and the
SKILL.md acts as a thin wrapper that spawns the agent (see Q5).
**Evidence:**

```
.claude/skills/qrspi-work/
  SKILL.md
  references/
    review-cascade.md
```

— `.claude/skills/qrspi-work/` (listing)
**Dependencies:** `.claude/agents/` (agent prompt bodies the wrappers spawn).
**Implicit contracts:** dir name == `name` field; `SKILL.md` is the single required file;
overflow content goes under `references/`.

## Q3: What frontmatter fields and format does the agentskills.io standard require in SKILL.md, and how do existing repo skills populate them?

**Answer:** The agentskills.io standard itself is out of scope (not in-repo). The **repo
convention**, observed across all ten skills, is YAML frontmatter delimited by `---` with
these fields: `name`, `description`, `command` (slash-command form, e.g. `/qrspi-research`),
`argument-hint` (e.g. `<ticket-id>`), and `allowed-tools` (comma-separated tool allowlist).
`name` and `description` appear in every skill; `command`/`argument-hint`/`allowed-tools`
appear in the nine workflow skills. `qrspi-ticket` and `qrspi-work` use `allowed-tools` but
the same five-field shape. A multi-line `description` is quoted (`qrspi-work` wraps it in
double quotes; others use unquoted single-line scalars).
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
**Dependencies:** Claude Code's skill loader (global) parses this frontmatter.
**Implicit contracts:** `allowed-tools` gates capability — e.g. omitting `Glob/Grep/Bash`
structurally prevents codebase exploration (the "questions firewall", see
`.claude/skills/qrspi-work/SKILL.md:450-453`); `name` must match the directory name.

## Q4: How is a skill's `description` field written so the skill triggers correctly, and what wording conventions do existing skills use?

**Answer:** Descriptions follow a two-part pattern: **(1) what the skill does** (imperative,
one clause) **+ (2) when to use it** ("Use after research is approved", "Use when the user
asks to 'work on' a ticket"). The richest example is `qrspi-work`, which adds explicit
**trigger phrasings** in the description: "Trigger on any variant of: 'work on <ticket-id>',
'continue <ticket-id>', 'pick up <ticket-id>'…". Shorter skills give a single "Use when…"
sentence. The trigger cues live in the `description` itself, not a separate field.
**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user
asks to 'work on' a ticket (e.g., 'work on RUS-42')... Trigger on any variant of:
'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to
progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`
**Dependencies:** the global skill router matches user intent against `description`.
**Implicit contracts:** concrete trigger phrases + a "Use when" clause improve match accuracy;
quote the scalar when it spans clauses/newlines.

## Q5: How does the slash-command wrapper relate to the skill definition, and does a SKILL.md-only skill need a separate wrapper in this repo's convention?

**Answer:** In this repo the `SKILL.md` **is** the slash-command wrapper. For the QRSPI phase
skills, `SKILL.md` is a *thin wrapper* whose body just parses `$ARGUMENTS`, resolves paths,
and spawns a sibling agent via the `Agent` tool (`subagent_type: qrspi-<phase>`); all real
prompt logic lives in `.claude/agents/qrspi-<phase>.md`. Two skills break this split and put
the **full logic inline** in SKILL.md with no separate agent: `qrspi-ticket` (119 lines,
guided-conversation author) and `qrspi-work` (565 lines, orchestrator). So a SKILL.md-only
skill needs **no** separate wrapper — the SKILL.md self-contains the behavior. A new PRD
skill that is a single interactive author (like `qrspi-ticket`) would be SKILL.md-only with
no `.claude/agents/` file.
**Evidence:**

```
# /qrspi-research
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in
`.claude/agents/qrspi-research.md`.
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
...
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

— `.claude/skills/qrspi-research/SKILL.md:9-18`
**Dependencies:** wrapper → `.claude/agents/qrspi-*.md` (only for the spawning skills).
**Implicit contracts:** spawning skills declare `Agent` in `allowed-tools`; inline skills
(`qrspi-ticket`) declare the concrete tools they use (`Read, Glob, Grep, Write, Bash, …`).

## Q6: What constitutes the "default lean one-pager" vs "expanded multi-section" format, and how would the skill encode both so the agent selects between them?

**Answer:** NOT FOUND — no existing skill or template in-repo encodes a dual lean/expanded
output format; this distinction is specific to the requested PRD feature and has no
precedent here. The **closest analog** is `qrspi-ticket`, which encodes a single fixed
output skeleton inline in the SKILL.md body (Title / Description{Context, Goal, Why Now} /
Acceptance Criteria / Constraints / Out of Scope) and reads `.qrspi/templates/ticket.md` as
the "single source of truth" for layout. The repo pattern for "let the agent select" is
**prose instructions + an inline skeleton**, not a code branch — e.g. `qrspi-ticket`'s
conversation rules tell the agent when to ask vs. infer. A PRD skill would similarly describe
both formats in prose and present the skeleton(s) inline or in `references/`.
**Evidence:**

```
Then present the full draft inline, following the structure from `.qrspi/templates/ticket.md`:
```
... (inline skeleton block) ...

— `.claude/skills/qrspi-ticket/SKILL.md:69-98`
**Dependencies:** templates under `.qrspi/templates/` as layout source-of-truth.
**Implicit contracts:** output format is conveyed by an inline skeleton + prose selection
rules; format selection is a model decision, not deterministic code.

## Q7: Which content belongs in the SKILL.md body vs the references/ directory, given the 500-line / 5000-token cap on the body?

**Answer:** The repo's de-facto rule: the SKILL.md body holds the **primary, always-needed**
procedure; **bulky conditional detail** moves to `references/`. The only worked example is
`qrspi-work`, which keeps its state-machine/dispatch logic in the body but factors the
two-scope cascade explanation into `references/review-cascade.md`, referenced by path
("see `references/review-cascade.md`", `.claude/skills/qrspi-work/SKILL.md:282`). Most phase
wrappers are tiny (25-35 lines) because their detail lives in `.claude/agents/`. Note the
**500-line cap is currently violated**: `qrspi-work/SKILL.md` is **565 lines** (see
Inconsistencies) — the only in-repo data point on the cap shows it can be exceeded, and that
overflow content (e.g. the Git/Graphite rules, error-handling appendices) is exactly the kind
that belongs in `references/`.
**Evidence:**

```
$ wc -l .claude/skills/qrspi-work/SKILL.md
565 .claude/skills/qrspi-work/SKILL.md
```
```
... a design-level change ... is handled by `reset`, not revise. (see `references/review-cascade.md`)
```

— `.claude/skills/qrspi-work/SKILL.md:282`; `wc -l` output
**Dependencies:** body → `references/*.md` by relative path.
**Implicit contracts:** reference files are pulled in on demand; the body must stand alone for
the common path. No tooling enforces the cap (Q12).

## Q8: How should the skill behave when the user's problem statement lacks supporting evidence — what clarifying-question behavior enforces problem-first validation before solution specification?

**Answer:** The strongest in-repo precedent is `qrspi-ticket`'s conversation discipline,
which is exactly a problem-first / no-solution-yet guard. Its rules: restate understanding
first; ask the most important unanswered question first; never ask more than 2 at once; don't
ask what can be inferred; and — critically — **redirect any premature solution back to the
problem**: "That sounds like it belongs in the Design phase — for now, what problem does that
solve?" It also bans solution content from the output ("Anti-patterns — do NOT include").
A PRD skill enforcing problem-first validation would mirror this: ask clarifying questions
until the problem is evidenced, and refuse to specify solution detail before then.
**Evidence:**

```
2. Ask the most important unanswered question first. Never ask more than 2 questions at once.
...
5. If the user provides implementation details, redirect: "That sounds like it belongs in
   the Design phase — for now, what problem does that solve?"
```

— `.claude/skills/qrspi-ticket/SKILL.md:43-48`
**Dependencies:** none (inline behavioral rules).
**Implicit contracts:** clarifying questions are throttled (≤2 at a time) and gate progress;
solution content is actively redirected, not just discouraged.

## Q9: How is the mandatory non-goals section enforced, and what happens when a generated PRD would omit it?

**Answer:** NOT FOUND as a PRD-specific mechanism, but the repo has a direct analog: the
**"Out of Scope"** section is mandatory in the ticket pipeline. The ticket template always
includes an `## Out of Scope` block (with "or 'None'" fallback), and `qrspi-ticket` lists it
as a required field with the same "may be none" allowance. Enforcement is via (a) the
template always carrying the section and (b) the skill's required-field checklist + a
self-review gate before output. There is no automated validator that rejects a missing
section — enforcement is prompt-level (the skill is instructed to include it and self-review).
**Evidence:**

```
## Out of Scope
- <explicitly excluded work, or "None">
```

— `.qrspi/templates/ticket.md:30-32`; required-field list at `.claude/skills/qrspi-ticket/SKILL.md:39`
**Dependencies:** template (`.qrspi/templates/ticket.md`) as the section source-of-truth.
**Implicit contracts:** mandatory sections are kept present by always emitting them with an
explicit "None" fallback rather than dropping them when empty; enforcement is by self-review,
not code.

## Q10: How does the skill distinguish outcome-oriented goals from output-oriented ones, and what guidance catches a goal stated as an output?

**Answer:** This exact distinction is a core, explicit rule in `qrspi-ticket`. Acceptance
Criteria "must describe what success looks like, not how to implement it," with a concrete
contrastive example: **"Users can authenticate via SSO" not "Skill covers SSO in the
Authentication section."** The skill adds a self-review gate that catches output-leakage:
"Could someone who doesn't know the solution understand what success looks like from this
ticket alone?… If understanding the ticket requires implementation knowledge, it has leaked
solution content. Revise." A PRD skill's goal/non-goal guidance can adopt this same
outcome-vs-output contrast and self-review test verbatim.
**Evidence:**

```
- **Acceptance Criteria** — outcomes observable by a user or stakeholder (minimum 2). Must
  describe what success looks like, not how to implement it. "Users can authenticate via SSO"
  not "Skill covers SSO in the Authentication section."
```

— `.claude/skills/qrspi-ticket/SKILL.md:37`; self-review gate at `:63-67`
**Dependencies:** none (inline rule + self-review).
**Implicit contracts:** goals are validated by an inline contrastive example + a "could a
solution-blind reader understand success?" self-test; failures trigger a revise loop.

## Q11: How is a SKILL.md authoring task verified in this repo — does skill-creator provide an eval loop, and what is the status of the evals/ + scripts/run_eval.py harness?

**Answer:** `scripts/run_eval.py` exists and is structured (loads a suite JSON, fans out
cases × trials over a thread pool, writes `results.json`) but its actual agent execution is a
**non-functional placeholder**: `execute_single` returns empty output and zeroed tokens, with
a comment block ("In a real implementation, this would… Replace this block with actual agent
invocation"). The `evals/` dir holds a `suite.json`, `graphite-evals.json`, ticket fixtures,
and an empty `golden/.gitkeep` — fixtures but no working runner. `skill-creator`'s own eval
loop is global/out of scope (NOT FOUND in-repo). The repo's real verification is **stdlib
unit tests** (`scripts/qrspi_*_test.py`) for logic and **manual end-to-end runs** for
orchestration — confirmed by the project CLAUDE.md convention note.
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

— `scripts/run_eval.py:111-133`; `.claude/CLAUDE.md` ("evals/ … is a non-functional placeholder")
**Dependencies:** `evals/suite.json`, `evals/fixtures/*`; sibling `_test.py` files for real tests.
**Implicit contracts:** verify pure logic with `_test.py`; treat run_eval.py output as a stub.

## Q12: What checks confirm the SKILL.md body stays under 500 lines / 5000 tokens and that frontmatter is valid against the agentskills.io standard?

**Answer:** NOT FOUND — there is **no in-repo tooling** that validates SKILL.md line count,
token count, or frontmatter. Searches for `frontmatter`, `yaml`, `500`, `5000`, and `wc -l`
across `scripts/*.py` returned no matches. `scripts/check_scope.py` validates implementation
file scope (which files an implement agent touched), not SKILL.md size or frontmatter. No
pre-commit, CI, or linter for skills exists under `REPO_ROOT`. The cap is therefore a prose
convention only — and is already violated by `qrspi-work/SKILL.md` at 565 lines (Q7,
Inconsistencies). Validation against the agentskills.io standard, if any, would come from the
global tooling, which is out of scope.
**Evidence:**

```
$ grep -rsin -e "frontmatter" -e "yaml" -e "500" -e "5000" -e "wc -l" scripts/*.py
(no output)
```

— grep across `scripts/*.py`
**Dependencies:** none.
**Implicit contracts:** size/frontmatter conformance is unenforced by code; authors must
self-check.

## Q13: What metadata or status markers should generated PRDs carry, and how would the skill instruct the agent to populate and update them so PRD state is traceable?

**Answer:** No PRD template exists, but every QRSPI **artifact template** carries a metadata
header with a `**Status:**` marker enumerating its lifecycle, and most include a generated
timestamp and a source pointer. The status vocabularies vary per artifact:
`draft | human-reviewed | approved` (research, questions), `draft | revision-N | approved`
(design — note the explicit revision counter), `draft | approved` (structure, plan, worktree).
The research template header is the canonical shape: a source line, a generated ISO-8601
timestamp, and a Status line. There is **no changelog or numeric `version` field** in any
template (the closest is design's `revision-N`). A PRD skill should follow this header
convention: a Status marker with an enumerated vocabulary (e.g. Draft / In Review / Approved),
a timestamp, and a source/reference line, and instruct the agent to bump Status as the PRD
advances.
**Evidence:**

```
**Questions source:** questions.md @ <timestamp>
**Generated:** <ISO-8601 timestamp>
**Status:** draft | human-reviewed | approved
```

— `.qrspi/templates/research.md:3-5`; design's revision counter at `.qrspi/templates/design.md:6`
**Dependencies:** templates under `.qrspi/templates/`.
**Implicit contracts:** artifacts open with a metadata header; Status is a constrained
enumeration; ISO-8601 timestamps; design uniquely tracks `revision-N` but no template has a
changelog or semver version.

---

## Discovered Patterns

- **Wrapper-vs-agent split:** QRSPI phase skills are thin SKILL.md wrappers
  (`Agent`-only `allowed-tools`, ~25-35 lines) that spawn a sibling prompt body in
  `.claude/agents/qrspi-<phase>.md`. Two skills (`qrspi-ticket`, `qrspi-work`) instead inline
  their full logic in SKILL.md — the model for a self-contained, no-agent skill like a PRD
  author. (`.claude/skills/*/SKILL.md`, `.claude/agents/*.md`)
- **Capability gating via `allowed-tools`:** firewalls are enforced structurally by omitting
  tools (e.g. questions agent excludes `Glob/Grep/Bash`; research agent excludes Linear MCP),
  not just by instruction. (`.claude/skills/qrspi-work/SKILL.md:422-453`)
- **Templates are the layout source-of-truth:** skills read `.qrspi/templates/<artifact>.md`
  at draft time and reproduce its skeleton inline; templates are reference-only and not
  written to disk by the skill. (`.claude/skills/qrspi-ticket/SKILL.md:28,69`)
- **Metadata header convention:** every artifact template opens with a source line, a
  generated ISO-8601 timestamp, and a `**Status:**` enumeration. (`.qrspi/templates/*.md`)
- **Problem-first / outcome-over-output discipline** is already codified in `qrspi-ticket`
  (clarifying-question throttling, solution redirection, outcome-vs-output contrast, a
  solution-blind self-review gate) — directly reusable for a PRD skill.
  (`.claude/skills/qrspi-ticket/SKILL.md:43-67`)
- **Verification = stdlib unit tests + manual e2e**, not the eval harness, which is a stub.
  (`scripts/qrspi_*_test.py`, `scripts/run_eval.py:111`)
- **`references/` overflow pattern:** only `qrspi-work` uses it, factoring bulky conditional
  logic out of the body. No skill uses `scripts/` or `assets/` subdirectories.

## Inconsistencies

- **500-line cap is already violated in-repo.** Q7/Q12 reference a 500-line / 5000-token
  SKILL.md body cap, but `.claude/skills/qrspi-work/SKILL.md` is **565 lines** — and nothing
  enforces the cap (no validator found, Q12). The repo both states a convention (project
  CLAUDE.md / questions) and ships a counterexample.
- **Two structural conventions for skills coexist.** Most skills are thin wrappers delegating
  to `.claude/agents/`; `qrspi-ticket` and `qrspi-work` inline everything. A new skill author
  must choose, and the questions assume a SKILL.md-centric model (Q5-Q10) which matches the
  inline `qrspi-ticket` style, not the wrapper style.
- **`description` quoting is inconsistent.** `qrspi-work`'s multi-clause description is double-
  quoted; all others use unquoted scalars. No documented rule on when quoting is required.
- **Status vocabularies diverge per artifact.** `draft | human-reviewed | approved` (research,
  questions) vs `draft | approved` (structure, plan, worktree) vs `draft | revision-N |
  approved` (design). No single canonical status enumeration; the questions' suggested
  "Draft / In Review / Approved" (Q13) matches none of the existing templates exactly.
- **No `version`/changelog anywhere.** Q13 asks about version + changelog metadata; the repo's
  templates carry only a Status marker (and design's `revision-N`), with no semver version
  field or changelog section — so that part of Q13 has no in-repo precedent.
- **Several question targets are global/out-of-repo** (`skill-creator`, the `agentskills.io`
  standard). The questions phrase them as if local; in fact they are installed outside
  `REPO_ROOT` and are NOT FOUND in-repo (Q1, Q3, Q11, Q12).
