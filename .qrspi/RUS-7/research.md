# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

> Scope note: The skills `skill-creator`, `using-graphite-cli`, and `writing-bash-scripts` referenced by several questions are **global/plugin skills, not present under this repo's `.claude/skills/`** (the only local skills are the 10 `qrspi-*` skills). Questions targeting those external skills are answered "NOT FOUND — outside project scope" with what the in-repo skills demonstrate by precedent instead.

## Q1: How does an existing SKILL.md reference and link to its `references/`, `scripts/`, and `assets/` subdirectories, and how are those auxiliary files loaded relative to the SKILL.md body?

**Answer:** Exactly one in-repo skill is multi-file: `qrspi-work`. It has a `references/` subdirectory (`references/review-cascade.md`) and links to it by a **relative path string inside the SKILL.md body prose** — there is no machine-readable manifest. The reference is a plain instruction telling the agent to read the file. No `scripts/` or `assets/` subdirectory exists in any local skill. The repo contains no loader code that resolves these paths; loading is the Claude Code harness's responsibility (out of repo). The convention is simply: place auxiliary file under the skill dir and cite it as `references/<name>.md` in the body.

**Evidence:**

```
# .claude/skills/qrspi-work/SKILL.md:282
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

```
# layout
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
```

— `.claude/skills/qrspi-work/SKILL.md:282`
— `.claude/skills/qrspi-work/references/review-cascade.md` (whole file)

**Dependencies:** SKILL.md body → relative `references/*.md` file. No code dependency; resolution is by the (external) harness.
**Implicit contracts:** Auxiliary content lives in a `references/` subdir of the skill directory and is referenced by a relative-path string the reading agent is expected to open on demand (progressive disclosure). Only `references/` is used in practice; `scripts/`/`assets/` are not exercised anywhere in this repo.

## Q2: What does the skill-creator skill take as input and what artifacts/files does it emit when generating a new skill?

**Answer:** NOT FOUND in repo. `skill-creator` is a global/plugin skill; it does not exist under `.claude/skills/`. The only in-repo references are mentions, not the definition: `.claude/agents/qrspi-structure.md:40` ("invoking skill-creator" as a validation step) and the questions file itself. Searched: `grep -rni "skill-creator\|skill_creator"` across `*.md`/`*.py`/`*.js` (only the two mention sites + questions.md), and `find . -name SKILL.md` (no skill-creator directory). Its input/output contract is not knowable from this repo.

**Evidence:**

```
# .claude/agents/qrspi-structure.md:40
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`
**Dependencies:** External skill; no in-repo dependency edge.
**Implicit contracts:** The repo treats `skill-creator` as the canonical way to author/validate a skill (a project convention reinforced by user global memory), but the contract details are external.

## Q3: What is the exact required frontmatter schema for a `SKILL.md` (field names, required vs optional, allowed values) as used by skills in this repo?

**Answer:** All 10 local SKILL.md files open with YAML frontmatter delimited by `---` lines. The fields actually used across them are: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. There is **no validator in the repo** enforcing this schema (no parser, no JSON schema, no lint) — it is convention derived from the existing files. Observed usage:

- `name` — present in all (string, matches the skill directory name in every case).
- `description` — present in all (string; may be quoted when it contains commas/colons, e.g. `qrspi-work`).
- `command` — present in all (the slash form, e.g. `/qrspi-research`).
- `argument-hint` — present in all (e.g. `<ticket-id>`, `<ticket-id> <slice-number>`, `<initial description>`).
- `allowed-tools` — present in all (comma-separated tool list; supports scoped forms like `Bash(pwd:*)` and MCP tool names like `mcp__linear-russelltsherman__get_issue`).

Note: the *agent* files in `.claude/agents/` use a **different** frontmatter shape (`name`, `description`, and a nested `claude:\n  tools:`), so the SKILL.md schema is distinct from the agent schema.

**Evidence:**

```
# .claude/skills/qrspi-research/SKILL.md:1-7
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

```
# .claude/agents/qrspi-research.md:1-6  (DIFFERENT schema — agent, not skill)
---
name: qrspi-research
description: Internal QRSPI workflow agent — ...
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`; `.claude/skills/qrspi-work/SKILL.md:1-7` (quoted description, expanded allowed-tools); `.claude/agents/qrspi-research.md:1-6`
**Dependencies:** Frontmatter consumed by the external Claude Code harness; no repo code reads it.
**Implicit contracts:** `name` must equal the directory name; `description` carries the auto-invocation trigger phrases (see Q12); `allowed-tools` is an allowlist using tool names, scoped-Bash `Tool(pattern:*)` syntax, and fully-qualified `mcp__server__tool` names.

## Q4: How are slash-command wrappers in `.claude/skills/` related to agent definitions in `.claude/agents/`, and which file types must coexist for a skill to be invocable?

**Answer:** The phase skills are **thin wrappers**: the SKILL.md (in `.claude/skills/<name>/`) parses arguments, resolves paths, and spawns the matching agent (in `.claude/agents/<name>.md`) via the `Agent` tool with `subagent_type: <name>`; all real prompt logic lives in the agent file. The skill explicitly states this. Pairing is by **identical base name** (e.g. `skills/qrspi-research/SKILL.md` ↔ `agents/qrspi-research.md`). Exceptions: `qrspi-ticket` and `qrspi-work` are self-contained skills with **no** agent counterpart (there are 10 skills but only 8 agent files); their logic lives entirely in the SKILL.md body. So: a wrapper-style skill needs BOTH a `skills/<n>/SKILL.md` and `agents/<n>.md`; a self-contained skill needs only the SKILL.md.

**Evidence:**

```
# .claude/skills/qrspi-research/SKILL.md:9-18
# /qrspi-research
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd` ...
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

```
# agent files present (8) vs skills (10)
agents/: qrspi-{design,implement,plan,pr,questions,research,structure,worktree}.md
skills/: the above 8 + qrspi-ticket + qrspi-work  (latter two have NO agent)
```

— `.claude/skills/qrspi-research/SKILL.md:9-25`; `.claude/agents/` listing (8 files); `.claude/skills/` listing (10 dirs)
**Dependencies:** `skills/<n>/SKILL.md` --(Agent tool, subagent_type)--> `agents/<n>.md`. README documents this split at README.md:86 and qrspi-orientation/CLAUDE.md ("Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`").
**Implicit contracts:** Wrapper and agent share the base name; the wrapper references the agent path in prose AND invokes it by `subagent_type`. A new CLI-wrapper skill could follow either pattern — but a *non-phase* utility skill (like the proposed Argo one) most resembles the self-contained `qrspi-ticket`/`qrspi-work` pattern (no agent needed).

## Q5: Where on disk must the new Argo skill directory live to be auto-discovered, and what naming convention (directory name vs. frontmatter `name`) is enforced?

**Answer:** Skills live at `.claude/skills/<skill-name>/SKILL.md` (relative to repo/worktree root). In every existing skill the directory name and the frontmatter `name` are **identical** (e.g. dir `qrspi-research` ↔ `name: qrspi-research`). No code in the repo enforces this — it is an invariant observed across all 10 skills, and the slash `command` field also mirrors the name (`/qrspi-research`). Discovery itself is performed by the external harness, not by any repo file (no enumerator/loader exists in-repo; see Q6).

**Evidence:**

```
# README.md:86-96  (documented location)
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/
    ...
    qrspi-work/        # Autonomous orchestrator (PR-gated state machine)
```

```
# invariant across all skills: dirname == name == command (minus slash)
dir qrspi-research  ->  name: qrspi-research  ->  command: /qrspi-research
```

— `README.md:86-96`; `.claude/skills/*/SKILL.md:2` (name) compared to directory names
**Dependencies:** Directory presence under `.claude/skills/` is the discovery surface; external harness reads it.
**Implicit contracts:** `directory name == frontmatter name == command without leading slash`. Follow this triple-match for the new Argo skill.

## Q6: Is there an index, manifest, or registry file that must be updated when a new skill is added, or is skill availability derived purely from directory presence?

**Answer:** No in-repo registry/manifest/index governs skill availability — it is derived purely from directory presence under `.claude/skills/`. Searched `grep -rniE "\.claude/skills"` across `*.py/*.js/*.sh`: the only references are the eval harness pointing at one file (`qrspi-batch.js:41` hardcodes `.claude/skills/qrspi-work/SKILL.md`) and run_loop.sh taking a skill path as an argument — neither is a registry. There IS, however, **human-facing documentation that lists skills** and would be stale if not updated: `README.md` (skills table at line 52+, tree at 86+) and `.claude/CLAUDE.md` ("Available skills" list). These are docs, not a functional registry.

**Evidence:**

```
# .claude/workflows/qrspi-batch.js:41  (only hardcoded skill path; not a registry)
const SKILL = '.claude/skills/qrspi-work/SKILL.md'
```

— `.claude/workflows/qrspi-batch.js:41`; `README.md:52-96`; `.claude/CLAUDE.md` "Available skills" section
**Dependencies:** None functional. Doc dependency: README + CLAUDE.md skill lists.
**Implicit contracts:** Adding a skill = create the directory; updating README/CLAUDE.md skill lists is a documentation convention (not enforced) to keep the human-facing catalog accurate.

## Q7: What is the enforced or conventional limit on SKILL.md body size (the ticket cites under 500 lines / 5000 tokens) — is this validated anywhere, or only a convention?

**Answer:** NOT FOUND as an enforced check — no line/token limit is validated by any repo script (no lint, no CI step references SKILL.md size). It is at most a convention (the cited 500-line/5000-token guidance originates from the external `skill-creator`, which is out of repo). Observed reality: most local skills are tiny thin wrappers (25–35 lines). Two exceed typical wrapper size — `qrspi-ticket` (119 lines) and `qrspi-work` (565 lines, the only one over 500 lines and it splits detail into `references/`). So the in-repo precedent both demonstrates the small-body norm and shows the >500-line case is handled by offloading to `references/` (see Q8).

**Evidence:**

```
# wc -l .claude/skills/*/SKILL.md
 28 qrspi-design     35 qrspi-implement   26 qrspi-plan       28 qrspi-pr
 26 qrspi-questions  26 qrspi-research    25 qrspi-structure  119 qrspi-ticket
565 qrspi-work       25 qrspi-worktree
```

— `wc -l` over `.claude/skills/*/SKILL.md`; grep for `500`/`5000`/`token`/`lint` found no validator
**Dependencies:** None enforce size.
**Implicit contracts:** Keep SKILL.md bodies small; when a body grows large (qrspi-work at 565 lines), push detail into `references/`. This is convention, unenforced.

## Q8: How do existing skills handle content that exceeds the body-size budget — what is the established pattern for splitting detail into `references/` files?

**Answer:** The single established example is `qrspi-work`: the SKILL.md keeps the orchestration state-machine prose, and the detailed cascade logic is extracted to `references/review-cascade.md`, referenced inline from the body (`see references/review-cascade.md`). The pattern is **progressive disclosure** — keep the always-loaded body lean; move conditional/detailed procedures into a `references/*.md` that the agent opens only when that branch applies. The reference file is itself a normal Markdown doc (headed `# Review Cascade Logic (PR-gated)`) with no special frontmatter.

**Evidence:**

```
# .claude/skills/qrspi-work/SKILL.md:282
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases

# .claude/skills/qrspi-work/references/review-cascade.md:1-3
# Review Cascade Logic (PR-gated)
Artifacts form a dependency chain, now split across **per-phase PR branches**:
```

— `.claude/skills/qrspi-work/SKILL.md:282`; `.claude/skills/qrspi-work/references/review-cascade.md:1-30`
**Dependencies:** SKILL.md body → `references/review-cascade.md` (relative path, prose link).
**Implicit contracts:** Reference files are plain Markdown (no frontmatter); the body must explicitly point the agent to them at the decision point where they become relevant.

## Q9: How are skills that wrap external CLIs (like the `argo` binary) expected to behave when the CLI is absent or a command fails — is there a precedent for prerequisite/availability checks?

**Answer:** No in-repo skill wraps an external binary, so there is no direct precedent inside `.claude/skills/`. (`using-graphite-cli`/`writing-bash-scripts` are external skills — NOT FOUND in repo.) The closest precedent for failure handling comes from the **agents and orchestrator scripts**, which establish a strong "HARD STOP on infrastructure/tooling error; surface the exact command and error; do not work around it" convention. Examples: the qrspi-work skill treats a failed required external call (Linear fetch) as a hard stop after one retry; agent definitions carry an explicit "HARD STOP: Infrastructure Errors" section (e.g. `command not found` → stop and report). This convention is reinforced by user global memory ("Error surfacing over workarounds").

**Evidence:**

```
# .claude/skills/qrspi-work/SKILL.md:52-54
2. **Fetch the ticket fresh** ... On failure, retry **once**; if the retry fails, this is a **hard stop**
   — print the exact error and exit.
```

— `.claude/skills/qrspi-work/SKILL.md:52-54`; agent "HARD STOP: Infrastructure Errors" sections (e.g. qrspi-research agent prompt; `command not found` listed as a stop trigger)
**Dependencies:** Pattern only; no shared prerequisite-check helper exists.
**Implicit contracts:** A CLI-wrapping skill should (a) check/announce prerequisites, and (b) on a missing binary or non-zero exit, surface the exact command + exact error and stop rather than improvise a workaround. There is no reusable availability-check utility to import — it must be written into the skill body.

## Q10: How are skills verified in this repo — is there an eval harness, and what is its current functional status?

**Answer:** There is an eval harness (`scripts/run_eval.py` + `evals/suite.json` + `evals/fixtures/` + `run_loop.sh` driver + `scripts/diagnose.py`/`scripts/revise.py`), but it is a **non-functional placeholder/stub**. `execute_single()` does not invoke any agent — it returns empty output and zeroed metrics, with a comment block describing what a "real implementation" would do. The suite/fixtures are real JSON, and `load_suite` does validate required fields, but no actual model execution occurs. This matches CLAUDE.md, which explicitly calls the harness "a **non-functional placeholder**", and project memory ("Eval harness is a placeholder"). Functional verification in this repo is done via **stdlib unit tests** (`scripts/qrspi_*_test.py`) and manual end-to-end runs, not the eval harness.

**Evidence:**

```
# scripts/run_eval.py:99-137  (execute_single is a stub)
"""... This stub captures the structure for integration with the actual agent runtime."""
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    ...
    result.output = ""
    result.files = []
    result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:93-143`; `evals/suite.json:1-40`; `.claude/CLAUDE.md` ("non-functional placeholder")
**Dependencies:** `run_loop.sh` → `run_eval.py` → `suite.json` → `fixtures/*.md`; `diagnose.py`/`revise.py` are sibling stubs.
**Implicit contracts:** Do not rely on `run_eval.py` to actually score a skill. Verify logic with `*_test.py` unit tests and orchestration with manual e2e runs.

## Q11: What lint or structural checks (if any) run against a `SKILL.md` and its directory layout before the skill is considered valid?

**Answer:** NOT FOUND — there is no SKILL.md linter or structural validator in the repo, and no CI step that checks skill layout. Searched `grep -rniE "frontmatter|lint|allowed-tools|skill.?path"` across code: matches are only the eval harness, run_loop.sh, and agent prose mentioning "linting" generically (`qrspi-structure.md:40`). The `.devcontainer/` is described as "Container sandbox for CI" but no CI config validating skills was found. The only "validation" anywhere is `run_eval.py:load_suite()`, which validates the *eval suite* JSON shape, not SKILL.md. Validity of a SKILL.md is therefore convention-only (matching the schema in Q3 and layout in Q5).

**Evidence:**

```
# scripts/run_eval.py:47-50  (only structural validator — for the eval suite, not SKILL.md)
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
```

— `scripts/run_eval.py:42-58`; `.claude/agents/qrspi-structure.md:40` (generic "linting" mention, no concrete linter)
**Dependencies:** None for SKILL.md.
**Implicit contracts:** A SKILL.md is "valid" if it matches the conventions of existing skills (correct frontmatter fields, dirname==name, `references/` for overflow). Nothing automated will catch a malformed one.

## Q12: How is a skill's invocation/triggering surfaced — what makes the `description` field effective for auto-invocation, and is there logging or any signal for whether a skill triggered?

**Answer:** Triggering is driven by the frontmatter `description` field: existing skills pack **explicit trigger phrases** into it so the (external) harness can match a user request to the skill. The clearest example is `qrspi-work`, whose description enumerates exact trigger variants ("'work on <ticket-id>'", "'continue <ticket-id>'", "'pick up <ticket-id>'") and the "use when" condition. Other skills follow the same "Use when…" / "Use after…" convention. There is **no in-repo logging or signal** that records whether a skill fired — that telemetry, like discovery and matching, belongs to the external harness, not this repo.

**Evidence:**

```
# .claude/skills/qrspi-work/SKILL.md:3 (trigger phrases embedded in description)
description: "... Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42').
... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>',
'pick up <ticket-id>', or any reference to progressing a QRSPI ticket ..."
```

```
# .claude/skills/qrspi-questions/SKILL.md:3 ("Use when ..." convention)
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
```

— `.claude/skills/qrspi-work/SKILL.md:3`; `.claude/skills/qrspi-questions/SKILL.md:3`
**Dependencies:** `description` → external harness matcher. No repo-side logging.
**Implicit contracts:** Effective auto-invocation requires the `description` to (a) state a one-line capability, (b) give a "Use when…" condition, and (c) for high-precision triggering, list concrete example phrases. No way to observe trigger outcomes from within the repo.

---

## Discovered Patterns

- **Thin-wrapper vs self-contained skills.** 8 phase skills are thin wrappers that delegate to a same-named `.claude/agents/<n>.md` via the `Agent` tool (`subagent_type`); 2 skills (`qrspi-ticket`, `qrspi-work`) are self-contained with no agent. A new utility skill (Argo) most resembles the self-contained pattern.
- **Triple-name invariant:** directory name == frontmatter `name` == `command` minus the leading slash, across all 10 skills. Unenforced but universal.
- **Two distinct frontmatter schemas:** skills use `name/description/command/argument-hint/allowed-tools`; agents use `name/description/claude.tools`. Do not mix them.
- **Progressive disclosure via `references/`:** the only oversize skill (`qrspi-work`, 565 lines) offloads detail to `references/review-cascade.md`, linked by relative-path prose. `scripts/` and `assets/` subdirs are conventionally available but unused in this repo.
- **`allowed-tools` is an allowlist DSL:** plain tool names, scoped Bash `Bash(pwd:*)`, and fully-qualified `mcp__server__tool` entries all appear.
- **Convention over enforcement:** there is NO loader, registry, frontmatter validator, size linter, or CI check for skills anywhere in the repo. Discovery and matching are entirely the external harness's job; the repo only supplies the files.
- **Hard-stop error culture:** agents/orchestrator consistently mandate "surface the exact command + error and stop" on tooling/infra failure rather than working around it — the relevant precedent for an Argo CLI wrapper's missing-binary/command-failure behavior.
- **Verification = unit tests + manual e2e**, not the eval harness, which is an explicit non-functional stub.

## Inconsistencies

- **Eval harness vs. its own docstrings:** `run_eval.py` reads as a working multi-trial runner (ThreadPoolExecutor, metrics, results.json), but `execute_single()` is a stub returning empty output. CLAUDE.md and project memory correctly flag it as non-functional; a reader of the code alone could be misled. (`scripts/run_eval.py:93-143` vs the file's overall structure.)
- **`skill-creator` referenced but absent:** `.claude/agents/qrspi-structure.md:40` instructs agents to validate by "invoking skill-creator", and user memory mandates it, yet no such skill exists in-repo — it is an external dependency the codebase assumes is installed.
- **Skill count mismatch in mental model:** there are 10 skills but only 8 agents; the README tree (README.md:86-96) lists all 10 skills but the agents list (README.md:79-85) lists 8 — correct, but easy to misread as a 1:1 pairing when 2 skills are agent-less.
- **"CI" claim without artifact:** `.devcontainer/` is described as a "Container sandbox for CI" (README.md:118) but no CI workflow/config that runs skill validation or the unit tests was found in the explored tree.
