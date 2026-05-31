# Design — Create a new agent skill for using the Claude CLI

**Ticket:** RUS-9
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

Skills in this repo live under `.claude/skills/<skill-name>/` and require a single `SKILL.md`; one skill (`qrspi-work`) also carries a `references/` subdirectory loaded on demand. No skill uses `scripts/` or `assets/` (ref: Q1). All 10 existing skills are thin wrappers: the SKILL.md parses arguments and spawns a purpose-built agent in `.claude/agents/*.md` by `subagent_type`, with the real prompt body living in the agent file (ref: Q1, Discovered Patterns). This is the dominant convention for skills that do real work.

There is no programmatic validator for SKILL.md frontmatter; the de facto schema comes from the 10 consistent existing skills, which all carry `name`, `description`, `command`, `argument-hint`, and `allowed-tools` (ref: Q3). The naming triple is invariant: directory name equals `name:` equals `command:` minus the leading slash (ref: Q3, Discovered Patterns). Tool-rule syntax is uniform across skills — bare tool names, `Bash(<cmd>:*)` for Bash scoping, and `mcp__<server>__<tool>` for MCP tools (ref: Q3, Q13).

The mandated `skill-creator` builder is **not present under the repo root**; its only in-repo mentions are the questions file and a one-line validation note in an agent prompt. It lives in global skill scope, outside this project (ref: Q2, Inconsistencies). Likewise, the entire external `claude` CLI surface the ticket asks the skill to document — flag set, session persistence, bare mode, stdin caps, JSON output schema, permission engine, subagent loader, agent teams (Q4–Q12, the builder half of Q2) — has **no source or documentation under the repo root**; research returned NOT FOUND for each, with searches enumerated (ref: Q4, Q5, Q7, Q8, Q9, Q11, Q12). The repo only shows the shared tool-rule syntax as a partial analog (ref: Q13).

A 5-stage Python eval pipeline exists (`run_eval.py` → `grade.py` → `report.py` → `diagnose.py` → `revise.py`) driven by declarative JSON suites with weighted programmatic/llm_judge/script assertions and a train/test split on seed 42 (ref: Q10). Critically, the harness does not actually invoke an agent — execution, LLM judging, and most script/programmatic checks are stubs that produce zeros; only 14 of ~37 checks and 4 of 21 fixtures exist (ref: Q10, Discovered Patterns).

## Desired End State

A new skill named `using-claude-cli` ships at `.claude/skills/using-claude-cli/SKILL.md` with a `references/` subdirectory, following the agentskills.io directory structure and the repo's skill frontmatter dialect.

Mapping each acceptance criterion to concrete behavior:

- **agentskills.io structure + valid frontmatter** → `SKILL.md` carries the repo skill dialect (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) with the naming triple satisfied (ref: Q1, Q3).
- **Built using the skill builder** → produced through the global `skill-creator` skill, which is out of repo scope but reachable in this session; the build step is invoked at implementation time, not authored ad-hoc (ref: Q2; see OQ1).
- **Body under 500 lines / 5000 tokens** → SKILL.md holds only the most common patterns (headless mode, subagents, sessions, permissions); advanced material is offloaded to references.
- **`references/` covering advanced flags, hooks, agent teams, permission patterns** → one Markdown file per topic under `references/`, mirroring the `qrspi-work/references/` precedent (ref: Q1).
- **All three CLI modes; subagent spawning; session management; MCP config; permission best practices; cost control; orchestration examples** → these map to SKILL.md sections plus reference files. The factual content is sourced from authoritative Claude Code documentation, not this repo, because the repo has no CLI source (ref: Q4–Q13). The one verifiable-in-repo convention to reuse is the tool-rule syntax `Bash(<cmd>:*)` / `mcp__<server>__<tool>` (ref: Q13).

## Delta

New files:
- `.claude/skills/using-claude-cli/SKILL.md` — frontmatter (skill dialect) + body covering the four common patterns and short orchestration examples.
- `.claude/skills/using-claude-cli/references/cli-flags.md` — advanced flags, output formats, cost/resource control.
- `.claude/skills/using-claude-cli/references/subagents-and-teams.md` — built-in subagent types, custom `.claude/agents/` definitions, `--agents` JSON, agent teams (flagged experimental), worktrees.
- `.claude/skills/using-claude-cli/references/hooks.md` — hook events, matcher syntax, exit codes, examples.
- `.claude/skills/using-claude-cli/references/permissions-and-mcp.md` — permission modes, deny→ask→allow order, settings hierarchy, rule syntax, MCP config.
- `.claude/skills/using-claude-cli/references/cicd-patterns.md` — brief GitHub Actions / GitLab CI examples (per ticket judgment call).

Optional (gated on OQ2): an eval case object appended to a suite under `evals/` plus any referenced fixtures under `evals/fixtures/`. Given the harness produces zeros (ref: Q10), this would be cosmetic unless agent execution is wired in first.

No modifications to existing skills or agents. No agent file is created — this skill is content/documentation, not an orchestrator that spawns a worker (see Decision 2).

## Pattern Decisions

### Decision 1: Skill shape — thin-wrapper-plus-agent vs. self-contained content skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md + references, no agent file | Matches the skill's nature (reference content, no orchestration); simplest; agentskills.io-native | Diverges from the repo's dominant thin-wrapper pattern |
| B | Thin SKILL.md that spawns a `using-claude-cli` agent | Consistent with all 10 existing skills (ref: Q1) | The wrapper pattern exists to hide a heavy spawned worker; there is no worker here — it would wrap nothing |

**Recommendation:** Option A
**Rationale:** The thin-wrapper convention (ref: Q1, Discovered Patterns) exists specifically for skills that dispatch a fat agent to do work. This skill produces no artifact and spawns no worker; it is reference guidance the model loads in-context. The `qrspi-work/references/` precedent shows skills may carry references directly (ref: Q1). Forcing a wrapper+agent here adds an empty indirection.
**NEW PATTERN?** Yes — a content/reference skill with no paired agent. Justified: the existing pattern targets orchestrators, and no current skill is purely documentation. This is the agentskills.io-standard shape the ticket explicitly asks for.

### Decision 2: Frontmatter dialect — skill vs. agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Skill dialect (`name`/`description`/`command`/`argument-hint`/`allowed-tools`) | Matches all 10 skills (ref: Q3); harness reads it as a skill | `argument-hint` is awkward for a no-argument reference skill |
| B | Agent dialect (`name`/`description`/`model`/nested `claude.tools`) | — | Wrong location and consumer; agents live in `.claude/agents/` (ref: Q6) |

**Recommendation:** Option A
**Rationale:** It lives in `.claude/skills/`, so it must use the skill dialect (ref: Q3, Discovered Patterns). `argument-hint` can be a no-op placeholder or a topic selector. `allowed-tools` should be minimal (likely `Read` only, since the skill mostly supplies guidance) using the verified syntax (ref: Q13).
**NEW PATTERN?** No.

### Decision 3: Sourcing the factual CLI content

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Transcribe the ticket's CLI conventions verbatim into the skill | Fast; ticket is detailed | Unverified against the real binary; ticket may contain aspirational or stale flags (ref: Q4 NOT FOUND) |
| B | Verify each flag against authoritative Claude Code docs / `claude --help`, then encode only confirmed behavior | Skill ships accurate, non-aspirational flags | Requires an external verification step the repo cannot supply |

**Recommendation:** Option B
**Rationale:** Research could not confirm a single CLI flag from this repo (ref: Q4, Q5, Q7, Q8, Q11, Q12). The ticket itself flags items as "experimental" and "judgment call," signalling uncertainty. Encoding unverified flags risks shipping a skill that instructs agents to use flags that do not exist. The honesty directive requires verifiable content. The verification source is external and must be confirmed (see OQ1, OQ3).
**NEW PATTERN?** No (process decision, not a code pattern).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ticket's CLI flag list is aspirational/stale; skill documents non-existent flags (ref: Q4 NOT FOUND for entire CLI surface) | high | high | Verify every flag against authoritative docs or `claude --help` before encoding (Decision 3); cite the source version in the skill. |
| `skill-creator` builder unavailable in the build session, blocking the "built using skill builder" criterion (ref: Q2, Inconsistencies) | med | med | Confirm `skill-creator` is reachable in session before structure phase (OQ1); if absent, escalate rather than hand-author silently. |
| SKILL.md body exceeds 500-line / 5000-token budget given the breadth of topics | med | med | Keep the four common patterns + short examples in the body; push all advanced flags, hooks, teams, and permission tables into `references/`. |
| New "content skill with no agent" pattern conflicts with reviewer expectation of the wrapper convention (ref: Discovered Patterns) | low | med | Document the deviation in Decision 1 and the PR; confirm acceptability (OQ4). |
| Eval coverage is non-functional; adding an eval case gives false confidence (harness produces zeros, ref: Q10) | med | low | Treat eval cases as optional/cosmetic until execution is wired in; do not claim benchmarking the harness cannot perform (OQ2). |

## Open Questions

- OQ1: Is the global `skill-creator` skill (and its eval loop) reachable in the implementation session, given it is not under the repo root (ref: Q2)? If not, is hand-authoring acceptable, or must the build block?
- OQ2: Should an eval case be added at all, given the harness execution is a stub that produces zeros (ref: Q10)? If yes, is wiring real agent execution into `run_eval.py` in scope, or out of scope for this ticket?
- OQ3: What is the authoritative source of truth for verifying CLI flags — installed `claude --help` in this environment, or a specific published Claude Code docs version? The answer fixes which flags are "real."
- OQ4: Is the new no-agent content-skill shape (Decision 1) acceptable, or does the reviewer require the thin-wrapper+agent convention even for a pure-reference skill?
- OQ5: Should the skill correct or echo the ticket's specifics that research could not verify (e.g., the 10MB stdin cap, the exact permission-mode list)? This depends on OQ3's verification source.
