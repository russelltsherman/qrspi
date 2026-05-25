# Bash Conventions Reference

## Quoting

- **Double-quote all variable expansions**: `"${var}"`, never `$var` bare.
- Use single quotes for literal strings that contain no variables: `'literal'`.
- Use `$'...'` for strings with escape sequences: `$'\n'`, `$'\t'`.
- Quote command substitutions: `"$(command)"`.
- Quote glob patterns when you want literal text: `"*.txt"` vs `*.txt`.
- Array expansion: `"${array[@]}"` (quoted, `@`) to preserve elements.

```bash
# Good
local msg="Hello ${name}"
local files=("${dir}"/*.txt)
local output
output="$(some_command)"

# Bad — word splitting, globbing risks
local msg=Hello $name
local output=$(some_command)
```

## Variable handling

- **Local variables in functions**: always declare with `local`.
- **Constants**: uppercase, declared with `readonly` at script top.
- **Naming**: lowercase with underscores for locals (`file_path`), uppercase for constants and exports (`LOG_LEVEL`).
- **Declare and assign separately** when using command substitution (avoids masking return values — SC2155):

```bash
# Good
local result
result="$(some_command)"

# Bad — masks the exit code of some_command
local result="$(some_command)"
```

- **Default values**: `"${var:-default}"` (use default), `"${var:=default}"` (assign default).
- **Required variables**: `"${var:?error message}"` — exits if unset or empty.
- **Arrays**: prefer arrays over space-separated strings for lists of items.

## Dependency checking

Check required commands at the start of the script, before doing any work:

```bash
check_dependencies() {
  local missing=()
  local cmd
  for cmd in jq curl git; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      missing+=("${cmd}")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "Missing required commands: ${missing[*]}"
    exit 1
  fi
}
```

- Use `command -v` (POSIX) instead of `which` (non-standard, unreliable).
- For version checks: parse `--version` output carefully; do not assume format.

## Temp file management

- **Always use `mktemp`** for temporary files and directories:

```bash
readonly TMPDIR_WORK="$(mktemp -d)"
readonly TMPFILE="$(mktemp)"
```

- **Always clean up with a trap** — register cleanup before creating temps:

```bash
cleanup() {
  rm -rf "${TMPDIR_WORK:-}" "${TMPFILE:-}"
}
trap cleanup EXIT
```

- Use `:-` in cleanup to avoid `set -u` errors if the variable was never set.
- Never hardcode temp paths (`/tmp/myscript.tmp`) — causes collisions.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Usage / argument error |
| 3-125 | Available for application-specific errors |
| 126 | Command found but not executable |
| 127 | Command not found |
| 128+N | Killed by signal N (e.g., 130 = SIGINT) |

- Define application exit codes as constants:

```bash
readonly EXIT_SUCCESS=0
readonly EXIT_GENERAL_ERROR=1
readonly EXIT_USAGE_ERROR=2
readonly EXIT_CONFIG_ERROR=3
```

## Signal trapping

- **Trap EXIT for cleanup** — fires on normal exit, errors, and most signals:

```bash
trap cleanup EXIT
```

- **Trap specific signals** when you need custom behavior:

```bash
trap 'log_warn "Interrupted"; exit 130' INT
trap 'log_warn "Terminated"; exit 143' TERM
```

- Do not trap `KILL` (signal 9) — it cannot be caught.
- Order matters: register traps before the code that needs protection.
- In the signal handler, call `exit` explicitly to trigger the EXIT trap.
- Keep trap handlers short — set a flag and let the main loop handle graceful shutdown for complex cases:

```bash
SHUTDOWN_REQUESTED=0
trap 'SHUTDOWN_REQUESTED=1' TERM
```
