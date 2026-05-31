# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T16:27:56Z
**Generated:** 2026-05-31T16:30:00Z
**Status:** draft

## Q1: On-disk layout of an existing agent skill and where skills live

**Answer:** Skills live in `.claude/skills/<skill-name>/`. Each skill is a directory containing a `SKILL.md` file. Subdirectories (`references/`) are optional and used only by larger skills. The repo currently has 10 skills, all `qrspi-*`. Only `qrspi-work` has a `references/` subdirectory; none currently ship `scripts/` or `assets/` subdirectories inside the skill folder.
**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
... (10 skill dirs total)
```

— `.claude/skills/` (directory listing)
**Dependencies:** Skills sit alongside `.claude/agents/` (agent prompt definitions) and `.claude/workflows/`. Per `.claude/CLAUDE.md`, "Agent prompt definitions live in `.qrspi/agents/`" and "Artifact templates live in `.qrspi/templates/`" — but the live skill/agent definitions used by Claude Code are under `.claude/skills/` and `.claude/agents/`.
**Implicit contracts:** A skill directory name equals the skill's `name` frontmatter value and its `command` (minus the leading slash). Directory name is kebab-case.

## Q2: Split between SKILL.md body and references/ files

**Answer:** Most qrspi skills are thin: the SKILL.md body is 25-35 lines and delegates to an agent definition under `.claude/agents/`. The exception is `qrspi-work` (730-line SKILL.md) which holds the full orchestrator logic inline and offloads only one piece — cascade logic — to `references/review-cascade.md`. The body loads a reference by an explicit instruction: "Read `references/review-cascade.md` for cascade logic." Reference files are pulled in on demand, not auto-loaded.
**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md:272:   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:272`
**Dependencies:** The body is the always-loaded surface; references are loaded only when the body's prose tells the agent to read them.
**Implicit contracts:** Reference paths are written relative to the skill directory (`references/<file>.md`), not absolute. The agent reads them with the Read tool when instructed.

## Q3: SKILL.md frontmatter fields, required vs optional

**Answer:** Observed frontmatter fields across skills: `name` (required), `description` (required), `command` (the slash command), `argument-hint` (e.g., `<ticket-id>`), and `allowed-tools` (comma-separated tool allowlist). All 10 qrspi skills declare `name`, `description`, `command`, `argument-hint`, `allowed-tools`. The agent definitions under `.claude/agents/` use a different frontmatter shape: `name`, `description`, `model: opus`, and a nested `claude: { tools: ... }` block.
**Evidence:**

```
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research...
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-7`
**Dependencies:** `allowed-tools` gates which tools the skill body may invoke.
**Implicit contracts:** `description` is what the harness matches on for auto-invocation; it tends to include explicit "Use when..." trigger phrasing. `command` is `/` + the skill name.

## Q4: How the skill-creator (Anthropic skill builder) skill is invoked and structured

**Answer:** NOT FOUND in repo scope. `skill-creator` is not present under `.claude/skills/` in this repo (only the 10 `qrspi-*` skills exist). It is a global/harness-provided skill available at runtime (it appears in the session's available-skills list as "skill-creator: Create new skills... run evals... optimize a skill's description"). Its directory structure and internal files live outside `REPO_ROOT` and were not read (scope boundary). The acceptance criterion "Built using the Anthropic skill builder skill" therefore relies on a runtime-available skill, not a repo asset.
**Evidence:** Search of `.claude/skills/` returned only `qrspi-*` directories; `ls .claude/skills/skill-creator` → "NO skill-creator in repo .claude/skills".
**Dependencies:** Runtime harness provides skill-creator; the new ADR skill files will land under `.claude/skills/`.
**Implicit contracts:** skill-creator is invoked via the Skill tool (`skill: skill-creator`), per the session's skill-invocation conventions.

## Q5: Existing ADR directories or pre-existing ADRs

**Answer:** NOT FOUND — no ADR directories exist. `docs/decisions/`, `docs/adr/`, and `architecture/decisions/` are all absent. The `docs/` tree contains only QRSPI workflow guides and eval-system docs. There are no existing ADRs to be consistent with, so the skill defines conventions greenfield.
**Evidence:**

```
ls -d docs/decisions docs/adr architecture/decisions  →  NO ADR dirs
docs/  contains: container-sandbox/, delivery_summary.md, eval-system.md,
qrspi-orientation.md, qrspi_*_guide.md, qrspi_quick_reference.md, ...
```

— repo-root `docs/` listing
**Dependencies:** None — no prior ADR state.
**Implicit contracts:** None constraining ADR location; the skill's stated default (`docs/decisions/`) does not collide with anything.

## Q6: How existing skills encode "default + alternatives" guidance

**Answer:** No skill in the repo encodes a "recommended default plus fallback alternatives" content pattern in the way the ADR skill needs (MADR default, Nygard/Y-statement alternatives). The closest analogue is the orchestrator's State Dispatch table in `qrspi-work` (a mapping from condition → action) and the design template's "Pattern Decisions" tables (Option A/B with a marked Recommendation). The design template's table format — options with pros/cons and an explicit "Recommendation" — is the repo's idiom for "default + alternatives."
**Evidence:**

```
## Pattern Decisions
### Decision 1: <short name>
| Option | Approach | Pros | Cons |
**Recommendation:** Option <X>
```

— `.qrspi/templates/design.md:23-34`
**Dependencies:** None.
**Implicit contracts:** When presenting a default with alternatives, the repo idiom is a table plus an explicit recommendation line.

## Q7: SKILL.md body size budget

**Answer:** No hard enforcement exists in the repo, but a clear convention: thin wrapper skills are 25-35 lines; the one large skill (`qrspi-work`) is 730 lines and holds an entire orchestrator. `qrspi-ticket` is 119 lines. The ticket's acceptance criterion ("under 500 lines / 5000 tokens") is well above the thin-skill norm and below the qrspi-work outlier, so it is comfortably achievable. The skill-creator skill (runtime) is the authority on size limits per its description; that guidance lives outside repo scope.
**Evidence:**

```
   25 .claude/skills/qrspi-structure/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  730 .claude/skills/qrspi-work/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`
**Dependencies:** None enforced; convention only.
**Implicit contracts:** Push detailed/long-form content into `references/` to keep the SKILL.md body lean (qrspi-work's pattern, though it kept most logic inline).

## Q8: How skills reference and copy assets/ template files

**Answer:** NOT FOUND in repo — no skill currently ships an `assets/` directory. The analogous mechanism in the repo is the QRSPI templates under `.qrspi/templates/` (e.g., `questions.md`, `design.md`), which agents are told to read via a `TEMPLATE_PATH` input and use as the output structure. The pattern to emulate for the ADR starter template: place a copyable file under the skill's `assets/`, and have the SKILL.md body instruct the agent to copy it (read the asset, write a new ADR file from it) — analogous to how agents read a `TEMPLATE_PATH` and write a populated artifact.
**Evidence:**

```
.qrspi/templates/  →  design.md, plan.md, questions.md, research.md,
structure.md, worktree.md, impl-log.md, pr-summary.md, ticket.md, revision-log.md
```

— `.qrspi/templates/` listing; agent defs reference `TEMPLATE_PATH` (e.g., `.claude/agents/qrspi-questions.md:16`)
**Dependencies:** Read tool to load the asset; Write tool to emit the new file.
**Implicit contracts:** Templates use `<PLACEHOLDER>` angle-bracket tokens the agent fills in (see all `.qrspi/templates/*.md`). The ADR starter template should follow the same placeholder convention.

## Q9: Skill naming convention and collision risk

**Answer:** All skill directory names are kebab-case and prefixed `qrspi-`. The `name` frontmatter matches the directory name. There is no existing skill whose name relates to ADRs/decision records, so no collision. The new skill needs a unique kebab-case name (the ticket title suggests something like "writing-architecture-decision-records"). skill-creator (runtime) owns naming/description optimization guidance.
**Evidence:**

```
qrspi-design, qrspi-implement, qrspi-plan, qrspi-pr, qrspi-questions,
qrspi-research, qrspi-structure, qrspi-ticket, qrspi-work, qrspi-worktree
```

— `.claude/skills/` listing
**Dependencies:** None.
**Implicit contracts:** Directory name == `name` == `command` (sans slash); kebab-case.

## Q10: Eval/validation harness for skills

**Answer:** An eval harness exists under `evals/` and `scripts/`, but it is specific to the QRSPI workflow agents (questions, research, design, etc.), not a general validator for arbitrary new skills. `evals/suite.json` defines cases keyed by `phase` (e.g., `"phase": "questions"`) with programmatic assertions like `output_file_exists('questions.md')` and `question_count('questions.md') >= 8`. `scripts/run_eval.py`, `grade.py`, `check_scope.py`, etc. drive it. There is no existing eval case for an ADR skill; validation of the new skill is structural (valid frontmatter, body size, required reference/asset files present) rather than harness-driven, unless a new eval case is authored.
**Evidence:**

```
"cases": [ { "id": "case_001", "name": "questions_happy_path",
"phase": "questions", ...
"assertions": [ { "type": "programmatic",
"check": "output_file_exists('questions.md')", "weight": 1.0 }, ...
"check": "question_count('questions.md') >= 8" ...
```

— `evals/suite.json:16-46`
**Dependencies:** `scripts/run_eval.py` (+ grade/report/check_scope). skill-creator (runtime) provides its own eval loop for skills, per its description.
**Implicit contracts:** Eval assertions are programmatic checks over produced artifact files. A new skill could be validated by skill-creator's eval loop rather than this QRSPI-specific suite.

## Q11: How a skill's description drives trigger/discovery

**Answer:** The `description` field is the trigger surface — the harness matches user intent against it for auto-invocation. Effective descriptions in this repo lead with what the skill does, then add explicit "Use when..." / "Trigger on..." clauses enumerating phrasings. `qrspi-work` is the most elaborate: it lists concrete trigger variants ("'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'"). Several descriptions also add negative scoping (e.g., agent defs say "Not for general-purpose ...") to avoid over-triggering.
**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development.
Use when the user asks to 'work on' a ticket... Trigger on any variant of:
'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`
**Dependencies:** Harness skill-matching layer.
**Implicit contracts:** Descriptions combine (a) a capability summary, (b) explicit "Use when/Trigger on" phrases, and (c) optional negative scope. skill-creator's description-optimization eval (runtime) is the tool for tuning trigger accuracy.

---

## Discovered Patterns

- **Thin-skill + agent-definition split:** Every QRSPI phase skill is a thin SKILL.md wrapper that delegates to a richer prompt in `.claude/agents/<name>.md`. This is a workflow-orchestration pattern, not a requirement for all skills. A self-contained content skill (like an ADR-writing guide) more naturally puts its guidance directly in SKILL.md + `references/`, closer to the standalone `agentskills.io` model than to the qrspi wrapper pattern.
- **Template-driven artifacts:** Agents read a `TEMPLATE_PATH` and emit a populated file, with `<ANGLE_BRACKET>` placeholders. This is the direct analogue for an ADR starter template in `assets/`.
- **On-demand reference loading:** Large skills keep the body lean and pull detail from `references/*.md` via explicit "Read ..." instructions (qrspi-work pattern). This matches the ticket's requirement to keep SKILL.md under 500 lines while housing MADR/Nygard/Y-statement detail in `references/`.
- **Description as trigger contract:** Capability summary + explicit "Use when/Trigger on" phrasing + optional negative scope.

## Inconsistencies

- **Skill-definition location mismatch:** `.claude/CLAUDE.md` states "Agent prompt definitions live in `.qrspi/agents/`" and "Artifact templates live in `.qrspi/templates/`", but the actually-loaded definitions live in `.claude/agents/` and the active templates in `.qrspi/templates/`. The `.qrspi/agents/` path referenced by CLAUDE.md does not match the live `.claude/agents/` location. For a new skill, the live, harness-loaded location is `.claude/skills/<name>/`.
- **No `assets/` or `scripts/` precedent in any skill:** The ticket requires `references/` and `assets/`. `references/` has one precedent (qrspi-work); `assets/` and per-skill `scripts/` have none in this repo. These will be new (but standard `agentskills.io`) structures here.
- **Eval harness scope:** `evals/` is purpose-built for QRSPI phase agents; it cannot validate an ADR skill without a new case. The ticket's "built using the skill builder" criterion points validation toward skill-creator's own eval loop instead.
