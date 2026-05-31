# Work Tree — Create a new agent skill called using-claude-cli

**Plan basis:** plan.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 → T19

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1, design.md §Pattern Decisions (Decisions 1, 2, 4, 5), design.md §Risk Register

**Estimated context:** ~30% of window (one slice's worth of plan + the four design sections; SKILL.md and references files are NEW so no large existing-file reads are needed)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `.claude/skills/using-claude-cli/` and `.claude/skills/using-claude-cli/references/` directories | — | §1.1 | S | pending |
| T2 | Side-session: invoke global `skill-creator` to produce the SKILL.md scaffold; capture output for T3 | T1 | §1.2 | M | pending |
| T3 | Write `SKILL.md` with five-key frontmatter and full body (≤ 500 lines) | T2 | §1.3 | L | pending |
| T4 | Write `references/cli-reference.md` covering interactive/print/bare/output-format/session/permission/prompt/cost/MCP flags | T3 | §1.4 | M | pending |
| T5 | Write `references/subagents.md` (built-in + custom + ephemeral + single-level rule) | T3 | §1.5 | M | pending |
| T6 | Write `references/sessions.md` (lifecycle, persistence layout, jq recipe, multi-turn) | T3 | §1.6 | M | pending |
| T7 | Write `references/mcp.md` (config precedence, strict mode, mcp__ pattern, bare-mode) | T3 | §1.7 | M | pending |
| T8 | Write `references/permissions.md` (modes, rules, hierarchy, auto-approved list, sandbox; cross-link to update-config) | T3 | §1.8 | M | pending |
| T9 | Write `references/hooks.md` (events, matchers, exit codes, four examples) | T3 | §1.9 | M | pending |
| T10 | Write `references/agent-teams.md` (experimental, decision tree, worktrees, background, display, cost note) | T3 | §1.10 | M | pending |
| T11 | Write `references/orchestration-patterns.md` (five recipes with `--allowedTools` callouts) | T3 | §1.11 | M | pending |
| T12 | Write `references/frontmatter.md` (required vs optional fields, model field rules) | T3 | §1.12 | S | pending |
| T13 | Write `references/build-notes.md` (one-paragraph attribution) | T3 | §1.13 | S | pending |
| T14 | Modify `.claude/CLAUDE.md` — add one bullet announcing `/using-claude-cli` | T3 | §1.14 | S | pending |
| T15 | Run frontmatter/line-count/index/sections tests (plan steps 15–21) | T4–T14 | §1.15–§1.21 | S | pending |
| T16 | **Verify Slice 1** — checkpoint at plan §1.22 (line count, references presence, CLAUDE.md announcement, spot-read) | T15 | §1.22 | S | pending |

--- SESSION BOUNDARY ---

**Reason:** Slice 1 is complete and verified. Fresh context for Slice 2 keeps the eval-suite editing session lean — Slice 2 needs only `evals/suite.json` and the new fixture, and brings its own assertions; reloading all references material is unnecessary. The slice-1 outputs are large (one SKILL.md + ten references files) so a session boundary here drops them from context.

## Session 2

**Load:** structure.md §Slice 2, plan.md §Slice 2, impl-log.md §Slice 1 (notes only), evals/suite.json (read-only inspection of existing cases for shape conformance), evals/fixtures/ticket_rest_endpoint.md (one existing fixture for shape conformance)

**Estimated context:** ~20% of window (suite.json + one reference fixture + the slice-2 plan section is small)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T17 | Write `evals/fixtures/skill_using_claude_cli.md` (10–50 lines, orchestration-task description) | T16 | §2.23 | S | pending |
| T18 | Modify `evals/suite.json` — append case_016 (programmatic structure), case_017 (llm_judge mode coverage), case_018 (llm_judge subagent accuracy) | T17 | §2.24 | M | pending |
| T19 | Verify `scripts/run_eval.py` accepts `phase: "meta"`; if validator rejects new phase values, switch all three cases to an existing phase or extend the validator (plan §2.25) | T18 | §2.25 | S | pending |
| T20 | Run all slice-2 tests (plan steps 26–31): JSON shape, count, IDs, fixture existence, line-count assertion presence, optional `run_eval.py` execution | T19 | §2.26–§2.31 | S | pending |
| T21 | **Verify Slice 2** — checkpoint at plan §2.32 (totals match, fixture present, assertions correct) | T20 | §2.32 | S | pending |

--- SESSION BOUNDARY ---

**Reason:** End of implementation. The PR-summary phase begins in a fresh context with the impl-log entries from both slices.
