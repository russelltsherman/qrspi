# Structure Outline — Create a new agent skill called using-claude-cli

**Design basis:** design.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This ticket ships Markdown documentation, not code, so there are no language-level types. The structural artifacts produced are:

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }` — the in-repo YAML frontmatter shape (ref: design.md §Pattern Decisions, Decision 4).
- `ReferenceFile { path: string, topic: string, max_lines: int }` — each file under `references/` represents one topic at a stable path.
- `EvalCase { id: string, name: string, phase: string, prompt: string, context: {files: string[]}, assertions: Assertion[] }` — the existing `evals/suite.json` case shape extended with cases for this skill (ref: design.md §Delta).
- `Assertion { type: "programmatic" | "llm_judge" | "script", check: string, weight: number }` — already exists in `evals/suite.json` (ref: research.md Q14).

## Modified Types

- None. No existing schema changes shape; only new entries are added to `evals/suite.json`'s `cases[]` array.

## Contracts

- **Skill invocation contract:** `/using-claude-cli [topic]` — when invoked with no argument, the skill returns its SKILL.md body summary plus a pointer index into `references/`. When invoked with a topic (e.g., `sessions`, `permissions`, `mcp`, `hooks`, `agent-teams`, `cli-reference`, `subagents`, `orchestration-patterns`, `frontmatter`), the skill reads the matching `references/<topic>.md` file before answering. The mapping topic → file is fixed; unknown topics get a "not a recognized topic — available: ..." response.
- **Reference file index contract:** SKILL.md contains a single canonical index section listing every `references/*.md` file with a one-line summary. Every file under `references/` must appear in the index, and every index entry must point to an existing file. The slice-2 eval case enforces this.
- **Line budget contract:** SKILL.md ≤ 500 lines AND ≤ 5000 tokens. Each `references/*.md` file has no individual cap, but the SKILL.md cap is hard.
- **Frontmatter contract:** Five required keys exactly: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. No `model` field. No optional fields. `allowed-tools` is `Read` only (ref: design.md §Risk Register, "allowed-tools overscoped").
- **Cross-skill non-overlap contract:** Permission-rule editing belongs to the global `update-config` skill, not this one. Code-review examples link to `/code-review` rather than restating its content. Both rules are stated explicitly in SKILL.md.

## Slice 1: Skill scaffold + SKILL.md + references/

**Goal:** Ship a complete, reviewable `.claude/skills/using-claude-cli/` directory — SKILL.md plus all nine `references/*.md` files — that satisfies every acceptance criterion except the eval coverage criterion. The deliverable is testable end-to-end by reading SKILL.md, navigating its index to each reference file, and verifying the three CLI modes / subagents / sessions / MCP / permissions / cost / examples requirements are all addressed.

**Files touched:**

- ✨ `.claude/skills/using-claude-cli/SKILL.md` — entry-point skill body (≤ 500 lines): frontmatter, when-to-use, the three CLI modes, subagent overview, session basics, MCP basics, permission overview, cost control, brief examples, and the canonical index into `references/`.
- ✨ `.claude/skills/using-claude-cli/references/cli-reference.md` — full enumeration of CLI flags grouped by mode and concern.
- ✨ `.claude/skills/using-claude-cli/references/subagents.md` — built-in types (Explore, Plan, General-purpose), custom subagent frontmatter (mirroring `.claude/agents/*.md`), `--agents '{JSON}'`, single-level constraint.
- ✨ `.claude/skills/using-claude-cli/references/sessions.md` — `-c`, `-r`, `-n`, `--continue` + `-p`, `--fork-session`, `--no-session-persistence`, `~/.claude/projects/<encoded>` layout, JSON `session_id` extraction with `jq`.
- ✨ `.claude/skills/using-claude-cli/references/mcp.md` — `.mcp.json` vs `~/.claude.json` vs `--mcp-config`, `--strict-mcp-config`, `mcp__<server>__<tool>` permission pattern, bare-mode behavior.
- ✨ `.claude/skills/using-claude-cli/references/permissions.md` — permission modes matrix, rule glob syntax, settings hierarchy, read-only auto-approved commands, sandbox interaction.
- ✨ `.claude/skills/using-claude-cli/references/hooks.md` — hook events, matcher syntax, exit-code semantics, four example configurations (PreToolUse, PostToolUse, SessionStart, Stop).
- ✨ `.claude/skills/using-claude-cli/references/agent-teams.md` — experimental status flag, team vs subagent decision tree, `claude -w` worktrees, `claude agents` background sessions.
- ✨ `.claude/skills/using-claude-cli/references/orchestration-patterns.md` — copy-paste recipes for commit automation, code review, piped analysis, structured JSON extraction, CI/CD usage.
- ✨ `.claude/skills/using-claude-cli/references/frontmatter.md` — the canonical five-field frontmatter shape, the agentskills.io extra fields treated as optional, and rules for when to declare a `model` (agents) vs not (skills).
- ✨ `.claude/skills/using-claude-cli/references/build-notes.md` — one-paragraph attribution recording that the skill was authored via the global `skill-creator` skill, with date and reviewer.
- ⚠️ `.claude/CLAUDE.md` — append a single line to the "Available skills" list announcing `/using-claude-cli`.

**Verification:**

- [ ] `head -10 .claude/skills/using-claude-cli/SKILL.md` shows the five-key YAML frontmatter exactly (name, description, command, argument-hint, allowed-tools).
- [ ] `wc -l .claude/skills/using-claude-cli/SKILL.md` reports ≤ 500.
- [ ] `ls .claude/skills/using-claude-cli/references/` lists ten files: `agent-teams.md`, `build-notes.md`, `cli-reference.md`, `frontmatter.md`, `hooks.md`, `mcp.md`, `orchestration-patterns.md`, `permissions.md`, `sessions.md`, `subagents.md`.
- [ ] `grep -q '/using-claude-cli' .claude/CLAUDE.md` succeeds (the skill is announced).
- [ ] A spot-read of SKILL.md confirms it contains explicit sections for: interactive mode, headless/print mode, bare mode, subagent spawning, session management, MCP, permissions, cost control, examples.
- [ ] Each `references/*.md` file referenced from the SKILL.md index actually exists (no broken pointers).

**Context cost:** L
**Depends on:** none

## Slice 2: Eval coverage + fixture

**Goal:** Add automated quality gates for the new skill to `evals/suite.json`, including a fixture, so future edits can't silently violate the line budget, lose a reference file, or drift from the acceptance criteria.

**Files touched:**

- ✨ `evals/fixtures/skill_using_claude_cli.md` — fixture describing an orchestration task ("set up a headless CI job that invokes `claude -p` with a JSON-output contract and a restricted permissions allow-list") used as the prompt context for the llm_judge cases.
- ⚠️ `evals/suite.json` — append three new cases under a new `phase: "meta"` (or `phase: "using-claude-cli"` — implementer chooses based on the eval system's enum tolerance; default is `"meta"`): (a) `meta_using_claude_cli_structure` — programmatic assertions on frontmatter, line count, references/ directory contents; (b) `meta_using_claude_cli_mode_coverage` — llm_judge that the three CLI modes are each explained correctly with a worked example; (c) `meta_using_claude_cli_subagent_accuracy` — llm_judge that the subagent docs match the in-repo `.claude/agents/*.md` frontmatter shape and explicitly state the single-level spawning constraint.

**Verification:**

- [ ] `python scripts/run_eval.py --suite evals/suite.json --case meta_using_claude_cli_structure` produces an output transcript and the programmatic assertions all pass.
- [ ] `python scripts/grade.py --results <run-dir>` aggregates a score for the three new cases and the suite-level aggregate score still meets the project target (0.85).
- [ ] `jq '.cases | map(select(.phase == "meta")) | length' evals/suite.json` returns 3 (or whatever the implementer's chosen phase name yields).
- [ ] `cat evals/fixtures/skill_using_claude_cli.md` shows a coherent fixture prompt of reasonable length (10–40 lines).

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- **The bare-mode auto-discovery claim from the ticket may not match current Claude Code behavior.** The ticket asserts `claude --bare -p` skips hooks, skills, plugins, MCP servers, and CLAUDE.md. The repo has no in-repo evidence to verify this (ref: research.md Q10). The implementer must verify against the current Claude Code CLI before writing `references/cli-reference.md`. If the behavior differs, update the design rather than coding around it.
- **`--max-budget-usd` is print-mode-only.** Asserted by the ticket; no in-repo verification exists. The slice-1 implementer must confirm before documenting.
- **Permission-mode names exactly as listed.** The ticket enumerates six modes (`default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`); the implementer must verify these are the current canonical names (and check whether `auto` is now `safetyAuto` or similar in newer releases).
- **Agent Teams environment variable name.** The ticket gives `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; case sensitivity and exact name must be re-verified.
- **`claude -w <name>` worktree syntax.** The ticket asserts this; needs verification — Claude Code may use a different flag (e.g., `--worktree`).
- **JSON output schema for `--output-format json`.** The ticket says the response contains `result`, `session_id`, and "cost metadata". Implementer must verify the actual top-level keys before documenting the `jq` extraction patterns.
- **Whether `evals/suite.json` accepts new phase enum values.** The implementer must confirm by reading `scripts/run_eval.py` whether `phase` is validated against a fixed set or free-form; if validated, choose an existing phase name or extend the validator. (Likely free-form per research.md Q14, but unverified.)
- **The `skill-creator` skill's expected directory layout for `references/`.** Since skill-creator is global (ref: research.md Q1), this skill's `references/` layout is built from the agentskills.io spec the ticket describes. If skill-creator produces a different shape on first invocation, reconcile during slice 1.
