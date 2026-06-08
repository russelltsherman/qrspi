# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-02T14:30:00Z
**Generated:** 2026-06-02T15:00:00Z
**Status:** draft

## Q1: Where in `.claude/agents/` should the "using claude cli" skill's `SKILL.md` be placed, and what frontmatter fields are required by the agentskills.io standard?

**Answer:** A skill's `SKILL.md` is placed at `.claude/skills/<skill-name>/SKILL.md` (e.g., `.claude/skills/using-claude-cli/SKILL.md`). Every existing skill in this repo follows this path pattern. The YAML frontmatter fields observed across all 10 skills are: `name`, `description`, `command` (the slash command string), `argument-hint` (parameter guidance for the user), and `allowed-tools` (comma-separated tool list). The question references a hypothetical "agentskills.io standard" with fields like `model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`; none of these appear in any existing SKILL.md.

**Evidence:**

```
# All 10 skill paths (pattern: .claude/skills/<name>/SKILL.md)
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
.claude/skills/qrspi-plan/SKILL.md
.claude/skills/qrspi-pr/SKILL.md
.claude/skills/qrspi-questions/SKILL.md
.claude/skills/qrspi-research/SKILL.md
.claude/skills/qrspi-structure/SKILL.md
.claude/skills/qrspi-ticket/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-worktree/SKILL.md

# Example frontmatter (from qrspi-design)
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `/workspaces/qrspi/.worktrees/RUS-9/.claude/skills/*/SKILL.md`

**Dependencies:** This is a project-level convention under `.claude/`; not controlled by any CLI source code in this repo.

**Implicit contracts:** The `command:` field value must match a slash command that Claude Code recognizes (prefixed with `/`). The `allowed-tools:` list constrains what tool calls the skill's agent can make; tools not listed are rejected at invocation time.

---

## Q2: How does the existing `skill-creator` skill (``.claude/skills/`) generate or scaffold SKILL.md files, and what template or reference does it use?

**Answer:** The `skill-creator` skill directory (`.claude/skills/skill-creator/`) does NOT exist in this codebase. There is no scaffolding generator present. However, the pattern for creating SKILL.md files can be inferred from the 10 existing skills: they share a nearly identical YAML frontmatter structure (`name`, `description`, `command`, `argument-hint`, `allowed-tools`), followed by prose/marked content that describes the skill's purpose, steps, and constraints. The `.claude/skills/qrspi-work/references/` directory (the only `references/` found) contains cross-reference docs but no templates. No template files exist for scaffolding skills.

**Evidence:**

```
# No skill-creator directory exists
$ ls .claude/skills/skill-creator/ 2>/dev/null
# (nothing — no such directory)

# The only references/ directory found:
.claude/skills/qrspi-work/references/review-cascade.md
# Contains review cascade logic, not a template

# Pattern observed across all 10 SKILL.md files:
# ---
# name: <slug-name>
# description: <imperative prose>
# command: /<slash-command>
# argument-hint: <parameters>
# allowed-tools: <tool1>, <tool2>, ...
# ---
# # Prose body...
```

— `.claude/skills/*/SKILL.md` (all 10 files)

**Dependencies:** This is an observation about the existing codebase; no generator exists to reference.

**Implicit contracts:** When creating a new skill manually, follow the YAML frontmatter format observed across all existing skills. The `description:` field uses imperative/prose style describing when to invoke and what happens. The prose body after frontmatter should include purpose, steps, and constraints — as seen in the thin wrappers (e.g., qrspi-design has ~30 lines).

---

## Q3: What references files (`references/`, `scripts/`, `assets/`) need to be created under the skill directory, and what content belongs in each relative to the CLI modes documented in the ticket?

**Answer:** Only one `references/` subdirectory exists in this codebase: `.claude/skills/qrspi-work/references/`, containing a single file `review-cascade.md` (a PR-gated lifecycle cross-reference doc). No `scripts/` or `assets/` directories exist under any skill. The content pattern is reference docs that support the skill's workflow logic. For a "using claude cli" skill, references would likely cover CLI mode variations and how each affects skill behavior. There is no existing convention for `scripts/` or `assets/` in skills — these do not need to be created.

**Evidence:**

```
# Only references/ directory in the entire .claude/skills tree:
.claude/skills/qrspi-work/references/review-cascade.md

# No scripts/ or assets/ under any skill:
$ find .claude/skills/ -name "scripts" -o -name "assets" | head
# (empty — no matches)

# review-cascade.md header (showing its purpose as a reference doc):
# Title: Review Cascade Logic (PR-gated)
# Content: dependency chains for per-phase revision cascades
```

— `.claude/skills/qrspi-work/references/review-cascade.md` (lines 1-5)

**Dependencies:** No upstream or downstream modules; this is a standalone reference file.

**Implicit contracts:** Reference files under `references/` are read by agents at runtime for cross-referencing but are not executed. They should contain static documentation relevant to the skill's domain.

---

## Q4: How are sub-agent definitions encoded as Markdown files with YAML frontmatter in `.claude/agents/`, and what YAML fields (`model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`) map to the CLI flags described in the ticket?

**Answer:** Sub-agent definitions use a two-part format: (1) YAML frontmatter with `name` and `description`, followed by a `claude:` block containing `tools:`, then (2) a Markdown body with agent instructions. All 8 agents share this exact pattern. However, the fields listed in the question (`model`, `permissionMode`, `skills`, `mcpServers`, `hooks`) do NOT appear in any existing agent YAML frontmatter. The only fields present are `name`, `description`, and `claude.tools` (a single flat key whose value is a comma-separated list of tool names).

**Evidence:**

```
# Agent frontmatter pattern (all 8 agents identical structure):
---
name: qrspi-design
description: Internal QRSPI workflow agent — produces the design document...
claude:
  tools: Read, Write
---

# The body follows immediately after the closing ---:
You are the Design phase agent for the QRSPI workflow...

# All agents and their tool sets:
qrspi-design.md       → tools: Read, Write
qrspi-implement.md    → tools: Read, Write, Edit, Glob, Grep, Bash
qrspi-plan.md         → tools: Read, Write
qrspi-pr.md           → tools: Read, Write, Bash
qrspi-questions.md    → tools: Read, Write
qrspi-research.md     → tools: Read, Write, Glob, Grep
qrspi-structure.md    → tools: Read, Write
qrspi-worktree.md     → tools: Read, Write
```

— `.claude/agents/*.md` (all 8 agent files)

**Dependencies:** Upstream: `.claude/skills/*/SKILL.md` (thin wrappers that spawn these agents via the `Agent` tool). Downstream: None — agents produce artifacts written to file paths.

**Implicit contracts:** The `claude.tools:` list defines which tool invocations are authorized for this agent. Tools not listed are silently rejected. The orchestrator uses `subagent_type: <name>` to spawn by matching the `name` field in the frontmatter.

---

## Q5: Where is the settings hierarchy (Managed > CLI args > Local project > Shared project > User settings) for MCP configuration (`~/.claude.json`, `.mcp.json`, `~/.claude/settings.json`) encoded in the codebase?

**Answer:** The settings hierarchy is NOT encoded in this codebase. No `~/.claude.json`, `.mcp.json`, or `~/.claude/settings.json` files exist within the project scope (`.worktrees/RUS-9/`). There is no settings loading, merging, or inheritance logic present. Configuration flows through two mechanisms: (1) CLAUDE.md at `.claude/CLAUDE.md` for project-level directives and QRSPI workflow rules, and (2) YAML frontmatter in agent/skill files for tool permissions. The Linear MCP server is referenced by name (`mcp__linear-russelltsherman__get_issue`) but its configuration lives outside this repo.

**Evidence:**

```
# No settings files exist:
$ find . -name "*.json" -path "*/.claude/*" | head
# (empty — no JSON config under .claude/)

# Configuration is entirely through markdown directives:
.claude/CLAUDE.md → QRSPI workflow lifecycle, skill listings, workflow rules

# Linear MCP reference (configured externally, referenced by name):
mcp__linear-russelltsherman__get_issue    # in qrspi-design SKILL.md
mcp__linear-russelltsherman__save_issue   # in qrspi-work SKILL.md
```

— `.claude/CLAUDE.md` (entire file, 61 lines)

**Dependencies:** No internal settings management; depends on external MCP server configuration.

**Implicit contracts:** The Linear MCP server name `russelltsherman` follows the pattern `<workspace-user>`. Its connection info must be configured in the Claude Code runtime's global config (outside project scope).

---

## Q6: How does the session management system (`-c`, `-r`, `-n`, `--continue`, `--resume`, `--fork-session`) track session IDs, and where is the session persistence logic implemented that `--no-session-persistence` would disable?

**Answer:** No session management flags (`-c`, `-r`, `-n`, `--continue`, `--resume`, `--fork-session`) or session persistence logic are encoded in this codebase. The project uses slash-command-based session control exclusively: `/clear` (full reset), `/compact` (compress conversation history), and `/context` (check utilization). Session tracking is entirely implicit — there are no session ID variables, no persistence files, and no CLI flag parsing for sessions. The design relies on fresh-session-per-phase patterns enforced by the workflow (each phase agent starts fresh via the orchestrator).

**Evidence:**

```
# Only session commands found in codebase:
/context      → "Check context utilization. If over 40%, take action."
/compact      → "Compress conversation history. Use within a phase if context is growing."
/clear        → "Full reset. Use between phases and between implementation slices."

# No session ID tracking:
$ grep -rn "session_id\|--continue\|--resume\|--fork\|sessionId" . --include="*.py" --include="*.js" --include="*.md" | head
# (only generic references to "session-aware" and "per-session budgets")

# Session guidance from docs:
"The workflow is designed so that a fresh session per phase (and per slice) is the default."
```

— `docs/qrspi_claude_code_guide.md` (line ~347, /context table)
— `docs/qrspi-orientation.md` (lines 170, 615-618)

**Dependencies:** No internal session management; relies on Claude Code CLI's built-in session control.

**Implicit contracts:** Each phase agent is invoked as a fresh subagent by the orchestrator, which effectively creates a fresh context. The `--no-session-persistence` flag would disable whatever persistence mechanism Claude Code uses internally (not visible in this codebase).

---

## Q7: How are hook events (`PreToolUse`, `PostToolUse`, `SubagentStop`, etc.) registered and dispatched in the settings system, and where do matcher patterns (e.g., `"Edit|Write"`) get evaluated?

**Answer:** No hook events (`PreToolUse`, `PostToolUse`, `SubagentStop`), hook registration, event dispatching, or matcher pattern evaluation logic exists in this codebase. This is entirely a Claude Code runtime feature external to the QRSPI project. The hooks system would be implemented within the Claude Code CLI source itself, not in any `.claude/` project configuration files.

**Evidence:**

```
# No hook references (filtered from 10k+ file search):
$ grep -rn "PreToolUse\|PostToolUse\|SubagentStop" . --include="*.py" --include="*.js" --include="*.md" --include="*.json" | head
# (empty — no results)

# The closest related concept is tool lockdown:
# Agents declare which tools they can use via claude.tools, but there's no
# event system around tool invocation.
```

— `.claude/agents/*.md` (all 8 files — none reference hooks)

**Dependencies:** Hooks are a Claude Code runtime feature, not a project-level configuration. They would be found in the Claude Code CLI source (not in this repo).

**Implicit contracts:** The absence of any hook logic means this QRSPI project operates entirely within the default tool execution flow without any custom pre/post-processing.

---

## Q8: What edge cases arise when encoding bare mode (`--bare -p`) CLI flags in the skill, given that bare mode skips auto-discovery of hooks, skills, plugins, MCP servers, and CLAUDE.md?

**Answer:** No `--bare` or `-p` flag handling is documented or implemented in this codebase. The closest evidence is the `--dangerously-skip-permissions` flag used in the devcontainer's post-create.sh, which defines a `yolo()` helper that wraps `claude --dangerously-skip-permissions "$@"`. This bypasses all permission checks but does not skip hook/skill/MCP discovery. In bare mode (per the question's description), auto-discovery of hooks, skills, plugins, MCP servers, and CLAUDE.md is skipped — meaning a skill defined in `.claude/` would not be found. The edge case: if `--bare` strips all auto-discovery, then the very skill you're trying to invoke (`using claude cli`) may be unfindable unless explicitly specified via a different mechanism.

**Evidence:**

```
# Only CLI flag evidence in devcontainer config:
echo 'yolo() { clear; command claude --dangerously-skip-permissions "$@"; printf '"'"'\x1b[>0u'"'"'; }' >> ~/.bashrc

# No bare mode references anywhere:
$ grep -rn "\-\-bare\|\-p \|bare.mode" . --include="*.sh" --include="*.py" --include="*.js" | head
# (empty — no results)
```

— `.devcontainer/config/post-create.sh` (lines 18-20, the `yolo()` function)

**Dependencies:** `--dangerously-skip-permissions` is a Claude Code CLI flag; this repo only references it in devcontainer setup. The `--bare` mode behavior (skip hooks, skills, plugins, MCP, CLAUDE.md) is external to this project.

**Implicit contracts:** If bare mode skips `.claude/` discovery entirely, then any QRSPI agent or skill defined here would be inaccessible from a bare invocation. A "using claude cli" skill encoded for bare mode would need to work without the standard `.claude/skills/` or `.claude/agents/` loading path.

---

## Q9: How does the permissions model (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`) handle the rule evaluation order (deny -> ask -> allow), and where is `--allowedTools` / `--disallowedTools` parsing implemented?

**Answer:** The permissions model as described in Q9 (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`) does NOT exist in this codebase. No permission mode enum, rule evaluation order (deny→ask→allow), or `--allowedTools`/`--disallowedTools` parsing is present. The only permissions evidence is: (1) per-phase tool lockdowns via `claude.tools:` in agent YAML frontmatter and `allowed-tools:` in skill frontmatter, and (2) the `--dangerously-skip-permissions` flag used to bypass Claude Code's sandbox entirely. These are structural tool restrictions defined at the project level, not runtime permission mode evaluation.

**Evidence:**

```
# Per-phase tool lockdowns (the only permissions mechanism):
---
claude:
  tools: Read, Write               # Design phase: read-only planning
---
---
claude:
  tools: Read, Write, Edit, Glob, Grep, Bash   # Implement: full access
---

# No permission mode enum or rule evaluation:
$ grep -rn "acceptEdits\|planMode\|dontAsk\b\|bypassPermission\|allowedTools" . | head
# (empty — no results)

# Single permissions flag reference in post-create.sh:
yolo() { clear; command claude --dangerously-skip-permissions "$@"; }
```

— `.claude/agents/*/` (all agent YAML frontmatter)
— `.devcontainer/config/post-create.sh` (the `yolo()` function)

**Dependencies:** Tool lockdowns are enforced by Claude Code's runtime when spawning subagents with `subagent_type`. The permission mode system described in Q9 is a CLI-level feature external to this project.

**Implicit contracts:** Per-phase tool lockdowns create structural firewalls — e.g., the research agent has `Read, Write, Glob, Grep` (no Bash, no MCP), preventing it from reading the ticket or calling Linear even if prompted to do so. This is a static allow-list pattern, not a dynamic rule-evaluation engine.

---

## Q10: What happens when subagents exceed session context limits, and how does `--max-budget-usd`, `--max-turns 3`, and `/compact` interact to prevent runaway loops in headless mode?

**Answer:** The interaction between budget, turns, and compaction is NOT encoded in this codebase. Observed mechanisms: (1) per-session context budgets from `worktree.md` keep sessions under 40% utilization, (2) `/clear` forces a fresh session between phases/slices, (3) `/compact` compresses history within a phase when usage grows, and (4) `/context` checks utilization. However, `--max-budget-usd`, `--max-turns`, and the specific interaction to prevent "runaway loops in headless mode" are not documented or implemented here. The budget mechanism is implicit: each phase agent runs as a fresh subagent with bounded tool access (tool lockdown), which limits what it can do. No USD budget, turn counters, or loop-prevention logic exists.

**Evidence:**

```
# Context management commands (from docs):
/context      → "Check context utilization. If over 40%, take action."
/compact      → "Compress conversation history. Use within a phase if context is growing."
/clear        → "Full reset. Use between phases and between implementation slices."

# Budget mechanism (implicit only — no code):
"The workflow is designed so that a fresh session per phase (and per slice) is the default."
"worktree.md's per-session budgets keep each implementation session under the 40% target."

# No budget/turn fields found:
$ grep -rn "max-budget\|max-turns\|budget-usd\|runaway\|headless" . --include="*.py" | head
# (empty — no results)
```

— `docs/qrspi_claude_code_guide.md` (lines ~346-350, /context table)
— `docs/qrspi-orientation.md` (line 618, compact guidance)

**Dependencies:** The budget mechanisms described in Q10 are CLI runtime features. This project relies on structural isolation (fresh sessions per phase) and tool lockdowns rather than explicit budget limits.

**Implicit contracts:** The per-phase fresh-session pattern is the primary anti-loop mechanism. If a subagent goes into a runaway loop, `/compact` compresses its history but does not terminate it. `/clear` creates a new session but does not kill existing ones. No automated termination or budget cap exists at this level.

---

## Q11: How can the generated skill be tested against existing agent teams and sub-agent patterns in the QRPI workflow (`qrspi-batch.js`), and what test fixtures or mock agents exist for validating CLI flag behavior?

**Answer:** The eval harness (`evals/`) is a non-functional placeholder — verified by both the project documentation and source code inspection. The `run_eval.py` script is a stub that defines dataclasses (`ExecutionResult`, `EvalConfig`) but does NOT execute agents. Test cases are defined in `evals/suite.json` (15 cases across 8 phases) with assertions, but the agent execution runtime at lines 117-137 is a no-op returning empty results. The LLM judge integration (`grade.py:208-227`) returns None. Only ~14 of ~37 referenced programmatic checks are implemented in `grade.py`. No test fixtures or mock agents exist for CLI flag behavior — the 4 fixture files that do exist are Linear ticket descriptions (REST endpoint, WebSocket, multi-tenancy), not CLI/agent tests. The only real tests are Python stdlib unit tests for pure logic: `qrspi_resolve_state_test.py` and `qrspi_pr_state_test.py`.

**Evidence:**

```python
# run_eval.py stub execution (lines 100-137):
def execute_single(skill_text, case, trial_id, timeout_ms):
    """Execute a single trial. This stub captures the structure for integration
    with the actual agent runtime."""
    result = ExecutionResult(case_id=case["id"], trial_id=trial_id)
    try:
        # ── Placeholder for agent execution ──
        # response = agent.run(system_prompt=skill_text, messages=build_messages(case))
        # result.output = response.final_output
        result.output = ""
        result.tokens = {"input": 0, "output": 0}
        result.transcript = messages    # Empty!
    except Exception as e:
        result.error = str(e)

# Eval system docs confirm:
# "Agent execution runtime: Stub — no actual agent invocation"
# "LLM judge integration: Stub — returns None"
# "Script check execution: Stub — returns None"
```

— `scripts/run_eval.py` (lines 96-137, execute_single function)
— `docs/eval-system.md` (Completeness table, all runtime components marked "Stub")

**Test fixtures present:**

```
evals/fixtures/ticket_15_acceptance_criteria.md   # Linear ticket description
evals/fixtures/ticket_multi_tenancy.md            # Multi-tenancy scenario
evals/fixtures/ticket_rest_endpoint.md             # REST endpoint test
evals/fixtures/ticket_websocket.md                 # WebSocket test
# (4 of 21 referenced fixtures exist — missing: questions, research, design,
#   structure, plan, worktree, implement, pr golden outputs)
```

— `evals/fixtures/` directory listing

**Dependencies:** The eval harness is completely standalone from the QRSPI workflow logic. Real validation relies on `scripts/qrspi_resolve_state_test.py` (stdlib-only, 40+ test cases for the state resolver) and manual end-to-end runs.

**Implicit contracts:** To test a generated skill, one would need to: (a) add eval cases to `suite.json`, (b) implement the `execute_single()` stub with real agent invocation, (c) add programmatic assertions to `grade.py`'s check registry, and (d) provide fixture files or golden outputs. None of these steps are completed.

---

## Q12: Where is the cost and resource metadata (`session_id`, cost fields in JSON output) emitted from the CLI, and how would logging or observability hooks surface that data for debugging orchestration flows?

**Answer:** No cost or resource metadata (including `session_id`) is emitted from this codebase. The `ExecutionResult` dataclass in `run_eval.py` has a `tokens` field (dict with `input`/`output` ints) and a `transcript` field (list), but both are always empty/zero in the stub implementation. There are no cost fields, no JSON output serialization for observability, no logging hooks, and no observability event emission paths. The `token` reference in post-create.sh appears in a different context: "expired auth" errors from command execution, not token counting.

**Evidence:**

```python
# ExecutionResult dataclass (only cost-adjacent fields):
@dataclass
class ExecutionResult:
    case_id: str
    trial_id: int
    output: str = ""
    files: list = field(default_factory=list)
    duration_ms: float = 0.0      # Timing, not cost
    tokens: dict = field(default_factory=dict)   # Empty in stub
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
    error: Optional[str] = None

# Stub always produces zero tokens:
result.tokens = {"input": 0, "output": 0}

# No session_id anywhere:
$ grep -rn "session_id\|sessionId" scripts/run_eval.py scripts/grade.py | head
# (empty — no results)

# No JSON output with cost metadata:
$ grep -rn "cost\|budget\|usage\|tokens" scripts/run_eval.py scripts/grade.py | head
# Only references to the empty tokens dict and duration_ms timing
```

— `scripts/run_eval.py` (lines 17-29, ExecutionResult; lines 135-137, stub values)

**Dependencies:** The eval harness outputs a JSON results file (`results.json`) with metadata fields: `skill_hash`, `skill_path`, `suite` name, `timestamp`, `config` (trials, timeout), and `results` array. No cost or session data is included.

**Implicit contracts:** To add cost/observability, one would need to: (a) add `session_id` to `ExecutionResult`, (b) populate it from the agent runtime's response headers or context, (c) add it to the output JSON schema in `run_suite()`, and (d) implement hook handlers in a hypothetical observability module. None of these steps exist.

---

## Discovered Patterns

1. **Dual-layer architecture for agents vs. skills:** `.claude/agents/<name>.md` files define subagent behavior with YAML frontmatter (`name`, `description`, `claude: { tools: ... }`) and a Markdown body containing the agent prompt. `.claude/skills/<name>/SKILL.md` files are thin slash-command wrappers that invoke phase agents via the `Agent` tool, using their own frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`).

2. **Per-phase tool lockdown is the primary firewall:** Each agent restricts its tools to exactly what that phase needs. Questions and Research get no Bash/MCP access. Design/Structure/Plan are read-only (Read, Write). Implement gets full access plus Agent. This creates structural firewalls against cross-phase contamination.

3. **Pure-logic Python for decision state:** The PR-gated state resolver (`qrspi_resolve_state.py`) and PR-state gatherer (`qrspi_pr_state.py`) are pure Python with no I/O dependencies. They are tested with stdlib-only unit tests using simple `assert` statements and a custom `check()` helper. This makes the decision logic independently verifiable and testable without any external services.

4. **PR review state (not Linear status) drives advancement:** The single source of truth for ticket progression is GitHub PR review state (`reviewDecision == APPROVED` AND zero unresolved threads from GraphQL `reviewThreads`). Linear only provides an entry gate (assigned + Selected) and a best-effort reporting projection.

5. **Eval harness is a stub with no execution runtime:** The eval system defines the complete data model (ExecutionResult, EvalConfig, suite.json with cases, assertions) but implements zero agent invocation logic. All 3 critical paths (agent execution, LLM judge, script check) are stubs returning empty/None values.

6. **Batch orchestrator uses `agent()` calls for all work:** The `qrspi-batch.js` workflow drives tickets by spawning registered agent types via `agent(prompt, { label, phase, agentType })`. It queries Linear for tickets, runs the Python resolver, and dispatches phase agents (questions, research, design, structure, plan, worktree, implement, pr) based on the resolved action.

7. **Worktree isolation per ticket:** Each ticket gets its own git worktree at `.worktrees/<ticket-id>/`. The main checkout stays on `main`. Worktrees are gitignored. All phase agents operate within their ticket's worktree.

8. **`gt` (Graphite CLI) for stacked PRs, `gh` for PR operations:** The batch workflow uses `gt create`, `gt modify -c`, `gt submit --publish` for Git operations and branch management. `gh` is used for repo metadata (`gh repo view --json nameWithOwner`). Linear MCP calls are handled separately.

9. **Phase artifacts follow template patterns:** Each phase produces one or more markdown files under `.qrspi/<ticket-id>/`. Templates at `.qrspi/templates/` define the canonical format but are not written locally — they are reference only.

10. **Sequential, PR-gated lifecycle:** The workflow enforces strict sequential ordering through PR gates. Nothing merges mid-feature. All phases are held open until fully approved, then landed bottom-up.

## Inconsistencies

1. **`skill-creator` referenced but nonexistent:** The `skill-creator` skill is mentioned in the questions (Q2) as "the existing" skill, but no `.claude/skills/skill-creator/` directory exists anywhere in this repo. Either it was removed, or the question references something outside this codebase.

2. **Eval harness claims 15 cases but fixtures are mostly missing:** The `evals/suite.json` defines 15 test cases across 8 phases. However, only 4 of 21 referenced fixture files exist (3 ticket descriptions). All other phase-specific fixtures (questions_rest_endpoint.md, research_websocket.md, design_billing_migration.md, etc.) are absent from `evals/fixtures/` and `evals/golden/`.

3. **`--max-budget-usd`/`--max-turns` appear in questions but nowhere else:** Q10 references CLI budget and turn-limiting flags, yet a comprehensive search of all code, scripts, docs, fixtures, and configs finds zero references to `max-budget`, `max-turns`, or `budget-usd` anywhere in the project.

4. **No settings hierarchy encoded despite being documented as a concept:** The questions reference a settings hierarchy (Managed > CLI args > Local project > Shared project > User) with specific file paths (`~/.claude.json`, `.mcp.json`, `~/.claude/settings.json`). None of these files or the loading/merging logic exist in this codebase.

5. **Hook system referenced in questions but absent from code:** Q7 references hook events (`PreToolUse`, `PostToolUse`, `SubagentStop`) and matcher patterns (`"Edit|Write"`). These terms appear nowhere in any file within this project scope, despite hooks being a central Claude Code feature.

6. **Agent YAML frontmatter fields differ from question's listed fields:** Q4 lists 7 fields (`model`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`), but no existing agent in `.claude/agents/` uses any of these except a flattened `tools` within the `claude:` block. The fields `model`, `permissionMode`, `skills`, `mcpServers`, and `hooks` are all absent from every agent definition.

7. **`qrspi-work` is listed as having 12 MCP tools but only references Linear ones:** The qrspi-work SKILL.md lists 12 `allowed-tools` entries, 10 of which are Linear MCP calls (`mcp__linear-russelltsherman__get_issue`, etc.). This suggests the skill's tool set was configured for a specific Linear workspace and may not generalize.

8. **Session context claims vs. implementation gap:** Multiple docs claim that "per-session budgets" in `worktree.md` keep sessions under 40% utilization, but no budget tracking code or session ID mechanism exists. The 40% threshold is a human-checked metric (via `/context`) rather than an automated guard.

9. **Template reference vs. reality:** Docs say "phase artifacts follow the formats in `.qrspi/templates/`" and that templates are the "single source of truth," yet `templates/` is documented as "reference only — not written locally." Agents produce artifacts that SHOULD conform to templates but there is no template-validation step.

10. **Batch workflow schema mismatch:** The `qrspi-batch.js` uses inline JSON schemas for agent calls (e.g., `TICKETS_SCHEMA`, `RESOLVE_SCHEMA`) with hardcoded property names, but the resolver Python script (`qrspi_resolve_state.py`) defines its own state shape independently. There is no shared type definition between the JS workflow and the Python resolver — they communicate via ad-hoc string-based prompts and JSON output parsing.
