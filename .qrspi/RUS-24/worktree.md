# Work Tree — Create a new agent skill called "using omlx cli"

**Plan basis:** plan.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T9 → T10 → T11 → T12 → T13 → T14

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1, design.md §Desired End State (acceptance-criteria mapping)
**Estimated context:** ~20% of window (single cohesive docs slice; ticket facts are the only source material)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `.claude/skills/using-omlx-cli/references/` directory (and parent skill dir) at the tracked path | — | §1 | S | pending |
| T2 | Create `SKILL.md` with frontmatter (`name: using-omlx-cli`, trigger-style `description`) | T1 | §2 | S | pending |
| T3 | Add Preconditions section (macOS 15+, Apple Silicon M1-M4, Python 3.10+, stop-if-unmet) to SKILL.md body | T2 | §3 | S | pending |
| T4 | Add Install & Setup section (brew tap/install, verify, brew services, MCP pip, upgrade) | T3 | §4 | S | pending |
| T5 | Add Server Lifecycle section (serve/auto-discovery/LRU, configure, monitor, stop) | T4 | §5 | S | pending |
| T6 | Add Memory-tier model-size decision table + memory rule + oversized-model guard | T5 | §6 | M | pending |
| T7 | Add two-tier KV cache summary + OpenAI-compatible API endpoint table + MCP/launch summary | T6 | §7 | M | pending |
| T8 | Add oMLX-vs-Ollama-vs-LM-Studio decision table + in-scope/out-of-scope list | T7 | §8 | S | pending |
| T9 | Add Troubleshooting quick table + "Detailed references" pointer list (all 4 references files) | T8 | §9 | S | pending |
| T10 | Create `references/configuration.md` (full flag table, settings precedence, env vars, port) | T1 | §10 | M | pending |
| T11 | Create `references/performance-tuning.md` (KV cache deep dive, batching, memory math, per-tier sizes, MTP, oQ) | T1 | §11 | M | pending |
| T12 | Create `references/api-and-mcp.md` (endpoints, client config, function calling, mcp-config, launch matrix) | T1 | §12 | M | pending |
| T13 | Create `references/troubleshooting.md` (failure modes, monitoring, production-hardening) | T1 | §13 | M | pending |
| T14 | Run frontmatter + pointer integrity check | T2, T9, T10, T11, T12, T13 | §14 | S | pending |
| T15 | Run size + coverage check | T9, T10, T11, T12, T13 | §15 | S | pending |
| T16 | **Verify Slice 1** (checkpoint: files exist, frontmatter valid, body < 500 lines, pointers resolve, coverage complete, tracked path) | T14, T15 | §16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Single-slice deliverable. No further sessions; slice completes the ticket. Boundary marks end of implementation.
