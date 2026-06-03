# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Q1: How does an existing skill in this repo flow from `SKILL.md` frontmatter through to invocation — what fields in the frontmatter (name, description, triggers) are consumed and where?

**Answer:** Skills are two-layer in this repo. A skill is a directory under `.claude/skills/<name>/` containing a `SKILL.md` with YAML frontmatter. The frontmatter fields actually used are: `name` (skill identifier), `description` (auto-invocation trigger text + human listing), `command` (the slash command, e.g. `/qrspi-research`), `argument-hint` (CLI argument shape), and `allowed-tools` (tool allowlist for the skill's own body). There is no separate "triggers" field — triggering is governed entirely by the `description` text. The QRSPI phase skills are *thin wrappers*: their `SKILL.md` body parses `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, and spawns a same-named agent (`.claude/agents/<name>.md`) via the `Agent` tool with a labelled input contract. The agent — not the skill — holds the actual phase logic.

**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
# /qrspi-research
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd` ...
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

— `.claude/skills/qrspi-research/SKILL.md:1-18`

**Dependencies:** Skill wrapper (`.claude/skills/<name>/SKILL.md`) → `Agent` tool → agent definition (`.claude/agents/<name>.md`). README confirms the split: "skills/ # Slash-command wrappers that invoke the phase agents" (`README.md:86`).
**Implicit contracts:** The skill `name` and the agent `subagent_type` must match (`qrspi-research` skill spawns `subagent_type: qrspi-research`). The wrapper assumes the agent definition file exists at the parallel `.claude/agents/<name>.md` path. The `command` value is conventionally `/` + `name`.

## Q2: Where are agent skills stored and discovered in this repo, and what is the on-disk directory layout for a single skill (SKILL.md plus optional `references/`, `scripts/`, `assets/`)?

**Answer:** Skills live under `.claude/skills/`, one directory per skill, each containing a `SKILL.md`. There are 10 skills present (qrspi-design, qrspi-implement, qrspi-plan, qrspi-pr, qrspi-questions, qrspi-research, qrspi-structure, qrspi-ticket, qrspi-work, qrspi-worktree). Only ONE skill uses a subdirectory: `qrspi-work/references/` holding `review-cascade.md`. No skill in this repo currently uses a `scripts/` or `assets/` subdirectory — those are conventional/optional but unexercised here. So the demonstrated layout is `.claude/skills/<name>/SKILL.md` plus an optional `references/<file>.md`.

**Evidence:**

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
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
```

— `.claude/skills/` (full file listing)

**Dependencies:** None beyond directory presence; `.claude/` is the agent/skill root.
**Implicit contracts:** A skill is identified by its directory name; the directory must contain a `SKILL.md`. `references/` is a sibling of `SKILL.md` inside the skill dir and is referenced by relative path from the SKILL.md body (see Q7).

## Q3: What exact `SKILL.md` frontmatter schema do existing skills use (required vs optional keys, value formats), and does it match the agentskills.io standard pattern referenced in the ticket?

**Answer:** Every skill `SKILL.md` uses this frontmatter key set: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. All 10 skills carry all five keys. Value formats: `name` is the skill slug (kebab-case, matches directory); `description` is a single-line string (qrspi-work wraps its long multi-sentence description in double quotes because it contains a colon/commas; others are unquoted); `command` is `/<name>`; `argument-hint` is an angle-bracket placeholder like `<ticket-id>`; `allowed-tools` is a comma-separated tool list (e.g. `Agent, Bash(pwd:*)`, with `Bash(pwd:*)` showing the parenthesized command-scoping syntax). NOTE: the agent definitions (`.claude/agents/*.md`) use a DIFFERENT schema — `name`, `description`, and a nested `claude:\n  tools: ...` block — not the skill schema. I cannot verify against the external "agentskills.io standard" because that is outside REPO_ROOT and the research firewall forbids fetching it; this answer documents only the in-repo convention.

**Evidence:**

```
allowed-tools: Agent, Bash(pwd:*)                                  # qrspi-research
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-...      # qrspi-ticket
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp...  # qrspi-work
```

— `.claude/skills/qrspi-research/SKILL.md:6`, `.claude/skills/qrspi-ticket/SKILL.md:6`, `.claude/skills/qrspi-work/SKILL.md:6`

Agent schema (different) for comparison:

```
---
name: qrspi-questions
description: Internal QRSPI workflow agent — generates 8-15 technical questions ...
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-questions.md:1-6`

**Dependencies:** None.
**Implicit contracts:** `allowed-tools` constrains what the skill body may call (wrappers list `Agent, Bash(pwd:*)`; the autonomous `qrspi-work` and the interactive `qrspi-ticket` list broader sets). Descriptions containing YAML-special characters (`:`, leading quotes) must be quoted, as qrspi-work demonstrates.

## Q4: What capabilities does the Anthropic skill-builder / skill-creator skill expose that this ticket requires using to generate the new skill?

**Answer:** NOT FOUND within project scope. There is no skill-creator/skill-builder definition inside REPO_ROOT. Searches (`grep -rn "skill-creator|skill_creator|skill-builder"`) found only *references* to it, never a definition: `.claude/agents/qrspi-structure.md:40` lists "invoking skill-creator" as an example validation pass, and the questions file itself mentions it. The skill-creator skill is a global/built-in skill living outside the repo (e.g. `~/.claude/skills/`), which the research firewall forbids reading. Its capabilities therefore cannot be enumerated from in-repo evidence. The only in-repo signal of intended use is the convention that skill creation should go through skill-creator and its eval loop (referenced as a project memory/global directive, not an in-repo file).

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

**Dependencies:** External (global) skill — outside REPO_ROOT.
**Implicit contracts:** The repo treats skill-creator as an external validation/authoring tool invoked during the implementation slice that produces skill files, not as a committed artifact.

## Q5: How does the project distinguish between a skill's slash-command wrapper and its underlying agent definition, and where does each live for an existing skill?

**Answer:** Two distinct files with distinct schemas and roles. The *wrapper* lives at `.claude/skills/<name>/SKILL.md` — frontmatter has `command`/`argument-hint`/`allowed-tools`; its body just parses arguments, resolves paths, and spawns the agent via the `Agent` tool (`subagent_type: <name>`). The *agent definition* lives at `.claude/agents/<name>.md` — frontmatter has a nested `claude.tools` block; its body is the full phase logic, inputs contract, rules, and firewall. The CLAUDE.md states this explicitly. Two exceptions to the thin-wrapper pattern: `qrspi-ticket` and `qrspi-work` carry their full logic *in the SKILL.md itself* (no separate agent file — there is no `.claude/agents/qrspi-ticket.md` or `qrspi-work.md`); they are interactive/orchestrator skills rather than spawned phase agents.

**Evidence:**

```
- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
```

— `.claude/CLAUDE.md` (Codebase conventions); agent dir has 8 files (qrspi-questions/research/design/structure/plan/worktree/implement/pr) — NO qrspi-ticket.md or qrspi-work.md, confirming those two skills are self-contained.

**Dependencies:** Wrapper depends on agent via `subagent_type`. Self-contained skills (ticket, work) depend only on the `Agent` tool to spawn *other* phase agents.
**Implicit contracts:** A phase that runs as a spawned agent needs BOTH a `.claude/skills/<name>/SKILL.md` wrapper and a `.claude/agents/<name>.md` definition. A standalone interactive skill needs only the SKILL.md. For a new "writing-bash-scripts" *knowledge* skill (not a spawned phase agent), the qrspi-ticket pattern (self-contained SKILL.md, optionally with `references/`) is the closest in-repo precedent.

## Q6: Is there an index, registry, or manifest that must be updated when a new skill is added, or are skills discovered purely by directory presence?

**Answer:** Skills are discovered purely by directory presence — no index/registry/manifest. There is no JSON/YAML/TOML file enumerating skills; the only config files in the repo are eval suites (`evals/suite.json`, `evals/graphite-evals.json`), the devcontainer config, and a seccomp profile — none register skills. No `settings.json` references skills. However, several *documentation* surfaces redundantly LIST the skills and would be stale (not broken) if not updated: `README.md` (Project Structure tree at 76-98, and skill tables at 56-65), `.claude/CLAUDE.md` ("Available skills" list). These are human-facing docs, not load-bearing for discovery.

**Evidence:**

```
=== any manifest/index/registry config? ===
./evals/suite.json
./evals/graphite-evals.json
./.devcontainer/devcontainer.json
./.devcontainer/etc/seccomp/hardened.json
=== settings.json mentions skills? ===   (none found)
```

— repo-wide `find` for `*.json/*.yaml/*.yml/*.toml` and `settings*.json`

**Dependencies:** Discovery mechanism = filesystem under `.claude/skills/`. Doc surfaces (README, CLAUDE.md) are downstream consumers that mirror the skill list manually.
**Implicit contracts:** Adding a skill = adding a directory with a SKILL.md; nothing else is *required* for discoverability. By convention, the README skill table and CLAUDE.md "Available skills" list should be updated to stay consistent.

## Q7: What is the enforced or conventional size limit for a `SKILL.md` body (the ticket cites under 500 lines / 5000 tokens) and how do existing skills handle overflow into `references/`?

**Answer:** No enforced limit exists in-repo (no linter or check found that bounds SKILL.md length). Observed sizes: the thin phase wrappers are 25-35 lines; `qrspi-ticket` is 119 lines; `qrspi-work` is by far the largest at 565 lines. So the existing corpus does NOT uniformly honor an "under 500 lines" guideline — qrspi-work exceeds it. The single example of `references/` overflow is qrspi-work: it pushes the bounded review-cascade detail into `references/review-cascade.md` (77 lines) and links it inline from the SKILL body rather than inlining it. That is the demonstrated overflow pattern: move a self-contained subtopic into `references/<topic>.md` and reference it by relative path.

**Evidence:**

```
   565 .claude/skills/qrspi-work/SKILL.md
   119 .claude/skills/qrspi-ticket/SKILL.md
    77 .claude/skills/qrspi-work/references/review-cascade.md
    25-35 (all other phase-wrapper SKILL.md files)
```

— `wc -l .claude/skills/*/SKILL.md`; reference link at `.claude/skills/qrspi-work/SKILL.md:282`: "the cascade is bounded to the phase's own artifacts (see `references/review-cascade.md`)."

**Dependencies:** SKILL.md body → `references/<file>.md` via relative path.
**Implicit contracts:** Overflow content is referenced by a relative `references/...` path from within the skill directory. The reference is loaded on demand (the SKILL body tells the reader/agent to consult it), keeping the main body shorter.

## Q8: How do existing skills that bundle executable helpers under `scripts/` reference and invoke those scripts, and what conventions (permissions, shebang) do they follow?

**Answer:** NOT FOUND — no skill in this repo bundles a `scripts/` subdirectory. The only subdirectory present under any skill is `qrspi-work/references/`. Executable helper scripts in this repo live at the repo-level `scripts/` directory (e.g. `scripts/qrspi_resolve.py`, `scripts/run_eval.py`), NOT inside skill directories. For the *convention* those repo-level scripts follow (transferable precedent): they are Python with `#!/usr/bin/env python3` shebangs and the executable bit set (e.g. `run_eval.py` is `-rwxr-xr-x`), and skills/agents invoke them by their repo-relative path via Bash (e.g. qrspi-work calls `python3 scripts/qrspi_resolve.py ...`). No in-skill `scripts/` invocation pattern exists to cite.

**Evidence:**

```
=== any scripts/ or assets/ dirs inside skills? ===
.claude/skills/qrspi-work/references     (only subdir; no scripts/ or assets/ anywhere)

-rwxr-xr-x ... scripts/run_eval.py
#!/usr/bin/env python3   (scripts/run_eval.py:1)
```

— `find .claude/skills -type d`; `scripts/run_eval.py:1`; `ls -l scripts/run_eval.py`

**Dependencies:** Repo-level `scripts/` invoked by skills/agents through Bash. Repo CLAUDE.md notes these scripts "self-locate the repo root from their own path" so they work from any cwd.
**Implicit contracts:** Executable helpers use `#!/usr/bin/env <interp>`, carry the exec bit, and are invoked by interpreter + path (`python3 scripts/x.py`); self-location from script path is preferred over cwd-relative assumptions.

## Q9: What does an existing skill's `description` field look like that governs auto-invocation triggering, and what level of specificity is needed to avoid false triggers for a broad topic like "bash scripts"?

**Answer:** Two description styles exist. (1) Terse phase descriptions: a one-line "what it does + when to use" (e.g. qrspi-structure: "Define vertical slices, types, and contracts from the approved design. Use after design is approved."). (2) A long, trigger-engineered description: qrspi-work's description is a quoted multi-sentence block that explicitly enumerates trigger phrases ("Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>' ...") and the conditions for invocation. The pattern for avoiding false triggers is to (a) state precise trigger phrases/conditions and (b) bound scope with "Use after/when ..." clauses. None of the in-repo descriptions include explicit *negative* triggers ("do NOT use for ..."), so for a broad topic like "bash scripts" the qrspi-work style of enumerated positive triggers plus an explicit scope boundary is the strongest in-repo precedent; a negative/skip clause would be a net-new addition not yet exemplified in this repo.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

```
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-questions/SKILL.md:3`

**Dependencies:** The `description` is the sole input to auto-invocation; no separate trigger config.
**Implicit contracts:** Description = trigger surface. Specificity (enumerated phrases + "Use when..." scope clause) reduces false triggers; quoting is required when the string contains colons/commas.

## Q10: How are skills verified or evaluated in this repo — is there an eval harness, and what is its current functional status?

**Answer:** There is an eval harness scaffold but it is a NON-FUNCTIONAL placeholder. `scripts/run_eval.py` defines the full structure — `EvalConfig`, suite loading/validation (`load_suite`), message building, parallel trial execution — but the core `execute_single` does NOT actually run an agent: its body is a stub that returns empty output (`result.output = ""`, `tokens = {"input":0,"output":0}`) with a comment "Placeholder for agent execution / Replace this block with actual agent invocation." Suites exist (`evals/suite.json`, `evals/graphite-evals.json`) with fixtures under `evals/fixtures/` and an empty `evals/golden/.gitkeep`. The repo CLAUDE.md and project memory both explicitly flag this: verify pure logic with the stdlib `_test.py` unit tests and orchestration with manual end-to-end runs, NOT with the eval harness. The skill-creator "eval loop" referenced in the question is part of the external skill-creator tool, not this repo's harness (see Q4).

**Evidence:**

```
        # ── Placeholder for agent execution ──
        # Replace this block with actual agent invocation:
        ...
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:117-135`

```
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions)

**Dependencies:** `run_eval.py` reads suite JSON + fixtures; would (when implemented) invoke an agent runtime that does not exist here.
**Implicit contracts:** Real verification = stdlib `_test.py` unit tests + manual e2e. The eval harness output cannot be trusted as a pass/fail signal in its current state.

## Q11: Is ShellCheck available in this environment, and how would the acceptance criterion "produces ShellCheck-clean output" be checked against sample scripts the skill guidance generates?

**Answer:** ShellCheck is NOT installed in this environment — `which shellcheck` returns "not found" and `shellcheck --version` errors with "command not found." It is not installed by the devcontainer Dockerfile (which installs system deps, Node.js 26.x, npm globals, and the Claude Code CLI, but no shellcheck) nor by `post-create.sh`. The repo *uses* ShellCheck conventions in its own bash (a `# shellcheck disable=SC2053` directive at `.devcontainer/config/protect-paths:116`), implying it is expected to be run somewhere, but the binary is absent from this container. Consequently, to check a "ShellCheck-clean" acceptance criterion one would first need to install shellcheck (e.g. `apt-get install shellcheck`, not currently in the image) and then run it against generated sample scripts. There is no existing in-repo harness that runs shellcheck.

**Evidence:**

```
=== shellcheck binary ===
shellcheck not found
(eval):1: command not found: shellcheck
```

— `which shellcheck` / `shellcheck --version` in this environment

```
116:      # shellcheck disable=SC2053  # intentional fnmatch via unquoted RHS
```

— `.devcontainer/config/protect-paths:116` (only shellcheck reference in repo)

**Dependencies:** ShellCheck would be an external toolchain dependency; the Dockerfile (`.devcontainer/Dockerfile:7-94`) is where system packages are added.
**Implicit contracts:** The repo authors already write ShellCheck-aware bash (disable directives), but verification depends on a binary not currently provisioned. Any acceptance check requiring shellcheck must provision it (Dockerfile/post-create) or run it where available.

## Q12: How can it be confirmed that a newly added skill is registered and discoverable by the agent (what surface lists available skills), so the new bash skill's presence and triggering can be verified?

**Answer:** Discoverability is filesystem-based (Q6), so confirmation = the directory `.claude/skills/<name>/SKILL.md` exists and parses. The repo provides no runtime "list skills" command or load-log of its own; the authoritative live list is the harness's available-skills surface (presented to the agent at session start — outside the repo's control). In-repo, the human-facing surfaces that should reflect a new skill are: `README.md` skill tables (`README.md:56-65`) and Project Structure tree (`README.md:76-98`), and the `.claude/CLAUDE.md` "Available skills" list. There is NO logging emitted on skill load within the repo. Practical verification: (1) confirm the SKILL.md frontmatter is valid YAML with the required keys (Q3); (2) confirm the skill appears in the session's available-skills list; (3) test a trigger phrase from its `description` to confirm auto-invocation.

**Evidence:**

```
| Skill | Command |
| Questions | `/qrspi-questions <ticket-id>` |
| Research | `/qrspi-research <ticket-id>` |
...
```

— `README.md:56-65` (manual skill table — a doc surface, not a discovery mechanism)

**Dependencies:** Live discovery = harness available-skills list (external). In-repo mirror surfaces = README + CLAUDE.md.
**Implicit contracts:** A new skill is "registered" the moment its directory+SKILL.md exist and frontmatter is valid; there is no separate activation step or load log to consult.

---

## Discovered Patterns

- **Thin-wrapper + agent split.** Eight QRSPI phases follow: `.claude/skills/<name>/SKILL.md` (thin wrapper: parse args, resolve `REPO_ROOT` from `pwd`, spawn `subagent_type: <name>`) → `.claude/agents/<name>.md` (full logic). Two skills (`qrspi-ticket`, `qrspi-work`) break the pattern and carry full logic in the SKILL.md with no agent file.
- **Two distinct frontmatter schemas.** Skills use `name/description/command/argument-hint/allowed-tools`; agents use `name/description/claude.tools`. They are NOT interchangeable.
- **`description` is the only trigger surface.** No separate triggers field; specificity (enumerated phrases + "Use when/after" scope) is how false triggers are reduced (qrspi-work is the engineered exemplar).
- **`allowed-tools` command-scoping.** `Bash(pwd:*)` shows the parenthesized syntax to restrict a tool to specific commands — wrappers grant only `Agent, Bash(pwd:*)`.
- **Self-locating repo-level scripts.** Executable helpers live in repo-root `scripts/`, use `#!/usr/bin/env python3`, carry the exec bit, self-locate the repo root, and are invoked as `python3 scripts/<x>.py` — never bundled inside skill dirs.
- **Templates as single source of truth.** Output formats live in `.qrspi/templates/`; skills/agents reference them rather than inlining (`README.md:126`).
- **Research/Questions firewalls enforced structurally.** The research agent's `claude.tools` omits Linear MCP; the questions agent omits Glob/Grep/Bash so codebase exploration is impossible (`.claude/agents/qrspi-questions.md:5`).
- **`references/` is the overflow mechanism** (only used by qrspi-work) — a sibling dir of SKILL.md, linked by relative path, consulted on demand.

## Inconsistencies

- **"Under 500 lines" guideline vs. reality.** The ticket-cited ~500-line / 5000-token guideline is NOT honored by the existing corpus: `qrspi-work/SKILL.md` is 565 lines. So the largest existing skill already violates the proposed limit — the bash-scripts skill cannot simply cite existing skills as conforming exemplars for that limit.
- **skill-creator referenced but not present.** `.claude/agents/qrspi-structure.md:40` and the questions file cite invoking skill-creator, but no skill-creator definition exists in-repo (it is global/external). Anyone following the convention must rely on a tool outside REPO_ROOT.
- **ShellCheck expected but absent.** The repo authors bash with ShellCheck disable directives (`.devcontainer/config/protect-paths:116`), implying ShellCheck is part of the intended workflow, yet the binary is not installed in this container and not provisioned by the Dockerfile/post-create. A "ShellCheck-clean" acceptance criterion has no runnable checker as-is.
- **Eval harness comments vs. behavior.** `scripts/run_eval.py`'s docstring says it "Runs each test case multiple trials in isolated environments, capturing full transcripts," but `execute_single` is a stub returning empty results — the harness does not actually execute anything. The CLAUDE.md correctly flags it as a placeholder, so docstring and behavior diverge.
- **Manual skill lists can drift.** Discovery is directory-based, but README (`:56-65`, `:76-98`) and CLAUDE.md both hand-maintain skill lists; nothing enforces they stay in sync with `.claude/skills/`.
