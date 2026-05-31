# Structure Outline — Create a new agent skill called "using omlx cli"

**Design basis:** design.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This is a documentation/skill deliverable — no programmatic types. The "types" here are the skill's structural contracts (files and their required shape):

- `SKILL.md { frontmatter: { name: "using-omlx-cli", description: string }, body: markdown }` — root skill file (ref: design.md §Delta, Decision 3)
- `ReferenceDoc { path: ".claude/skills/using-omlx-cli/references/<topic>.md", body: markdown }` — on-demand detail file pulled in by an explicit in-body pointer (ref: design.md Decision 2)

## Modified Types

None. No existing files are modified (ref: design.md §Delta).

## Contracts

Cross-file contracts within the skill (the SKILL.md body must reference each by relative path, and each referenced file must exist):

- `SKILL.md → references/configuration.md` — full `omlx serve` flag reference + settings/env precedence
- `SKILL.md → references/performance-tuning.md` — two-tier KV cache, batching, memory-planning math, per-tier model-size recommendations
- `SKILL.md → references/api-and-mcp.md` — OpenAI/Anthropic-compatible endpoints, client config, `--mcp-config`, `omlx launch` agent matrix
- `SKILL.md → references/troubleshooting.md` — failure modes, monitoring commands, production-hardening checklist
- Frontmatter contract: `name` value === directory slug `using-omlx-cli` (ref: design.md Decision 3, research Q5)

## Slice 1: Author the using-omlx-cli skill (SKILL.md + references)

**Goal:** A complete, self-contained skill at `.claude/skills/using-omlx-cli/` whose SKILL.md (valid frontmatter, under the size budget) covers the full omlx server lifecycle and decision guidance, with each detail topic offloaded to a `references/` file that the body links to. End-to-end verifiable: every acceptance-criterion topic is present, every body pointer resolves to an existing reference file, and frontmatter matches the in-repo convention.

**Files touched:**

- ✨ `.claude/skills/using-omlx-cli/SKILL.md` — frontmatter (`name: using-omlx-cli`, trigger-style `description`) + lean body: hard preconditions (macOS 15+, Apple Silicon M1-M4, Python 3.10+) with stop-if-unmet; install/setup (brew tap+install, verify, brew services, optional MCP pip, upgrade); server lifecycle (serve/configure/monitor/stop); memory-tier model-size decision table (16/24/32/64 GB) + ~0.5 GB/B + 5-6 GB rule with an explicit "do not load oversized models" guard; two-tier KV cache summary; OpenAI-compatible API endpoint table; MCP + `omlx launch` summary; oMLX-vs-Ollama-vs-LM-Studio decision table; in-scope/out-of-scope list; troubleshooting quick table; explicit pointers to each references file.
- ✨ `.claude/skills/using-omlx-cli/references/configuration.md` — full `omlx serve` flag table, `~/.omlx/settings.json` + CLI-precedence, `OMLX_MODEL_DIR`/`OMLX_PORT`, default port 8000.
- ✨ `.claude/skills/using-omlx-cli/references/performance-tuning.md` — two-tier KV cache (hot unified-memory / cold SSD via `--paged-ssd-cache-dir`), TTFT 30-90s→1-3s, continuous batching (~1.64x at 5 reqs), `--max-batch-size` tradeoff, TurboQuant KV, memory-planning math, full per-tier model-size recommendations, MTP speculative decoding.
- ✨ `.claude/skills/using-omlx-cli/references/api-and-mcp.md` — endpoints (`/v1/chat/completions`, `/v1/embeddings`, `/v1/messages`), admin dashboard + chat UI, client config (LangChain/LlamaIndex/OpenAI SDK), function calling, `--mcp-config`, `omlx launch <claude|codex|opencode|openclaw|pi|copilot|hermes>`, tool-result trimming.
- ✨ `.claude/skills/using-omlx-cli/references/troubleshooting.md` — Metal OOM crash loop (reboot to clear leaked Metal memory; do not chase destructive workarounds), silent memory pressure / swap storms, mixed chat+embeddings Metal assertion failures, model-not-showing (MLX safetensors in subdirs), pre-load checklist (close Chrome/Xcode/Docker), monitoring (`powermetrics` GPU + memory pressure), production-hardening (always set `--max-model-memory`/`--max-process-memory`, enable SSD cache).

**Verification:**
- [ ] `.claude/skills/using-omlx-cli/SKILL.md` exists with frontmatter containing `name: using-omlx-cli` and a non-empty `description`; slug matches directory name.
- [ ] SKILL.md body is under 500 lines and ~5000 tokens (`wc -l`; spot-check token budget).
- [ ] All four `references/*.md` files exist and are non-empty.
- [ ] Every `references/...` pointer in SKILL.md resolves to an existing file (grep body pointers, confirm each path exists).
- [ ] Acceptance-criteria coverage check: lifecycle (install/serve/configure/monitor/stop), memory-tier table, two-tier KV cache, OpenAI-compatible API, MCP + agent launch, troubleshooting, and oMLX-vs-Ollama-vs-LM-Studio opinion are each present (grep for anchor headings/keywords).
- [ ] Files are at the tracked path `.claude/skills/using-omlx-cli/`, NOT under `.worktrees/`/gitignored path (`git status --short` shows them as additions).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- All omlx CLI facts (flag names, install commands, URLs, behaviors, memory tiers) come solely from the ticket body; they cannot be verified against the actual tool from within this repo (ref: design.md Risk Register). The skill content must mirror the ticket verbatim and must not invent additional flags or behaviors.
- The skill is authored to follow global skill-creator conventions rather than literally invoking that external skill inside this automated run (ref: design.md OQ2). If acceptance strictly requires the builder to have been invoked, a human must confirm this substitution is acceptable.
- Frontmatter is the agentskills.io minimum (`name` + `description`), with no slash `command`/`allowed-tools` (ref: design.md Decision 3, OQ1). If a manual slash entry point is wanted, that is a one-line frontmatter addition.
- Four references files is the assumed granularity (ref: design.md OQ3); merging perf/troubleshooting is a non-breaking alternative if reviewers prefer fewer files.
