# omlx serve — flags, lifecycle, API, MCP, and agent launch

Detailed companion to SKILL.md. Read this when you need exact flags, endpoint shapes, or the
install/start/stop mechanics. Values here describe the omlx CLI's documented behavior; when a
user needs a precise value confirm against their installed `omlx --help`, since flags evolve.

## Contents

- [Install](#install)
- [Serve lifecycle](#serve-lifecycle)
- [omlx serve flags](#omlx-serve-flags)
- [KV-cache flags](#kv-cache-flags)
- [Monitoring](#monitoring)
- [Stopping](#stopping)
- [OpenAI-compatible API](#openai-compatible-api)
- [MCP integration](#mcp-integration)
- [Agent launch](#agent-launch)

## Install

omlx targets Apple Silicon (M-series) Macs running macOS with Metal.

```bash
# Homebrew (typical)
brew install omlx

# Verify
omlx --version

# Pull / register an MLX-format model (model identifiers are repo/name style)
omlx pull <model>

# List locally available models
omlx list
```

A model must be present locally (pulled or on disk in MLX format) before `omlx serve` can
load it. If a model name is not in `omlx list`, serving it will fail — see
`troubleshooting.md` (model-not-showing).

## Serve lifecycle

```bash
omlx serve --model <model> [flags]
```

Serving loads the full model weights into **unified memory** and holds them resident for the
life of the process. The server is foreground by default; background it with your shell job
control or a process manager. Default bind address is `http://localhost:8000`.

The cardinal rule on Apple Silicon: weights + KV hot cache + OS/app headroom must all fit in
unified memory. See `memory-tiers.md` for sizing.

## omlx serve flags

| Flag | Purpose |
|------|---------|
| `--model <model>` | Model to load and serve (required). |
| `--host <addr>` | Bind address (default `localhost`). |
| `--port <n>` | Bind port (default `8000`). |
| `--hot-cache-max-size <size>` | Cap on the in-memory hot KV-cache tier (see below). |
| `--paged-ssd-cache-dir <dir>` | Directory for the SSD-paged cold KV-cache tier (see below). |
| `--mcp-config <path>` | Attach an MCP server config to expose tools to the model. |

Confirm the exact flag set and defaults with `omlx serve --help` on the target machine.

## KV-cache flags

omlx uses a two-tier KV cache so long-context workloads can exceed physical RAM:

- **Hot tier** — lives in unified memory, fast. Bounded by `--hot-cache-max-size`.
- **Cold tier** — paged to SSD under `--paged-ssd-cache-dir`, slower on access but lets total
  context exceed what fits in RAM.

```bash
omlx serve --model <model> \
  --hot-cache-max-size 8GB \
  --paged-ssd-cache-dir /var/tmp/omlx-kv
```

Tuning logic: size `--hot-cache-max-size` so that `weights + hot cache + OS headroom <=
unified memory`. Anything beyond that spills to the cold tier instead of triggering an OOM
crash. Tuning tables per memory tier are in `memory-tiers.md`.

## Monitoring

While serving, watch unified-memory pressure (e.g., Activity Monitor's Memory Pressure graph
or `memory_pressure` / `vm_stat` from the terminal) and the server's own throughput logs.
Rising swap usage or yellow/red memory pressure is the early warning for the failure modes in
`troubleshooting.md`. Catch it here before the OOM crash loop starts.

## Stopping

Stop the server process (Ctrl-C in the foreground, or kill the PID / stop the process
manager) to release the weights and hot cache from unified memory. The cold-tier directory
under `--paged-ssd-cache-dir` can be cleared between runs to reclaim SSD space.

## OpenAI-compatible API

Base URL: `http://localhost:8000/v1`. Endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Chat-style completions (OpenAI shape). |
| `/v1/embeddings` | POST | Embedding vectors. |
| `/v1/messages` | POST | Anthropic-style messages endpoint. |

Example chat call:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<model>",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Any OpenAI-compatible SDK works by setting the base URL to `http://localhost:8000/v1` (an API
key is typically not required for the local server, but pass a dummy key if your client
demands one).

## MCP integration

Attach an MCP server config so the served model can call tools:

```bash
omlx serve --model <model> --mcp-config ./mcp.json
```

`--mcp-config` points at a standard MCP server configuration. This lets a local model use the
same MCP tool ecosystem a hosted model would.

## Agent launch

Run a packaged agent against the local server:

```bash
omlx launch <agent>
```

`omlx launch` wires a named agent to the running (or to-be-started) local server so the
agent's inference goes through omlx rather than a remote provider.
