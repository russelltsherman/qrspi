---
name: writing-bash-scripts
description: Guide for writing robust, ShellCheck-clean bash scripts. Use whenever creating a new bash or shell script (.sh file), modifying an existing bash script, writing shell functions or shell snippets longer than a few lines, scaffolding CLI tools in bash, or when the user asks for help with bash scripting, shell portability, or ShellCheck compliance. Also trigger when reviewing bash scripts for correctness. Even simple scripts benefit from these conventions — always use this skill for any .sh file work.
command: writing-bash-scripts
---

# Writing Bash Scripts

Follow these conventions for every bash script you write or modify. The goal is
ShellCheck-clean, portable, maintainable shell code.

## When this skill activates

- Creating a new `.sh` file or bash script
- Modifying an existing bash script
- Writing shell functions or snippets longer than a few lines
- Scaffolding CLI tools in bash
- Reviewing bash scripts for correctness
- Answering questions about bash portability or ShellCheck compliance

## Script structure

Every bash script follows this skeleton. See `references/template.sh` for a
complete working example.

```
#!/usr/bin/env bash
set -euo pipefail

# 1. Constants (readonly, uppercase)
# 2. Helper functions (logging, cleanup)
# 3. Command functions (cmd_* prefix, one per subcommand)
# 4. Main dispatcher
# 5. main "$@" (last line)
```

### 1. Shebang and strict mode

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- `set -e` — exit on any command failure.
- `set -u` — treat unset variables as errors.
- `set -o pipefail` — propagate failures through pipes.
- Use `#!/usr/bin/env bash`, not `#!/bin/bash` — more portable.

### 2. Constants

```bash
readonly SCRIPT_NAME="${0##*/}"
readonly VERSION="1.0.0"
```

- Uppercase, `readonly`, declared at the top.
- Separate declaration and assignment when using command substitution:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
```

### 3. Helper functions

Logging and cleanup go here. Always log to stderr:

```bash
log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }

cleanup() { rm -rf "${TMPDIR_WORK:-}"; }
trap cleanup EXIT
```

### 4. Command functions

One function per subcommand, prefixed with `cmd_`:

```bash
cmd_deploy() {
  local target="${1:?Usage: ${SCRIPT_NAME} deploy <target>}"
  # ...
}
```

- Use `local` for all variables inside functions.
- Use `"${1:?message}"` for required arguments.

### 5. Main dispatcher

```bash
main() {
  local command="${1:?Usage: ${SCRIPT_NAME} <command>}"
  shift
  case "${command}" in
    deploy)            cmd_deploy "$@" ;;
    help | --help | -h) cmd_help ;;
    *)                 log_error "Unknown: ${command}"; exit 1 ;;
  esac
}
main "$@"
```

## Error handling essentials

- `set -euo pipefail` catches most errors automatically.
- Guard `cd` calls: `cd "${dir}" || exit 1`.
- Register `trap cleanup EXIT` before creating any temporary resources.
- Check external dependencies at startup with `command -v`.
- Use meaningful exit codes (0 = success, 1 = error, 2 = usage error).

## Quoting rules (summary)

- **Double-quote every variable expansion**: `"${var}"`, `"$@"`, `"$(cmd)"`.
- Use single quotes for literals with no interpolation.
- Quote array expansions: `"${array[@]}"`.
- Separate `local` declaration from assignment when using command substitution.

## Argument parsing (summary)

- **Simple short options**: use `getopts`.
- **Long options or mixed args**: use a `while/case/shift` loop.
- Always handle `--help` / `-h`.
- Handle `--` as end-of-flags separator.

## Code organization rules

- Functions in declaration order: helpers, then commands, then main.
- `snake_case` for function names, `cmd_` prefix for subcommand handlers.
- Keep functions under 50 lines — extract helpers when they grow.
- Use `return` in functions, `exit` only in `main` or trap handlers.
- Stdout is for program output. Logging, diagnostics, and prompts go to stderr.

## Testing

- Use [bats-core](https://github.com/bats-core/bats-core) for testing bash scripts.
- Structure command logic as callable functions so tests can source the script
  and call functions directly.
- Run `shellcheck` on every script before committing — zero warnings required.

## Reference files

Load these for detailed guidance when the situation calls for it:

### Template

Read `references/template.sh` when starting a new script from scratch. It
demonstrates the full structural skeleton with all conventions applied.

### Conventions

Read `references/conventions.md` when you need detailed rules for:
- Quoting and variable handling
- Dependency checking with `command -v`
- Temp file management with `mktemp` and traps
- Exit code conventions
- Signal trapping patterns

### Patterns

Read `references/patterns.md` when the script involves:
- Subcommand dispatching (multi-command CLI tools)
- Argument parsing (getopts or manual long-option parsing)
- Logging with level filtering (debug/info/warn/error)
- Function organization in larger scripts

### Gotchas

Read `references/gotchas.md` when dealing with:
- Cross-platform portability (macOS BSD vs Linux GNU coreutils)
- Bash version compatibility (3.2 vs 4+ feature differences)
- ShellCheck warnings you need to understand or suppress
- Word splitting, globbing, or subshell variable scope issues
