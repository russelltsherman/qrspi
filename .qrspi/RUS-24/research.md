# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: What is the on-disk directory layout an agent skill must produce in this repo (SKILL.md plus references/, scripts/, assets/) and where do existing skills physically live?

**Answer:** Skills live under `.claude/skills/<skill-name>/`. Each skill directory contains a `SKILL.md` at its root. Optional supporting material lives in a `references/` subdirectory. In this repo, ten skills exist, all named `qrspi-*`. Only one skill (`qrspi-work`) currently uses a `references/` subdirectory; none use `scripts/` or `assets/` subdirectories. There is NO `skill-creator` skill and NO `using-graphite-cli` skill physically present in this repo — those are global skills referenced by the environment, not checked in here.

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-questions/SKILL.md
```

— `.claude/skills/` directory listing
**Dependencies:** The deliverable for RUS-24 (`using omlx cli`) will be a new sibling directory under `.claude/skills/`.
**Implicit contracts:** Skill directory name is the slug; SKILL.md sits at the directory root; reference docs go in `references/`.

## Q2: How do existing skills in this repo split content between the top-level SKILL.md body and supporting files under references/, and what triggers a reader to load a reference file?

**Answer:** The `qrspi-work` SKILL.md keeps the main procedure inline (730 lines, the orchestrator is an exception) and offloads one focused topic — review cascade logic — into `references/review-cascade.md` (63 lines). The SKILL.md body explicitly instructs the reader to load the reference at the relevant decision point: "Read `references/review-cascade.md` for cascade logic." So the trigger is an explicit in-body pointer, not auto-loading.

**Evidence:**

```
# qrspi-work/SKILL.md, State: Plan Review section:
   c. Read `references/review-cascade.md` for cascade logic.
   d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
```

— `.claude/skills/qrspi-work/SKILL.md` (Plan Review state)
**Dependencies:** Reference files are pulled on demand by an explicit instruction in the body.
**Implicit contracts:** Keep the body focused; move long, situational detail into `references/` and link to it by relative path.

## Q3: What exact YAML frontmatter fields are required and permitted in a SKILL.md, and what are their value constraints?

**Answer:** Observed frontmatter fields across in-repo skills: `name` (slug matching the directory), `description` (one-to-three sentence triggering description that includes "Use when…"), `command` (slash form, e.g. `/qrspi-design`), `argument-hint` (e.g. `<ticket-id>`), and `allowed-tools` (comma-separated tool list). The phase-skill `description` strings are written in the trigger-oriented style. The global/agentskills.io standard (from the environment's skill list) uses `name` + `description` as the minimum; `command`/`argument-hint`/`allowed-tools` are the Claude Code extensions seen here. NOTE: the exact agentskills.io frontmatter spec is NOT documented inside this repo — NOT FOUND in-repo (searched `*.md` for "frontmatter"/"agentskills"). The authoritative pattern available here is the existing SKILL.md files.

**Evidence:**

```
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-7`
**Dependencies:** Frontmatter `description` drives auto-invocation; `allowed-tools` constrains the tool surface.
**Implicit contracts:** `name` must equal the directory slug; `description` must start with a capability statement and include a "Use when" trigger clause.

## Q4: What does the skill-creator skill expect as inputs and what does its eval/validation loop check?

**Answer:** NOT FOUND in-repo. There is no `skill-creator` directory under `.claude/skills/` and no skill-authoring eval in `evals/`. `skill-creator` is a global skill surfaced by the environment (per the available-skills list), but its definition and eval loop are NOT checked into this repo. Searched: `find .claude/skills -name '*skill-creator*'` (empty), `grep -ril skill-creator` (only matches in docs and this ticket's artifacts, not an implementation). The repo's `evals/` harness targets QRSPI phase outputs (tickets, research, design), not skill authoring.

**Evidence:**

```
evals/suite.json
evals/graphite-evals.json
evals/fixtures/ticket_websocket.md   (QRSPI ticket fixtures, not skill fixtures)
scripts/run_eval.py  scripts/grade.py  scripts/check_scope.py
```

— `evals/` and `scripts/` listings
**Dependencies:** The ticket's instruction to "use the Anthropic skill builder skill" relies on the GLOBAL skill-creator, invoked at authoring time — its eval loop is external to this repo.
**Implicit contracts:** Validation of the new skill happens via the global skill-creator's own eval loop, not via a repo-local harness.

## Q5: What naming convention governs a skill's name frontmatter field and its containing directory, and how must the ticket's intended name ("using omlx cli") map to a valid slug?

**Answer:** Every in-repo skill uses a lowercase, hyphen-separated slug for both the directory name and the `name` frontmatter field, and the two always match (e.g. directory `qrspi-design` ↔ `name: qrspi-design`). The global non-qrspi skills follow the same gerund-style convention: `using-graphite-cli`, `writing-bash-scripts`, `skill-creator`. The ticket's intended name "using omlx cli" maps cleanly to the slug `using-omlx-cli` (directory `.claude/skills/using-omlx-cli/`, `name: using-omlx-cli`), matching the `using-graphite-cli` precedent.

**Evidence:**

```
.claude/skills/qrspi-design/  →  name: qrspi-design
.claude/skills/qrspi-questions/ → name: qrspi-questions
(global precedent) using-graphite-cli, writing-bash-scripts
```

— directory listing + frontmatter of `.claude/skills/*/SKILL.md`
**Dependencies:** Slug must be filesystem- and reference-safe.
**Implicit contracts:** directory name === `name` frontmatter value; lowercase + hyphens; gerund-style "using-<tool>" is the established naming for tool-wrapper skills.

## Q6: Where are skill description strings tuned for auto-invocation triggering, and is there a documented format or eval for description quality in this repo?

**Answer:** Description triggering tuning is NOT done by a repo-local tool — NOT FOUND. The description-optimization capability belongs to the global `skill-creator` skill (per its environment description: "optimize a skill's description for better triggering accuracy"), which is not checked in. In-repo, the observable convention is that every `description` leads with a capability statement and contains an explicit "Use when…/Trigger on…" clause (see `qrspi-work` description, which enumerates trigger phrases). No `evals/` entry scores skill descriptions.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>' ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (frontmatter)
**Dependencies:** Description quality is judged by the global skill-creator eval, not a repo harness.
**Implicit contracts:** Lead with the capability; include concrete trigger phrases and an explicit "Use when" clause to maximize auto-invocation accuracy.

## Q7: What is the enforced or recommended maximum size for a SKILL.md body, and where is that limit checked or documented?

**Answer:** There is NO repo-local enforcement of a SKILL.md size limit — NOT FOUND. No script in `scripts/` lints SKILL.md length. The "under 500 lines / 5000 tokens" target stated in the RUS-24 acceptance criteria is a convention from the agentskills.io / Anthropic skill standard, not a repo-checked rule. Observationally, the concise phase skills run 25-35 lines; only the orchestrator (`qrspi-work`, 730 lines) and `qrspi-ticket` (119 lines) exceed that, and the orchestrator is a special case. The practical guidance the new skill should follow: keep SKILL.md lean and push detail into `references/`.

**Evidence:**

```
   25-35  most phase SKILL.md files
   119    qrspi-ticket/SKILL.md
   730    qrspi-work/SKILL.md   (orchestrator, exceptional)
```

— `wc -l .claude/skills/*/SKILL.md`
**Dependencies:** None enforced in-repo.
**Implicit contracts:** Lean body + `references/` offload is the pattern that keeps a SKILL.md under the standard's size budget.

## Q8: How do existing skills handle platform- or environment-specific instructions so an agent on the wrong platform behaves correctly?

**Answer:** NOT FOUND as a direct in-repo precedent for hardware/OS gating — the qrspi skills are environment-agnostic (they manipulate Linear + git, not host hardware). The closest precedent is the `env` block the orchestrator relies on (Platform: linux, etc.) and the HARD-STOP infrastructure-error guidance in `qrspi-work` SKILL.md, which models how a skill encodes "stop and report rather than work around" preconditions. For an Apple-Silicon-only tool like omlx, the new skill will need to state its preconditions (macOS 15+, Apple Silicon, Python 3.10+) up front in the body, since no in-repo skill does platform gating to copy verbatim.

**Evidence:**

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve
When ANY operation fails due to permissions, authentication, configuration, or tooling errors ... STOP.
```

— `.claude/skills/qrspi-work/SKILL.md` (Error Handling)
**Dependencies:** None — the new skill introduces the platform-precondition pattern.
**Implicit contracts:** State preconditions explicitly; on infra failure, stop and report rather than attempting destructive workarounds (a repo-wide value worth mirroring in troubleshooting guidance).

## Q9: How do existing skills encode opinionated "prefer X over Y" decision guidance without overstepping into out-of-scope territory?

**Answer:** The strongest in-repo precedent is the global skills' description style and the `qrspi-work` State Dispatch table — a compact decision table mapping a condition to an action. Skills express opinion via (a) a "Use when / when NOT to use" framing in the description and (b) tables that map a situation to a recommended path. The new omlx skill should encode "prefer oMLX vs Ollama vs LM Studio" as a small decision table plus an explicit out-of-scope list, mirroring how `qrspi-work` separates valid states (table) from forbidden actions (explicit "Explicitly forbidden" list).

**Evidence:**

```
| Linear Status | Action |
|---|---|
| `Backlog` or `Selected` | → Run Planning |
| `Plan Review` | → Address Planning Feedback |
```

— `.claude/skills/qrspi-work/SKILL.md` (State Dispatch table)
**Dependencies:** None.
**Implicit contracts:** Decision tables + explicit scope boundaries are the idiom for opinionated guidance in this repo.

## Q10: What test or eval harness exists for skills in this repo, and what would a passing validation run for a new skill look like?

**Answer:** The `evals/` + `scripts/` harness exists but targets QRSPI **phase outputs** (ticket → questions → research → design grading), NOT skill-authoring artifacts. `scripts/run_eval.py`, `scripts/grade.py`, and `scripts/report.py` operate over `evals/suite.json` and ticket fixtures in `evals/fixtures/`. There is NO eval that validates a newly authored SKILL.md. For RUS-24, a "passing validation" therefore means: valid frontmatter modeled on existing skills, body under the size budget, references present, and the acceptance-criteria checklist satisfied — verified by inspection, not by this harness.

**Evidence:**

```
evals/suite.json
evals/fixtures/ticket_rest_endpoint.md
scripts/run_eval.py  scripts/grade.py  scripts/report.py
```

— `evals/` and `scripts/` listings
**Dependencies:** Skill validation falls to the global skill-creator eval loop and manual acceptance-criteria checking.
**Implicit contracts:** Repo eval harness is for QRSPI phase quality, not skill linting.

## Q11: Does the repo provide a way to lint or validate SKILL.md frontmatter and structure before a skill is considered done?

**Answer:** NOT FOUND. No frontmatter linter exists in `scripts/`. `scripts/check_scope.py` exists but (by name and its role in the research firewall) checks research/path scope, not SKILL.md schema. Validation of a new skill's frontmatter is done by matching the established in-repo pattern (Q3) and by the global skill-creator's checks at authoring time.

**Evidence:**

```
scripts/check_scope.py   (scope/path validation, not frontmatter schema)
scripts/run_eval.py scripts/revise.py scripts/diagnose.py scripts/report.py scripts/grade.py
```

— `scripts/` listing
**Dependencies:** None in-repo for SKILL.md schema.
**Implicit contracts:** "Valid frontmatter" = structurally identical to existing SKILL.md frontmatter.

## Q12: How does this repo surface skill-authoring failures or eval results so the author can confirm the skill meets acceptance criteria?

**Answer:** The repo surfaces eval results through `scripts/report.py` writing into the `results/` directory (top-level `results/` exists) and `run_loop.sh` orchestrating eval runs. However these surface QRSPI phase-eval results, not skill-authoring results. For RUS-24, confirmation that the skill meets acceptance criteria is by direct inspection against the ticket's checklist (frontmatter valid, body < 500 lines / 5000 tokens, references/ present, lifecycle/memory-tier/KV-cache/API/MCP/troubleshooting/decision-table coverage). No automated pass/fail signal is emitted for skill authoring.

**Evidence:**

```
results/                 (top-level eval output directory)
run_loop.sh
scripts/report.py
```

— top-level repo listing
**Dependencies:** Acceptance-criteria verification is manual/by-inspection for this skill.
**Implicit contracts:** Confirm completeness against the ticket's acceptance-criteria checklist.

---

## Discovered Patterns

- **Skill = directory + SKILL.md + optional `references/`.** No in-repo skill uses `scripts/` or `assets/`. The new omlx skill can legitimately use `references/` for the long detail (memory tiers, KV cache tuning, troubleshooting, flag reference) and keep SKILL.md lean.
- **Thin-wrapper idiom.** Every qrspi phase SKILL.md is a thin wrapper that delegates to an agent in `.claude/agents/`; the substantive content lives elsewhere. This is QRSPI-internal architecture and does NOT apply to a standalone tool-wrapper skill like using-omlx-cli, which should be self-contained (more like the global `using-graphite-cli`/`writing-bash-scripts` model: full guidance inside the skill, no agent delegation).
- **Frontmatter convention:** `name` (== dir slug) + `description` (capability + "Use when" trigger). `command`/`argument-hint`/`allowed-tools` are optional Claude Code extensions; a content/reference skill (no slash command) can omit them and rely on `name` + `description` alone.
- **Naming:** gerund "using-<tool>" slug (`using-graphite-cli`) → `using-omlx-cli`.
- **Opinionated guidance idiom:** compact decision tables + explicit forbidden/out-of-scope lists.
- **Repo value to mirror:** "stop and report on infra errors rather than destructive workarounds" — a good principle to echo in the omlx troubleshooting section (e.g. Metal OOM crash loop → reboot, do not chase workarounds).

## Inconsistencies

- The ticket directs "use the Anthropic skill builder skill" (global `skill-creator`), but that skill is NOT checked into this repo — it is environment-provided. So the build step depends on an external tool; the deliverable artifact (`.claude/skills/using-omlx-cli/`) lives in-repo while the builder does not.
- The stated acceptance limit "SKILL.md under 500 lines / 5000 tokens" is NOT enforced by any repo script; it is a convention. Most in-repo phase skills are far under it (25-35 lines), but `qrspi-work` (730) and `qrspi-ticket` (119) exceed the line target — confirming the limit is advisory and content-type-dependent, not mechanically enforced.
- `evals/`/`scripts/` give the impression of a skill-validation harness, but on inspection they grade QRSPI **phase outputs**, not authored skills. No automated gate validates a new SKILL.md.
