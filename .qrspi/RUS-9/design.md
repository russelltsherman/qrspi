# Design — Create a new agent skill called using-claude-cli

**Ticket:** RUS-9
**Research basis:** research.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

The repository ships ten in-house skills under `.claude/skills/<name>/SKILL.md` and eight matching agent prompts under `.claude/agents/<name>.md` (ref: Q3, Q5). Skills follow a thin-wrapper-fat-agent split: eight skills are ≤35-line dispatch shims and the orchestrator `qrspi-work/SKILL.md` is the single 730-line state machine (ref: Q3). Skill frontmatter uses five required keys — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — and no `model` field; agent frontmatter adds `model: opus` and a `claude.tools` allow-list (ref: Q2, Q5). The repo does not vendor Claude Code CLI reference documentation, has no `.mcp.json`, no `.claude/settings.json`, and no `.github/workflows/` (ref: Q4, Q6, Q8, Q9, Q15). The skill-creator skill called out in the acceptance criteria is installed globally and not present under `REPO_ROOT/` (ref: Q1, Inconsistencies). Evaluation of skill quality runs through the five-stage Python pipeline driven by `run_loop.sh` against `evals/suite.json`; the target score is 0.85 (ref: Q14). No static linter validates SKILL.md frontmatter (ref: Q15). The repository convention prohibits subagents from spawning other subagents — every `Agent` dispatch in-repo originates from a skill, never from an agent body (ref: Q11). Commit messages always carry the `Co-Authored-By: Claude Opus 4.7 (1M context)` trailer and use heredoc form through `gt modify -c` (ref: Q16). Every agent body carries an "Infrastructure Errors HARD STOP" prose block forbidding workarounds (ref: Discovered Patterns). Captured commit-automation examples already exist in `qrspi-work/SKILL.md`; there are no in-repo code-review or piped-analysis examples — those skills are global (ref: Q16).

## Desired End State

A new project-scoped skill named `using-claude-cli` is shipped at `.claude/skills/using-claude-cli/SKILL.md` together with a `references/` subdirectory of deeper material. It is invocable as `/using-claude-cli` and is also triggered automatically when an agent needs guidance on Claude Code CLI orchestration. Mapped acceptance criteria:

- **Follows agentskills.io directory structure with valid SKILL.md frontmatter.** The new skill carries `name`, `description`, `command`, `argument-hint`, `allowed-tools` matching the in-repo convention. Optional fields from agentskills.io (e.g., a `license` or `version` field) are documented in `references/frontmatter.md` so future skills can adopt them.
- **Built using the Anthropic skill-creator skill.** Production of the skill is authored by a session that explicitly invokes the global `skill-creator` skill; the resulting SKILL.md is committed to this repo. The handoff is documented in the PR summary.
- **SKILL.md body under 500 lines / 5000 tokens.** A line-count assertion is included in the eval suite (case definition added in Slice 3) so future edits cannot silently exceed the budget.
- **Detailed reference material in `references/`** covering: advanced CLI flags, hook configuration examples, agent team orchestration, permission rule patterns. One file per topic.
- **Covers all three CLI modes** (interactive, headless/print, bare) with correct flag usage.
- **Documents sub-agent spawning patterns** including built-in types (Explore, Plan, General-purpose) and custom agents declared in `.claude/agents/`, plus the `--agents '{JSON}'` ephemeral form. Includes the single-level constraint (subagents cannot spawn subagents) as a hard rule.
- **Session management patterns** for multi-turn orchestration: `-c`, `-r`, `-n`, `--continue` + `-p`, `--fork-session`, `--no-session-persistence`, capturing `session_id` from JSON output with `jq`.
- **MCP server configuration and integration** documented, including the `mcp__<server>__<tool>` permission pattern and the bare-mode requirement to re-supply `--mcp-config`.
- **Permission model best practices for CI/CD and scripted usage** — `--allowedTools`, `--disallowedTools`, when to use `acceptEdits` vs `bypassPermissions` (containers only), the deny→ask→allow order.
- **Cost control flags and resource management** — `--max-budget-usd`, `--max-turns`, `--model`, `--effort`.
- **Actionable examples for common orchestration patterns** — commit automation, code review, piped analysis. These live in `references/orchestration-patterns.md` to keep SKILL.md lean.

## Delta

New files:

- `.claude/skills/using-claude-cli/SKILL.md` — entry point with the high-frequency 80/20 content: frontmatter, when-to-use, the three CLI modes, the most common headless-mode flags, subagent overview, session basics, MCP basics, permission overview, cost control, a brief examples section.
- `.claude/skills/using-claude-cli/references/cli-reference.md` — full enumeration of CLI flags grouped by mode and concern, including the rarer ones (`--include-partial-messages`, `--json-schema`, `--append-system-prompt-file`, `--strict-mcp-config`, `--fork-session`).
- `.claude/skills/using-claude-cli/references/subagents.md` — built-in subagent types, custom subagent frontmatter (mirrors the in-repo `.claude/agents/*.md` shape so users see the convention), `--agents '{JSON}'` syntax, the single-level spawning constraint, when to choose subagents over Agent Teams.
- `.claude/skills/using-claude-cli/references/sessions.md` — session lifecycle, persistence path layout (`~/.claude/projects/<encoded>`), JSON `session_id` extraction patterns, `--continue`/`--resume`/`--fork-session` semantics, multi-turn orchestration recipes.
- `.claude/skills/using-claude-cli/references/mcp.md` — config file precedence (`.mcp.json` → `~/.claude.json` → `--mcp-config`), `--strict-mcp-config` semantics, the `mcp__<server>__<tool>` permission pattern, bare-mode behavior.
- `.claude/skills/using-claude-cli/references/permissions.md` — full permission-mode matrix (default/acceptEdits/plan/auto/dontAsk/bypassPermissions), rule glob syntax, settings hierarchy (Managed > CLI args > Local project > Shared project > User settings), read-only auto-approved commands list, sandbox interaction.
- `.claude/skills/using-claude-cli/references/hooks.md` — hook events, matcher syntax, exit-code semantics (0/1/2), example configurations for the four most useful events (PreToolUse, PostToolUse, SessionStart, Stop).
- `.claude/skills/using-claude-cli/references/agent-teams.md` — experimental status, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, team vs subagent decision tree, `claude -w` worktree usage, background agents (`claude agents`).
- `.claude/skills/using-claude-cli/references/orchestration-patterns.md` — copy-paste-ready examples for commit automation, code review, piped analysis, structured JSON output extraction with `jq`, and CI/CD usage (GitHub Actions snippet).

New eval cases (in slice 3, not slice 1):

- A new fixture (`evals/fixtures/skill_using_claude_cli.md`) describing an orchestration task the new skill should help with.
- New cases in `evals/suite.json` under a new phase `using-claude-cli` (or under an existing `meta` phase) that assert: frontmatter validity, line count ≤ 500, at least seven `references/*.md` files, and three llm_judge cases (mode coverage, accuracy of subagent rules, presence of orchestration examples).

Modified files:

- `.claude/CLAUDE.md` — add a single line to the "Available skills" list announcing `/using-claude-cli`. No other change.
- `evals/suite.json` — append cases (slice 3).

No code in `scripts/` changes. No `gt` configuration changes. No `.mcp.json` is added.

## Pattern Decisions

### Decision 1: Where to put the bulk of the prose

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | All content inline in SKILL.md | One file to read; matches `qrspi-work` orchestrator pattern | Likely exceeds the 500-line / 5000-token acceptance criterion; users hit the most-frequent-80% only after wading through niche flags |
| B | Lean SKILL.md (80/20) + `references/*.md` | Honors the line budget; matches the only in-repo skill that already has a `references/` dir (`qrspi-work`); easier to edit one topic at a time | Two files for users to navigate; cross-references must be kept correct |

**Recommendation:** Option B
**Rationale:** Q3 shows the in-repo precedent (`qrspi-work` is the only skill with a `references/` subdirectory). The acceptance criterion explicitly requires `references/` with four named topics, so Option A is non-viable on its face. Option B is also the canonical agentskills.io shape (ref: ticket scope guidance).
**NEW PATTERN?** No — it follows the `qrspi-work/references/` precedent (ref: Q3).

### Decision 2: Whether to bundle a custom agent (`.claude/agents/using-claude-cli.md`)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Skill-only (no agent) | This skill is purely informational reference material; no orchestration logic to delegate; matches `qrspi-work` and `qrspi-ticket` shape | None observable |
| B | Skill + dedicated agent | Mirrors the eight thin-wrapper QRSPI phase skills | The new skill has no workflow that benefits from a separate agent context; spawning would be ceremony for no behavior change |

**Recommendation:** Option A
**Rationale:** The thin-wrapper-fat-agent split (ref: Q3 Discovered Patterns) exists because the QRSPI phases each need an isolated context for the actual phase work. This skill produces no artifact and orchestrates no workflow — it answers questions about CLI usage. Adding a child agent would dilute the boundary, not strengthen it. `qrspi-ticket/SKILL.md` is the in-repo precedent for a skill that does its work inline (ref: Q3).
**NEW PATTERN?** No — follows `qrspi-ticket` precedent for inline-prose skills (ref: Q3).

### Decision 3: Eval coverage strategy

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | No eval cases (informational skill, no testable output) | Avoids drift if external CLI changes | Conflicts with the project convention (Q14) that skill quality is tracked via evals; the acceptance criterion implies the skill must be testable |
| B | Programmatic-only cases (line count, frontmatter, references/ present) | Deterministic; cheap to run; catches drift in our own skill | Doesn't validate accuracy of CLI claims |
| C | Programmatic + llm_judge cases | Structural + content quality; matches the suite.json convention (Q14) | LLM judges add cost and variance |

**Recommendation:** Option C
**Rationale:** The eval suite already mixes programmatic and llm_judge assertions (ref: Q14); going all-programmatic would be inconsistent with the codebase pattern. Cost is bounded by `evals/suite.json` defaults (`trials_per_case: 3`).
**NEW PATTERN?** No — same assertion types as existing cases (ref: Q14).

### Decision 4: Frontmatter shape

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Five-field minimum (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Matches every in-repo skill exactly (ref: Q2) | None |
| B | Add `model: opus` | Mirrors agent frontmatter | Diverges from in-repo skill convention; no in-repo skill carries `model` |
| C | Add `version`, `license` fields | Aligns with agentskills.io conventions outside this repo | Diverges from in-repo convention; no enforcement |

**Recommendation:** Option A, with `argument-hint` set to `[topic]` (optional positional) so the skill is invoked as bare `/using-claude-cli` or `/using-claude-cli sessions` and so on.
**Rationale:** Q2 shows the five-field convention is strict in this repo; no skill diverges. The agentskills.io extra fields are documented in `references/frontmatter.md` for users who want to ship to other repos.
**NEW PATTERN?** No — exact match to ten existing skills (ref: Q2).

### Decision 5: Build process — how to invoke skill-creator

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Invoke the global `skill-creator` skill in a separate Claude Code session, capture its output, commit the result | Honors AC #2 literally; uses the recommended creation tool | Requires a side session; build is not reproducible from this repo alone |
| B | Hand-author SKILL.md following the agentskills.io spec, skip the skill-creator skill | Reproducible from this repo only | Violates AC #2 (which mandates using the skill-creator skill) |

**Recommendation:** Option A
**Rationale:** AC #2 is explicit. The skill-creator skill lives outside the repo (ref: Q1) so the build process is necessarily a manual session that produces a committed result. The PR summary will document the side-session usage.
**NEW PATTERN?** No — same as how `qrspi-*` skills were originally authored.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CLI flag documentation drifts as Claude Code releases new versions | high | medium | Pin to a documented Claude Code version range in SKILL.md preamble; add a "Last verified" date; the eval llm_judge cases will surface staleness when answers no longer match. |
| Coverage exceeds 500-line/5000-token budget once examples are added | medium | medium | Land slice 1 as content-light scaffold; measure with `wc -l` and a token count; offload examples to `references/orchestration-patterns.md` if budget is tight (slice 2). The slice-3 eval case `line_count('SKILL.md') <= 500` will fail-fast on regression. |
| The acceptance criterion "Built using the Anthropic skill-creator skill" cannot be verified after the fact | medium | low | Capture and commit a brief authoring note in `references/build-notes.md` (one-paragraph attribution + date) so the provenance is reviewable. |
| New `references/` files duplicate or contradict the system-reminder-driven `update-config`, `code-review`, and `run` skills | medium | low | Cross-link rather than restate: `references/permissions.md` notes "see global `update-config` skill for settings.json mutations"; `references/orchestration-patterns.md` links to `/code-review` instead of duplicating its examples. |
| Subagent claims contradict Claude Code's true runtime behavior (e.g., the "subagents cannot spawn subagents" rule could be version-dependent) | low | high | Phrase rules with version qualifier ("As of Claude Code 1.x, subagents cannot…"); flag any uncertain claims explicitly in the SKILL body. |
| `allowed-tools` for the new skill is overscoped, granting it tools it does not need | low | low | Restrict to `Read` (the skill only reads its own references and answers questions — it should not edit, run bash, or call MCP). |
| Bare-mode examples leak a permission misconfiguration into a user's CI | low | medium | Every bare-mode example block in `references/cli-reference.md` and `references/orchestration-patterns.md` is preceded by a "scope this with `--allowedTools`" callout. |

## Open Questions

- OQ1: Should `argument-hint` be `[topic]` (the skill answers about a specific topic) or empty (the skill is purely informational and ignores arguments)? Preferred is `[topic]` with the body documenting which topics map to which `references/` file; please confirm.
- OQ2: AC #1 references "agentskills.io standard pattern" — should the SKILL.md additionally include any agentskills.io-only frontmatter fields not currently used in this repo (e.g., `version`, `tags`), or stick strictly to the in-repo five-field convention? Default plan is the latter (Decision 4 Option A).
- OQ3: Should the slice-3 eval cases go under a new `phase: "meta"` in `evals/suite.json`, or be appended to the closest existing phase? Existing phases are all QRSPI-stage names; a meta phase is cleanest but introduces a new schema value.
- OQ4: The ticket says "bare mode (`claude --bare -p`): Skip auto-discovery of hooks, skills, plugins, MCP servers, and CLAUDE.md". This is a strong assertion that should be re-verified against current Claude Code behavior before shipping. Who owns that verification — the implementer or a reviewer with CLI access?
- OQ5: Should the skill's `allowed-tools` include `Bash(claude:*)` so the skill can demonstrate commands by running them, or stay read-only (the recommended default)? Default plan is read-only.
