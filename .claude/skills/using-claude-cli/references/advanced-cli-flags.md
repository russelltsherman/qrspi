# Advanced CLI flags

> **Provenance.** Everything here is **[CLI-spec]** — synthesized from the Claude Code
> CLI specification and **not** verified against this repository. Treat flag names,
> output shapes, and event types as externally-derived and review before relying on them.

The SKILL.md body covers the common-path flags. This file is the full catalog for the
five run modes, every `--output-format` shape, streaming event structure, and model
selection.

## The five run modes [CLI-spec]

| Mode | Invocation | Behavior |
|------|------------|----------|
| Interactive (REPL) | `claude` | Opens an interactive session in the cwd. Default for hands-on work. |
| Interactive + seed prompt | `claude "explain this repo"` | Opens interactively but seeds the first turn with the prompt. |
| Headless / print | `claude -p "<prompt>"` | Non-interactive; runs to completion, prints the final result to stdout, exits. The scripting/CI mode. |
| Piped (stdin) | `cat x \| claude -p "<prompt>"` | Headless run whose stdin is the piped content; the prompt instructs what to do with it. |
| Background | `claude -p "<prompt>" &` (or a detached job) | A headless run launched detached so the caller continues; capture the session id to rejoin or read results later. |

"Bare" interactive (`claude` with no prompt) and "interactive with a seed prompt" are the
two interactive variants; the remaining three (headless, piped, background) are the
scripted variants.

## Output formats [CLI-spec]

`--output-format <text|json|stream-json>` controls how a headless run emits its result.

### `text` (default)

Plain final answer to stdout, nothing else. Use for humans and for when you only need the
text result piped onward.

```bash
claude -p "one-line summary of README.md" --output-format text
```

### `json`

A single structured result object after the run completes. Use when a script needs the
result **plus** metadata (session id, usage/cost, stop reason). Parse with `jq`.

```bash
claude -p "$PROMPT" --output-format json | jq -r '.result'
claude -p "$PROMPT" --output-format json | jq -r '.session_id'   # to resume later
claude -p "$PROMPT" --output-format json | jq '.usage'           # token/cost accounting
```

Typical top-level fields: `result` (final text), `session_id`, `usage`/cost accounting,
and a stop/`is_error` indicator. Field names are **[CLI-spec]** — inspect the actual JSON
in your installed CLI before depending on a specific key.

### `stream-json`

Newline-delimited JSON events emitted incrementally as the run proceeds — one JSON object
per line (JSONL). Use for live progress, long runs, or feeding another process token by
token.

```bash
claude -p "$PROMPT" --output-format stream-json | while IFS= read -r line; do
  printf '%s\n' "$line" | jq -r 'select(.type=="text") | .text'
done
```

Event objects carry a `type` discriminator (e.g. message/text deltas, tool-use events,
and a final result event). Exact event taxonomy is **[CLI-spec]**; print raw lines first
to learn the shapes your version emits.

## Input format [CLI-spec]

`--input-format <text|stream-json>` mirrors the output side:

- `text` (default) — stdin is treated as plain text appended to the prompt context.
- `stream-json` — stdin is a JSONL stream of input events, for driving a run
  programmatically turn by turn.

```bash
cat error.log | claude -p "Summarize the root cause." --input-format text
```

## Model selection [CLI-spec]

`--model <name>` chooses the model for the run. Use a smaller/cheaper model for routine
transforms (commit messages, summaries, lint-style passes) and reserve the largest model
for hard reasoning or large refactors.

```bash
git diff --cached | claude -p "Conventional-commit message, message only." --model <small-model>
claude -p "Design a migration plan for X." --model <large-model>
```

Model identifiers are environment-specific (and this repo runs on both the Anthropic API
and local Ollama); confirm the available model names in your environment rather than
hard-coding one.

## Directory scope [CLI-spec]

- `--add-dir <path>` — grant the run access to directories beyond the cwd. Repeatable.
  Keep the set minimal: a narrower scope means fewer input tokens and a smaller blast
  radius.

```bash
claude -p "Cross-reference lib and tests." --add-dir ../shared-lib --add-dir ./tests
```

## Putting it together [CLI-spec]

A deterministic, resumable, machine-readable headless invocation:

```bash
SID="$(uuidgen)"
git diff --cached | claude -p "Review staged changes; JSON array of {file,line,issue}." \
  --session-id "$SID" \
  --output-format json \
  --model <small-model> | jq -r '.result'
# ...later, continue the same conversation:
claude -p "Now fix the highest-severity issue." --resume "$SID" --output-format json
```

See also: [permission-rule-patterns.md](permission-rule-patterns.md) for locking down
what a scripted run may do, and [hook-examples.md](hook-examples.md) for enforcing checks
around tool calls.
