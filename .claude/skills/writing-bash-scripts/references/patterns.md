# Bash Patterns Reference

## Subcommand dispatcher

Use a `case` statement in a `main` function to route subcommands. Each subcommand is its own function with a `cmd_` prefix:

```bash
main() {
  if [[ $# -eq 0 ]]; then
    cmd_help
    exit 1
  fi

  local command="$1"
  shift

  case "${command}" in
    deploy)               cmd_deploy "$@" ;;
    status)               cmd_status "$@" ;;
    help | --help | -h)   cmd_help ;;
    *)
      log_error "Unknown command: ${command}"
      cmd_help
      exit 1
      ;;
  esac
}

main "$@"
```

- Always call `main "$@"` at the bottom of the script.
- Always `shift` after consuming the subcommand name.
- Include `help`, `--help`, and `-h` as aliases.
- Use `exit 1` for unknown commands (not `return`).

### Help generation

Put help text in a `cmd_help` function using a heredoc:

```bash
cmd_help() {
  cat <<EOF
Usage: ${SCRIPT_NAME} <command> [options]

Commands:
  deploy <target>   Deploy to the specified target
  status            Show current status
  help              Show this help message
EOF
}
```

## Argument parsing with getopts

For scripts with simple short options:

```bash
parse_args() {
  local OPTIND OPTARG opt
  while getopts ":vhd:" opt; do
    case "${opt}" in
      v) VERBOSE=1 ;;
      h) cmd_help; exit 0 ;;
      d) DEPLOY_TARGET="${OPTARG}" ;;
      :) log_error "Option -${OPTARG} requires an argument"; exit 2 ;;
      ?) log_error "Unknown option: -${OPTARG}"; exit 2 ;;
    esac
  done
  shift $((OPTIND - 1))
  REMAINING_ARGS=("$@")
}
```

- Declare `OPTIND`, `OPTARG`, and `opt` as local.
- Leading `:` in the optstring enables silent error handling.
- Always `shift $((OPTIND - 1))` after parsing.
- `getopts` does not support long options (`--verbose`). Use manual parsing if you need them.

## Manual argument parsing

For long options or mixed positional and flag arguments:

```bash
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -v | --verbose) VERBOSE=1; shift ;;
      -h | --help)    cmd_help; exit 0 ;;
      -o | --output)
        OUTPUT_FILE="${2:?--output requires a value}"
        shift 2
        ;;
      --)             shift; break ;;  # End of flags
      -*)             log_error "Unknown option: $1"; exit 2 ;;
      *)              break ;;  # Start of positional args
    esac
  done
  POSITIONAL_ARGS=("$@")
}
```

- Handle `--` to separate flags from positional arguments.
- Use `${2:?message}` to require a value for options that take one.
- Collect remaining positional args after the loop.

## Logging helpers

Consistent logging functions that write to stderr:

```bash
# Optional: support LOG_LEVEL for filtering
readonly LOG_LEVEL="${LOG_LEVEL:-info}"

_should_log() {
  local level="$1"
  case "${LOG_LEVEL}" in
    debug) return 0 ;;
    info)  [[ "${level}" != "debug" ]] ;;
    warn)  [[ "${level}" == "warn" || "${level}" == "error" ]] ;;
    error) [[ "${level}" == "error" ]] ;;
    *)     return 0 ;;
  esac
}

log_debug() { _should_log debug && printf '[DEBUG] %s\n' "$*" >&2; }
log_info()  { _should_log info  && printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { _should_log warn  && printf '[WARN]  %s\n' "$*" >&2; }
log_error() { _should_log error && printf '[ERROR] %s\n' "$*" >&2; }
```

- Always log to stderr (`>&2`) — stdout is for program output.
- Use `printf` instead of `echo` — it is more portable and predictable.
- Prefix each line with the level for easy grep/filtering.

## Function organization

Organize functions in declaration order matching the execution flow:

```
1. Constants (readonly, at top)
2. Helper functions (logging, utilities, cleanup)
3. Command functions (cmd_deploy, cmd_status, cmd_help)
4. Argument parsing (parse_args, if separate from main)
5. Main function (dispatcher)
6. main "$@" invocation (last line)
```

- **Naming**: `snake_case` for all functions. Prefix subcommand handlers with `cmd_`.
- **Size**: keep functions under 50 lines. Extract helpers if a function grows.
- **Return vs exit**: use `return` in functions (lets callers handle errors), `exit` only in `main` or top-level traps.
- **No global side effects**: functions should take arguments and produce output, not silently modify global state. If globals are necessary, document them.
