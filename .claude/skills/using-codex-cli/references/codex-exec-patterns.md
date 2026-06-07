# codex exec patterns

`codex exec` is the non-interactive entry point: it takes a prompt, runs the agent to
completion without the TUI, prints the result, and exits with a status code. This makes
Codex a normal Unix citizen you can pipe into and out of, schedule, and run in CI.

## Table of contents

- [Prompt input: positional vs stdin](#prompt-input-positional-vs-stdin)
- [Output flags](#output-flags)
- [Config-bypass flags](#config-bypass-flags)
- [Unix pipe composition](#unix-pipe-composition)
- [CI pipeline patterns](#ci-pipeline-patterns)

## Prompt input: positional vs stdin

```bash
codex exec "explain what main.py does"        # prompt as positional argument
echo "explain what main.py does" | codex exec # prompt via stdin
codex exec - < prompt.txt                      # explicit stdin marker `-`
```

You can also **combine** a positional instruction with piped data — the pipe supplies
context, the argument supplies the instruction:

```bash
git diff | codex exec "review this diff for bugs and security issues"
cat error.log | codex exec "what is the root cause of these errors?"
```

The piped stdin becomes input the agent reasons over; the quoted string is the task.

## Output flags

| Flag | Effect |
| --- | --- |
| `--json` | Emit structured JSON (events/result) for machine parsing — pipe to `jq` |
| `--quiet` | Suppress progress/log chatter; print only the final result |

```bash
codex exec --json "list every TODO with file and line" | jq -r '.todos[]'
codex exec --quiet "bump the version in pyproject.toml"
```

Use `--json` when a downstream tool consumes the output; `--quiet` when a human or log
just needs the answer without the noise.

## Config-bypass flags

For reproducible, environment-independent runs (CI especially), bypass machine- and
repo-specific config so the run depends only on the prompt and flags:

| Flag | Effect |
| --- | --- |
| `--ignore-user-config` | Ignore `~/.codex/config.toml` (user-level settings) |
| `--ignore-rules` | Ignore project rule/instruction files for this run |

```bash
codex exec --ignore-user-config --ignore-rules \
  --sandbox read-only "audit dependencies for known CVEs"
```

This guarantees a developer's personal `config.toml` or local overrides don't change CI
behavior. Always pin `--sandbox` and `--ask-for-approval` explicitly in CI rather than
inheriting them.

## Unix pipe composition

`codex exec` reads stdin and writes stdout, so it chains with any tool:

```bash
# Generate, then act on, in one pipeline
rg -l "deprecated_api" | codex exec "list these files and suggest replacements"

# Feed Codex output into another command
codex exec --json "produce a conventional-commit message for the staged diff" \
  | jq -r '.message' \
  | git commit -F -

# Fan a prompt over many inputs
for f in src/*.py; do
  codex exec --quiet "add a module docstring to $f"
done
```

## CI pipeline patterns

A typical CI job runs Codex headless, full-auto, sandboxed, config-pinned:

```bash
codex exec \
  --full-auto \
  --sandbox workspace-write \
  --ignore-user-config \
  --quiet \
  "apply the lint autofixes and update the changelog"
```

Guidelines for CI:

- **Pin everything** — `--sandbox`, approval policy (`--full-auto`), and
  `--ignore-user-config` so the run is reproducible across machines.
- **Keep network off** unless a step truly needs it; prefer pre-installing deps before
  the Codex step so `workspace-write` (network-off) suffices.
- **Check the exit code** and capture `--json` output as a build artifact for debugging.
- Run inside the CI container's isolation; only there is `danger-full-access` (if ever)
  acceptable.
