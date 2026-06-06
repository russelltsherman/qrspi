# Work Tree — Create `using-gemini-cli` Agent Skill

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T16 → T17 → T18 (15 tasks)

> Single-slice ticket: all 18 plan steps build one cohesive pure-markdown skill
> authored inside the `skill-creator` workflow. Body sections (T3–T12) serialize on
> the same `SKILL.md` file, so they form the critical-path spine. Reference files
> (T13–T15) are shorter branches off body sections that mention them; they must exist
> before the trim (T16) but never overtake the body spine. There is one Verify
> checkpoint (T18), process- and content-based rather than a test runner.

## Session 1 — Scaffold + SKILL.md body

**Load:** structure.md §Contracts (frontmatter required set, body cap),
        structure.md §Types (`SKILLFrontmatter`), design.md §Desired End State,
        design.md §Decision 3, plan.md §Slice 1 (Setup + Core Logic),
        `skill-creator` skill
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` to scaffold `using-gemini-cli/` + SKILL.md skeleton | — | §1 | S | pending |
| T2 | Author SKILL.md frontmatter (name, description, allowed-tools ⊇ {Bash}) | T1 | §2 | S | pending |
| T3 | Add "Install & Authenticate" section (version/date-pinned facts) | T2 | §3 | S | pending |
| T4 | Add "Invocation" section (interactive, `-p`, stdin-pipe via Bash) | T3 | §4 | S | pending |
| T5 | Add "Permission & Approval Model" section (default/auto_edit/yolo, HARD-STOP) | T4 | §5 | S | pending |
| T6 | Add "Sandbox" section (`--sandbox`, profiles, SANDBOX_MOUNTS; no cross-ref) | T5 | §6 | S | pending |
| T7 | Add "GEMINI.md Context Hierarchy" section | T6 | §7 | S | pending |
| T8 | Add "MCP & Extensions" section (mcpServers, extensions install) | T7 | §8 | S | pending |
| T9 | Add "Subagents" section (`.gemini/agents/*.md`, routing, tool grants) | T8 | §9 | S | pending |
| T10 | Add "Multi-Agent Orchestration" section (`-p`, stdin/stdout, HARD-STOP) | T9 | §10 | M | pending |
| T11 | Add "Limitations" section (Antigravity-deprecation note, date-pinned) | T10 | §11 | S | pending |
| T12 | Add "Worked Examples" section (review/test-gen/exploration as Bash gemini) | T11 | §12 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body authored. Fresh context to write the three reference
deep-dive files without carrying the full body-authoring transcript.

## Session 2 — Reference deep-dives

**Load:** structure.md §Files touched, design.md §Delta, design.md §Decision 3,
        plan.md §Slice 1 (Reference deep-dives), SKILL.md §Permission/§Sandbox/
        §MCP/§Subagents/§Multi-Agent Orchestration (relative-path mentions only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Create `references/permissions-and-sandbox.md` (deep dive) | T6 | §13 | M | pending |
| T14 | Create `references/orchestration.md` (external-agent invocation deep dive) | T10 | §14 | M | pending |
| T15 | Create `references/subagents-mcp-extensions.md` (deep dive) | T9 | §15 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Reference files written. Fresh context for the consistency pass +
Verify, which audits the now-complete SKILL.md + references against the contracts.

## Session 3 — Consistency pass + Verify

**Load:** structure.md §Contracts (body ≤ 500 lines / ≤ 5000 tokens, link
        resolution / no orphans), plan.md §Slice 1 (Consistency pass + Verify),
        SKILL.md (full) + references/*.md (authored)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Trim SKILL.md body to cap, relocating overflow detail into references | T12, T13, T14, T15 | §16 | M | pending |
| T17 | Verify every prose `references/*.md` path resolves; no orphan ref files | T16 | §17 | S | pending |
| T18 | **Verify Slice 1** — skill-creator eval loop, frontmatter YAML check, read-through | T16, T17 | §18 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. No further sessions — single-slice ticket.
