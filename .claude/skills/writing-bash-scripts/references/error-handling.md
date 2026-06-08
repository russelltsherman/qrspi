# Error handling, traps, and exit codes

`set -euo pipefail` aborts on failure; traps decide what happens *when* it aborts —
cleanup, diagnostics, and a meaningful exit status.

## Exit codes

- `0` means success; any non-zero means failure. Reserve specific codes for
  specific conditions if callers branch on them, and document them in usage.
- Stay under 125. The shell reserves `126` (found but not executable), `127`
  (command not found), and `128+N` (killed by signal N — `130` is Ctrl-C / SIGINT).
- Return, do not `exit`, from functions you may want to call in a condition:

```bash
need_file() {
  [[ -f "$1" ]] && return 0
  printf 'missing: %s\n' "$1" >&2
  return 1
}
```

## Fail with a message, not a bare exit

Centralize failure so every abort prints to stderr and uses a consistent code:

```bash
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

[[ -n "${API_TOKEN:-}" ]] || die "API_TOKEN is not set"
```

## Traps — cleanup that always runs

A trap on `EXIT` runs whether the script ends normally, via `die`, or via an
`errexit` abort. Use it to remove temp files, kill background jobs, or restore
state. Set it *after* you create the thing it cleans up.

```bash
cleanup() {
  local status=$?
  [[ -n "${workdir:-}" && -d "$workdir" ]] && rm -rf "$workdir"
  return "$status"
}
trap cleanup EXIT

workdir=$(mktemp -d)
```

- One `EXIT` trap fires once on the way out — put all cleanup there; do not
  scatter `rm` calls along every error path.
- Capture `$?` as the first line of the handler if you want the original exit
  status; the handler's own commands overwrite `$?`.

## ERR trap for diagnostics

`trap ... ERR` fires on the command that trips `errexit`, ideal for a stack-style
trace. Requires `set -E` (`errtrace`) to also fire inside functions.

```bash
set -Eeuo pipefail
trap 'printf "failed at line %d: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR
```

## Signals

Trap `INT`/`TERM` to clean up on Ctrl-C or `kill`. Listing them alongside `EXIT`
is usually enough since `EXIT` fires after the signal handler:

```bash
trap cleanup EXIT INT TERM
```

For long-running scripts that spawn children, kill the process group or named PIDs
in cleanup so a Ctrl-C does not orphan background work.

## Retries

Wrap a flaky command in a bounded loop rather than disabling `errexit`:

```bash
retry() {
  local -i tries=$1 n=0; shift
  until "$@"; do
    n=$((n + 1))
    (( n >= tries )) && return 1
    sleep $(( n * 2 ))
  done
}
retry 3 curl -fsS "$url"
```
