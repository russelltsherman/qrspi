# Questions — Create a new agent skill called using codex cli

**Ticket:** RUS-21
**Generated:** 2026-06-02T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where does the skill-builder skill store its generated output — specifically, where does it place the `SKILL.md` file and the optional `references/`, `scripts/`, `assets/` subdirectories relative to the parent agent skills directory?
   **Target:** `skill-creator` skill implementation in `.claude/skills/mcp-builder/` or `.claude/agents/`

- Q2: How does the existing slash-command wrapper pattern (in `.claude/skills/`) invoke a skill's `SKILL.md` content, and how can I model my new skill's directory structure to integrate with this mechanism?
   **Target:** `.claude/skills/` wrapper scripts for all registered skills

- Q3: When the skill-creator generates a `SKILL.md`, what frontmatter fields are mandatory vs. optional per the agentskills.io specification, and how is that schema validated during registration?
   **Target:** `skill-creator` skill definition and any validation logic in `.claude/`

## API Surface

- Q4: The `codex exec` command supports three input patterns (positional argument, stdin via `-`, and prompt-plus-stdin with a pipe). How does the CLI parse and disambiguate these at the shell interface level?
   **Target:** Codex CLI source code — specifically the argument parser module handling positional args and stdin detection

- Q5: For the MCP server mode (`codex` as an MCP provider exposing `codex()` and `codex-reply()` tools), what is the wire protocol schema for these tool calls — parameter names, types, and return value structure?
   **Target:** Codex CLI MCP server extension or documentation of the MCP protocol integration

## State Management

- Q6: Session transcripts are persisted locally. Where on disk are they stored, what is the file format (JSON, plain text, etc.), and how does `codex resume --last` locate the most recent session for a given working directory?
   **Target:** Codex CLI session persistence module — local storage of transcript files

- Q7: The AGENTS.md hierarchy uses concatenation with precedence from deeper directories. How does the CLI resolve which `.md` files to load when traversing from project root down to the current working directory, and how is the 32 KiB combined size limit enforced?
   **Target:** Codex CLI agent instruction resolution logic — the file discovery and concatenation module

- Q8: In config.toml, profiles (`[profiles.<name>]`) allow named configuration sets. How does `codex --profile <name>` swap the active configuration in memory, and what happens to existing session state when a profile switch occurs mid-session?
   **Target:** Codex CLI config module handling `[profiles.*]` sections and the profile switching logic

## Edge Cases

- Q9: On macOS, `network_access = true` in config.toml may be silently ignored by the Seatbelt sandbox. What fallback mechanism (`--sandbox` CLI flag override) exists, and how does the skill guide agents to detect when this override has already been applied?
   **Target:** Codex CLI sandbox enforcement layer on macOS — Seatbelt `sandbox-exec` profile handling

- Q10: Re-running the same prompt in Codex may produce alternative implementations or reintroduce bugs. What deterministic guardrails (e.g., unit test integration, diff comparison) does the skill recommend encoding to prevent regression across repeated invocations?
   **Target:** Codex CLI prompt execution module — particularly how results are compared across runs and whether cached diffs exist

- Q11: When using `codex exec --json` for programmatic consumption, the output is newline-delimited JSON events. How does the skill determine the boundary between individual event lines in a piped consumer, and what happens if an agent's internal JSON output contains embedded newlines?
   **Target:** Codex CLI JSON output formatter in `codex exec` — specifically the event serialization logic

## Testing

- Q12: For `codex exec` automation in CI/CD pipelines, how does the skill verify that a given pipeline invocation actually executed as intended when using `--json` output versus stderr progress streams? What test patterns are recommended for asserting on the JSON event stream?
   **Target:** Codex CLI test harness or documented CI integration examples — assertion strategies for `--json` events

- Q13: When designing tests for the skill itself, how should the agent validate that the generated `SKILL.md` adheres to the agentskills.io spec (frontmatter validity, line count under 500 lines, token count under 5000)?
   **Target:** `skill-creator` validation logic or any linting/verification scripts in `.claude/`

## Observability

- Q14: For MCP server-mode Codex sessions, what observability signals (logs, metrics, tracing) are emitted by the MCP protocol layer that an orchestrating agent can consume? How are these surfaced when running `codex()` tool calls from an external orchestrator?
   **Target:** Codex CLI MCP server log output — specifically stdout/stderr streams and any structured logging formats

- Q15: The `--ephemeral` flag skips persisting session files. What diagnostic artifacts remain after an ephemeral session completes, if any, and how does this affect post-mortem debugging of failed automation runs?
   **Target:** Codex CLI session lifecycle — what is cleared vs. retained when `--ephemeral` is passed
