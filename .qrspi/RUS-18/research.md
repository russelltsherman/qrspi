# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Q1: What is the on-disk directory layout an agentskills.io skill is expected to occupy in this repo, and where do new skills get created relative to `.claude/skills/` and any agent definitions in `.claude/agents/`?

**Answer:** Each skill is a directory under `.claude/skills/<skill-name>/` whose entry point is a `SKILL.md` file. The directory name matches the `name:` frontmatter field and the slash command (e.g. `.claude/skills/qrspi-research/` → `name: qrspi-research` → `/qrspi-research`). There are 10 skill directories, each containing exactly one `SKILL.md`; only `qrspi-work` also contains a subdirectory (`references/`).

In this repo there is a documented split of responsibility unique to the QRSPI pattern: the **slash-command wrapper** lives in `.claude/skills/<name>/SKILL.md` (a thin shell that spawns an agent) while the **heavyweight phase logic** lives in a sibling file `.claude/agents/<name>.md` (flat `.md` files, not directories). This split is explicit in CLAUDE.md: "Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`". Note this agent/skill split is a QRSPI-specific convention, not a general agentskills.io requirement — a self-contained skill (like `qrspi-work` or `qrspi-ticket`) keeps all its logic in `SKILL.md` with no agent counterpart.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   <- only subdir in any skill
.claude/agents/qrspi-design.md                            <- agent counterpart (flat .md)
.claude/agents/qrspi-research.md
```

— `.claude/skills/` (directory listing) and `.claude/agents/` (directory listing)

```
- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
```

— `.claude/CLAUDE.md` ("Codebase conventions" bullet)

**Dependencies:** A wrapper SKILL.md (e.g. `qrspi-research/SKILL.md`) depends on its agent definition `.claude/agents/qrspi-research.md` via the `Agent` tool (`subagent_type: qrspi-research`). Discovery is by Claude Code scanning `.claude/skills/*/SKILL.md`.
**Implicit contracts:** Directory name == frontmatter `name` == slash command (minus leading `/`). One `SKILL.md` per directory. `references/` / `scripts/` / `assets/` are optional sibling subdirectories of `SKILL.md`. A "phase" skill is thin and delegates to a matching `.claude/agents/<name>.md`; a standalone skill is self-contained.

## Q2: How does an existing skill split content between the top-level `SKILL.md` body and the `references/`, `scripts/`, and `assets/` subdirectories, and how does the body point an agent to the reference files?

**Answer:** Exactly one skill in this repo uses a subdirectory: `qrspi-work`, which has `references/review-cascade.md`. There are NO `scripts/` or `assets/` subdirectories inside any skill (a repo-wide find returned none). The pattern in `qrspi-work` is: keep the always-needed orchestration logic inline in `SKILL.md`, and push detailed, conditionally-needed reference material (the full cascade decision tables for the manual `revise` path) into `references/review-cascade.md`. The body points to it with a relative path mention in prose, not a tool call:

**Evidence:**

```
Address feedback **within this phase only** — the cascade is bounded to the
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:280-283`

```
> Rule of thumb: **same phase → revise in place; upstream phase with downstream open → reset.**
```

— `.claude/skills/qrspi-work/references/review-cascade.md:76` (the referenced file; 78 lines, markdown, H1 title + decision tables)

**Dependencies:** `SKILL.md` references `references/review-cascade.md` by relative path. The reference file is self-contained markdown (no back-pointer to SKILL.md).
**Implicit contracts:** Reference files are pointed to by a parenthetical `(see \`references/<file>.md\`)` in the body prose — the agent is expected to read it on demand, not have it preloaded. The path is relative to the skill directory. `references/` holds progressive-disclosure detail that would otherwise bloat the body.

## Q3: What exact frontmatter fields and value formats does a valid `SKILL.md` require in this repo (name, description, and any others), and what are the naming/length constraints on each?

**Answer:** Every `SKILL.md` opens with a YAML frontmatter block delimited by `---`. The fields used across all 10 skills are: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. All five appear in every skill. Formats observed:

- `name`: bare string, kebab-case, matches the directory name (e.g. `qrspi-research`).
- `description`: a single string. Usually unquoted; `qrspi-work` wraps it in double quotes because it contains embedded single quotes and commas. Content is "what it does + when to use it" trigger phrasing.
- `command`: the slash command, leading `/` (e.g. `/qrspi-research`).
- `argument-hint`: angle-bracket placeholder, e.g. `<ticket-id>` or `<ticket-id> <slice-number>` or `<initial description>`.
- `allowed-tools`: comma-separated tool allowlist. Supports scoped forms: bare names (`Read`, `Agent`), parenthesized scoping (`Bash(pwd:*)`), and MCP tool names (`mcp__linear__get_issue`).

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
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear__save_issue, mcp__linear__list_teams
```

— `.claude/skills/qrspi-ticket/SKILL.md:6` (shows bare-name + MCP-name forms)

**Dependencies:** `allowed-tools` constrains what tools the skill/agent may call (tool lockdown). `command` is the user-facing invocation.
**Implicit contracts:** No explicit length cap is enforced in code (see Q7). `name` must equal the directory name. A `description` with commas/apostrophes must be quoted. `allowed-tools` is the security boundary — e.g. `qrspi-research` deliberately omits Linear MCP tools (research firewall, Q4/Q6).

## Q4: How is the Anthropic skill-builder/skill-creator skill invoked, and what inputs and output structure does it produce that the ticket's "built using the Anthropic skill builder skill" criterion depends on?

**Answer:** NOT FOUND inside the project scope. There is no `skill-creator` or `skill-builder` skill directory under `.claude/skills/`, and no script implementing one. The only repo reference is in an agent doc that mentions invoking it as a validation step, treating it as an external tool, not a repo asset.

The `skill-creator` skill referenced by the ticket is a **global Anthropic skill** that lives outside `REPO_ROOT` (it appears in the harness's available-skills list, not in this repo). Per the project-scope firewall I must not read it. Its invocation, inputs, and output structure therefore cannot be documented from repo evidence.

Searches attempted: `grep -rl "skill-creator"`, `grep -rln "skill builder|skill-builder|skill_builder"`, `find .claude/skills -type d`. Only hits: `.qrspi/RUS-18/questions.md` (the questions file itself) and the structure agent below.

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40` (the only substantive in-repo mention; treats skill-creator as an external validation invocation, not a repo file)

**Dependencies:** External to the repo; the project relies on the harness-provided global `skill-creator` skill.
**Implicit contracts:** The user's global instructions (CLAUDE.md memory) require: "Always invoke the skill-creator skill (and its eval loop) when creating or substantially modifying a skill; never ship a SKILL.md ad-hoc." So skill creation is expected to route through skill-creator, but the contract lives in user instructions, not repo code.

## Q5: How is a skill's `description` field written so the harness auto-triggers it on relevant user requests, and what triggering/anti-triggering conventions do existing skills follow?

**Answer:** Descriptions follow a "what it does + when to use it" shape, often with explicit literal trigger phrases. The richest example is `qrspi-work`, which enumerates positive triggers verbatim ("Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'"). Most phase skills use a terser "<does X>. Use after <prior phase> is approved." form that encodes a sequencing trigger. None of the in-repo QRSPI skill descriptions contain explicit anti-trigger / SKIP clauses — that convention is visible only in harness-level skills (e.g. the global `claude-api` skill uses `TRIGGER:` / `SKIP:`), not in this repo's files.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). … Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

```
description: Define vertical slices, types, and contracts from the approved design. Use after design is approved.
```

— `.claude/skills/qrspi-structure/SKILL.md:3` (terse sequencing-trigger form)

**Dependencies:** The harness reads `description` to decide auto-invocation. Phase descriptions reference each other implicitly via "after <phase> is approved".
**Implicit contracts:** Description = capability sentence + "Use when/after …" trigger. Quote the description if it contains commas/apostrophes. Embedding literal user phrasings ('work on …') strengthens auto-trigger matching. No repo skill currently writes negative/anti-trigger clauses, so a new skill adding one would be introducing a convention, not matching one.

## Q6: How are skill artifacts versioned, committed, and reviewed in this repo — do skills live on the default branch directly, or do they flow through the QRSPI PR-gated lifecycle and worktree at `.worktrees/<id>/`?

**Answer:** Existing skills are committed on the default branch (`main`) under `.claude/skills/` — they are tracked source, not gitignored. NEW work (including changes to skills) flows through the QRSPI PR-gated lifecycle: a per-ticket git worktree at `.worktrees/<ticket-id>/`, a Graphite stack of branches `<id>/design` → `<id>/plan` → `<id>/slice-1..N`, each its own stacked PR, held open until the whole feature is approved then landed bottom-up. `.worktrees/` itself is gitignored (this research is running inside `.worktrees/RUS-18`). Advancement is gated on PR review state (APPROVED + zero unresolved threads), computed by `scripts/qrspi_resolve_state.py`, not on Linear status.

**Evidence:**

```
Each ticket gets an isolated git worktree at `.worktrees/<ticket-id>/`. … The main repo
checkout stays on `main`; all ticket work happens in worktrees. `.worktrees/` is gitignored.
```

— `.claude/CLAUDE.md` ("Worktrees" section)

```
**Branches:** `<id>/design` → `<id>/plan` → `<id>/slice-1..N`, each its own PR, stacked.
```

— `.claude/CLAUDE.md` ("Lifecycle — PR-gated" section)

**Dependencies:** Skill files are committed via the implementation slices of a ticket. Final source-of-truth is `main` after the stack lands.
**Implicit contracts:** Skills are normal tracked files. A new skill is delivered as code in implementation slice PRs of its ticket, reviewed before landing. The single-commit-per-phase Graphite convention applies. Implementation must stay inside `.worktrees/<id>/` (implement-phase project-scope firewall, `.claude/skills/qrspi-work/SKILL.md:460-476`).

## Q7: What is the enforced or conventional ceiling on `SKILL.md` size in this repo, and how does it compare to the ticket's "under 500 lines / 5000 tokens" requirement — is there tooling that measures it?

**Answer:** There is NO enforced size limit and NO tooling that measures SKILL.md line/token count. A repo-wide search for `500`, `5000`, `token`, line-count, or `SKILL.md` size checks in `scripts/` found only unrelated hits (test fixtures, persistence byte checks). `grade.py` has a "line count" programmatic check concept for eval assertions (per `docs/eval-system.md`), but it is not wired to any SKILL.md size gate and the eval harness is a non-functional placeholder (Q10).

Conventionally, the QRSPI skills are far under the ticket's 500-line target: most are 25–35 lines; `qrspi-ticket` is 127; the outlier `qrspi-work` is 565 lines — which actually **exceeds** the ticket's stated "under 500 lines" requirement. So a Terraform skill aiming for <500 lines / <5000 tokens has no automated gate; compliance is self-checked (e.g. `wc -l`).

**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
   25 .claude/skills/qrspi-structure/SKILL.md
  127 .claude/skills/qrspi-ticket/SKILL.md
  565 .claude/skills/qrspi-work/SKILL.md   <- exceeds the ticket's 500-line target
  911 total
```

— `wc -l .claude/skills/*/SKILL.md`

**Dependencies:** None — no size-check tool exists.
**Implicit contracts:** Brevity is conventional, not enforced. Progressive disclosure (move detail to `references/`, as `qrspi-work` partly does) is the lever for staying small. The 500-line / 5000-token target is a ticket-imposed goal with no harness enforcement.

## Q8: How do existing skills that ship runnable helpers handle the `scripts/` directory (language, shebang, executable bit, test siblings), and which conventions would a Terraform skill's optional scripts need to follow?

**Answer:** NO skill in this repo ships a `scripts/` subdirectory (find returned none). The only runnable scripts live at the **repo-level** `scripts/` directory and are invoked by agents/workflows, not bundled inside a skill. Their conventions are the closest analog a Terraform skill's optional scripts should mirror:

- Language: Python 3, stdlib-only (no third-party deps).
- Shebang: `#!/usr/bin/env python3` on executable scripts (`check_scope.py`, `diagnose.py`, `grade.py`, `report.py`, `revise.py`, `run_eval.py`).
- Executable bit: set (`-rwxr-xr-x`) on the runnable CLIs; the importable modules (`qrspi_resolve.py`, `qrspi_persist.py`, etc.) are `-rw-r--r--` and run via `python3 scripts/<name>.py`.
- Test siblings: every `qrspi_*.py` logic module has a `<name>_test.py` sibling, stdlib unittest, run with `python3`.

**Evidence:**

```
-rwxr-xr-x  scripts/run_eval.py        (shebang #!/usr/bin/env python3)
-rw-r--r--  scripts/qrspi_resolve.py
-rw-r--r--  scripts/qrspi_resolve_test.py
-rw-r--r--  scripts/qrspi_persist.py
-rw-r--r--  scripts/qrspi_persist_test.py
```

— `ls -la scripts/` and `sed -n '1p' scripts/run_eval.py` → `#!/usr/bin/env python3`

```
- All of the above have stdlib-only unit tests as `_test.py` siblings (`scripts/qrspi_*_test.py`, run with `python3`).
```

— `.claude/CLAUDE.md` ("Codebase conventions")

**Dependencies:** Repo-level scripts are invoked by agents (e.g. `qrspi-work` runs `python3 scripts/qrspi_resolve.py`) and by `qrspi-batch.js`.
**Implicit contracts:** Python 3, stdlib-only, `#!/usr/bin/env python3`, executable bit on CLIs, mandatory `_test.py` sibling per logic module, self-locating from script path. A skill-bundled `scripts/` directory would be new ground; the user's global TDD directive ("A coding task is never complete without tests") reinforces shipping test siblings.

## Q9: Are there existing infrastructure/CLI-oriented skills in this repo whose scope overlaps with Terraform CLI guidance, that could cause triggering collisions or duplicated conventions?

**Answer:** No in-repo skill overlaps with Terraform CLI guidance. All 10 `.claude/skills/` are QRSPI-workflow phase skills (ticket, questions, research, design, structure, plan, worktree, implement, pr, work) — none are infrastructure/IaC/CLI-tool skills. The one CLI-adjacent capability is the **global** `using-graphite-cli` skill (version control via Graphite), which lives outside the repo (harness-level) and concerns git/PR operations, not infrastructure provisioning — no triggering collision with Terraform. So a Terraform CLI skill added here would be the first infrastructure-oriented skill and faces no in-repo description collision.

**Evidence:** All in-repo descriptions are phase-scoped, e.g.:

```
description: Write atomic implementation steps per vertical slice. Use after structure is approved.
```

— `.claude/skills/qrspi-plan/SKILL.md:3` (representative; all 10 are QRSPI-phase descriptions, none mention infra/terraform/cli-tool provisioning)

**Dependencies:** None overlapping. `using-graphite-cli` is global, not in `.claude/skills/`.
**Implicit contracts:** A new Terraform skill should pick a distinct name (no `qrspi-` prefix, which is reserved for the workflow phases) and triggers anchored on Terraform/IaC vocabulary so it does not contend with the QRSPI-phase descriptions or the global graphite skill.

## Q10: What is the established way to verify a skill in this repo given that "the `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder" — what does the skill-creator eval loop actually run, and what counts as a passing skill?

**Answer:** Repo verification is by (1) the stdlib unit tests for any logic scripts, and (2) manual end-to-end runs of the orchestration — CLAUDE.md states this explicitly. The `evals/` + `scripts/run_eval.py` pipeline is documented as a 5-stage harness (run → grade → report → diagnose → revise) but `run_eval.py`'s `execute_single` is an explicit stub: it returns empty output and never invokes a real agent (the agent-invocation block is commented out as a placeholder). So eval scores are not a real pass gate here.

What the **skill-creator eval loop** runs is NOT determinable from repo evidence — skill-creator is a global skill outside `REPO_ROOT` (Q4) and cannot be read. From the user's global instructions, the expectation is that creating/modifying a skill routes through skill-creator "and its eval loop", but the loop's internals live outside this project.

A "passing" skill in-repo terms = its logic scripts' unit tests pass and a manual e2e invocation behaves correctly; there is no automated SKILL.md correctness gate.

**Evidence:**

```python
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
…
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:116-135` (stub — returns empty, no agent run)

```
The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` ("Codebase conventions", final bullet)

**Dependencies:** `evals/suite.json` (15 cases) feeds `run_eval.py` → `grade.py` → `report.py`; all downstream of the stub, so non-functional end-to-end.
**Implicit contracts:** Trust unit tests + manual e2e, not eval scores, for in-repo verification. skill-creator's eval loop is the user-mandated external check but is out of project scope to inspect.

## Q11: What conventions govern reference files in `references/` (file naming, headings, cross-linking from `SKILL.md`) that the ticket's backend-setup/CI-CD/migration reference documents must match?

**Answer:** Only one reference file exists to set the convention: `.claude/skills/qrspi-work/references/review-cascade.md`. Observed conventions:

- Naming: kebab-case, topic-descriptive, `.md` (e.g. `review-cascade.md`).
- Headings: starts with a single H1 (`# Review Cascade Logic (PR-gated)`), then numbered H2 sections (`## 1. Within-phase cascade …`, `## 2. Cross-phase change …`), with markdown tables and fenced ASCII diagrams for decision logic.
- Cross-linking: the `SKILL.md` body points to it with an inline parenthetical relative path `(see \`references/review-cascade.md\`)`; the reference file does NOT link back to SKILL.md but cross-references repo docs by relative path (`docs/qrspi-pr-gated-lifecycle-design.md §4`).
- Self-contained: the reference holds the detailed decision tables that would bloat the body; the body keeps only the rule-of-thumb summary.

**Evidence:**

```
# Review Cascade Logic (PR-gated)
…
## 1. Within-phase cascade — the manual `revise` path
…
## 2. Cross-phase change — the automatic `reset` path (NOT a patch)
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1,15,57`

```
(see `references/review-cascade.md`)
```

— `.claude/skills/qrspi-work/SKILL.md:281`

**Dependencies:** Referenced from `SKILL.md`; references repo docs in `docs/`.
**Implicit contracts:** One H1 per reference file; numbered/descriptive H2 sections; kebab-case `.md` filename; linked from the body via `(see \`references/<file>.md\`)`; progressive disclosure (detail lives here, summary stays in body). Multiple reference docs (backend-setup, CI-CD, migration) would each be a separate kebab-case `.md` under `references/`, each cited from the body.

## Q12: How would an agent or operator confirm a newly added skill is registered and discoverable by the harness (appears in the available-skills list) after it is written — what surfaces the skill name and description?

**Answer:** Discovery is automatic: Claude Code scans `.claude/skills/*/SKILL.md` and surfaces each skill's `name` + `description` from the YAML frontmatter into the harness's available-skills list (the same list visible in the system prompt, where each skill appears as "- <name>: <description>"). There is NO explicit registration file, manifest, or index to update — creating a valid `.claude/skills/<name>/SKILL.md` with correct frontmatter is sufficient. Confirmation methods available in-repo: (1) verify the directory/`SKILL.md` exists with valid frontmatter (`name`, `description`); (2) the slash command `/<name>` becomes invocable; (3) the skill appears in the available-skills system reminder. There is no in-repo script that lists or validates registration.

**Evidence:**

```
thin slash-command **skills** (`.claude/skills/qrspi-<phase>/SKILL.md`) wrap them.
```

— `docs/qrspi_claude_code_guide.md:5`

```
│   │   │   └── SKILL.md                   # /qrspi-research
```

— `docs/qrspi_claude_code_guide.md:32` (one SKILL.md per skill dir = one entry in the list)

**Dependencies:** The harness (Claude Code) is the registrar; it reads frontmatter `name`/`description`. No repo-side index.
**Implicit contracts:** A correctly-placed `SKILL.md` with valid `name`/`description` frontmatter is auto-discovered — placement IS registration. `name` must match the directory; `description` is what surfaces as the trigger text. No manual list edit is required (though the human-facing list in `.claude/CLAUDE.md` and `docs/` is maintained by hand for documentation, not by the harness).

---

## Discovered Patterns

- **Skill = thin wrapper, agent = heavy logic (QRSPI-specific).** Phase skills (`qrspi-research`, `qrspi-design`, etc.) are 25–35-line shells whose entire job is to spawn `subagent_type: <name>` against `.claude/agents/<name>.md`. Self-contained skills (`qrspi-work`, `qrspi-ticket`) inline all logic. A non-phase skill (like a Terraform skill) would follow the self-contained model.
- **Five-field frontmatter is universal:** `name`, `description`, `command`, `argument-hint`, `allowed-tools` on all 10 skills.
- **`allowed-tools` is a deliberate security boundary** (tool lockdown), e.g. research omits Linear MCP and Bash-beyond-`pwd` to enforce the research firewall; questions omits Glob/Grep/Bash to make codebase exploration "structurally impossible" (`.claude/skills/qrspi-work/SKILL.md:450-453`).
- **Progressive disclosure via `references/`** is the established lever for keeping `SKILL.md` small — only `qrspi-work` uses it so far, with `(see \`references/<file>.md\`)` inline links.
- **Stdlib-only Python + mandatory `_test.py` sibling** is the universal pattern for all runnable logic (`scripts/qrspi_*`), reinforced by the user's TDD directive.
- **PR-gated, worktree-isolated, single-commit-per-phase Graphite stack** governs how any new file (including a skill) is delivered and reviewed.
- **No size/lint/registration tooling exists** for skills — placement is registration, brevity is convention, verification is unit tests + manual e2e.

## Inconsistencies

- **`qrspi-work/SKILL.md` is 565 lines** — it exceeds the ticket's stated "under 500 lines" target and is ~16x the size of the typical phase skill. It demonstrates the progressive-disclosure pattern only partially (one `references/` file). So the repo's own flagship skill does not meet the 500-line bar the ticket sets; there is no tooling to flag this.
- **Eval harness documented as a 5-stage pipeline but is a non-functional stub.** `docs/eval-system.md` and `docs/qrspi-orientation` describe run/grade/report/diagnose/revise in detail, while `scripts/run_eval.py:116-135` is an explicit placeholder returning empty output and CLAUDE.md flatly calls it "non-functional." Documentation reads as if functional; code is not.
- **Co-author trailer drift:** `.claude/skills/qrspi-work/SKILL.md` commit-message blocks cite `Claude Opus 4.7 (1M context)` while this session's environment trailer is `Claude Opus 4.8 (1M context)`. Cosmetic, but a mismatch between committed convention and current model.
- **Skill-creator referenced but absent from repo.** `.claude/agents/qrspi-structure.md:40` and the user's global instructions assume a `skill-creator` skill, but it exists only as a global harness skill outside `REPO_ROOT` — so the ticket's "built using the Anthropic skill builder skill" criterion depends on an asset that cannot be inspected or version-controlled within this project.
