---
name: using-omlx-cli
description: Operate the omlx CLI to run local LLM inference on Apple Silicon (M-series) Macs — install, serve, configure memory tiers and two-tier KV cache, hit the OpenAI-compatible API, wire up MCP, launch agents, and troubleshoot. Use when working on an Apple Silicon Mac and the task involves local LLM inference, running models offline/on-device, an `omlx` command, an `omlx serve` server on localhost:8000, choosing a model size for available unified memory, or deciding between oMLX, Ollama, and LM Studio.
command: /using-omlx-cli
argument-hint: <what you want to do with omlx, e.g. "serve a 32B model on a 64GB M3 Max">
allowed-tools: Read, Bash
---

# Using the omlx CLI

`omlx` is a command-line server for running large language models **locally on Apple
Silicon** (M-series) Macs. It uses Apple's MLX framework and the Metal GPU, serving models
over an **OpenAI-compatible HTTP API** so existing OpenAI/Anthropic-style clients, MCP
configs, and agent runners point at it with only a base-URL change.

This skill is reference knowledge. The SKILL.md below is a thin overview; the detailed flag
lists, tuning tables, and failure-mode catalogs live in `references/` and should be read on
demand (see pointers in each section). Read the relevant reference file before giving the
user exact flag values — do not guess from memory.

## When this applies

The defining constraint is **Apple Silicon + unified memory**. The model weights and the KV
cache share the same physical RAM as the OS and every other app, so the central skill is
sizing the workload to fit memory. If the machine is not an M-series Mac, omlx does not apply
— recommend a different runtime.

## Lifecycle overview

omlx follows a simple install → serve → configure → monitor → stop loop.

1. **Install** — install the `omlx` CLI (Homebrew or the project installer), then pull or
   point at a local MLX-format model.
2. **Serve** — `omlx serve --model <model> [flags]` starts the HTTP server, by default on
   `http://localhost:8000`. Serving loads the weights into unified memory and holds them
   resident until the process stops.
3. **Configure** — choose the model size for the machine's memory tier, then tune the
   two-tier KV cache for the expected context length and concurrency.
4. **Monitor** — watch memory pressure and throughput while serving; on Apple Silicon the
   failure mode is memory exhaustion, so this is where you catch trouble early.
5. **Stop** — stop the server to release the weights from unified memory.

For the complete `omlx serve` flag reference, lifecycle detail, and the
install/start/stop mechanics, read `references/serve-flags.md`.

## Choosing a model for the memory tier

The single most important decision is matching model size to the Mac's unified memory.
Loading a model that does not leave headroom for the KV cache and the OS triggers the OOM
crash loop described in troubleshooting. Rough starting points:

| Unified memory | Comfortable model size (quantized) |
|----------------|------------------------------------|
| 16 GB          | up to ~7–8B                        |
| 24 GB          | up to ~13–14B                      |
| 32 GB          | up to ~32B (tight) / ~20B (comfortable) |
| 64 GB          | up to ~70B (quantized)             |

These are deliberately conservative because weights are only part of the budget — the KV
cache grows with context length and concurrency, and the OS needs its own headroom. For the
full per-tier table, quantization notes, and how to leave KV-cache headroom, read
`references/memory-tiers.md`.

## Two-tier KV cache

omlx splits the KV cache into a **hot tier** (kept in fast unified memory) and a **cold
tier** (paged out to SSD), so long-context workloads can exceed what fits in RAM at the cost
of latency on cold reads. Two flags drive this:

- `--hot-cache-max-size` — cap on the in-memory hot tier; once exceeded, older cache pages
  spill to the cold tier.
- `--paged-ssd-cache-dir` — directory where the cold tier is paged to SSD.

Set `--hot-cache-max-size` so that weights + hot cache + OS headroom stay within unified
memory; let overflow page to SSD rather than crashing. For the hot/cold tuning tables and
worked examples per memory tier, read `references/memory-tiers.md`.

## OpenAI-compatible API, MCP, and agent launch

`omlx serve` exposes an OpenAI-compatible API at `http://localhost:8000/v1`:

- `POST /v1/chat/completions` — chat-style completions.
- `POST /v1/embeddings` — embedding vectors.
- `POST /v1/messages` — Anthropic-style messages endpoint.

Point any OpenAI-compatible client at the base URL `http://localhost:8000/v1`. To wire the
server into an MCP-based toolchain, pass `--mcp-config <path>` to attach an MCP server
config. To run a packaged agent against the local server, use `omlx launch <agent>`.

For request/response examples, the full endpoint list, the `--mcp-config` format, and
`omlx launch` patterns, read `references/serve-flags.md`.

## oMLX vs Ollama vs LM Studio

All three run local models; pick by context.

- **Prefer oMLX** when you are on Apple Silicon and want maximum performance from the Metal
  GPU and unified memory, need the two-tier SSD-paged KV cache for long contexts that exceed
  RAM, or want a scriptable CLI server with an OpenAI-compatible API and MCP/agent wiring.
- **Prefer Ollama** when you need cross-platform portability (Linux/Windows/Intel Macs as
  well), want the largest turnkey model library with one-command pulls, or value the broad
  ecosystem and simplest possible setup over peak Apple-Silicon throughput.
- **Prefer LM Studio** when you want a GUI for browsing, downloading, and chatting with
  models interactively, or are onboarding a non-CLI user — it trades scriptability for
  discoverability.

The deciding factors are platform (Apple-Silicon-only vs cross-platform), interface (CLI
server vs GUI), and whether you need SSD-paged long-context inference.

## Troubleshooting

On Apple Silicon almost every failure traces back to unified-memory pressure. The common
modes are the Metal OOM crash loop, silent memory pressure (swap thrashing without a hard
crash), mixed-workload instability (other GPU apps competing for memory), and a model not
showing up in the served model list. For symptoms, root causes, and fixes for each, read
`references/troubleshooting.md`.
