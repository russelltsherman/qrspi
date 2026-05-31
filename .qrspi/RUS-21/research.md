# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T17:01:05Z
**Generated:** 2026-05-31T17:05:00Z
**Status:** draft

## Q1: How is an existing skill's directory laid out in this repo — what files and subdirectories (SKILL.md, references/, scripts/, assets/) are present, and where do they live relative to the repo root?

**Answer:** Skills live under `.claude/skills/<skill-name>/`. Each skill directory contains a single `SKILL.md`. Only one skill (`qrspi-work`) has a `references/` subdirectory; no skill in the repo uses `scripts/` or `assets/` subdirectories. So the minimal, dominant layout is just `<skill-name>/SKILL.md`, with an optional `references/` directory for overflow material.
**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-research/SKILL.md
... (10 skills total, each with SKILL.md)
```

— `.claude/skills/` (directory listing); `find .claude/skills -type d -name references` → only `.claude/skills/qrspi-work/references`
**Dependencies:** Skills are consumed by the Claude Code harness, which auto-discovers them from `.claude/skills/`. No build step.
**Implicit contracts:** Directory name = skill identity. A `references/` directory is sibling to SKILL.md and referenced by relative path from the body.

## Q2: How does content flow from a SKILL.md body into its references/ files — what is the convention for when material is inlined in SKILL.md versus split into a reference file?

**Answer:** The only example is `qrspi-work`, whose SKILL.md body (731 lines) references `references/review-cascade.md` for "cascade logic" that is needed only in a specific branch (addressing planning feedback). The convention observed: keep the always-needed procedure inline; push conditional, deep, or rarely-traversed detail into a `references/<topic>.md` file and point to it by relative path from the body (e.g., "Read `references/review-cascade.md` for cascade logic.").
**Evidence:**

```
c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:273`
**Dependencies:** The body must name the reference file by its relative path; the harness does not auto-load references.
**Implicit contracts:** Reference files are loaded on demand by the agent reading the body, not injected automatically. The body remains the entry point.

## Q3: What exact frontmatter fields and value formats appear in existing SKILL.md files (name, description, command, argument-hint, allowed-tools, model, and any others)?

**Answer:** SKILL.md frontmatter is YAML between `---` fences. Fields used across skills: `name` (string, matches directory name), `description` (single-line string describing what the skill does and when to use it), `command` (slash command, e.g. `/qrspi-work`), `argument-hint` (e.g. `<ticket-id>`), and `allowed-tools` (comma-separated tool allowlist, supporting scoped forms like `Bash(pwd:*)` and MCP tool names). Agent definitions (`.claude/agents/*.md`) additionally use `model: opus` and a nested `claude:` block with `tools:`, but those are agents, not skills.
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
**Dependencies:** The harness parses this frontmatter to register the slash command and tool allowlist.
**Implicit contracts:** `name` must equal the directory name. `description` is the trigger surface for auto-invocation. `allowed-tools` gates which tools the skill may call.

## Q4: Is there a documented or de-facto agentskills.io standard reference already captured in this repo that defines the required SKILL.md structure and frontmatter?

**Answer:** No file in the repo contains the string "agentskills". There is no captured copy of the agentskills.io standard. The de-facto standard in this repo is the existing `.claude/skills/*/SKILL.md` files plus the QRSPI docs in `docs/`. The closest authoritative structure guidance is the README phase table and the per-skill SKILL.md frontmatter shown in Q3. There is NO skill-creator/skill-builder skill present (search returned nothing).
**Evidence:**

```
$ grep -rn "agentskills" . --include=*.md   → (no matches)
$ find . -iname '*skill-creator*' -o -iname '*skill-builder*'   → (no matches)
```

— repo-wide search from `.worktrees/RUS-21/`
**Dependencies:** None in-repo. The agentskills.io standard and the Anthropic skill-builder skill referenced by the ticket are external to this repo.
**Implicit contracts:** New skills must conform to the existing in-repo SKILL.md shape (Q3) since that is what the harness actually parses; agentskills.io compliance is layered on top via SKILL.md + optional references/scripts/assets.

## Q5: Where should the new using-codex-cli skill physically live, and what naming convention do sibling skills follow for their directory name versus their frontmatter name field?

**Answer:** It should live at `.claude/skills/using-codex-cli/SKILL.md`. Sibling skills use kebab-case directory names that exactly match the `name:` frontmatter value (e.g., directory `qrspi-research` ↔ `name: qrspi-research`). The user's own skill list also includes externally-provided skills named with a `using-` prefix (e.g., `using-graphite-cli`), matching the ticket's intended skill name `using codex cli` → `using-codex-cli`.
**Evidence:**

```
.claude/skills/qrspi-research/SKILL.md  →  name: qrspi-research
.claude/skills/qrspi-work/SKILL.md      →  name: qrspi-work
```

— directory listing + frontmatter `name` fields; convention is 1:1 directory↔name match
**Dependencies:** Harness auto-discovery keys on the directory under `.claude/skills/`.
**Implicit contracts:** directory name == frontmatter `name`, kebab-case, no spaces.

## Q6: How is a skill's description field written so the harness can auto-trigger it — what length, phrasing, and trigger-keyword patterns do existing descriptions use?

**Answer:** Descriptions are written as "what it does + when to use it," often listing explicit trigger phrases. The orchestrator skill `qrspi-work` uses a long description enumerating trigger variants ("Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>'..."). Phase skills use shorter one-to-two-sentence descriptions ending with a "Use after X" / "Use when Y" clause. The pattern: lead with capability, then a clear triggering condition.
**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>' ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`
**Dependencies:** The harness matches user intent against this description to auto-invoke.
**Implicit contracts:** Description must contain natural-language trigger cues; a bare capability statement under-triggers.

## Q7: What enforces or measures the acceptance criteria "SKILL.md body under 500 lines / 5000 tokens" — is there a linter, eval, or script in the repo that checks skill size or frontmatter validity?

**Answer:** Nothing in the repo enforces SKILL.md size or frontmatter validity for arbitrary skills. The `evals/` harness (`suite.json`, `scripts/run_eval.py`, `scripts/grade.py`) tests QRSPI workflow agent phases (questions, research, etc.) against fixtures and golden outputs — it does not lint SKILL.md files. `scripts/check_scope.py` checks that an implement agent stayed within its allowed file set; it is not a skill-size linter. Therefore the 500-line/5000-token criterion is a manual review gate, not an automated check. For reference, the largest existing body, `qrspi-work/SKILL.md`, is 731 lines (an orchestrator) — so the criterion is a target for content skills, not a repo-wide invariant.
**Evidence:**

```
"""Check that implementation stayed within allowed scope.
Used as a script-type assertion in evals to verify the implement agent
only touched files listed in its session task list."""
```

— `scripts/check_scope.py:1-6`; `evals/suite.json` cases are all `"phase": "questions"|"research"|...`
**Dependencies:** Manual reviewer + the PR review gate enforce the size criterion.
**Implicit contracts:** Keep SKILL.md body lean; move overflow into `references/` (Q2) to satisfy the size budget.

## Q8: How do existing skills handle platform-specific or conditional guidance without bloating the SKILL.md body — is branching pushed into reference files?

**Answer:** No existing skill documents OS/platform branching in its body. The one use of a reference file (`qrspi-work` → `review-cascade.md`) pushes conditional branch logic out of the body. By extension, the established mechanism for conditional/platform-specific depth is a `references/<topic>.md` file linked from the body, keeping the body to the common path. There is no in-repo precedent for inlining large macOS-vs-Linux tables in a body.
**Evidence:**

```
$ find .claude/skills -type d -name references  → only qrspi-work/references
```

— directory search; `qrspi-work/SKILL.md:273` is the sole "read this reference" pattern
**Dependencies:** Body links to reference by relative path; reader loads on demand.
**Implicit contracts:** Platform/sandbox detail belongs in references; the body should state the decision rule and defer the table.

## Q9: The ticket says to build the skill "using the Anthropic skill builder skill" — is that skill-creator skill present and invocable in this environment, and what artifacts does it expect to produce or consume?

**Answer:** No skill-creator/skill-builder skill is present in the repo (`find` for `*skill-creator*`/`*skill-builder*` returned nothing; `.claude/skills/` contains only the 10 qrspi-* skills). If such a skill exists, it is provided by the harness/environment rather than checked into this repo. From the repo's perspective, the consumable artifact contract is the in-repo SKILL.md shape (Q3): a `SKILL.md` with valid YAML frontmatter plus optional `references/`, `scripts/`, `assets/` directories. The deliverable can be authored to that contract whether or not an external builder skill is invoked.
**Evidence:**

```
$ ls .claude/skills/  → qrspi-design qrspi-implement qrspi-plan qrspi-pr
   qrspi-questions qrspi-research qrspi-structure qrspi-ticket qrspi-work qrspi-worktree
$ find . -iname '*skill-creator*' -o -iname '*skill-builder*'  → (no matches)
```

— `.claude/skills/` listing + repo-wide search
**Dependencies:** External (harness-provided) builder skill, if used, is out of repo scope.
**Implicit contracts:** Regardless of authoring tool, the output must be a valid in-repo SKILL.md (Q3) discoverable under `.claude/skills/`.

## Q10: How are skills validated or tested in this repo — is there an eval harness in evals/ that runs against skills, and what input/output contract does it expect?

**Answer:** The `evals/` harness validates QRSPI *workflow phase agents*, not skills-in-general. `evals/suite.json` defines cases keyed by `phase` (questions, research, ...), each with a prompt, context fixtures, and assertions. Assertions are `programmatic` (e.g., `output_file_exists('questions.md')`, `section_count(...) >= 5`, `question_count(...) >= 8`) graded by `scripts/grade.py` via `scripts/run_eval.py`, with golden references in `evals/golden/` and inputs in `evals/fixtures/`. There is no eval case type for "validate an arbitrary SKILL.md." So a new content skill like using-codex-cli has no automated eval path here.
**Evidence:**

```
"assertions": [
  {"type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0},
  {"type": "programmatic", "check": "section_count('questions.md', '## ') >= 5", "weight": 1.0},
  {"type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0}
]
```

— `evals/suite.json` (case_001, questions_happy_path)
**Dependencies:** `scripts/run_eval.py` → `scripts/grade.py`; fixtures in `evals/fixtures/`, goldens in `evals/golden/`.
**Implicit contracts:** Eval assertions are file-existence + structural-count checks. A new skill's "test" must therefore be a structural/manual check (frontmatter present, body size, required sections), not a code unit test.

## Q11: What test or verification convention does the project's contributor guidance require for a new skill?

**Answer:** There is no CONTRIBUTING file and no documented skill-verification convention beyond (a) the README's phase model and (b) the eval harness for workflow phases. The practical verification for a new content skill is structural: SKILL.md exists with valid frontmatter, body within the size budget (Q7), required acceptance-criteria sections present, and any `references/` files linked from the body resolve. The user's global directives also require tests for any coding task — for a documentation skill this maps to a verification script/checklist asserting the structural invariants rather than runtime unit tests.
**Evidence:**

```
docs/: container-sandbox  delivery_summary.md  eval-system.md  qrspi-orientation.md
       qrspi_claude_code_guide.md  qrspi_complete_guide.md ...
(no CONTRIBUTING; no skill-lint doc)
```

— `docs/` listing; absence of CONTRIBUTING in repo root listing
**Dependencies:** README + docs are the only contributor guidance.
**Implicit contracts:** Verification is structural/manual; encode it as a checklist or a small validation script over the SKILL.md.

## Q12: How would a reviewer or operator confirm the new skill is discoverable and correctly registered — is there a manifest, index, or listing that skills must be added to, or are they auto-discovered from .claude/skills/?

**Answer:** Skills are auto-discovered from `.claude/skills/` — there is no manifest or index file that must be edited. No `.claude/*.json` registry of skills exists (`grep` for a skills index returned no matches). The user-facing README maintains a human-readable table of primary skills, and `.claude/CLAUDE.md` lists available skills for operators, but neither is a load-bearing registry; they are documentation. Discoverability is confirmed by the harness listing the skill (it appears in the available-skills list once `.claude/skills/<name>/SKILL.md` exists with valid frontmatter).
**Evidence:**

```
$ ls .claude/  → CLAUDE.md  agents  skills  workflows   (no skills index json)
$ grep -rn "skills" .claude/*.json  → no .claude/*.json files exist
```

— `.claude/` listing; README "Individual phase skills" table is documentation, not a registry
**Dependencies:** Harness auto-discovery; optional doc updates to README/`.claude/CLAUDE.md` for human discoverability.
**Implicit contracts:** Creating `.claude/skills/<name>/SKILL.md` with valid frontmatter is sufficient for registration; updating README/CLAUDE.md skill lists is a documentation courtesy, not a hard requirement.

---

## Discovered Patterns

- All 10 existing skills are QRSPI workflow skills with kebab-case names matching their directory. Frontmatter is consistently `name`/`description`/`command`/`argument-hint`/`allowed-tools`.
- Heavy procedural skills (orchestrators) run long (qrspi-work = 731 lines); phase skills are short and delegate to agent definitions in `.claude/agents/`.
- The repo cleanly separates **skills** (`.claude/skills/`, slash-command entry points) from **agents** (`.claude/agents/`, spawned workers with `model:`/`claude.tools:` frontmatter). A new standalone content skill like using-codex-cli does not need a paired agent.
- `references/` is the sanctioned overflow mechanism; `scripts/` and `assets/` directories are permitted by the agentskills.io standard but unused in-repo so far.

## Inconsistencies

- The README "Why" section contains a stray `x` on its own line (`README.md`), and `qrspi-work` frontmatter cites `Claude Opus 4.7` in commit-message templates while this environment runs Opus 4.8 — cosmetic, not blocking.
- Acceptance criterion "body under 500 lines" conflicts with the in-repo precedent of a 731-line orchestrator body; the criterion is a content-skill target, not a repo invariant, and is unenforced by any tool (Q7).
- The ticket references an "Anthropic skill builder skill" that is not present in this repo (Q9); authoring must proceed to the in-repo SKILL.md contract regardless.
