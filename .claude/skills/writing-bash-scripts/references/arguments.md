# Argument parsing and subcommand dispatch

Parse arguments explicitly. Reaching into `$1`/`$2` by position past two or three
arguments is how scripts grow undocumented, order-sensitive interfaces.

## `getopts` for short flags

`getopts` is a bash builtin — no external `getopt`, portable, handles bundling
(`-ab`) and option arguments (`-o value`). It only does single-letter options.

```bash
usage() { printf 'usage: %s [-v] [-o FILE] FILE...\n' "${0##*/}" >&2; }

verbose=0
outfile=""
while getopts ":vo:h" opt; do
  case "$opt" in
    v) verbose=1 ;;
    o) outfile="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) printf 'option -%s requires an argument\n' "$OPTARG" >&2; usage; exit 2 ;;
    \?) printf 'unknown option: -%s\n' "$OPTARG" >&2; usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))   # drop parsed options; "$@" is now positionals
```

- The **leading colon** in `":vo:h"` enables silent error handling so you control
  the messages via the `:` and `\?` cases. A trailing colon on a letter (`o:`)
  means that option takes an argument, available in `$OPTARG`.
- `shift $((OPTIND - 1))` is mandatory — it removes the options it consumed so the
  remaining `"$@"` is just positional arguments.

## Long options (`--flag`) by hand

`getopts` cannot do `--long` forms. For those, a `while`/`case` loop over `$@` is
the portable approach (avoid GNU `getopt`, which is non-portable and quoting-prone):

```bash
while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--verbose) verbose=1; shift ;;
    -o|--output)  outfile="$2"; shift 2 ;;
    --output=*)   outfile="${1#*=}"; shift ;;
    --)           shift; break ;;          # explicit end of options
    -*)           die "unknown option: $1" ;;
    *)            break ;;                  # first positional
  esac
done
```

## Positional arguments and validation

After parsing options, validate required positionals up front and fail with usage:

```bash
[[ $# -ge 1 ]] || { usage; exit 2; }
src=$1
dest=${2:-.}     # optional with a default
```

Use exit code `2` for usage errors by convention (distinct from `1` runtime failure).

## Subcommand dispatch

For multi-command tools (`tool build`, `tool deploy`), dispatch on the first
positional to a `cmd_*` function. Keep each subcommand self-contained.

```bash
main() {
  local subcmd=${1:-help}; shift || true
  case "$subcmd" in
    build)  cmd_build "$@" ;;
    deploy) cmd_deploy "$@" ;;
    help|-h|--help) usage ;;
    *) printf 'unknown command: %s\n' "$subcmd" >&2; usage; exit 2 ;;
  esac
}

main "$@"
```

This pattern composes with `getopts`: each `cmd_*` runs its own `getopts` loop over
its `"$@"`, so subcommands can have independent flags.
