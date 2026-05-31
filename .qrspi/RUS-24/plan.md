# Implementation Plan — Create a new agent skill called "using omlx cli"

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 16

## Slice 1: Author the using-omlx-cli skill (SKILL.md + references)

### Setup

1. ✨ Create directory `.claude/skills/using-omlx-cli/references/` (also creates the parent skill directory). Per structure.md Contracts, all skill files live under `.claude/skills/using-omlx-cli/` — a TRACKED path, NOT under `.worktrees/`.

### Core Logic

2. ✨ Create `.claude/skills/using-omlx-cli/SKILL.md` — frontmatter only first: `name: using-omlx-cli` (== directory slug, ref structure.md Contracts) and a `description` that leads with the capability ("Manage local LLM inference on Apple Silicon via the omlx CLI…") and includes an explicit "Use when…" trigger clause naming Apple Silicon + omlx + local model serving (ref design.md Decision 3, research Q6). No `command`/`allowed-tools`.

3. ⚠️ Extend `.claude/skills/using-omlx-cli/SKILL.md` body — Preconditions section: macOS 15.0+ (Sequoia), Apple Silicon (M1/M2/M3/M4), Python 3.10+; instruct the agent to STOP and report if a precondition is unmet rather than proceeding (ref design.md Risk Register, research Q8).

4. ⚠️ Extend `SKILL.md` body — Install & Setup section: `brew tap jundot/omlx https://github.com/jundot/omlx` then `brew install omlx`; verify `omlx --version`; run as service `brew services start omlx`; optional MCP `/opt/homebrew/opt/omlx/libexec/bin/pip install mcp`; upgrade `brew update && brew upgrade omlx`. Content sourced verbatim from ticket (ref structure.md Unverified Assumptions).

5. ⚠️ Extend `SKILL.md` body — Server Lifecycle section: start (`omlx serve --model-dir ~/models`, auto-discovery of LLM/VLM/embedding/reranker, simultaneous multi-model, LRU eviction), configure (point to references/configuration.md), monitor (point to references/troubleshooting.md monitoring commands), stop (`brew services stop omlx` / menu bar app).

6. ⚠️ Extend `SKILL.md` body — Memory-tier model-size decision table (16 GB / 24 GB / 32 GB / 64 GB+) + the ~0.5 GB/B weights + 5-6 GB overhead rule, with an explicit opinionated guard: "do not attempt to load a 70B model on a 16 GB machine" (ref design.md Decision 4, ticket Scope Guidance). Point to references/performance-tuning.md for the full math.

7. ⚠️ Extend `SKILL.md` body — Two-tier KV cache summary (Tier 1 hot unified memory, Tier 2 cold SSD via `--paged-ssd-cache-dir`; TTFT 30-90s→1-3s on long sessions) + OpenAI-compatible API endpoint table (`/v1/chat/completions`, `/v1/embeddings`, `/v1/messages`, `/admin`) + MCP/agent-launch summary (`--mcp-config`, `omlx launch <agent>`). Each points to its references file.

8. ⚠️ Extend `SKILL.md` body — Decision table: prefer oMLX vs Ollama vs LM Studio (oMLX when Apple Silicon + max throughput + two-tier KV + multi-model LRU; Ollama when cross-platform / simpler Modelfile) + In-scope / Out-of-scope list (out: fine-tuning, oQ quantization pipeline, custom MLX kernels, iOS/iPadOS) (ref design.md Decision 4, ticket Scope Guidance).

9. ⚠️ Extend `SKILL.md` body — Troubleshooting quick table (Metal OOM crash loop → reboot; mixed chat+embeddings → Metal assertion failures; model not showing → MLX safetensors in subdirs) + a "Detailed references" section listing all four references/*.md with one-line purposes (the in-body pointers required by structure.md Contracts).

10. ✨ Create `.claude/skills/using-omlx-cli/references/configuration.md` — full `omlx serve` flag table (--model-dir, --max-model-memory, --max-process-memory, --paged-ssd-cache-dir, --hot-cache-max-size, --max-batch-size, --max-context-length, --max-concurrent-requests [default 8], --mcp-config, --api-key, --hf-endpoint); `~/.omlx/settings.json` persistence with CLI-flag precedence; env vars `OMLX_MODEL_DIR`/`OMLX_PORT`; default port 8000.

11. ✨ Create `.claude/skills/using-omlx-cli/references/performance-tuning.md` — two-tier KV cache deep dive; continuous batching (~1.64x at 5 concurrent reqs); `--max-batch-size` throughput/latency tradeoff; TurboQuant KV for 10K+ token / concurrent serving; memory-planning math; full per-tier model-size recommendations (16/24/32/64 GB); MTP speculative decoding (enable per-model in admin); oQ-quantized models from huggingface.co/Jundot.

12. ✨ Create `.claude/skills/using-omlx-cli/references/api-and-mcp.md` — endpoint details + example client config for OpenAI SDK / LangChain / LlamaIndex against `http://localhost:8000/v1`; `/v1/messages` Anthropic compatibility; admin dashboard `/admin` + chat UI `/admin/chat`; function calling / JSON-schema tool use; `--mcp-config mcp.json`; `omlx launch <claude|codex|opencode|openclaw|pi|copilot|hermes>` agent matrix + curses TUI picker; tool-result trimming.

13. ✨ Create `.claude/skills/using-omlx-cli/references/troubleshooting.md` — Metal OOM crash loop (leaked Metal memory across crash-restart; only full reboot clears it; do NOT chase destructive workarounds, ref research Discovered Patterns); silent memory pressure / swap storms; mixed-workload Metal assertion failures; pre-load checklist (close Chrome/Xcode/Docker); model-not-showing (MLX safetensors in subdirs of model-dir); monitoring (`sudo powermetrics --samplers gpu_power -i 5000`, `sudo powermetrics --samplers smc -n 1 | grep "GPU Active"`); production-hardening (always set --max-model-memory/--max-process-memory; enable SSD cache for long-context).

### Tests

14. Run frontmatter + pointer integrity check:
    - Confirm `name: using-omlx-cli` present and equals directory slug.
    - For each `references/<file>.md` referenced in SKILL.md, confirm the file exists.
    - **Expected:** name matches; every body pointer resolves.

15. Run size + coverage check:
    - `wc -l .claude/skills/using-omlx-cli/SKILL.md` → under 500.
    - Grep SKILL.md for anchors: install, serve, stop, memory tier table, KV cache, `/v1/`, `omlx launch`, troubleshooting, oMLX vs Ollama.
    - **Expected:** body < 500 lines; every acceptance-criterion topic present.

### Verify Slice 1

16. **Checkpoint:**
    ```
    test -f .claude/skills/using-omlx-cli/SKILL.md \
      && ls .claude/skills/using-omlx-cli/references/ \
      && wc -l .claude/skills/using-omlx-cli/SKILL.md \
      && grep -c '^name: using-omlx-cli' .claude/skills/using-omlx-cli/SKILL.md \
      && git status --short | grep '.claude/skills/using-omlx-cli'
    ```
    - [ ] `SKILL.md` exists with valid frontmatter (`name: using-omlx-cli`, non-empty description).
    - [ ] All four `references/*.md` exist and are non-empty.
    - [ ] SKILL.md body < 500 lines / ~5000 tokens.
    - [ ] Every references pointer in SKILL.md resolves to an existing file.
    - [ ] Coverage: lifecycle, memory-tier table, two-tier KV cache, OpenAI-compatible API, MCP + agent launch, troubleshooting, oMLX-vs-Ollama-vs-LM-Studio opinion all present.
    - [ ] Files appear in `git status --short` under `.claude/skills/using-omlx-cli/` (tracked path, not gitignored).

---

## Rollback Notes

- Steps 1-13 (file/dir creation): rollback is removal of the `.claude/skills/using-omlx-cli/` directory — `git rm -r .claude/skills/using-omlx-cli/` (or delete untracked dir before commit). No destructive effect on existing files; the slice only adds files, modifies none.
- No DB migrations, no config changes to existing files, no destructive operations.
