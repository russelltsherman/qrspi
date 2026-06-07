# Research — Codebase Map

**Questions source:** questions.md @ RUS-22 (Generated 2026-06-02T00:00:00Z)
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

> Scope note: Several questions (Q5, Q8, Q9, Q10, Q11) target the **Gemini CLI binary** and its
> published interface — an external tool. No Gemini/Antigravity/Gemini-SDK code, config, or
> reference exists anywhere under `REPO_ROOT` (verified: `grep -rni "gemini\|antigravity"` across
> README.md, scripts/, .claude/, .devcontainer/ returns zero matches). Those questions are
> answered **NOT FOUND — target outside project scope**, with the in-repo facts that constrain
> how such a skill must be authored documented instead. This repository contains the **skill
> infrastructure** the new `using-gemini-cli` skill must conform to, not any Gemini integration.

---

## Q1: Where does the existing skill infrastructure live — what files/dirs in `.claude/agents/` and `.claude/skills/` are read when Claude Code loads a slash-command skill, and how is `SKILL.md` parsed to determine which references/scripts/assets to expose?

**Answer:** Skills live as **one directory per skill** under `.claude/skills/<name>/`, each containing a
`SKILL.md` with YAML frontmatter. Phase *agents* (the heavy prompt bodies) live as flat files
`.claude/agents/<name>.md`, also with YAML frontmatter. The two-layer split is a project convention
(documented in `.claude/CLAUDE.md`): the `SKILL.md` is a **thin slash-command wrapper** that spawns
the matching agent; the agent file holds the actual instructions.

`SKILL.md` frontmatter fields observed in-repo: `name`, `description`, `command`, `argument-hint`,
`allowed-tools`. Agent (`.claude/agents/*.md`) frontmatter uses `name`, `description`, and a
`claude:` block with `tools:`. Supplementary references are exposed by being placed in a
`references/` subdirectory and **referenced by relative path from the SKILL.md prose** — there is no
declarative "assets/scripts" manifest field; the model is told to read them. The only example in-repo:
`.claude/skills/qrspi-work/references/review-cascade.md`.

**Evidence:**
```
--- .claude/skills/qrspi-plan/ ---  SKILL.md
--- .claude/skills/qrspi-work/ ---  SKILL.md  references/review-cascade.md
--- .claude/agents/ ---  qrspi-design.md qrspi-implement.md ... qrspi-research.md (flat files)
```
— `.claude/skills/` (directory listing) and `.claude/agents/` (directory listing)

```
---
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation. ...
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
---
```
— `.claude/skills/qrspi-ticket/SKILL.md:1-7`

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts ...
claude:
  tools: Read, Write, Glob, Grep
---
```
— `.claude/agents/qrspi-research.md:1-6`

**Dependencies:** SKILL.md (wrapper) → `.claude/agents/<name>.md` (agent body) via the `Agent`
tool's `subagent_type`. Agents → `.qrspi/templates/<artifact>.md` (output format, single source of
truth) per README.md:126.
**Implicit contracts:** (1) `SKILL.md` `name` must equal the agent `name` it spawns (e.g.
`qrspi-research`). (2) The `SKILL.md` `command` is the slash command. (3) `allowed-tools` gates
the wrapper's tools; the agent's `claude: tools:` block gates the agent's tools. (4) References are
plain markdown read on demand — no registration step. The README documents this exact layout at
README.md:86-96.

## Q2: How does the batch orchestrator in `.claude/workflows/qrspi-batch.js` register and invoke skills, and what entrypoint mechanism links a skill name (e.g. `/qrspi-design`) to its underlying agent definition?

**Answer:** The orchestrator does **not** invoke slash-command skills at all. It bypasses the
`SKILL.md` wrappers and spawns the **typed agents directly** via the workflow runner's
`agent(prompt, { agentType })` call, where `agentType` is the agent's `name` (e.g.
`'qrspi-research'`, matching `.claude/agents/qrspi-research.md`). The link from name → agent is the
`agentType` string resolving to a registered `.claude/agents/<name>.md` file. There is no skill
registry or skill-name dispatch table in the JS.

The reason is documented in the file header: a workflow-subagent is not given the `Agent`
(subagent-spawning) tool, but the **workflow RUNNER can** spawn registered agent types, so
orchestration is lifted into the script.

**Evidence:**
```
// The Workflow RUNNER (this script) CAN
// spawn registered agent types via agent({ agentType }). So orchestration is
// lifted into the script: it spawns the typed phase agents directly ...
```
— `.claude/workflows/qrspi-batch.js:20-23`

```
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```
— `.claude/workflows/qrspi-batch.js:209` (inside `runPhase`)

```
if (!await runPhase('research', 'qrspi-research',
    `TICKET_ID = ${t.id}
QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
OUTPUT_PATH = ${stg(t.id, 'research')}
TEMPLATE_PATH = ${tpl(wd, 'research.md')}
REPO_ROOT = ${wd} ...
```
— `.claude/workflows/qrspi-batch.js:275-282`

**Dependencies:** `qrspi-batch.js` → `agent({agentType})` runtime → `.claude/agents/<name>.md`.
Worker agents (resolve/finalize/persist/commit) follow `.claude/skills/qrspi-work/SKILL.md`
(`const SKILL = '.claude/skills/qrspi-work/SKILL.md'`, qrspi-batch.js:41) for git/gh/Linear mechanics.
**Implicit contracts:** (1) Each phase agent receives inputs as **plain `KEY = value` lines in the
prompt body** (TICKET_ID, OUTPUT_PATH, TEMPLATE_PATH, etc.), not structured args. (2) Phase agents
write to a **token-free staging path** `/tmp/phase-stage/<id>/<artifact>.md` (the `stg()` helper,
qrspi-batch.js:175), never the canonical `.qrspi` path — then `scripts/qrspi_persist.py` moves it.
(3) The agent returns a one-line summary string; success is gated on the persisted artifact, not the
return value (`runPhase`, qrspi-batch.js:204-224).

## Q3: What is the exact file layout of an existing skill (e.g. `qrspi-design`, `qrspi-research`), and does each follow a canonical directory structure?

**Answer:** Yes — canonical and uniform. Every QRSPI skill is a directory `.claude/skills/<name>/`
containing exactly one `SKILL.md`. Only `qrspi-work` additionally has a `references/` subdir. There
are **no** `scripts/`, `assets/`, or other subdirs inside any skill directory. The companion agent
body is a sibling file at `.claude/agents/<name>.md` (NOT nested inside the skill dir).

A phase skill's `SKILL.md` is short (1.0–1.5 KB) and stereotyped: frontmatter +
`# /<command>` header + a "Thin wrapper that spawns the `<name>` agent" sentence + numbered Steps
(parse args, resolve REPO_ROOT from `pwd`, spawn agent with `KEY = value` inputs, verify artifact
non-empty, message the user). `qrspi-ticket` (4.9 KB) and `qrspi-work` (26.9 KB) are the
exceptions — they carry full logic inline rather than delegating to an agent.

**Evidence:**
```
.claude/skills/qrspi-design/      SKILL.md (1514 B)
.claude/skills/qrspi-research/    SKILL.md (1240 B)
.claude/skills/qrspi-plan/        SKILL.md (1116 B)
.claude/skills/qrspi-work/        SKILL.md (26860 B) + references/review-cascade.md
```
— directory listing of `.claude/skills/`

```
# /qrspi-plan
Thin wrapper that spawns the `qrspi-plan` agent. All prompt content lives in
`.claude/agents/qrspi-plan.md`.
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-plan`
   - Prompt body containing the five inputs: ...
```
— `.claude/skills/qrspi-plan/SKILL.md:9-19`

**Dependencies:** skill dir ↔ sibling agent file by shared `name`.
**Implicit contracts:** The canonical phase-skill template = thin wrapper delegating to an agent.
A *standalone, non-phase* skill (which `using-gemini-cli` likely is — a "how to use tool X" skill, not a
QRSPI lifecycle phase) has the closest precedent in `qrspi-ticket` (self-contained logic in SKILL.md,
no spawned agent), not the thin-wrapper phase skills.

## Q4: How are agent skills discovered at runtime — manifest, glob, or hardcoded registry mapping skill names → SKILL.md and reference scripts?

**Answer:** **By convention/auto-discovery — there is no in-repo manifest, glob config, or registry.**
There is no `.claude/settings.json`, no skill index file, and no registry anywhere in the repo
(verified: `.claude/*.json` → no matches; no `settings*` files). Discovery is performed by the
Claude Code harness itself: each `.claude/skills/<name>/SKILL.md` is a skill (keyed by its `name`/
`command` frontmatter) and each `.claude/agents/<name>.md` is a spawnable agent type (keyed by
`name`). The mapping is **directory-structure + frontmatter `name`**, not a declared list.

**Evidence:**
```
=== any registry/manifest/settings files ===
(eval):1: no matches found: .claude/*.json
(none found above means auto-discovery)
```
— shell check for `.claude/*.json` / `settings*` (no matches)

```
.claude/skills/   # Slash-command wrappers that invoke the phase agents
.claude/agents/   # phase agent definitions
```
— README.md:74-96 documents the layout with no registry file

**Dependencies:** The harness (outside the repo) is the discovery engine; the repo only supplies the
conventional directory tree.
**Implicit contracts:** To add `using-gemini-cli`, create `.claude/skills/using-gemini-cli/SKILL.md`
with a unique `name` — no registration edit anywhere is needed. (Note: the QRSPI skills are
namespaced `qrspi-*`; a `using-*` name would be consistent with the global skill-naming style seen in
the available-skills list, e.g. `using-graphite-cli`.)

## Q5: What CLI flags, env vars, and config paths does the Gemini SDK expose (GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT, --yolo, --sandbox) that must be encoded in the skill's SKILL.md?

**Answer:** **NOT FOUND — target outside project scope.** The Gemini CLI binary is an external tool
not present in this repository. Searched `grep -rni "gemini\|antigravity\|GEMINI_API_KEY\|GOOGLE_CLOUD_PROJECT\|--yolo\|--sandbox"`
across README.md, scripts/, `.claude/`, `.devcontainer/` — zero matches for any Gemini-specific
token. The repo cannot supply Gemini's flag/env surface; that must come from Gemini's published docs
during Design.

> In-repo constraint that bounds the answer: the only `--yolo`/`yolo`/`--sandbox`-adjacent
> precedents are unrelated to Gemini — `.devcontainer/config/post-create.sh:26` defines a `yolo()`
> bash function wrapping `claude --dangerously-skip-permissions`, and qrspi-batch.js:23,29 uses
> "sandbox" to mean the JS workflow execution sandbox. Neither is Gemini.

**Dependencies / Implicit contracts:** N/A in-repo.

## Q6: How does `qrspi-ticket` invoke Claude Code tools, and how should the new Gemini CLI skill encode tool usage (read/write/grep/replace/shell/subagent delegation) compatibly with the harness?

**Answer:** `qrspi-ticket` declares its permitted tools in the `allowed-tools` frontmatter list and
then invokes them by **named instruction in the prose** — it does not call tools through a wrapper
API. Its `allowed-tools` is `Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue`.
The body then instructs the model to e.g. "Call `mcp__linear-russelltsherman__save_issue` with ..."
and "run `mkdir -p .qrspi/<id>` via Bash". This is the canonical Claude Code tool-usage encoding:
**enumerate tools in `allowed-tools`, then reference them by their exact tool name in the steps.**

Subagent delegation, when needed, is done with the `Agent` tool listing it in `allowed-tools` and
spawning via `subagent_type` (see the phase wrappers, qrspi-plan/SKILL.md:18 `subagent_type:
qrspi-plan`). To run an external CLI (the Gemini case), the precedent is the **`Bash` tool**, exactly
how qrspi-ticket runs `mkdir` and how the persist/finalize workers run `python3 scripts/...` in
qrspi-batch.js. Standard Claude tool names available in-repo: `Read, Write, Edit, Glob, Grep, Bash,
Agent` (the canonical tool vocabulary; note Claude uses `Edit`, not "replace").

**Evidence:**
```
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
```
— `.claude/skills/qrspi-ticket/SKILL.md:6`

```
1. Call `mcp__linear-russelltsherman__save_issue` with: ...
4. Create the local artifact directory: run `mkdir -p .qrspi/<id>` via Bash.
```
— `.claude/skills/qrspi-ticket/SKILL.md:106-117`

```
claude:
  tools: Read, Write, Edit, Glob, Grep, Bash
```
— `.claude/agents/qrspi-implement.md:4-5` (the full standard tool set; `Edit` is the
replace/edit tool, there is no "replace" tool)

**Dependencies:** SKILL.md `allowed-tools` → harness tool grants → `Bash`/MCP/`Agent` at runtime.
**Implicit contracts:** (1) A tool not listed in `allowed-tools` cannot be used. (2) External-CLI
invocation goes through `Bash` (no dedicated "shell"/"subprocess" tool exists; qrspi-batch.js worker
prompts all shell out via `Bash`). (3) MCP tools are named `mcp__<server>__<tool>`. (4) Tool names
are case-sensitive exact strings.

## Q7: How should session commands (`/chat save`, `/chat resume`, `/compact`) be encoded in SKILL.md when calling Gemini CLI non-interactively from another agent, given non-interactive mode lacks session persistence?

**Answer:** **NOT FOUND for Gemini specifics — outside project scope** (no Gemini CLI in repo). The
in-repo analog: QRSPI handles "no session persistence across agent calls" by making each agent
**stateless** and passing all needed state explicitly as `KEY = value` prompt inputs plus
file-on-disk artifacts. There is no session save/resume mechanism in the repo; continuity between
slices is carried by the `PREVIOUS_NOTES` prompt field and the `impl-log.md` artifact, not a session
store.

**Evidence:**
```
PREVIOUS_NOTES =
${previousNotes || '(none — first slice)'}
```
— `.claude/workflows/qrspi-batch.js:380-381` (state passed explicitly, not via a session)

> The repo's own guidance mentions `/compact` only as a human-facing context-management hint
> (`.claude/CLAUDE.md` "Use `/compact` if context grows large within a phase"), never as a
> programmatic call. There is no `/chat save`/`/chat resume` usage anywhere.

**Dependencies / Implicit contracts:** The established pattern for cross-call continuity without
sessions = explicit prompt inputs + a persisted markdown artifact. Any Gemini session encoding should
follow this stateless-handoff convention rather than relying on Gemini interactive session state.

## Q8: What is the config resolution priority (CLI args > env > project > global > defaults), and how should the skill surface this hierarchy for locating/writing a GEMINI.md context file?

**Answer:** **NOT FOUND — outside project scope.** Gemini's configuration loader and `GEMINI.md`
resolution are external; no such logic or file exists in the repo (zero `GEMINI` matches).

> In-repo precedent for "context file" + "config precedence" that the design can mirror:
> (1) `CLAUDE.md` is the project context file, layered: user-global `~/.agents/AGENTS.md` is
> `@`-imported by both `/home/vscode/.claude/CLAUDE.md` and the project `.claude/CLAUDE.md` — i.e.
> project context composes over global via `@import`. (2) The devcontainer launcher establishes an
> env-var precedence pattern: `ANTHROPIC_MODEL="${OLLAMA_MODEL:?...}"` with `:?` to fail loudly when
> a required var is unset, and `${OMLX_PORT:-8000}` defaulting — i.e. env var with explicit default,
> CLI/launcher overriding the base (post-create.sh:88-98).

**Evidence:**
```
ANTHROPIC_BASE_URL="http://host.docker.internal:${OLLAMA_PORT:-11434}"
ANTHROPIC_MODEL="${OLLAMA_MODEL:?set OLLAMA_MODEL to an installed Ollama model ...}"
```
— `.devcontainer/config/post-create.sh:91-92` (env-with-default / required-env precedence idiom)

**Dependencies / Implicit contracts:** The `GEMINI.md`-as-context-file concept maps onto the repo's
`CLAUDE.md`/`AGENTS.md` layered-context convention; actual Gemini precedence rules must come from
Gemini docs.

## Q9: How should the skill handle the deprecation notice — Google transitions free/personal accounts to Antigravity CLI after June 18, 2026, and the existing gemini-cli binary stops working?

**Answer:** **NOT FOUND — outside project scope.** No deprecation handling, Antigravity reference, or
migration path exists in the repo (zero `antigravity` matches). This is a documentation-content
decision for the SKILL.md "limitations/caveats" section, sourced from Google's announcement, not the
codebase.

> In-repo precedent for documenting time-bound caveats inline: the devcontainer launcher comments
> record exact tool versions a behavior was verified against ("Determined empirically against claude
> 2.1.160 + ollama 0.24.0", post-create.sh:69-70) — the repo's convention is to **pin caveats to
> verified versions/dates in prose comments**, which a deprecation notice in SKILL.md should follow.

**Dependencies / Implicit contracts:** N/A in-repo (pure documentation content).

## Q10: What happens when YOLO mode auto-approves but hits a shell-redirection prompt or Plan-mode transition — how should agents detect/handle these bugs?

**Answer:** **NOT FOUND — outside project scope.** These are Gemini CLI runtime behaviors; the repo
has no Gemini invocation wrapper and no error-handling path for it. The repo's only YOLO concept is
the unrelated `yolo`/`ollama-yolo` bash functions wrapping Claude with
`--dangerously-skip-permissions` (post-create.sh:26,62-64,102-104) — not Gemini, and they contain no
prompt-detection logic.

> In-repo error-handling convention the new skill should adopt: **HARD STOP on infrastructure/tooling
> errors — surface the exact error, do not retry, do not improvise.** This is stated identically in
> the agent prompts and worker prompts.

**Evidence:**
```
If (and only if) ... return that error verbatim (HARD STOP — do NOT
retry, do NOT improvise alternative commands or paths).
```
— `.claude/workflows/qrspi-batch.js:251-252` (resolve worker); same idiom at qrspi-batch.js:196-197
(persist worker) and `.claude/agents/qrspi-research.md:56-58` ("HARD STOP: Infrastructure Errors").

**Dependencies / Implicit contracts:** Any Gemini-invocation wrapper should follow the repo-wide
HARD-STOP-and-surface-verbatim error contract rather than silently working around prompts.

## Q11: When running Gemini CLI as an autonomous subagent via --sandbox, what Docker/Podman sandbox profiles are available, and how does SANDBOX_MOUNTS interact with external dir mounts?

**Answer:** **NOT FOUND — outside project scope.** No `SANDBOX_MOUNTS`, Gemini sandbox profile, or
Podman config exists in the repo (zero matches). The repo's `.devcontainer/` is a **VS Code dev
container** for the QRSPI project itself, unrelated to a Gemini `--sandbox` runtime.

> In-repo precedent: the devcontainer (`.devcontainer/config/post-create.sh`) is the only
> containerization, and it configures the Claude Code shell environment (env vars, git safe.directory,
> launcher functions) — it does not implement a per-invocation sandbox with mount profiles.

**Dependencies / Implicit contracts:** N/A in-repo; Gemini sandbox details must come from Gemini docs.

## Q12: How should the skill author validate that invoking Gemini CLI from a parent agent produces expected output — is there a test harness (evals/ + scripts/run_eval.py) or a manual smoke-test pattern?

**Answer:** There is an `evals/` + `scripts/run_eval.py` harness, but it is a **non-functional
placeholder** — `execute_single()` returns empty stubbed output (`result.output = ""`) with an
inline "Placeholder for agent execution" comment; it never actually runs an agent or a CLI. Both
`.claude/CLAUDE.md` and the project memory state the harness is non-functional and that verification
is done via **stdlib unit tests + manual end-to-end runs**. So the validation pattern is: pure logic
→ `scripts/*_test.py` (stdlib `unittest`, run with `python3`); orchestration/CLI behavior → manual
e2e smoke test.

**Evidence:**
```python
try:
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation:
    ...
    messages = build_messages(case)
    result.output = ""
    result.files = []
    result.tokens = {"input": 0, "output": 0}
```
— `scripts/run_eval.py:116-135`

```
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```
— `.claude/CLAUDE.md` (Codebase conventions, final bullet)

**Dependencies:** `run_eval.py` reads `evals/suite.json` (`load_suite`, run_eval.py:42-58) and a
skill/agent prompt file (`load_skill`, run_eval.py:61-64); fixtures live in `evals/fixtures/`.
**Implicit contracts:** Do **not** rely on `run_eval.py` to prove a skill works — it produces empty
results. Real verification = unit tests (for any extracted pure logic) + a manual cross-agent smoke
test.

## Q13: What integration tests exist for the existing skills (qrspi-design, qrspi-research, etc.), and how should the Gemini CLI skill's correctness be verified end-to-end before merge?

**Answer:** There are **no integration tests for the skills/agents themselves** — no test exercises
`SKILL.md` or `.claude/agents/*.md` behavior. The only automated tests are **stdlib unit tests for
the Python orchestration logic**: `scripts/qrspi_persist_test.py`, `scripts/qrspi_pr_state_test.py`,
`scripts/qrspi_resolve_state_test.py`, `scripts/qrspi_resolve_test.py` (each a `_test.py` sibling of
its module, run with `python3`). Skills/agents are markdown prompts with no executable test coverage;
the project verifies them by **manual end-to-end runs** (per `.claude/CLAUDE.md` and memory).

**Evidence:**
```
scripts/qrspi_persist_test.py
scripts/qrspi_pr_state_test.py
scripts/qrspi_resolve_state_test.py
scripts/qrspi_resolve_test.py
```
— `ls scripts/*_test.py` (the complete test inventory; all target Python modules, none target a skill)

```
- All of the above have stdlib-only unit tests as `_test.py` siblings
  (`scripts/qrspi_*_test.py`, run with `python3`).
```
— `.claude/CLAUDE.md` (Codebase conventions)

**Dependencies:** unit tests → their sibling `scripts/qrspi_*.py` modules only.
**Implicit contracts:** A pure-markdown skill like `using-gemini-cli` would carry **no automated
test** under the current conventions — correctness is established by manual e2e smoke test. If any
reusable shell/python logic is extracted (e.g. an invocation wrapper script under `scripts/`), the
convention requires a stdlib `_test.py` sibling.

## Q14: How should agent calls to Gemini CLI be logged — is there an existing observability layer (logs, metrics, tracing hooks) that captures when a skill invokes an external CLI, and what metadata fields should be attached?

**Answer:** There is **no application-level observability layer** (no logging library, metrics, or
tracing hooks) for skill/CLI invocation in the repo. The only logging present is:
(1) the workflow runner's `log(...)` calls inside `qrspi-batch.js`, which emit human-readable
progress lines to the workflow's own output (e.g. `log(\`  ${id}: ${name} → saved ...\`)`,
qrspi-batch.js:222) — these are orchestration breadcrumbs, not structured telemetry; and
(2) `scripts/run_eval.py`'s `print()` progress lines and `results.json` dump (run_eval.py:185-213),
which captures per-trial `duration_ms`, `tokens`, `tool_calls`, `transcript`, `error` — but only as a
**placeholder** that never populates them with real data (Q12). There is no hook that fires when a
skill shells out to an external CLI.

**Evidence:**
```
log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```
— `.claude/workflows/qrspi-batch.js:222` (the only "logging" idiom — `log()` progress lines)

```python
result.duration_ms = 0.0
result.tokens: dict = field(default_factory=dict)
result.tool_calls: list = field(default_factory=list)
result.transcript: list = field(default_factory=list)
```
— `scripts/run_eval.py:19-29` (`ExecutionResult` — the only place metadata fields are defined, and
they are stub-filled per run_eval.py:133-137)

**Dependencies:** `log()` is a workflow-runtime builtin (not defined in-repo); `run_eval.py` writes
`<output_dir>/results.json`.
**Implicit contracts:** There is no observability contract to conform to. If logging is desired for
Gemini calls, the only existing precedent is plain `log()`/`print()` progress lines and the
`ExecutionResult` field shape (`case_id, trial_id, output, duration_ms, tokens, tool_calls,
transcript, error`) — but nothing currently consumes structured telemetry.

---

## Discovered Patterns

- **Two-layer skill architecture:** thin `SKILL.md` wrapper (slash command, `allowed-tools`,
  spawns agent) + heavyweight `.claude/agents/<name>.md` body (`claude: tools:`, full prompt).
  Wrapper and agent share the same `name`. (`.claude/skills/qrspi-plan/SKILL.md:18`,
  `.claude/agents/qrspi-plan.md:1-5`.)
- **Self-contained vs. wrapper skills:** phase skills delegate to agents; `qrspi-ticket` and
  `qrspi-work` instead carry full logic inline in their SKILL.md. A "how to use tool X" skill
  (the `using-gemini-cli` shape) has its closest precedent in the self-contained form.
- **Stateless agents + explicit input passing:** every agent receives `KEY = value` prompt lines;
  cross-call state rides in artifacts (`impl-log.md`) and `PREVIOUS_NOTES`, never a session store.
- **Token-free staging + deterministic persist (Fix A):** agents write `/tmp/phase-stage/<id>/...`;
  `scripts/qrspi_persist.py` moves to canonical `.qrspi/` paths. Motivated by a weak local worker
  model mangling the literal `qrspi` token (qrspi-batch.js:171-199).
- **External tools run via `Bash`:** no dedicated shell/subprocess tool; `mkdir`, `python3 scripts/...`
  all go through `Bash` (qrspi-ticket/SKILL.md:117; qrspi-batch.js worker prompts).
- **HARD-STOP-on-error contract:** surface the exact error verbatim, never retry/improvise on
  infra/tooling failures. Repeated across agents and workers (qrspi-research.md:56-58;
  qrspi-batch.js:196-197,251-252).
- **Templates as single source of truth:** output formats live in `.qrspi/templates/`; skills/agents
  reference them rather than embedding (README.md:126).
- **Caveats pinned to verified versions:** prose comments record exact tool versions a behavior was
  tested against (post-create.sh:69-70).
- **Auto-discovery, no registry:** skills/agents discovered by directory + frontmatter `name`; no
  manifest, no `.claude/settings.json`.
- **Testing convention:** only Python orchestration modules have stdlib `_test.py` unit tests; the
  `evals/` harness is a non-functional placeholder; skills are verified by manual e2e.

## Inconsistencies

- **`evals/run_eval.py` is a documented placeholder, yet fully scaffolded.** It defines a complete
  config/result/threadpool harness and a CLI, but `execute_single()` returns empty output
  (run_eval.py:116-137). A reader skimming the harness could mistake it for functional; only the
  inline comment and `.claude/CLAUDE.md` reveal it is non-functional. Any test plan that cites
  `scripts/run_eval.py` as the validation mechanism contradicts the stated reality (Q12/Q13).
- **"sandbox" / "yolo" are overloaded terms.** `qrspi-batch.js:23,29` uses "sandbox" for the JS
  workflow execution environment; README.md:118 uses it for the dev container; Q11 uses it for a
  Gemini `--sandbox` runtime. `yolo` is a Claude `--dangerously-skip-permissions` bash wrapper
  (post-create.sh:26) vs. Q10's Gemini YOLO auto-approve mode. These are unrelated despite shared
  names — a Gemini skill author could conflate them.
- **README skill-naming vs. likely new-skill name.** Every in-repo skill is `qrspi-*` namespaced
  (README.md:86-96), but the new skill is `using-gemini-cli` (un-namespaced, matching the
  global `using-*` style). It will not visually group with the QRSPI lifecycle skills — intentional
  for a non-phase utility skill, but inconsistent with the local naming convention.
- **Q1 premise vs. reality:** Q1 references "the CLAUDE.md parsing logic." No CLAUDE.md *parsing*
  code exists in the repo — `CLAUDE.md`/`AGENTS.md` composition is done by the harness via `@import`
  directives, not by any repo-local parser. The premise assumes in-repo parsing that does not exist.
