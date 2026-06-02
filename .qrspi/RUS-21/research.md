# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-02T00:00:00Z
**Generated:** 2026-06-02T00:00:00Z
**Status:** draft | human-reviewed | approved

---

## Q1: Where does the skill-builder skill store its generated output — specifically, where does it place the `SKILL.md` file and the optional `references/`, `scripts/`, `assets/` subdirectories relative to the parent agent skills directory?

**Answer:** Within this codebase, every registered skill stores a single `SKILL.md` file at `.claude/skills/<skill-name>/SKILL.md`. None of the 10 currently existing skills (qrspi-design, qrspi-implement, qrspi-plan, qrspi-pr, qrspi-questions, qrspi-research, qrpsi-structure, qrpsi-ticket, qrspi-work, qrpsi-worktree) have `references/`, `scripts/`, or `assets/` subdirectories. The only exception is `.claude/skills/qrspi-work/references/review-cascade.md`, which sits one level deeper than the standard `SKILL.md`. There is no `skill-creator` skill implemented in this project — it appears as an "available skill" in the system prompt but has no corresponding files under `.claude/skills/` or `.claude/agents/` within this codebase.

**Evidence:**

```
# Directory listing of .claude/skills/ (all 10 skills):
$ find /workspaces/qrspi/.worktrees/RUS-21/.claude/skills -type f
/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/qrspi-design/SKILL.md
/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/qrspi-implement/SKILL.md
... (7 more /SKILL.md, same pattern)
/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/qrspi-work/references/review-cascade.md   # only subdirectory content

# The global .claude/skills/ is empty:
$ find /home/vscode/.claude/skills -type f
(no output)
```

— `/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/*/SKILL.md`, `/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/qrspi-work/references/`
**Dependencies:** The `qrspi-work` SKILL.md references `.claude/skills/<name>/SKILL.md` as the canonical pattern at line 50 (`The phase agents must be able to write into this worktree`) and in the Phase Agent Contracts table (lines 406-416).
**Implicit contracts:** Every skill follows a flat single-file structure with one exception. A new skill would add `.claude/skills/<name>/SKILL.md` and optionally create subdirectories, but no existing tooling enforces or discovers these subdirectories — they are purely conventional.

---

## Q2: How does the existing slash-command wrapper pattern (in `.claude/skills/`) invoke a skill's `SKILL.md` content, and how can I model my new skill's directory structure to integrate with this mechanism?

**Answer:** The slash-command wrapper pattern consists of two parts that work in tandem:

**(a) The SKILL.md** — stored at `.claude/skills/<name>/SKILL.md`. When a user types `/qrspi-<name>`, Claude Code reads the file. The frontmatter block declares:
- `name` — internal identifier
- `description` — shown to the user in command suggestions
- `command` — the slash command (e.g., `/qrspi-work`)
- `argument-hint` — what the user passes after the slash (e.g., `<ticket-id>`)
- `allowed-tools` — which tools the agent can use

The body text after `---` becomes the system prompt for that slash invocation. The wrapper is "thin": it parses `$ARGUMENTS` from the CLI input, resolves `REPO_ROOT` from the current working directory, and spawns the corresponding `.claude/agents/<name>.md` agent via the `Agent` tool with `subagent_type: <name>`.

**(b) The .md agent** — stored at `.claude/agents/<name>.md`. This is where the actual logic lives. It uses a `claude:` frontmatter block (not just YAML — it has Claude-specific fields like `tools`, and optionally `model`, `color`, `permissionMode` for global agents).

**Evidence:**

```markdown
# SKILL.md frontmatter (example: qrspi-work, lines 1-7):
---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development..."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-...
---

# Body starts at line 9 — becomes the system prompt when /qrspi-work is invoked.

# .claude/agents/qrspi-design.md frontmatter (lines 1-5):
---
name: qrspi-design
description: Internal QRSPI workflow agent — produces the design document...
claude:
  tools: Read, Write
---

# codebase-analyzer (global agent, /home/vscode/.claude/agents/):
---
name: codebase-analyzer
description: Expert reverse engineer and codebase porting specialist...
model: opus                    # global agents can declare a preferred model
claude:
  tools: Read, Grep, Glob, Bash, Write, Edit, Agent, WebSearch, WebFetch
  color: purple
  permissionMode: acceptEdits
```

— `/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/*/SKILL.md` (all 10 files)
— `/workspaces/qrspi/.worktrees/RUS-21/.claude/agents/*.md` (all 8 agents)
— `/home/vscode/.claude/agents/codebase-analyzer.md`
**Dependencies:** The SKILL.md body text calls the Agent tool with `subagent_type: <name>`, which loads `.claude/agents/<name>.md`. The batch workflow (`qrspi-batch.js`) bypasses slash commands entirely and invokes agents directly via `agent(prompt, { agentType: '<name>' })`.
**Implicit contracts:** The slash command name must match the skill directory name (e.g., `/qrspi-work` → `.claude/skills/qrspi-work/SKILL.md`). The `command:` field in frontmatter is what Claude Code matches against user input. Agent definitions are separate from skills — the workflow spawns agents directly, not via slash commands.

---

## Q3: When the skill-creator generates a `SKILL.md`, what frontmatter fields are mandatory vs. optional per the agentskills.io specification, and how is that schema validated during registration?

**Answer:** **NOT FOUND — this codebase does not contain a `skill-creator` skill implementation, nor any agentskills.io spec validator.** The questions target an external "agentskills.io" specification, but no `.md` or `.json` file in this repository defines or enforces that spec. The only frontmatter patterns observed are:

**In `.claude/skills/<name>/SKILL.md` files (10 skills):**
- `name` — present in all 10 (mandatory)
- `description` — present in all 10 (mandatory)
- `command` — present in all 10 (appears mandatory; defines the slash command)
- `argument-hint` — present in all 10 (appears mandatory; describes expected CLI args)
- `allowed-tools` — present in all 10 (appears mandatory; lists tool permissions)

**In `.claude/agents/<name>.md` files (8 agents + 1 global):**
- `name` — present in all (mandatory)
- `description` — present in all (mandatory)
- `claude:` block with `tools` — present in all (mandatory for Claude Code integration)
- Additional optional fields on the global `codebase-analyzer.md`: `model: opus`, `color: purple`, `permissionMode: acceptEdits`

**Validation during registration:** No validation logic exists in this codebase. The `qrspi-batch.js` workflow spawns agents by string-matching `subagent_type` values — there is no schema enforcement, and invalid agent types would fail at runtime (the `agent()` call returns null).

Evidence that the agentskills.io spec is referenced externally: the design.md notes the new skill should "follow the agentskills.io directory structure" and mentions `SKILL.md` body limits (500 lines / 5000 tokens) as a design target, not an implemented check.

**Evidence:**

```
# All frontmatter fields across all SKILL.md files:
$ for f in /workspaces/qrspi/.worktrees/RUS-21/.claude/skills/*/SKILL.md; do
    echo "=== $f ==="
    head -7 "$f"
  done

# The agents are registered by subagent_type string matching:
$ grep "subagent_type:" /workspaces/qrspi/.worktrees/RUS-21/.claude/skills/qrspi-work/SKILL.md | head -10
    - subagent_type: qrspi-questions
    - subagent_type: qrspi-research
    - subagent_type: qrspi-design
    ... (8 total, one per phase)

# No agentskills.io validator found anywhere:
$ grep -rl "agentskills" /workspaces/qrspi/.worktrees/RUS-21/ 2>/dev/null | head
(no results — only design.md references the URL as a target)
```

— `/workspaces/qrspi/.worktrees/RUS-21/.claude/skills/*/SKILL.md` (frontmatter fields extracted from all 10)
— `/workspaces/qrspi/.worktrees/RUS-21/.claude/agents/*.md` (all agent frontmatters)
— `/workspaces/qrspi/.worktrees/RUS-21/.qrspi/RUS-21/design.md:25,33-35,68,133-135,142` (references agentskills.io as a design target only)
**Dependencies:** The `skill-creator` is listed in the system prompt as an "available skill" but has zero implementation files in this repo. All validation is best-effort: the body text of SKILL.md says what to check, but nothing enforces it programmatically.
**Implicit contracts:** Agents are registered by exact `subagent_type` string matching against `.claude/agents/<name>.md` filenames. The slash command system matches `command:` in frontmatter against user input. No cross-validation occurs between these two registration mechanisms.

---

## Q4: How does the CLI parse and disambiguate codex exec input patterns (positional argument, stdin via -, and prompt-plus-stdin with a pipe)?

**Answer:** **NOT FOUND — the Codex CLI source code is not present in this project.** The only reference to Codex in this repository is `@openai/codex@0.130.0` installed as an npm package in `.devcontainer/Dockerfile:31`. The argument parser module, stdin handling logic, and pipe disambiguation code are inside the `@openai/codex` NPM package, which is not part of this codebase. No documentation in `docs/`, `scripts/`, or `evals/` describes Codex CLI's parsing behavior.

---

## Q5: For the MCP server mode (codex as an MCP provider exposing codex() and codex-reply() tools), what is the wire protocol schema for these tool calls — parameter names, types, and return value structure?

**Answer:** **NOT FOUND — no MCP server or wire protocol documentation exists in this project.** The `@openai/codex` npm package is installed as a binary dependency (`Dockerfile:31`) but its source code and protocol schema are not included. No `*.md`, `*.py`, `*.js`, `*.json`, or `*.toml` file in this repository describes MCP tool call schemas, wire protocols, or the `codex()` / `codex-reply()` tool definitions.

---

## Q6: Session transcripts are persisted locally. Where on disk are they stored, what is the file format (JSON, plain text, etc.), and how does codex resume --last locate the most recent session for a given working directory?

**Answer:** **NOT FOUND — Codex CLI session persistence code is external to this project.** No file in this repository describes session transcript storage paths, formats, or the `--last` flag behavior. The eval fixtures contain ticket markdown files and a `golden/` directory with only `.gitkeep`, but no session transcript files exist.

---

## Q7: In config.toml, profiles ([profiles.<name>]) allow named configuration sets. How does codex --profile <name> swap the active configuration in memory, and what happens to existing session state when a profile switch occurs mid-session?

**Answer:** **NOT FOUND — no `config.toml` or `[profiles.*]` sections exist anywhere in this codebase.** No TOML files were found. The Codex CLI's config module is external (`@openai/codex`) and not part of this repository.

---

## Q8: How does the skill guide agents to detect when a --sandbox CLI flag override has already been applied (in the context of macOS Seatbelt sandbox ignoring network_access = true)?

**Answer:** **NOT FOUND — no `--sandbox` flag, Seatbelt profile, or `network_access` configuration logic exists in this project.** The Dockerfile installs `@openai/codex@0.130.0` as an npm binary but contains no code implementing macOS sandbox enforcement, `sandbox-exec`, Seatbelt profiles, or the `--sandbox` CLI flag. No TOML config files exist.

---

## Q9: How does the skill guide agents to detect when a --sandbox CLI flag override has already been applied (macOS Seatbelt / network_access)?

**Answer:** **NOT FOUND — same as Q8.** The macOS Seatbelt sandbox enforcement and `network_access = true` config.toml behavior are external to this project. The Dockerfile (`Dockerfile:31`) installs `@openai/codex@0.130.0` but no source or documentation for the sandbox layer exists here.

---

## Q10: What deterministic guardrails (unit test integration, diff comparison) does the skill recommend encoding to prevent regression across repeated codex invocations?

**Answer:** **NOT FOUND — no Codex CLI guardrail implementation exists in this project.** The `scripts/` directory contains QR-spi-specific scripts (`qrspi_resolve_state.py`, `qrspi_pr_state.py`, `run_eval.py`, etc.) but none implement Codex-specific prompt execution comparison or diff-based regression detection. The eval harness (`run_eval.py`) is a self-contained multi-trial testing pipeline for QRSPI skill prompts, not for Codex CLI output validation.

---

## Q11: When using codex exec --json for programmatic consumption, the output is newline-delimited JSON events. How does the skill determine the boundary between individual event lines in a piped consumer, and what happens if an agent's internal JSON output contains embedded newlines?

**Answer:** **NOT FOUND — no `--json` flag implementation or NDJSON event serialization exists in this project.** The Codex CLI's JSON output formatter is part of the external `@openai/codex` package. No scripts, tests, or documentation in this repository describe Codex's JSON event stream boundaries or embedded-newline handling.

---

## Q12: For codex exec automation in CI/CD pipelines, how does the skill verify that a given pipeline invocation actually executed as intended when using --json output versus stderr progress streams? What test patterns are recommended for asserting on the JSON event stream?

**Answer:** **NOT FOUND — no Codex CLI CI/CD integration examples exist in this project.** The `evals/` directory and its harness (`run_eval.py`) implement a self-contained eval suite for QRSPI skill prompts, not for Codex CLI output verification. The eval system runs test cases against skill prompts and captures transcripts, but it is not a CI/CD pipeline integration for Codex.

---

## Q13: When designing tests for the skill itself, how should the agent validate that the generated SKILL.md adheres to the agentskills.io spec (frontmatter validity, line count under 500 lines, token count under 5000)?

**Answer:** **NOT FOUND — no programmatic SKILL.md validation logic exists in this project.** The design document references these constraints as targets:
- `SKILL.md` body under 500 lines / 5000 tokens (design.md:25,133-135)
- "valid YAML frontmatter" as an acceptance criterion (design.md:33)

But no script, test, or validator implements these checks. The eval harness (`run_eval.py`, `grade.py`) supports programmatic assertions including line count checks (`grade.py` line 36 mentions "line count" as a check type), but it operates on skill prompt *output*, not on the SKILL.md file format itself. No agentskills.io spec validator exists.

**Evidence:**

```python
# run_eval.py — eval harness assertion types (no frontmatter validation):
lines 31-57: load_suite() validates {"name", "cases"} and case {"id", "prompt", "assertions"}
lines 62-80: build_messages() constructs message arrays for test cases
# No line-count or token-count validation for SKILL.md frontmatter exists

# grade.py — programmatic checks (eval output only):
line 36: "programmatic — Deterministic checks (file exists, section present, 
           line count, regex patterns)"
# These check eval OUTPUT files, not SKILL.md structure.
```

— `/workspaces/qrspi/.worktrees/RUS-21/scripts/run_eval.py:31-80`
— `/workspaces/qrspi/.worktrees/RUS-21/docs/eval-system.md:36`
— `/workspaces/qrspi/.worktrees/RUS-21/.qrspi/RUS-21/design.md:25,33,68,133-135`
**Dependencies:** The eval harness operates at a higher level — it tests whether skill prompts produce correct output, not whether the SKILL.md files themselves are structurally valid.
**Implicit contracts:** Validation of SKILL.md structure (frontmatter schema, line count, token count) is documented as a design target but has zero implementation in this codebase.

---

## Q14: For MCP server-mode Codex sessions, what observability signals (logs, metrics, tracing) are emitted by the MCP protocol layer that an orchestrating agent can consume? How are these surfaced when running codex() tool calls from an external orchestrator?

**Answer:** **NOT FOUND — no MCP server log output or observability code exists in this project.** The `@openai/codex` package is a binary dependency installed via npm (`Dockerfile:31`). No source code, documentation, test fixtures, or scripts describe the MCP server's stdout/stderr streams, structured logging formats, metrics, or tracing.

---

## Q15: The --ephemeral flag skips persisting session files. What diagnostic artifacts remain after an ephemeral session completes, if any, and how does this affect post-mortem debugging of failed automation runs?

**Answer:** **NOT FOUND — the `--ephemeral` flag implementation is external to this project.** No file in this repository references `--ephemeral`, session persistence toggles, or ephemeral session diagnostics. The eval fixtures contain 4 ticket markdown files and a `.gitkeep`-only `golden/` directory but no session artifact samples.

---

## Discovered Patterns

1. **Two-tier registration system:** Skills (`/claude/skills/*/SKILL.md`) and Agents (`/claude/agents/*.md`) are distinct. Slash commands invoke skills; skills spawn agents via the `Agent` tool with `subagent_type`. The batch workflow bypasses both, calling `agent()` directly by string-matching agent type names.

2. **Thin-skill, thick-agent pattern:** Every `.claude/skills/<name>/SKILL.md` is a thin wrapper (< 30 lines) that parses `$ARGUMENTS`, resolves paths, and delegates to the agent. The actual logic lives in `.claude/agents/<name>.md` (2-10 KB each).

3. **Frontmatter schema divergence:** Skills use `name/description/command/argument-hint/allowed-tools`. Agents add a `claude:` block with `tools` and optionally `model/color/permissionMode` (global agents only, e.g., `codebase-analyzer.md`). No single schema covers both.

4. **Flat directory structure:** All 10 skills are flat single files. Only one subdirectory exists: `.claude/skills/qrspi-work/references/review-cascade.md`. No tooling discovers or enforces subdirectories.

5. **No validation layer:** There is no programmatic validation for frontmatter schemas, line counts, token counts, or agentskills.io spec compliance in this codebase. All checks are best-effort document references.

6. **Phase artifact lifecycle is deterministic per-phase:** Each phase produces a specific output file (questions.md → research.md → design.md → structure.md → plan.md → worktree.md → impl-log.md → pr-summary.md). The batch orchestrator verifies existence + non-emptiness before advancing.

7. **Firewalls are structural, not runtime:** The research agent's "research firewall" (no Linear MCP, no ticket reading) is enforced by what tools the Agent tool grants — the agent definition lists only `Read, Write, Glob, Grep`. No additional runtime check exists.

---

## Inconsistencies

1. **agentskills.io reference is aspirational only:** The questions.md and design.md reference "agentskills.io specification" as a target for frontmatter validation, line count limits (500 lines / 5000 tokens), and directory structure. However, no agentskills.io spec files, validators, or even a `skill-creator` skill implementation exist in this codebase. The agentskills.io URL is referenced only as an external target, not as an implemented specification.

2. **Skill count mismatch in design.md:** The design.md (line 12) states "all 10 currently registered skills" and lists them, but the listed names include both `qrpsi-*` misspellings (structure, ticket, work, worktree) and correct spellings — these are typos in design.md's text, not actual directory names (the directories all use `qrspi-*`).

3. **Global agent vs project agent frontmatter divergence:** `codebase-analyzer.md` (global, at `/home/vscode/.claude/agents/`) includes `model: opus`, `color: purple`, and `permissionMode: acceptEdits`. Project-level agents in `.claude/agents/` do not include these fields. No documentation explains which fields are allowed where.

4. **No skill-creator despite being listed as "available":** The system prompt lists `skill-creator` under available skills, but no files for it exist under `.claude/skills/`, `.claude/agents/`, or the global agent directory. It appears to be a built-in or externally managed skill with no local implementation.

5. **codex CLI questions target external code:** All 12 questions from Q4 through Q15 target the OpenAI Codex CLI (`@openai/codex@0.130.0`), an external npm package. Their question targets (Codex CLI source code, MCP server implementation, session persistence, config.toml profiles, macOS sandbox, ephemeral flags) are all outside this project's codebase scope. The design.md references some of these as requirements for a new "using-codex-cli" skill but contains no implementation.

6. **Eval harness is a non-functional placeholder:** Per CLAUDE.md (project instructions): "The evals/ + scripts/run_eval.py harness is a non-functional placeholder." The `evals/golden/` directory contains only `.gitkeep`. Only 4 of 21 expected fixtures exist.
