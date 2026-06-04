# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Q1: What is the on-disk directory layout an agentskills.io-standard skill must follow in this repo (`SKILL.md` plus `references/`, `scripts/`, `assets/`), and where do existing skills physically live versus their slash-command wrappers?

**Answer:** Skills live under `.claude/skills/<name>/SKILL.md`. There are 10 skills, all prefixed `qrspi-`. Only ONE skill is multi-file: `qrspi-work` has a `references/` subdirectory. There are **no** `scripts/` or `assets/` subdirectories under any skill in this repo, so the `references/`-as-only-extra-dir is the sole established pattern. The "agentskills.io standard" itself is NOT documented anywhere in this repo (no file mentions it). Slash-command wrappers and phase logic are split: the SKILL.md under `.claude/skills/<name>/` is a thin wrapper that spawns a matching agent definition in `.claude/agents/<name>.md`. Note: 8 agents exist (`qrspi-design/implement/plan/pr/questions/research/structure/worktree`) but there is no `qrspi-ticket.md` or `qrspi-work.md` agent — `qrspi-ticket` and `qrspi-work` carry their full logic in their SKILL.md instead of delegating to an agent.

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-research/SKILL.md   (+ 8 more single-file SKILL.md)
.claude/agents/qrspi-research.md         (+ 7 more agent defs)
```

— `.claude/skills/` (directory listing); `.claude/agents/` (directory listing)
**Dependencies:** `.claude/skills/*/SKILL.md` → spawns `.claude/agents/*.md` via the `Agent` tool. `qrspi-work` additionally reads `references/review-cascade.md`.
**Implicit contracts:** Skill directory name == `name` frontmatter field == agent `subagent_type` == slash command (minus leading `/`). One skill dir = one `SKILL.md`. `references/` is an optional sibling dir; `scripts/`/`assets/` are unused conventions (no precedent).

## Q2: How does the skill-creator skill generate a new skill — what inputs does it consume, what files does it scaffold, and where does it write its output?

**Answer:** NOT FOUND — no `skill-creator` skill exists in this repo. Searched `find . -iname '*skill-creator*'` (no matches except the literal string inside `.claude/agents/qrspi-structure.md` and the questions file), and `grep -rl "skill-creator"`. The only structural references are: `qrspi-structure.md` mentions it in prose, and `questions.md` (the input for this phase). The skill-creator referenced in the ticket is a globally-available Claude Code skill, OUTSIDE project scope — it is not vendored into `.claude/skills/`. Per the research firewall I cannot inspect resources outside `REPO_ROOT`. The only in-repo skill-authoring precedent to follow is the existing `.claude/skills/*/SKILL.md` + `.claude/agents/*.md` pattern documented in Q1.

**Evidence:**

```
$ find . -iname '*skill-creator*'   → (no files)
$ grep -rl "skill-creator" --include='*.md'
.claude/agents/qrspi-structure.md
.qrspi/RUS-27/questions.md
```

— search results, `REPO_ROOT` = `/workspaces/qrspi/.worktrees/RUS-27`
**Dependencies:** none in-repo.
**Implicit contracts:** none discoverable in-repo.

## Q3: How is a skill's content split between the `SKILL.md` body and the `references/` directory, and what mechanism loads reference files on demand versus eagerly?

**Answer:** Only `qrspi-work` demonstrates the split. Its 565-line SKILL.md carries the main procedure; detailed cascade logic is offloaded to `references/review-cascade.md` (77 lines) and referenced inline by relative path. The load mechanism is **prose instruction, not code** — the SKILL.md tells the agent to "see `references/review-cascade.md`", i.e. the model reads it on demand via its Read tool when the relevant branch of logic is hit. There is no eager-loading/include directive; nothing concatenates the reference automatically. Single-file skills (the other 9) inline everything in SKILL.md (the 8 phase wrappers are 25–35 lines because their substance lives in `.claude/agents/`).

**Evidence:**

```
282:phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`; reference file: `.claude/skills/qrspi-work/references/review-cascade.md:1`
**Dependencies:** `qrspi-work/SKILL.md` → `qrspi-work/references/review-cascade.md` (relative path, same skill dir).
**Implicit contracts:** Reference files are addressed by a path relative to the skill directory (`references/<file>.md`), and are pulled in lazily by the agent at read-time, not auto-injected.

## Q4: What frontmatter fields are required and valid in a `SKILL.md` (e.g. name, description, trigger conditions), and what format/constraints does each field carry?

**Answer:** Two distinct frontmatter shapes are used in-repo:

- **Skill (`.claude/skills/*/SKILL.md`)** fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. `name` = directory/slash name. `description` = triggering prose (plain or quoted scalar). `command` = the `/`-slash form (e.g. `/qrspi-research`). `argument-hint` = positional arg template (e.g. `<ticket-id>`). `allowed-tools` = comma-separated tool allowlist (e.g. `Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue`; `Bash(pwd:*)` shows scoped-permission syntax).
- **Agent (`.claude/agents/*.md`)** fields: `name`, `description`, and a nested `claude:` map with `tools:` (e.g. `Read, Write, Glob, Grep`).

No schema/validator enforces these — they are conventions only.

**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. ...
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`; agent shape at `.claude/agents/qrspi-research.md:1-6`
**Dependencies:** none.
**Implicit contracts:** `name` must equal the directory name and the `command` slug. `allowed-tools` gates which tools the wrapper may call; phase wrappers list `Agent` (+ `Bash(pwd:*)`, + Linear MCP tools where they fetch issues). Long descriptions may be a YAML quoted scalar (see `qrspi-work`).

## Q5: What naming convention governs a skill's directory name and its invocation name, and how does that name map to a `/`-slash command?

**Answer:** Convention is a strict 1:1:1:1 mapping — `directory name` == `name` frontmatter == `command` (with leading `/`) == agent `subagent_type`. All skills use the `qrspi-<phase>` kebab-case prefix. There is **no in-repo registration module**; mapping is by convention consumed by the Claude Code harness (external to this repo). The wrapper spawns the agent by passing `subagent_type: qrspi-<name>` to the `Agent` tool.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md:4:command: /qrspi-design
.claude/skills/qrspi-design/SKILL.md:19:   - `subagent_type: qrspi-design`
```

— `.claude/skills/qrspi-design/SKILL.md:4,19`
**Dependencies:** Registration is handled by the Claude Code runtime (outside `REPO_ROOT`); not present in-repo.
**Implicit contracts:** Renaming a skill requires renaming the directory, `name`, `command`, and the matching `.claude/agents/<name>.md` (and `subagent_type`) together or dispatch breaks.

## Q6: How is a skill's `description` field written to control auto-invocation/triggering accuracy, and are there length or wording conventions enforced?

**Answer:** Descriptions follow a "what it does + when to use it" pattern, often with explicit trigger phrases. Phase wrappers are short ("...Use after research is approved."). `qrspi-work` is the most elaborate: it embeds literal trigger variants ("'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'") and is a quoted scalar to allow punctuation. Nothing enforces length or wording — no linter, no length check. The agent `description` additionally states negative scope (e.g. research agent: "Not for general codebase exploration.") to suppress mis-triggering.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when
the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>',
'continue <ticket-id>', 'pick up <ticket-id>', ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`; negative-scope example `.claude/agents/qrspi-research.md:3`
**Dependencies:** none.
**Implicit contracts:** Description = the only triggering signal; include both purpose and explicit trigger phrasings; quote the scalar when it contains `:`/`'`. Negative scope ("Not for…") is used to reduce false triggers.

## Q7: Are there constraints or tooling in this repo for the stated `SKILL.md` size limit (under 500 lines / 5000 tokens), and how is body length currently measured or enforced for existing skills?

**Answer:** NOT FOUND — no in-repo tooling, lint, test, or doc enforces or even mentions a 500-line / 5000-token limit (`grep -rn "500 line|5000 token|agentskills"` → no real matches; the earlier hits were grep OR-term false positives). Body length is not measured by anything in the repo. Empirically, the largest skill is `qrspi-work/SKILL.md` at **565 lines** — already over the 500-line guideline the ticket cites — which is the in-repo case where reference-offloading (Q3) was used to keep the main body smaller. All other SKILL.md files are 25–119 lines.

**Evidence:**

```
  565 .claude/skills/qrspi-work/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
   35 .claude/skills/qrspi-implement/SKILL.md
   25 .claude/skills/qrspi-structure/SKILL.md  (smallest)
```

— `wc -l .claude/skills/*/SKILL.md`
**Dependencies:** none.
**Implicit contracts:** The 500-line/5000-token limit is an external (agentskills.io) standard, not repo-enforced; `qrspi-work` (565 lines) already exceeds it. Offloading to `references/` is the in-repo lever for staying small.

## Q8: When a skill ships `references/`, `scripts/`, and `assets/` subdirectories, what conventions govern relative-path references between `SKILL.md` and those subdirectories?

**Answer:** Only `references/` has an in-repo precedent. Convention: address subdir files by a path relative to the skill root, written as inline backticked text within prose, e.g. `` `references/review-cascade.md` `` — no leading `./`, no absolute path. `scripts/` and `assets/` have NO precedent inside any skill (none exist). Note: project-level (non-skill) scripts under the repo-root `scripts/` dir are invoked by absolute path from agent prompts (e.g. `scripts/qrspi_resolve.py`), but that is the workflow convention, not a skill-internal one.

**Evidence:**

```
282:... (see `references/review-cascade.md`). ...
```

— `.claude/skills/qrspi-work/SKILL.md:282`
**Dependencies:** `qrspi-work/SKILL.md` → `references/review-cascade.md`.
**Implicit contracts:** Relative-to-skill-root, backticked, lazily Read by the agent. No established pattern for `scripts/`/`assets/` inside a skill — a new skill bundling those would be setting precedent.

## Q9: How do existing skills that include `scripts/` declare runtime/interpreter and dependencies, and what would a script in this new skill need to remain stdlib-only / dependency-free per repo convention?

**Answer:** NO skill in this repo ships a `scripts/` directory, so there is no skill-internal precedent. The repo-wide convention lives in the project-level `scripts/` dir: every script is Python 3, declares `#!/usr/bin/env python3`, and is **stdlib-only**. The QRSPI scripts import only stdlib modules (e.g. `run_eval.py` imports `argparse, json, os, time, hashlib, dataclasses, pathlib, typing, concurrent.futures`). Each logic script ships a stdlib-only `*_test.py` sibling run with `python3` (per CLAUDE.md). A new skill's script should: use `#!/usr/bin/env python3`, import only the stdlib, and add a `_test.py` sibling.

**Evidence:**

```
#!/usr/bin/env python3
"""Execute an eval suite against a skill/agent prompt version. ..."""
import argparse, json, os, time, hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
```

— `scripts/run_eval.py:1-15`; test-sibling convention: `scripts/qrspi_*_test.py` (e.g. `scripts/qrspi_resolve_state_test.py`)
**Dependencies:** Project scripts depend only on Python 3 stdlib + `gh`/`gt` CLIs (invoked, not imported).
**Implicit contracts:** `#!/usr/bin/env python3` shebang; stdlib-only imports; self-locating from `__file__` for path-sensitive scripts; ship a `_test.py` sibling runnable with bare `python3`.

## Q10: Does the skill-creator skill provide an eval/benchmark loop, and what is required (eval fixtures, expected outputs, harness wiring) to run it against a newly created skill in this repo?

**Answer:** The skill-creator skill itself is out of project scope (Q2) so its eval loop cannot be inspected here. The in-repo eval harness is `scripts/run_eval.py` — a **non-functional placeholder** (per CLAUDE.md and confirmed in code: `execute_single` is an explicit stub that returns empty output and never invokes an agent). Wiring to run it against any skill: CLI `--skill <path-to-SKILL.md-or-agent.md>` `--suite <suite.json>` `--output <dir>` (plus `--trials`, `--workers`, `--timeout`). Fixtures live in `evals/fixtures/` (e.g. `ticket_rest_endpoint.md`), suites in `evals/suite.json` / `evals/graphite-evals.json`, golden outputs in `evals/golden/` (currently just `.gitkeep`). `load_skill()` just reads the prompt file; `build_messages()` assembles prompt + fixture file context. Because execution is stubbed, no real grading happens end-to-end today.

**Evidence:**

```
parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
parser.add_argument("--output", required=True, help="Output directory for results")
...
#   This stub captures the structure for integration with the actual agent runtime.
result.output = ""   # ── Placeholder for agent execution ──
```

— `scripts/run_eval.py:219-224` (args); `scripts/run_eval.py:107,117,133` (stub)
**Dependencies:** `run_eval.py` reads `evals/suite.json`, `evals/fixtures/*`, writes to an output dir. `evals/golden/` is empty.
**Implicit contracts:** The harness is structural-only; do NOT rely on it for real verification. Suite cases carry `id`, `prompt`, and optional `context.files` / `context.conversation_history`.

## Q11: How do existing skills handle the case where content overlaps another skill's domain — is there a precedent for cross-referencing rather than duplicating guidance?

**Answer:** The dominant precedent is **delegation, not duplication**: a SKILL.md wrapper holds almost no logic and points to its agent ("All prompt content lives in `.claude/agents/qrspi-research.md`"). Within the qrspi family, shared lifecycle/cascade knowledge is centralized in `references/review-cascade.md` and `docs/qrspi-pr-gated-lifecycle-design.md` and referenced by pointer rather than copied. CLAUDE.md itself models cross-referencing (it points to `docs/...` for the full design rather than restating it). There is no example of two skills duplicating a shared body; the established move is to extract to a reference/agent/doc and link.

**Evidence:**

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives
in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:11`; centralization example `.claude/skills/qrspi-work/SKILL.md:282` → `references/review-cascade.md`
**Dependencies:** wrappers → agents; agents/docs → shared design docs (`docs/qrspi-pr-gated-lifecycle-design.md`).
**Implicit contracts:** Single source of truth per concern; cross-reference by relative/repo path instead of restating. A broad-domain skill (e.g. GitHub Actions conventions) would follow this by pointing at canonical guidance rather than inlining duplicate rules.

## Q12: What is the established way to verify a skill in this repo prior to acceptance — does any skill ship automated tests, and how is the placeholder eval harness expected to be used versus manual end-to-end checks?

**Answer:** No skill ships automated tests (`grep "SKILL.md|skills/" scripts/*_test.py` → none). The repo's stated verification policy (CLAUDE.md, "Codebase conventions"): verify **pure logic with the stdlib-only unit tests** (`scripts/qrspi_*_test.py`) and verify **orchestration / skill behavior with manual end-to-end runs** — because the `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder (Q10). So for a prompt-only skill (no Python logic), acceptance rests on manual end-to-end invocation, not the eval harness and not unit tests. If the new skill bundles a script, that script gets a `_test.py` sibling.

**Evidence:**

```
The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` ("Codebase conventions"); stub confirmation `scripts/run_eval.py:107,117`
**Dependencies:** unit tests (`scripts/qrspi_*_test.py`, run with `python3`) for logic; manual runs for prompt behavior.
**Implicit contracts:** Prompt-only skills are verified by manual end-to-end checks; only scripted logic earns a `_test.py`. The eval harness must not be treated as a passing gate.

## Q13: How is skill invocation surfaced or logged when a skill triggers (auto or via slash command), so that correct triggering of the new skill can be confirmed during review?

**Answer:** NOT FOUND in project scope — there is no in-repo module that dispatches skills or logs skill invocations. Skill dispatch and any invocation logging are handled by the Claude Code runtime, which is outside `REPO_ROOT`. The only in-repo "invocation" surface is the `qrspi-batch.js` workflow (the sole `.js` under `.claude/`), which spawns *phase agents* programmatically — not slash-command/skill triggering, and it does not log skill auto-invocation. Within this repo, correct triggering can only be confirmed by manual observation during an end-to-end run (consistent with Q12), e.g. seeing the wrapper report its completion message to the user (each phase wrapper ends with a "X written to … then tell me 'approved'" message — see `.claude/skills/qrspi-research/SKILL.md:26`).

**Evidence:**

```
$ grep -rln "invoke|dispatch|register" --include='*.js' .claude/
.claude/workflows/qrspi-batch.js   (workflow agent-spawning, not skill dispatch/logging)
```

— search results; user-facing completion message convention at `.claude/skills/qrspi-research/SKILL.md:26`
**Dependencies:** runtime dispatch is external; `qrspi-batch.js` spawns agents but is workflow-driven, not slash-triggered.
**Implicit contracts:** No in-repo logging hook for skill triggering. Confirmation of triggering = manual observation / the wrapper's terminal user message.

---

## Discovered Patterns

- **Wrapper/agent split:** Every phase skill is a thin `.claude/skills/<name>/SKILL.md` that resolves args, computes paths, and spawns `subagent_type: <name>` defined in `.claude/agents/<name>.md`. The skill carries triggering + plumbing; the agent carries the real prompt. `qrspi-ticket` and `qrspi-work` are the two exceptions that keep logic in the SKILL.md (no matching agent file).
- **1:1:1:1 naming:** directory name == `name` frontmatter == `/command` == agent `subagent_type`, all kebab-case `qrspi-<phase>`.
- **Lazy reference offloading:** Large skills push detail into `references/*.md` and pull it in on demand via prose pointers (only `qrspi-work` does this today).
- **Self-locating, stdlib-only Python + `_test.py` siblings:** all repo scripts are `#!/usr/bin/env python3`, stdlib-only, with a stdlib-only unit-test sibling.
- **Staging + deterministic move (Fix A):** phase agents write to a short token-free staging path (`/tmp/phase-stage/<id>/<artifact>.md`) and a persist script moves it — to dodge weak-model mangling of the `qrspi` token in long Write paths.
- **Cross-reference over duplication:** shared knowledge lives once (a reference, an agent, or `docs/`) and is linked by path.
- **No enforcement tooling:** frontmatter fields, description style, and size limits are conventions only — nothing lints or validates them.

## Inconsistencies

- **Size guideline vs. reality:** The ticket cites a <500-line / <5000-token SKILL.md limit, but `qrspi-work/SKILL.md` is **565 lines** — already over — and nothing in the repo measures or enforces it.
- **`scripts/` / `assets/` are conventions without precedent:** The question set (and agentskills.io) assume skills may ship `scripts/` and `assets/`, but NO skill in this repo has either; only `references/` is actually used. A new skill using those dirs sets precedent.
- **Agent coverage gap:** 10 skills but only 8 agent files — `qrspi-ticket` and `qrspi-work` have no `.claude/agents/*.md`, breaking the otherwise-uniform wrapper/agent split.
- **MCP tool name binding:** CLAUDE.md (root project doc) says the Linear MCP server is referenced by the fixed name `linear` (`mcp__linear__*`), but every skill's `allowed-tools` hard-codes a per-user name `mcp__linear-russelltsherman__*` (e.g. `.claude/skills/qrspi-design/SKILL.md:6`). The committed frontmatter contradicts the "no per-user server name is hard-coded" claim in CLAUDE.md.
- **Eval harness is documented and CLI-complete but non-functional:** `run_eval.py` exposes a full argparse CLI and result dataclasses yet `execute_single` is a stub returning empty output (`run_eval.py:117,133`); `evals/golden/` holds only `.gitkeep`. Code structure implies a working harness that does not exist.
