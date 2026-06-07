---
name: using-gemini-cli
description: "Use for ANY task that involves Google's Gemini CLI (the `gemini` command) — installing or authenticating it, invoking it interactively, non-interactively with `-p`, or by piping stdin; choosing a permission/approval mode (default, auto_edit, yolo) and sandbox; managing GEMINI.md context files, settings.json, MCP servers, extensions, or subagents; or orchestrating Gemini as a sub-process from another agent or script. Trigger whenever the user wants to call `gemini`, delegate work to Gemini, review code or generate tests with Gemini, set up Gemini CLI config, or run Gemini autonomously. Even a single `gemini -p` invocation should go through this skill so it is run safely and with the right flags."
allowed-tools: Bash, Read, Write
---

# Using the Gemini CLI

Google's **Gemini CLI** (`gemini`, npm package `@google/gemini-cli`, Apache-2.0,
repo `google-gemini/gemini-cli`) is an open-source terminal AI agent. This skill
teaches you to install it, authenticate, invoke it three ways, control how much it
is allowed to do, and drive it as a sub-process from another agent.

Every `gemini …` command in this skill is meant to be run through the **`Bash`
tool** — that is the only mechanism for invoking an external CLI here. A tool not
listed in `allowed-tools` cannot be used, and tool names are case-sensitive.

## Fact-pinning and verification

All Gemini-specific facts below (flags, env vars, config keys, sandbox profile
names, the deprecation date) were verified against the official docs
(`geminicli.com`, `github.com/google-gemini/gemini-cli`) in **June 2026**, on the
**v0.38.x** line (the release where subagents landed). Gemini ships fast; treat
exact flag spellings as version-pinned to that line and re-confirm with
`gemini --version` and `gemini --help` before relying on anything load-bearing.
Anything that could not be confirmed is marked `⚠ UNVERIFIED` inline.

## CRITICAL: deprecation — read before investing

On **June 18, 2026**, Google deprecates the standalone Gemini CLI for Google AI
Pro/Ultra and free-tier users (and the Gemini Code Assist IDE extensions), steering
users to the new **Antigravity CLI** (Go-based, not open source as of this writing).
Access via paid Gemini API keys and Gemini Code Assist Standard/Enterprise/Google
Cloud licenses is documented as unchanged. Antigravity is stated to support agent
skills, hooks, subagents, and extensions at launch, but **not** 1:1 feature parity.
See `references/orchestration.md` for what this means for automation. Confirm the
current status before building anything long-lived on the free-tier CLI.

## Install & Authenticate

Install (Node.js ≥ 20 required):

```bash
npm install -g @google/gemini-cli   # global install, provides `gemini`
gemini --version                    # confirm it is on PATH
npx @google/gemini-cli              # or run without installing
```

Authenticate — pick one path:

- **Google account (OAuth, free tier):** run `gemini` once interactively and
  complete the browser login. Credentials are cached under `~/.gemini/`.
- **Gemini API key:** `export GEMINI_API_KEY="…"` (key from Google AI Studio).
  Best for non-interactive/CI use — no browser round-trip.
- **Vertex AI:** `export GOOGLE_API_KEY="…"` and
  `export GOOGLE_GENAI_USE_VERTEXAI=true`.

For unattended/agent use prefer an API key in the environment, since OAuth needs a
one-time interactive browser step.

## Invocation

Three modes, all via the `Bash` tool:

```bash
# 1. Interactive REPL — opens a session; for humans, not for agents.
gemini

# 2. Non-interactive (single shot) — pass the prompt with -p, capture stdout.
gemini -p "Explain what src/auth.ts does in two sentences"

# 3. stdin pipe — feed file/command context on stdin; -p is the instruction.
cat src/auth.ts | gemini -p "Review this file for security bugs"
git diff | gemini -p "Summarize this diff as a changelog entry"
```

Piped stdin is appended to the prompt, so `cmd | gemini -p "…"` is the canonical
way to hand Gemini a chunk of context without an interactive session. Add
`--output-format json` when a script needs to parse the result structurally.

For agents, **always** use mode 2 or 3 — the interactive REPL (mode 1) blocks
waiting for human input and will hang an automated run.

## Permission & Approval Model

Gemini gates tool calls (file writes, shell commands) behind an approval mode set
with `--approval-mode`:

| Mode        | Behavior                                                        |
|-------------|-----------------------------------------------------------------|
| `default`   | Prompt for approval on every tool call.                          |
| `auto_edit` | Auto-approve edit tools (`replace`, `write_file`); prompt others.|
| `yolo`      | Auto-approve **all** tool calls (equivalent to `--yolo`).        |

`yolo` cannot be made the default in `settings.json` — it must be passed on the
command line each time, which is a deliberate guardrail against accidental
full-permission sessions.

```bash
gemini --approval-mode auto_edit -p "Fix the failing test in test_user.py"
gemini --yolo --sandbox -p "Refactor module X"   # full auto, but sandboxed
```

**HARD STOP on error:** if a `gemini` invocation exits non-zero or reports an auth,
permission, quota, or sandbox error, stop immediately, surface the exact error text
verbatim, and do not retry or escalate permissions to "get past" it. Choosing a
broader approval mode is a deliberate decision, never an error workaround.

Deep dive: `references/permissions-and-sandbox.md`.

## Sandbox

Sandboxing isolates tool execution (file and network access) from the host. Enable
with `--sandbox`/`-s` or `GEMINI_SANDBOX`:

```bash
gemini -s -p "…"                 # enable sandbox for this run
export GEMINI_SANDBOX=docker     # true | docker | podman | sandbox-exec
```

- **macOS Seatbelt** (`sandbox-exec`): six profiles via `SEATBELT_PROFILE` —
  `permissive-open` (default), `permissive-proxied`, `restrictive-open`,
  `restrictive-proxied`, `strict-open`, `strict-proxied`.
- **Container** (Docker/Podman): full process isolation; your CWD is mounted at the
  same absolute path inside the container.
- Grant access to paths outside the project with `SANDBOX_MOUNTS`; inject extra
  container flags with `SANDBOX_FLAGS`.

`--yolo`/`--approval-mode=yolo` enables the sandbox by default. **Recommend the
sandbox for any autonomous or subagent-driven run** — it is what makes broad
approval modes safe. Deep dive: `references/permissions-and-sandbox.md`.

## GEMINI.md Context Hierarchy

`GEMINI.md` files supply standing instructions that are concatenated and prepended
to every prompt (the CLI footer shows how many were loaded). Resolution is
hierarchical:

- **Global:** `~/.gemini/GEMINI.md` — defaults for all projects.
- **Project/ancestors:** `GEMINI.md` found in the workspace dirs and their parents.

Split a large file with the `@path/to/file.md` import syntax (relative or absolute).
Rename the context file via `context.fileName` in `settings.json`. Use `GEMINI.md`
for durable, project-wide conventions; pass one-off context on the prompt/stdin
instead.

## MCP & Extensions

- **MCP servers** are configured under the `mcpServers` key in `settings.json`. Each
  entry supplies at least one of `command` (Stdio), `url` (SSE), or `httpUrl`
  (Streamable HTTP); precedence is `httpUrl` > `url` > `command`. Discovered tools
  are namespaced `mcp_<serverAlias>_<toolName>`.
- **Extensions** bundle prompts, MCP servers, commands, subagents, and more.
  Install from a GitHub URL or local path (run from the shell, not inside the REPL):

```bash
gemini extensions install https://github.com/<owner>/<repo>
gemini extensions install --path ./my-extension
```

Extensions install under `~/.gemini/extensions/` and are picked up on next CLI
start. Deep dive: `references/subagents-mcp-extensions.md`.

## Subagents

Subagents are specialized agents with their own context window, system prompt, and
tool grants. Define them as Markdown files with YAML frontmatter:

- **Global:** `~/.gemini/agents/*.md`  •  **Project:** `.gemini/agents/*.md`
- The frontmatter declares metadata; the markdown body is the agent's system prompt.
- **Routing:** Gemini auto-delegates by the subagent's description, or you target one
  explicitly with `@agent-name` in your prompt (e.g. `@codebase_investigator Map the
  auth flow`).
- **Tool grants:** wildcards — `*` (all tools), `mcp_*` (all MCP tools),
  `mcp_<server>_*` (one server's tools).

Subagents can run in parallel for fan-out work. Deep dive:
`references/subagents-mcp-extensions.md`.

## Multi-Agent Orchestration

To drive Gemini as a sub-process from another agent (including this one), use the
non-interactive modes and treat each call as **stateless**:

- Invoke with `-p` (and stdin for context) so the call never blocks on input.
- **No session persistence:** non-interactive calls do not remember prior calls.
  Carry all needed state forward explicitly — in the prompt, on stdin, or via files
  on disk that both sides read/write (the durable handoff channel).
- **Capture stdout** as the result; use `--output-format json` when parsing.
- **Sandbox** autonomous runs (`-s`) and choose the approval mode deliberately.
- **HARD STOP on error:** surface the exact failing command and error verbatim; do
  not retry blindly or broaden permissions to push through.

Deep dive: `references/orchestration.md`.

## Worked Examples

```bash
# Code review of a diff
git diff main...HEAD | gemini -p "Review this diff for correctness and security \
  issues. List concrete problems with file:line references; say 'no issues' if none."

# Test generation for a module
cat src/user.py | gemini --approval-mode auto_edit -s \
  -p "Write pytest unit tests for this module into tests/test_user.py covering \
  edge cases and error paths."

# Codebase exploration (read-only)
gemini -p "Trace how an HTTP request flows from the router to the database in this \
  repo. List the key files and functions in call order."
```

## Limitations

- **Deprecation (June 18, 2026):** see the CRITICAL section above. Plan migrations
  to Antigravity CLI accordingly; do not assume long-term free-tier availability.
- Non-interactive mode is **stateless** — no memory across `-p` calls.
- `yolo` cannot be persisted in `settings.json` (CLI-flag only, by design).
- `gemini extensions install` runs from the shell, not inside the REPL, and changes
  apply on restart.
- Exact flags evolve quickly; re-verify with `gemini --help` for your version.
