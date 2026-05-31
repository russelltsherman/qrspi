# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: How does the existing skill-creator skill structure its outputs, and what files does it expect a new skill author to produce (e.g., SKILL.md, references/, scripts/, assets/)?

**Answer:** NOT FOUND — the `skill-creator` skill is not vendored in this repo. The system-reminder lists it as a globally available skill installed outside `REPO_ROOT/`. Per the research firewall I did not read it. Locally, the repo follows a `.claude/skills/<name>/SKILL.md` (+ optional `references/`) layout; see Q3 for the in-repo precedent.
**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
```

— `.claude/skills/` (directory listing)
**Dependencies:** External skill — not researchable under scope constraints.
**Implicit contracts:** None observable in-repo.

## Q2: What format does this repo use for skill frontmatter (name, description, command, argument-hint, allowed-tools, model), and what fields are required vs. optional?

**Answer:** Every in-repo skill uses YAML frontmatter with five required keys: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. No `model` field appears on any skill (model is set on agents, not skills — see Q5). `description` is a free-form sentence-or-paragraph string used for auto-invocation triggering.
**Evidence:**

```
---
name: qrspi-pr
description: Prepare a pull request summary after all slices are implemented. Use when implementation is complete.
command: /qrspi-pr
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-pr/SKILL.md:1-6`

```
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, ...
```

— `.claude/skills/qrspi-work/SKILL.md:6`
**Dependencies:** Frontmatter is parsed by Claude Code skill loader (external).
**Implicit contracts:** `allowed-tools` values include bare tool names (`Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `Agent`), narrowed Bash patterns (`Bash(pwd:*)`), and MCP-prefixed tool ids (`mcp__linear-russelltsherman__*`).

## Q3: How are existing skills in this repo distributed between SKILL.md, references/, scripts/, and assets/ — what content lives where?

**Answer:** All ten in-repo skills consist of a single `SKILL.md` body; only `qrspi-work` has a `references/` subdirectory. There are no `scripts/` or `assets/` subdirectories inside any skill. Scripts live at the repo-root `scripts/` and eval fixtures live at `evals/fixtures/`, not under any skill. The "wrapper" skills (qrspi-questions, qrspi-research, qrspi-design, qrspi-structure, qrspi-plan, qrspi-worktree, qrspi-implement, qrspi-pr) are 25–35 lines and delegate to agents in `.claude/agents/`. The orchestrator skill `qrspi-work/SKILL.md` is 730 lines and contains full state-machine logic.
**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
   35 .claude/skills/qrspi-implement/SKILL.md
   26 .claude/skills/qrspi-plan/SKILL.md
   28 .claude/skills/qrspi-pr/SKILL.md
   26 .claude/skills/qrspi-questions/SKILL.md
   26 .claude/skills/qrspi-research/SKILL.md
   25 .claude/skills/qrspi-structure/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  730 .claude/skills/qrspi-work/SKILL.md
   25 .claude/skills/qrspi-worktree/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`

```
.claude/skills/qrspi-work/references/review-cascade.md
```

— only `references/` subdir in any skill
**Dependencies:** Skills reference agent prompts in `.claude/agents/` and templates in `.qrspi/templates/`.
**Implicit contracts:** Thin-wrapper skills (≤35 lines) push narrative content into `.claude/agents/<name>.md`. Orchestrator skills hold logic inline.

## Q4: What CLI flags does `claude` expose for interactive, headless/print, and bare modes, and which flag combinations are valid together?

**Answer:** NOT FOUND — this repo does not vendor Claude Code CLI reference documentation. No `--help` capture, no man page, no docs file enumerates CLI flags. The only CLI behavior captured in-repo concerns `gh` and `gt` invocations.
**Evidence:**

```
$ grep -rn "claude -p\|--output-format\|--bare\|--allowedTools" .claude/ docs/ scripts/
# (no results)
```

— `grep` returned no matches in this repo
**Dependencies:** External — Claude Code CLI documentation must be sourced from Anthropic's docs site, not from this repo.
**Implicit contracts:** The new skill will need to encode CLI knowledge from outside the repo (this is unavoidable for a skill about the Claude CLI itself).

## Q5: How are custom subagents declared in this repo (frontmatter shape, tool restrictions, model field, hooks/skills/mcpServers entries), and what is the canonical example?

**Answer:** Custom subagents live in `.claude/agents/<name>.md` with a YAML frontmatter block containing three top-level keys (`name`, `description`, `model`) and a `claude:` block whose only sub-key is `tools:` (a comma-separated allow-list). No `hooks`, `skills`, `mcpServers`, `permissionMode`, or `name` collision handling appears on any in-repo agent. The agent body is a plain-prose system prompt that defines inputs, behavior, hard constraints, and an infrastructure-error HARD STOP.
**Evidence:**

```
---
name: qrspi-questions
description: Internal QRSPI workflow agent — generates 8-15 technical questions from feature ticket content. Spawned by the /qrspi-questions skill or the qrspi-work orchestrator. Not for general-purpose question generation.
model: opus
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-questions.md:1-7`

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts by answering Questions-phase questions. ...
model: opus
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/agents/qrspi-research.md:1-7`

```
---
name: qrspi-implement
description: Internal QRSPI workflow agent — implements one vertical slice in a fresh context. ...
model: opus
claude:
  tools: Read, Write, Edit, Glob, Grep, Bash
---
```

— `.claude/agents/qrspi-implement.md:1-7`
**Dependencies:** Agents are spawned by skills via the `Agent` tool with `subagent_type: <agent-name>`.
**Implicit contracts:** Tool lock-down is enforced at the frontmatter `claude.tools` field, NOT in skill `allowed-tools`. Each agent owns its own firewall (questions has no Glob/Grep/Bash; research has no Linear MCP).

## Q6: What is the syntax for `--agents '{JSON}'`, `--mcp-config`, `--allowedTools`, etc.?

**Answer:** NOT FOUND in repo. Same situation as Q4 — no vendored CLI reference. The new skill must source these from external Claude Code documentation.
**Evidence:** Same `grep` evidence as Q4.
**Dependencies:** External.
**Implicit contracts:** None in-repo.

## Q7: How does Claude Code track and persist sessions on disk, what does `--no-session-persistence` change, and where does `-r <session-id>` look up resumed sessions?

**Answer:** NOT FOUND in repo source. The user MEMORY auto-injection at session start mentions `~/.claude/projects/-Users-russelltsherman-src-github-com-russelltsherman-qrspi/memory/MEMORY.md` — i.e., Claude Code stores per-project memory under `~/.claude/projects/<encoded-path>/`. Per the research firewall I did not read those external paths.
**Evidence:** Referenced only via the system-injected `# claudeMd` block at session start; no in-repo file documents the session storage layout.
**Dependencies:** External — `~/.claude/projects/`.
**Implicit contracts:** None in-repo.

## Q8: How are MCP server configurations layered (`.mcp.json`, `~/.claude.json`, `--mcp-config`, `--strict-mcp-config`), and what is the precedence order?

**Answer:** NOT FOUND — this repo has no `.mcp.json` file. The Linear MCP server is configured outside the repo (user-level). The repo's only references to MCP are tool names in `allowed-tools` (`mcp__linear-russelltsherman__*`).
**Evidence:**

```
$ find . -maxdepth 3 -name ".mcp.json" -not -path "./.git/*"
# (no results)
```

— no `.mcp.json` in repo
**Dependencies:** External MCP config at user level.
**Implicit contracts:** The tool-id pattern is `mcp__<server-name>__<tool-name>` (double-underscore separators) — confirmed across every `allowed-tools` line that references Linear.

## Q9: How does the settings hierarchy (Managed > CLI args > Local project > Shared project > User settings) actually resolve in this repo, given `.claude/settings.json`, `.claude/settings.local.json`, and `~/.claude/settings.json`?

**Answer:** NOT FOUND — this repo does not contain `.claude/settings.json` or `.claude/settings.local.json`. Only `.claude/CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, and `.claude/workflows/` exist under `.claude/`.
**Evidence:**

```
$ ls -la .claude/
drwxr-xr-x agents
-rw-r--r-- CLAUDE.md
drwxr-xr-x skills
drwxr-xr-x workflows
```

— `ls -la .claude/` (only four entries, no settings*.json)
**Dependencies:** Settings hierarchy is external to this repo.
**Implicit contracts:** None in-repo.

## Q10: What does the new skill need to say about bare mode (`--bare -p`) skipping auto-discovery — specifically, which discovery paths are skipped (hooks, skills, plugins, MCP servers, CLAUDE.md), and what must be re-supplied explicitly?

**Answer:** NOT FOUND in repo. No in-repo skill, agent, or script invokes `claude --bare`. The eval harness uses Python scripts (`scripts/run_eval.py`), not direct CLI invocation patterns we can inspect for bare-mode usage.
**Evidence:**

```
$ grep -rn "claude --bare\|claude -p" .claude/ docs/ scripts/ evals/ run_loop.sh
# (no results)
```

— no bare-mode usage anywhere in the repo
**Dependencies:** External documentation.
**Implicit contracts:** None in-repo.

## Q11: What is the documented behavior when a subagent attempts to spawn another subagent (the ticket states this is forbidden), and how should the skill warn the user about this?

**Answer:** NOT FOUND as a formal in-repo doc statement, but the repo's behavior is consistent with that contract: every skill that spawns an agent (the eight thin wrappers) does so from the skill itself, not from inside an agent. No agent prompt in `.claude/agents/` references the `Agent` tool. `qrspi-work/SKILL.md` explicitly performs all `Agent` dispatches from the orchestrator (not from spawned children).
**Evidence:**

```
$ grep -l "Agent" .claude/agents/*.md
# (no results)

$ grep -l "Agent" .claude/skills/*/SKILL.md
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
.claude/skills/qrspi-pr/SKILL.md
.claude/skills/qrspi-plan/SKILL.md
.claude/skills/qrspi-questions/SKILL.md
.claude/skills/qrspi-research/SKILL.md
.claude/skills/qrspi-structure/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-worktree/SKILL.md
```

— only skills (not agents) reference the `Agent` tool
**Dependencies:** Claude Code subagent runtime (external).
**Implicit contracts:** Single-level agent spawning is a hard architectural rule throughout the codebase.

## Q12: What stdin size cap applies to piped input (the ticket mentions 10MB), and what error/behavior occurs when exceeded?

**Answer:** NOT FOUND in repo. No script in `scripts/` pipes data into `claude`, and no doc records this limit.
**Evidence:** Same `grep` evidence as Q4/Q10 — no `claude` CLI invocations exist in the repo.
**Dependencies:** External documentation.
**Implicit contracts:** None in-repo.

## Q13: For permission modes (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`), what are the failure modes if the wrong mode is chosen for CI/CD, and what is the safe default for scripted usage?

**Answer:** NOT FOUND in repo — no settings.json with `permissions` block exists locally (Q9). The `update-config` skill referenced by the ticket is a globally installed skill outside `REPO_ROOT/`.
**Evidence:** Same as Q9.
**Dependencies:** External.
**Implicit contracts:** None in-repo.

## Q14: How are existing skills in this repo evaluated, and what is the expected eval format for a new skill?

**Answer:** `evals/suite.json` defines 15 weighted test cases, three per phase, distributed across the eight QRSPI agents. Each case has: `id`, `name`, `phase`, `prompt`, `context` (input files), and `assertions` (typed list). Assertion types are `programmatic`, `llm_judge`, and `script`. The pipeline runs five scripts: `run_eval.py → grade.py → report.py → diagnose.py → revise.py`. A `train_ratio: 0.65 / test_ratio: 0.35` split with `seed: 42` separates training from held-out cases. Defaults: `trials_per_case: 3`, `timeout_ms: 120000`, `max_tokens: 128000`. `run_loop.sh` drives one full iteration; arguments are `<skill_path> <eval_suite> [max_iterations] [target_score]` (default target 0.85).
**Evidence:**

```
{
  "name": "qrspi-agent-evals",
  "split": { "train_ratio": 0.65, "test_ratio": 0.35, "seed": 42 },
  "defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 },
  "cases": [
    {
      "id": "case_001",
      "name": "questions_happy_path",
      "phase": "questions",
      ...
      "assertions": [
        { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
        { "type": "programmatic", "check": "section_count('questions.md', '## ') >= 5", "weight": 1.0 },
        { "type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0 }
      ]
    }
  ]
}
```

— `evals/suite.json:1-50`

```
SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
EVAL_SUITE=${2:?...}
MAX_ITER=${3:-5}
TARGET_SCORE=${4:-0.85}
TRIALS=${TRIALS:-3}
WORKERS=${WORKERS:-4}
```

— `run_loop.sh:14-19`
**Dependencies:** Python 3 + the five eval scripts.
**Implicit contracts:** New skills are scored on the same 0.85 target; assertions favor structural checks (file exists, section count, regex) plus LLM-judge subjective quality. Adding a new skill that fits this eval system would require defining new cases in `evals/suite.json` and shipping fixture files under `evals/fixtures/`.

## Q15: Does this repo have any existing tests, lints, or validators for SKILL.md files (frontmatter validation, line-count limits, broken references), and if so, how are they invoked?

**Answer:** NOT FOUND for frontmatter/SKILL.md validators. The only repo-level validation is the eval suite (Q14), which validates artifact outputs, not skill source files. No CI workflows exist (no `.github/workflows/`, no Makefile, no `package.json`). `scripts/check_scope.py` validates implementation scope against the worktree session — it does not lint skills.
**Evidence:**

```
$ ls .github 2>/dev/null
# (no output — directory does not exist)

$ find . -maxdepth 2 -name "Makefile" -o -name "package.json"
# (no results)
```

— no CI or task-runner files at the repo root

```python
def load_allowed_files(worktree_session_path: str) -> set:
    """Extract allowed file paths from a worktree session manifest."""
```

— `scripts/check_scope.py:14-15` (scope check, not a skill linter)
**Dependencies:** None.
**Implicit contracts:** Skill quality control is handled via evals, not static linting.

## Q16: What captured examples (commit automation, code review, piped analysis) already exist in this repo's skills or workflows that the new skill should reference rather than re-invent?

**Answer:** Captured examples in-repo:

- **Commit automation:** `qrspi-work/SKILL.md` shows extensive Graphite-based commit patterns: `gt modify -c --no-interactive -m "..."` (lines 142-149), `gt create <branch> ...` (line 361), `gt submit --stack --no-edit --no-interactive` (line 393). These use heredoc message format and a Co-Authored-By trailer.
- **Sub-agent spawning examples:** the eight thin-wrapper skills (`qrspi-questions/SKILL.md` etc.) show the canonical `Agent` tool spawn with `subagent_type: <agent-name>` and a labelled input contract.
- **Workflows directory:** `.claude/workflows/` exists but is git-untracked (per the session-start `git status` showing `?? .claude/workflows/`). I did not read inside it because it is on the staging boundary and unrelated to the in-repo skill examples.
- **Piped analysis / code review:** NOT FOUND in repo. Both the global `/code-review` skill and `/review` skill referenced in the system reminder live outside `REPO_ROOT/`.

**Evidence:**

```
gt modify -c --no-interactive -m "$(cat <<'EOF'
<ticket-id>: Planning

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

— `.claude/skills/qrspi-work/SKILL.md:142-149`

```
1. Spawn the questions agent via the Agent tool with `subagent_type: qrspi-questions` and `mode: "auto"`. Build the prompt as an input contract:
   - `TICKET_ID = <ticket-id>`
   - `TICKET_CONTENT = <title + description from the Linear fetch>`
   - `ARTIFACT_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/questions.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/questions.md`
```

— `.claude/skills/qrspi-work/SKILL.md:134-139`
**Dependencies:** Graphite CLI (`gt`), `gh` CLI.
**Implicit contracts:** Sub-agent prompt format is a labelled "input contract" (KEY = value pairs prefixed with absolute paths under `<WORKTREE_PATH>/`).

---

## Discovered Patterns

- **Thin skill + fat agent split.** Of the ten skills, only `qrspi-work` and `qrspi-ticket` carry meaningful prose; the other eight are ≤35-line shims that dispatch to a `.claude/agents/<name>.md` system prompt. New skills that warrant an agent should follow the same split.
- **Two firewall mechanisms.** (1) Agent frontmatter `claude.tools` restricts available tools (e.g., `qrspi-questions` has no `Glob/Grep/Bash`; `qrspi-research` has no Linear MCP). (2) Hard-constraint prose blocks in the agent body re-state the firewall as instructions. Defense in depth.
- **Input contracts are uppercase, equal-signed, absolute-pathed.** Every sub-agent prompt uses `KEY = <value>` lines; paths are always `<WORKTREE_PATH>/.qrspi/...`, never relative. The orchestrator (`qrspi-work/SKILL.md:91`) explicitly warns "Never pass relative paths like `.qrspi/<ticket-id>/...` to a sub-agent".
- **Infrastructure-error HARD STOP.** Every agent (research, implement, others) carries the same prose block forbidding workarounds on permissions/auth/config failures and requiring immediate exit with verbatim error output. This is a project-wide convention worth replicating in any new skill.
- **Co-Authored-By trailer is mandatory.** `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` appears in every commit message in `qrspi-work/SKILL.md`.
- **No model field on skills, but `model: opus` on every agent.** Skills do not declare a model; agents always do.
- **Worktree isolation is project canon.** `.worktrees/` is gitignored; each ticket gets `.worktrees/<ticket-id>/` from `main`. The new skill must respect this when its operational guidance touches branching.
- **External skill references abound.** The new skill will reference globally-installed skills (`skill-creator`, `update-config`, `/code-review`, `/run`) that do not live in this repo. The research firewall blocked direct inspection of those.

## Inconsistencies

- **Skill-creator skill is named but not present locally.** The ticket's process step #1 says "Use the Anthropic skill builder skill to generate the skill", but no `skill-creator/` directory exists under `.claude/skills/`. The build process must invoke a globally installed skill, not an in-repo one.
- **`allowed-tools: Agent` on every wrapper skill, but the spawned agent has different tools.** This is intentional (the skill's `allowed-tools` controls what the skill prompt can use; the agent's `claude.tools` controls what the agent itself can use), but the discrepancy is worth calling out in the new skill so users don't conflate the two.
- **`docs/qrspi-orientation.md` says "Phase 0 — Ticket" creates `.qrspi/<ticket-id>/ticket.md`** but the `qrspi-work` orchestrator never reads or expects `ticket.md`; it fetches the ticket from Linear. The two sources of truth are reconciled by the fact that `/qrspi-ticket` writes the artifact AND creates the Linear issue, but the doc could be read as implying the file is the source of truth.
- **No `.mcp.json` in repo, yet skills reference MCP tools (`mcp__linear-russelltsherman__*`).** MCP server configuration is purely user-level. A user cloning this repo and running the QRSPI skills cold will need their own MCP setup — undocumented in-repo.
- **`evals/golden/` directory exists but is empty.** Per the directory listing, no golden outputs have been committed. The eval system is operational but ungrounded against reference outputs for the in-repo phases.
