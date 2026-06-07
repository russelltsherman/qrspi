# Gemini CLI — Subagents, MCP & Extensions (deep dive)

Verified against `geminicli.com/docs/core/subagents/`,
`geminicli.com/docs/tools/mcp-server/`, `geminicli.com/docs/extensions/`, and the
`google-gemini/gemini-cli` repo in **June 2026** (subagents landed in v0.38.x).
Re-confirm with `gemini --help`. `⚠ UNVERIFIED` marks anything not confirmed against
official docs.

## Table of contents

- [Subagents](#subagents)
- [MCP servers](#mcp-servers)
- [Extensions](#extensions)

## Subagents

Subagents are specialized agents, each with its **own context window**, custom system
prompt, and a curated set of tools — useful for delegating repetitive or high-volume
work and for keeping the main context clean.

### Definition

Markdown files with YAML frontmatter:

- **Global:** `~/.gemini/agents/*.md` (personal, all projects).
- **Project:** `.gemini/agents/*.md` (commit to share with the team).
- The file **must** start with `---` YAML frontmatter (metadata, including a
  description used for routing). The **markdown body becomes the agent's system
  prompt**.

### Routing

- **Automatic:** Gemini delegates a task to a subagent when its description makes it
  the most efficient path.
- **Explicit:** target one with `@agent-name` in the prompt, e.g.
  - `@frontend-specialist Review the app and flag improvements`
  - `@codebase_investigator Map out the authentication flow`

### Tool grants

Declare which tools a subagent may use; wildcards expand groups:

| Pattern          | Grants                                            |
|------------------|---------------------------------------------------|
| `*`              | All available built-in and discovered tools.      |
| `mcp_*`          | All tools from all connected MCP servers.         |
| `mcp_my-server_*`| All tools from the MCP server aliased `my-server`.|

Grant the **minimum** set a subagent needs — narrow tool access is a primary safety
lever.

### Parallelism

Gemini can dispatch multiple subagents (or many instances of one) **in parallel** —
e.g. research several topics or refactor several components at once — cutting total
wall-clock time. `⚠ UNVERIFIED`: exact concurrency limits; check your version.

## MCP servers

Model Context Protocol (MCP) servers expose custom tools to Gemini. Configure them
under the **`mcpServers`** key in `settings.json`:

- Each server entry must provide **at least one** of:
  - `command` — Stdio transport (launch a local process),
  - `url` — SSE transport,
  - `httpUrl` — Streamable HTTP transport.
- If more than one is given, precedence is **`httpUrl` > `url` > `command`**.
- On startup Gemini connects to each server and fetches its tool definitions.
- Every discovered tool is namespaced to a fully qualified name
  `mcp_<serverAlias>_<toolName>` to avoid collisions (this is the same prefix the
  subagent `mcp_*` wildcards match).

## Extensions

Extensions package prompts, MCP servers, custom commands, themes, hooks, subagents,
and agent skills into one installable unit.

### Install (run from the shell, not inside the REPL)

```bash
gemini extensions install https://github.com/<owner>/<repo>   # from a GitHub URL
gemini extensions install --path ./my-extension               # from a local dir
```

- GitHub installs clone into `~/.gemini/extensions/<name>`; local installs copy the
  directory there.
- These subcommands are **not** available from within an active CLI session; changes
  take effect on the **next** CLI start.
- List installed extensions with the `/extensions list` slash command inside the REPL.
- Browse the official extension gallery to discover available ones.
