# Work Tree — Create a new agent skill for using the Claude CLI

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T0 → T1 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T17 → T18 → T19

## Session 0 — Pre-slice gate (blocking)

**Load:** plan.md §Pre-slice gate, design.md §Open Questions, structure.md §Open Questions
**Estimated context:** ~12%

These open questions have no file mapping but constrain content authored in every
downstream task. They must be resolved (or escalated) before Slice 1 begins.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T0 | Resolve OQ3 — fix authoritative CLI source of truth (installed `claude --help` vs. pinned docs version); no CLI fact encoded until fixed | — | §Gate/OQ3 | M | pending |
| T0a | Resolve OQ1 — confirm `skill-creator` reachability this session; if unreachable, escalate rather than hand-author | — | §Gate/OQ1 | S | pending |
| T0b | Resolve OQ4 — confirm acceptance of no-agent content-skill shape; if rejected, halt and rework structure | — | §Gate/OQ4 | S | pending |
| T0c | Resolve OQ5 — decide correct-vs-echo for unverified ticket specifics (10MB stdin cap, permission-mode list); depends on OQ3 | T0 | §Gate/OQ5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Gate resolved. The gate is a decision/escalation activity, not file authoring; isolating it keeps Slice 1 context free of OQ deliberation and ensures a hard stop if OQ4 invalidates the structure.

## Session 1 — Slice 1: Verified SKILL.md (frontmatter + body)

**Load:** structure.md §New Types (SkillFrontmatter), structure.md §Contracts (references/ link contract), plan.md §Slice 1, design.md §Decision 2, gate decisions (OQ3/OQ5 fact set)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create SKILL.md with YAML frontmatter only (name/command/description/argument-hint/allowed-tools; naming triple) | T0c, T0a, T0b | §1.1 | S | pending |
| T2 | Create references/cli-flags.md stub (H1 + scope note) | T1 | §1.2 | S | pending |
| T3 | Create references/subagents-and-teams.md stub | T1 | §1.3 | S | pending |
| T4 | Create references/hooks.md stub | T1 | §1.4 | S | pending |
| T5 | Create references/permissions-and-mcp.md stub | T1 | §1.5 | S | pending |
| T6 | Create references/cicd-patterns.md stub | T1 | §1.6 | S | pending |
| T7 | Append body: CLI modes (headless/bare + three modes), OQ3-verified facts only | T1 | §1.7 | M | pending |
| T8 | Append body: subagent spawning (common pattern; defer to references link) | T7 | §1.8 | S | pending |
| T9 | Append body: session management (resume/continue/persistence), verified facts | T8 | §1.9 | S | pending |
| T10 | Append body: permission best practices (defer detail to references link) | T9 | §1.10 | S | pending |
| T11 | Append body: short orchestration examples (cost control + composition) | T10 | §1.11 | S | pending |
| T12 | Append "References" section linking all five references/*.md (topic names match stubs) | T11, T2, T3, T4, T5, T6 | §1.12 | S | pending |
| T13 | **Verify Slice 1** — run steps 13–15: frontmatter YAML + naming triple, body budget (<500 lines / <5000 tok), every reference link resolves, no unverified flags, skill-creator validation or escalation recorded | T12 | §1.16 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Fresh context for Slice 2 reference content; drop body-authoring detail, carry forward only the verified link contract and the OQ3 fact set.

## Session 2 — Slice 2: Reference content

**Load:** structure.md §Contracts (references/ link contract), plan.md §Slice 2, gate decisions (OQ3 fact set, OQ5), impl-log.md §Slice 1 (notes only — link topics + body budget)
**Estimated context:** ~28%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Fill cli-flags.md — verified advanced flags, output formats, cost/resource control; experimental labeled; OQ5-handled | T13 | §2.17 | M | pending |
| T15 | Fill subagents-and-teams.md — built-in types, custom .claude/agents/, --agents JSON, agent teams (experimental), worktrees | T13 | §2.18 | M | pending |
| T16 | Fill hooks.md — events, matcher syntax, exit codes, examples | T13 | §2.19 | M | pending |
| T17 | Fill permissions-and-mcp.md — modes, deny→ask→allow order, settings hierarchy, rule syntax, MCP config; verified `Bash(<cmd>:*)`/`mcp__<server>__<tool>` syntax | T13 | §2.20 | M | pending |
| T18 | Fill cicd-patterns.md — brief GitHub Actions / GitLab CI examples | T13 | §2.21 | S | pending |
| T19 | **Verify Slice 2** — run steps 22–25: no stubs remain, topics match body links, every flag in OQ3 fact set (experimental labeled), MCP/tool-rule syntax verified, no unverified ticket specifics echoed, body still within budget, skill-creator eval if reachable | T14, T15, T16, T17, T18 | §2.26 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete. Both slices verified; skill is self-sufficient. No further authoring sessions — proceed to PR phase.
