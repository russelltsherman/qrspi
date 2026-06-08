# Quoting, logging, dependencies, temp files, and portability

The single largest source of bash bugs is unquoted expansion. Most of the rest is
assuming a feature exists everywhere. This file covers both, plus the small
utilities every non-trivial script needs.

## Quoting — the rules

- **Always double-quote expansions:** `"$var"`, `"${arr[@]}"`, `"$(cmd)"`. Without
  quotes the value is word-split on `IFS` and glob-expanded. A path with a space
  silently becomes two arguments.
- **`"$@"` not `$@`** to forward arguments — `"$@"` preserves each argument intact;
  `$*` joins them into one string.
- **Use `${var}` braces** when adjacent text would otherwise glue on:
  `"${file}_backup"`, `"${count}th"`.
- **Single-quote literals** with no expansion: `grep 'fixed$string' file`.
- Quoting inside `[[ ]]` is optional for the left side but harmless; quote the
  right side of `==`/`!=` to compare literally instead of as a glob pattern:
  `[[ "$x" == "*.txt" ]]` matches the literal, `[[ "$x" == *.txt ]]` globs.

## Parameter expansion instead of subshells

Prefer builtins to forking `sed`/`basename`/`dirname`:

```bash
"${path##*/}"     # basename
"${path%/*}"      # dirname
"${name%.*}"      # strip extension
"${var:-default}" # default if unset/empty
"${var//old/new}" # replace all
"${#var}"         # length
```

## Logging

Send diagnostics to stderr so stdout stays clean for data/piping. A timestamped
helper keeps logs consistent:

```bash
log()  { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
warn() { printf 'warning: %s\n' "$*" >&2; }
```

Guard verbose output behind a flag rather than commenting lines in and out:
`(( verbose )) && log "..."`.

## Dependency checks

Fail fast and clearly if a required external tool is missing, instead of erroring
deep in the script:

```bash
require() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}
require jq
require curl
```

Use `command -v`, not `which` (which is an external, non-portable program).

## Usage heredoc

Keep usage text readable with a quoted heredoc so `$` and backticks stay literal:

```bash
usage() {
  cat >&2 <<'EOF'
usage: deploy [-v] [-o FILE] ENVIRONMENT

  -v        verbose output
  -o FILE   write report to FILE
  -h        show this help
EOF
}
```

The quoted delimiter (`<<'EOF'`) prevents expansion; use unquoted `<<EOF` only when
you intend `$var` inside to expand.

## Temp files and directories

Create temps with `mktemp` (never a fixed `/tmp/foo`, which races and collides) and
remove them in an `EXIT` trap (see `error-handling.md`):

```bash
tmp=$(mktemp)
workdir=$(mktemp -d)
trap 'rm -rf "$tmp" "$workdir"' EXIT
```

`mktemp -d` for a directory; pass a `XXXXXX` template only if you need a name
pattern. Quote the result — temp paths can contain the system temp dir's spaces.

## Portability — bash vs POSIX sh, GNU vs BSD

If the shebang is `#!/usr/bin/env bash`, bash features (`[[ ]]`, arrays, `local`,
`${var//}`) are fair game. If it must run under `/bin/sh` (dash, BusyBox), they are
not. Decide explicitly and match the shebang.

| Feature | bash | POSIX `sh` |
|---------|------|-----------|
| `[[ cond ]]` | yes | no — use `[ cond ]` / `test` |
| arrays | yes | no |
| `local` | yes | no (use subshells or naming discipline) |
| `${var//a/b}` | yes | no — use `sed`/`case` |
| `function name {}` | yes | use `name() {}` (works in both) |

Cross-platform GNU vs BSD pitfalls (macOS ships BSD):

- `sed -i` needs a backup-suffix argument on BSD (`sed -i '' ...`) but not GNU.
  Avoid in-place edits in portable scripts, or branch on `uname`.
- `date`, `readlink -f`, `grep -P`, `stat` flags differ. Prefer POSIX-common
  options or detect and adapt.
- `mapfile`/`readarray` is bash 4+; macOS's system bash is 3.2.

When portability is not required, say so in a comment and use the clearer bash
construct.
