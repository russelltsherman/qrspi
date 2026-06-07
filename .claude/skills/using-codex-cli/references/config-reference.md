# config.toml reference

Codex reads TOML configuration from two locations, merged with project overriding user:

- **User-level:** `~/.codex/config.toml` — your personal defaults across all repos.
- **Project-level:** `.codex/config.toml` at a repo root — shared, committable
  per-project settings. Project values override the matching user-level keys; keys not
  set at the project level fall back to the user file.

Most keys also have a per-run flag equivalent (e.g. `--model`, `--ask-for-approval`,
`--sandbox`, `--profile`). Flags beat config; config beats built-in defaults.

## Table of contents

- [Top-level keys](#top-level-keys)
- [Model settings](#model-settings)
- [Sandbox and approval](#sandbox-and-approval)
- [AGENTS.md / project-doc keys](#agentsmd--project-doc-keys)
- [Profiles](#profiles)
- [Feature flags](#feature-flags)
- [MCP servers](#mcp-servers)

## Top-level keys

```toml
model = "o4-mini"                  # default model slug
model_provider = "openai"          # provider id (see [model_providers])
approval_policy = "suggest"        # suggest | auto-edit | full-auto
sandbox_mode = "workspace-write"   # read-only | workspace-write | danger-full-access
model_instructions_file = "~/.codex/instructions.md"  # extra system instructions
```

- `model` — default model for new sessions; override per run with `--model`.
- `model_instructions_file` — path to a markdown file appended as standing
  instructions to every session (separate from per-project `AGENTS.md`).

## Model settings

```toml
model = "o4-mini"

[model_providers.openai]
name = "openai"
# base_url / env_key style fields define how Codex reaches the model API
```

Custom or self-hosted providers are configured under `[model_providers.<id>]` and
selected with the top-level `model_provider`. Consult `codex --help` and the live
docs for the exact provider sub-keys, which evolve.

## Sandbox and approval

```toml
approval_policy = "suggest"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false   # network is OFF by default even in workspace-write
```

To let `workspace-write` runs reach the network (package installs, fetches), enable
the workspace-write network toggle rather than dropping to `danger-full-access`.
On macOS, prefer the `--sandbox` flag over relying solely on these keys — see
`limitations-and-workarounds.md`.

## AGENTS.md / project-doc keys

These govern how `AGENTS.md` project instructions are discovered and merged:

```toml
project_doc_max_bytes = 32768                 # per-file cap; content beyond is truncated
project_doc_fallback_filenames = ["AGENTS.md"] # filenames tried in order
```

- `project_doc_max_bytes` — byte cap applied to each project-doc file (commonly
  32 KiB). Keep `AGENTS.md` tight; push detail into linked docs to avoid truncation.
- `project_doc_fallback_filenames` — ordered list of filenames Codex looks for as
  project docs, allowing alternates beyond the default `AGENTS.md`.
- Discovery walks from the repo root down to the working directory; an
  `AGENTS.override.md`, when present, takes precedence over the regular cascade, and
  deeper files override shallower ones.

## Profiles

Named bundles of settings, selected with `codex --profile <name>`:

```toml
[profiles.ci]
approval_policy = "full-auto"
sandbox_mode = "workspace-write"
model = "o4-mini"

[profiles.review]
approval_policy = "full-auto"
sandbox_mode = "read-only"
```

A profile overrides the top-level keys it sets; unset keys inherit the top-level /
user values. Profiles keep distinct workflows (CI, read-only review, local dev) one
flag apart.

## Feature flags

Optional capabilities are toggled via the `codex features` surface (e.g.
`codex features enable <name>` / `codex features disable <name>`) and/or
corresponding config keys. Because the available flags change between releases, run
`codex features --help` to see the current set rather than hard-coding names.

## MCP servers

Codex can act as an MCP client, launching external MCP servers Codex itself can call
as tools:

```toml
[mcp_servers.example]
command = "npx"
args = ["-y", "@some/mcp-server"]
```

This is distinct from running **Codex as an MCP server** (see `mcp-server-mode.md`),
where an outer orchestrator calls Codex.
