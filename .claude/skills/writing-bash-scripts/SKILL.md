---
name: writing-bash-scripts
description: "Guides agents when writing bash scripts. Encodes project conventions for strict mode, error handling, argument parsing, subcommand dispatch, logging, quoting, dependency checking, and portability. Always use for any task that creates, modifies, or reviews bash scripts. Produces ShellCheck-clean output."
command: /writing-bash-scripts
argument-hint: <script-description>
allowed-tools: [Bash, Read, Write, Edit]
---

# Writing Bash Scripts

You are a careful bash script developer. Follow every convention below — no exceptions. The goal is production-grade, ShellCheck-clean scripts that work on both Linux and macOS.

---

## When to Use

Use this skill whenever:
- Creating a new `.sh` or bash script file
- Modifying an existing bash script
- Reviewing a bash script for correctness and convention compliance
- The user asks to "write a bash script", "fix a script", or "add a utility script"

---

## Code Organization

Every script follows this exact order:

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly SCRIPT_NAME="${0##*/}"
readonly VERSION="1.0.0"

# --- Source statements (if any) ---
# source ./lib.sh

# --- Helper functions ---
log()          { ... }
info()         { ... }
warn()         { ... }
die()          { ... }
usage()        { ... }
cleanup()      { ... }

# --- Command functions (subcommand pattern) ---
cmd_deploy()   { ... }
cmd_status()   { ... }

# --- Main ---
main() { ... }
main "$@"
```

Lines above `main` are parsed, not executed. This ordering is mandatory.

---

## Strict Mode

Always use `set -euo pipefail`. It is never optional.

- `-e` : Exit immediately on command failure.
- `-u` : Treat unset variables as errors.
- `-o pipefail` : A pipeline fails if any command in it fails.

Do NOT use `set -x` in production scripts (it leaks secrets to logs). Only enable it for debugging, and always disable it afterward.

---

## Error Handling

Use traps for guaranteed cleanup and error reporting:

```bash
cleanup() {
    rm -f "${TMPFILE:-}" 2>/dev/null || true
}
trap cleanup EXIT

trap 'echo "Error on line $LINENO" >&2' ERR
```

Exit code conventions:
- `0` — success
- `1` — general error
- `2` — misuse / bad arguments

All diagnostics go to stderr (`>&2`). Reserved stdout for pipeable data.

---

## Argument Parsing

**Simple flags:** Use `getopts`.

```bash
verbose=false
while getopts "vqf:" opt; do
    case "$opt" in
        v) verbose=true ;;
        q) quiet=true ;;
        f) config_file="$OPTARG" ;;
        \?) usage; exit 2 ;;
    esac
done
shift $((OPTIND - 1))
```

**Long options or subcommands:** Use a `while/case/shift` loop.

```bash
while [[ $# -gt 0 ]]; do
    case "$1" in
        --config) config_file="$2"; shift 2 ;;
        --help)   usage; exit 0 ;;
        --)       shift; break ;;
        *)        echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done
```

Never use GNU `getopt` — it is not portable to macOS.

---

## Subcommand Dispatcher

When the script has 2+ distinct operations, use the subcommand pattern:

```bash
cmd_help() {
    usage
}

cmd_deploy() {
    echo "Deploying..."
}

cmd_status() {
    echo "Status: OK"
}

main() {
    local subcmd="${1:-help}"
    shift || true

    if declare -f "cmd_${subcmd}" >/dev/null 2>&1; then
        "cmd_${subcmd}" "$@"
    else
        echo "Unknown command: ${subcmd}" >&2
        cmd_help
        exit 2
    fi
}

main "$@"
```

- Prefix subcommand functions with `cmd_`.
- Lookup via `declare -f "cmd_${subcmd}"` — works for functions only.
- Default to `help` when no subcommand given.
- Fail clearly on unknown commands with exit code 2.

---

## Logging

Define these helper functions. Color only when stderr is a terminal:

```bash
# Color helpers — only active when stderr is a TTY
if [[ -t 2 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

log()     { echo "${NC}$*${NC}" >&2; }
info()    { echo "${GREEN}[INFO]${NC} $*" >&2; }
warn()    { echo "${YELLOW}[WARN]${NC} $*" >&2; }
die()     { echo "${RED}[ERROR]${NC} $*" >&2; exit 1; }
```

Never use `echo` directly for logging — always use the helpers.

---

## Quoting & Variables

Always double-quote variables:

```bash
# CORRECT
echo "${var}"
echo "$@"
result="$(command)"
args=("${array[@]}")

# WRONG
echo $var
echo $@
result=`command`
```

Use defaults for optional variables:

```bash
readonly HOME_DIR="${1:-/tmp}"
```

Use arrays for argument lists that may contain spaces:

```bash
files=("file 1.txt" "file 2.txt")
for f in "${files[@]}"; do
    echo "Processing: ${f}"
done
```

---

## Dependency Checking

Check all dependencies at the top of the script, before any logic:

```bash
check_dep() {
    if ! command -v "$1" >/dev/null 2>&1; then
        die "Required command not found: $1"
    fi
}

check_dep jq
check_dep curl
check_dep mktemp
```

The pattern: `command -v "$name" >/dev/null 2>&1`. Check exit code 1. Report the missing tool name in the error.

---

## Usage/Help

Provide a heredoc-based usage function:

```bash
usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} <command> [options]

Commands:
  deploy    Deploy the application
  status    Show current status
  help      Show this help message

Options:
  -v, --verbose    Enable verbose output
  -q, --quiet      Suppress non-error output
  -f, --config     Path to config file
  --help           Show this help message

Exit Codes:
  0  Success
  1  General error
  2  Bad arguments or unknown command
EOF
}
```

Always show `${0##*/}` (basename) so the usage works regardless of how the script is invoked.

---

## Temp Files

Always use `mktemp` — never predictable names:

```bash
TMPFILE="$(mktemp)"
trap cleanup EXIT  # ensure cleanup is registered

cleanup() {
    rm -f "${TMPFILE}" 2>/dev/null || true
}
```

If you need multiple temp files, use an array:

```bash
TEMP_FILES=()
add_temp() { TEMP_FILES+=("$1"); }

cleanup() {
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f" 2>/dev/null || true
    done
}
trap cleanup EXIT
```

---

## Testing & Linting

Every script must pass ShellCheck with zero warnings:

```bash
shellcheck myscript.sh
```

For testable scripts, use BATS-core (Bash Automated Testing System):

```bash
# test/myscript.bats
#!/usr/bin/env bats

setup() {
    setup_fixtures
}

@test "deploy succeeds with valid config" {
    run "${SCRIPT_DIR}/myscript.sh" deploy --config "test/config.yaml"
    [ "$status" -eq 0 ]
}

@test "deploy fails with missing command" {
    run "${SCRIPT_DIR}/myscript.sh" badcommand
    [ "$status" -eq 2 ]
}
```

Include an invocation guard at the bottom for executable scripts:

```bash
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

---

## Portability

Target bash 4+. Note that macOS ships bash 3.2 by default — use `#!/usr/bin/env bash` for portability.

Be aware of BSD vs GNU coreutils differences:

- `sed`: GNU supports `-i` (edit in-place); macOS requires `sed -i ''`
- `date`: GNU uses `%Y-%m-%d`; macOS requires `+` prefix (`date +%Y-%m-%d`)
- `grep`: GNU returns exit code 1 on no match; same for BSD, but behavior can differ with `-q`
- `sort`: GNU supports `--stable`; macOS does not

When portability matters, test on both platforms.

---

## Gotchas

Common pitfalls that cause silent failures or security issues:

### 1. Unquoted variables

```bash
# BUG: fails if var contains spaces or is empty
echo $var

# FIX: always quote
echo "${var}"
```

### 2. Missing `--` in commands

```bash
# BUG: --config deletes an argument that looks like an option
cat $file --option

# FIX: use -- to stop option parsing
cat -- "$file" --option
```

### 3. `cd` without error check

```bash
# BUG: script continues in wrong directory if cd fails
cd /some/path
rm -rf *

# FIX: always check cd
cd /some/path || die "Cannot enter directory"
```

### 4. Variable expansion in traps

```bash
# BUG: variable captured at trap definition, not at execution
TMPFILE="$(mktemp)"
# If TMPFILE changes, cleanup removes the wrong file

# FIX: use a function that reads the variable at runtime
cleanup() { rm -f "${TMPFILE:-}" 2>/dev/null || true; }
trap cleanup EXIT
```

### 5. Forgetting pipefail

```bash
# BUG: last command in pipe determines exit code
false | true  # exits 0 — the failure is silent

# FIX: always use pipefail
set -o pipefail
false | true  # exits 1 — failure detected
```

---

## Scope Guidance

- **Always** use the subcommand pattern when the script has 2+ distinct operations.
- **Always** use strict mode (`set -euo pipefail`) — no exceptions.
- **Never** exceed ~200 lines without strong justification. If you are, split into a main script + sourced library.
- **Always** include a gotchas section relevant to the script's purpose.
- **Always** produce ShellCheck-clean output — review with `shellcheck` before delivering.
