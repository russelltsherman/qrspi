# Design — Create a new agent skill for using the Claude Code CLI

**Ticket:** RUS-9
**Research basis:** research.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Current State

This repo has no `claude`-CLI usage skill and no skill-creator skill inside `REPO_ROOT`; skill-creator is a global tool referenced only incidentally as a validation pass (ref: Q1). Skills live at `.claude/skills/<name>/SKILL.md`, where `<name>` is kebab-case and equals the `name` frontmatter value; there are 10 such skill directories today (ref: Q4). The dominant architecture is a **thin SKILL.md wrapper delegating to a fat agent definition** under `.claude/agents/<name>.md`; two skills (qrspi-ticket, qrspi-work) are self-contained with no agent file (ref: Q2, Q4). Only one skill, `qrspi-work`, uses a `references/` subdirectory, offloading one large decision table into `references/review-cascade.md`; the body stays orchestration-level and references are pulled in by workflow/agent logic rather than inline markdown links (ref: Q2).

Skill frontmatter uses five fields — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — where `description` is single-line (quoted only when it contains a colon), `command` is the slash form, and `allowed-tools` is a comma-separated list supporting scoped Bash and namespaced MCP tools (ref: Q3). Agent definition files use a *different* frontmatter shape: `name`, `description`, `model`, plus a nested `claude.tools` block (ref: Q3). Required-vs-optional status is convention only — no in-repo validator enforces frontmatter or directory conformance (ref: Q3, Q10). The 500-line / ~40-instruction ceiling is documentation-only guidance in `docs/qrspi_claude_code_guide.md:592`; there is no codified 5000-token rule and no automated SKILL.md size check (ref: Q7). There is no experimental/version-gated labeling convention anywhere in-repo to mirror (ref: Q9). No `session_id` / `--resume` / `--continue` capture pattern exists; cross-invocation continuity rides on `.qrspi/<ticket-id>/` disk artifacts, Graphite per-slice branches, and a free-text "Notes for next session" block (ref: Q6). The eval harness (`run_loop.sh` → `run_eval.py` → `grade.py` → `revise.py` → `report.py`) validates suite/case schemas and writes versioned `results/v<n>/` JSON, but its LLM-judge and script-check graders are stubs returning `passed: None`, and it never parses skill frontmatter (ref: Q5, Q8, Q10, Q11, Q12).

## Desired End State

A new self-contained skill named `using-claude-cli` lives at `.claude/skills/using-claude-cli/SKILL.md` with a `references/` directory, conforming to this repo's skill conventions and the agentskills.io layout. Acceptance criteria map to behavior as follows:

- **agentskills.io structure + valid frontmatter** → `SKILL.md` carries the five-field frontmatter pattern from this repo (ref: Q3), with a `references/` directory alongside it (ref: Q2).
- **Built using the Anthropic skill builder** → the skill is authored via the global skill-creator skill and its eval loop (ref: Q1); the repo's own `evals/`+`scripts/` harness is the in-repo confirmation analog (ref: Q5, Q12).
- **SKILL.md under 500 lines / 5000 tokens** → body stays within the documented 500-line / ~40-instruction ceiling (ref: Q7); the 5000-token figure is honored as an authoring target since no in-repo check enforces it.
- **`references/` covering advanced flags, hooks, agent teams, permission patterns** → four reference files offloaded from the body, following the qrspi-work offload precedent (ref: Q2).
- **Three CLI modes** (interactive, headless/print, bare) → documented in the body with correct flags.
- **Sub-agent spawning** (built-in + custom + CLI-defined) → body section; the repo's own agent-definition frontmatter shape is a concrete in-repo example (ref: Q3).
- **Session management for multi-turn orchestration** → body section; note that this repo itself uses file-and-branch continuity, not session tokens, so the skill documents the SDK pattern while flagging it is not used in-repo (ref: Q6).
- **MCP server configuration** → body section; namespaced `mcp__<server>__<tool>` permission tokens already appear in this repo's `allowed-tools` (ref: Q3).
- **Permission best practices for CI/CD** → body section plus a permission-patterns reference file.
- **Cost control flags** → body section.
- **Actionable orchestration examples** (commit automation, code review, piped analysis) → body section with runnable command examples.

## Delta

New files (all under `.claude/skills/using-claude-cli/`):

- `SKILL.md` — self-contained body (no agent wrapper, matching qrspi-ticket/qrspi-work; ref: Q4). Frontmatter: `name: using-claude-cli`, single-line `description` with explicit trigger guidance, `command: /using-claude-cli`, `argument-hint` (optional/empty since the skill is reference-style), `allowed-tools` minimal/read-only. Body sections: CLI modes, output formats, sub-agents, sessions, MCP, permissions, cost control, orchestration examples. Cross-links to references via prose pointers (matching the repo's non-inline-link convention; ref: Q2).
- `references/advanced-cli-flags.md` — full flag catalog (system-prompt, output-format/json-schema, fork/no-persistence, effort, etc.).
- `references/hooks.md` — hook events, matcher syntax, exit codes, config locations, prompt/agent-based hooks.
- `references/agent-teams.md` — experimental multi-agent orchestration; explicitly labeled experimental (no in-repo precedent for the label, so the skill establishes one; ref: Q9).
- `references/permission-patterns.md` — permission modes, rule syntax, settings hierarchy, CI/CD allowlists, sandboxing.

No modifications to existing files. No agent definition under `.claude/agents/` (self-contained skill; ref: Q4). No new DB/queries/middleware. Optionally, an eval suite under `evals/` could exercise the skill, but the harness's grading backends are stubs (ref: Q10, Q11) so this is deferred to Open Questions.

## Pattern Decisions

### Decision 1: Skill shape — self-contained vs thin-wrapper-plus-agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md, no agent file (like qrspi-ticket/qrspi-work) | Matches reference-skill nature; one file to maintain; no spurious agent | Body must stay disciplined under the 500-line ceiling |
| B | Thin SKILL.md wrapper + `.claude/agents/using-claude-cli.md` | Matches the 8 phase skills | This skill spawns nothing — an agent wrapper would be dead weight |

**Recommendation:** Option A
**Rationale:** The two self-contained skills in-repo (qrspi-ticket, qrspi-work) exist precisely because they are not phase agents that spawn a subagent (ref: Q2, Q4). A CLI-usage reference skill is consumed in-context, not dispatched, so the fat-agent split adds no value.
**NEW PATTERN?** No — mirrors the qrspi-work self-contained-skill-with-references pattern.

### Decision 2: Body/references split granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One monolithic SKILL.md | Single read | Blows the 500-line ceiling; ticket explicitly mandates `references/` |
| B | Body = common patterns (modes, subagents, sessions, permissions, cost); 4 reference files = advanced flags, hooks, teams, permission patterns | Honors ticket's reference list; body stays orchestration-level (ref: Q2) | Reader must follow pointers for depth |

**Recommendation:** Option B
**Rationale:** Directly satisfies the acceptance criterion enumerating the four reference files and matches the qrspi-work convention of offloading large detail tables to `references/` while the body stays high-level (ref: Q2). The ticket's own scope guidance ("put advanced orchestration in references/") prescribes this split.
**NEW PATTERN?** No — extends the single existing `references/` precedent to multiple files.

### Decision 3: Cross-linking convention from body to references

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Prose pointers ("see references/hooks.md for full event list") | Matches observed repo convention — no inline markdown links found (ref: Q2) | Less navigable in a rendered viewer |
| B | Inline markdown hyperlinks `[hooks](references/hooks.md)` | Clickable | No in-repo precedent; would diverge from existing skills |

**Recommendation:** Option A
**Rationale:** Research found no `[link](references/...)` from any body into its reference file; references are pulled in by prose/logic (ref: Q2). Consistency with the established repo style outweighs viewer convenience.
**NEW PATTERN?** No.

### Decision 4: Experimental-feature labeling (agent teams)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline "Experimental:" prefix in the agent-teams reference + env-var gate note | Self-documenting; ticket demands experimental status be flagged | Establishes a new convention (none exists in-repo; ref: Q9) |
| B | Omit labeling, document teams as stable | Simpler | Misleads readers; violates ticket scope guidance |

**Recommendation:** Option A
**Rationale:** The ticket explicitly requires agent teams be documented with clear experimental status, but research found no existing labeling convention to copy (ref: Q9). This skill therefore sets the convention: an "Experimental" callout plus the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` gate.
**NEW PATTERN?** Yes — no experimental-labeling pattern exists in-repo; justified because the ticket mandates the label and there is nothing to mirror.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CLI flag/behavior claims drift from actual `claude` CLI (model knowledge may be stale or wrong) | high | high | Treat ticket's flag list as the spec of record; flag any flag the author cannot verify; recommend a human pass against `claude --help` before approval (see OQ1) |
| SKILL.md body exceeds the 500-line ceiling once examples are added | med | med | Aggressively offload to the four reference files; keep examples terse; no automated check exists (ref: Q7) so reviewer-enforce by hand |
| "Built using skill-creator" criterion is unverifiable in-repo (skill-creator is global, out of scope) | high | low | Document that authoring used the global skill-creator; the in-repo eval harness is only a partial analog with stubbed graders (ref: Q1, Q10, Q11) |
| Session-management guidance recommends SDK session tokens that this repo never uses, causing confusion | med | low | Note explicitly that in-repo continuity is file-and-branch + "Notes for next session", not session tokens (ref: Q6) |
| Stale worktree CLAUDE.md says agents live in `.qrspi/agents/`, which does not exist | low | low | Author against `.claude/skills/` and `.claude/agents/` (the real locations; ref: Q4); ignore the stale worktree doc |

## Open Questions

- OQ1: Should the implementer verify every documented CLI flag against the installed `claude` CLI (`claude --help`) before approval, or treat the ticket's flag list as authoritative? Flag claims are the highest-risk surface and model knowledge of CLI flags may be inaccurate.
- OQ2: Is an `evals/` suite expected for this skill, given the harness's LLM-judge and script-check graders are stubs returning `passed: None` (ref: Q10, Q11)? If yes, accept that scoring is not yet wired to a model runtime.
- OQ3: Which batch workflow is canonical — `qrspi-batch.js` or `qrspi-batch-v2.js` — for any session/orchestration example that references this repo's own usage? Both exist with no deprecation marker (ref: Inconsistencies).
- OQ4: Should `argument-hint` be empty/omitted for a reference-style skill, or carry an optional topic selector (e.g., `<topic>`)? No existing skill is purely reference-style, so there is no precedent (ref: Q3).
