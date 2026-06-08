# Work Tree — Create a new agent skill "using-claude-cli"

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T6 → T7 → T8 → T9 → T13 → T14 (10 tasks)

## Session 1 — Slice 1: Core skill (valid, discoverable, body-complete)

**Load:** structure.md §Types, structure.md §Contracts ("SKILL.md frontmatter", "SKILL.md body", "validate_skill_structure()", "references/ link set"), plan.md §Slice 1
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `SKILL.md` with five-field YAML frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) per `SkillFrontmatter`; no agentskills.io fields | — | §1 | S | pending |
| T2 | Append body sections for AC5 (CLI modes summary) and AC11 (orchestration examples) with provenance notes | T1 | §2 | M | pending |
| T3 | Append body sections for AC6 (subagents), AC7 (sessions), AC9 (permissions), AC10 (cost control); common path inline, depth deferred to `references/` | T2 | §3 | M | pending |
| T4 | Append "References" section linking the exact four Slice-2 filenames; keep body ≤ 500 lines | T3 | §4 | S | pending |
| T5 | Modify `.claude/CLAUDE.md` — add `using-claude-cli` to "Available skills" list, marked utility/infra | T1 | §5 | S | pending |
| T6 | Create `scripts/using_claude_cli_skill_test.py` — `validate_skill_structure()`: 5-key YAML parse, body ≤ 500 lines, non-empty body | T4 | §6 | M | pending |
| T7 | Run `python3 scripts/using_claude_cli_skill_test.py` — expect exit 0 | T6 | §7 | S | pending |
| T8 | **Verify Slice 1** — test passes; skill listed in CLAUDE.md; common-path coverage inline, advanced deferred | T5, T7 | §8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Fresh context for Slice 2 — drop Slice 1 working detail, keep only the SKILL.md References link set and the test contract.

## Session 2 — Slice 2: Advanced reference docs

**Load:** structure.md §Contracts ("references/ link set", "validate_skill_structure()"), plan.md §Slice 2, impl-log.md §Slice 1 (SKILL.md References link set + test signature, notes only)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9  | Create `references/advanced-cli-flags.md` — five CLI modes, output formats, streaming, model selection (non-empty) | T8 | §9 | M | pending |
| T10 | Create `references/hook-examples.md` — matcher syntax, exit-code semantics, pre/post tool-use, prompt vs agent hooks; provenance-marked | T8 | §10 | M | pending |
| T11 | Create `references/agent-team-orchestration.md` — agent teams, git worktrees, background agents, teammate communication | T8 | §11 | M | pending |
| T12 | Create `references/permission-rule-patterns.md` — rule syntax, eval order (deny→ask→allow), read-only lists, CI/CD safety; provenance-marked | T8 | §12 | M | pending |
| T13 | Modify `scripts/using_claude_cli_skill_test.py` — assert all four `references/*.md` exist non-empty and every SKILL.md `references/` link resolves | T9, T10, T11, T12, T4 | §13 | M | pending |
| T14 | **Verify Slice 2** — test passes with reference-existence assertions; four files non-empty; no dangling links | T13 | §14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice complete and verified — no further sessions; stack ready for PR.
