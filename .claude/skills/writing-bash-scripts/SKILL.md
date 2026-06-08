---
name: writing-bash-scripts
description: "Guide for writing robust, ShellCheck-clean bash scripts. Use whenever creating a new bash or shell script (.sh file), modifying an existing bash script, writing shell functions or shell snippets longer than a few lines, scaffolding CLI tools in bash, or when the user asks for help with bash scripting, shell portability, or ShellCheck compliance. Also trigger when reviewing bash scripts for correctness. Even simple scripts benefit from these conventions — always use this skill for any .sh file work. Do NOT use for non-shell scripting languages (Python, Node, Ruby, Go), for Dockerfile or CI-YAML authoring (use the relevant CI skill), for Windows PowerShell/batch, or for one-off interactive shell commands you are not saving to a file."
command: /writing-bash-scripts
argument-hint:
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Writing bash scripts

Bash is forgiving by default and that is the problem: unquoted variables split,
failed commands are ignored, unset variables expand to nothing, and pipelines hide
errors. This skill encodes opinionated defaults that turn those silent failures into
loud, early ones, so the scripts you write are robust and ShellCheck-clean.

Apply these conventions to **any** shell script work — a five-line helper benefits
from strict mode and quoting just as much as a 300-line CLI.

## Opinionated defaults

Start every script with this skeleton. It is the single highest-leverage habit.

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

- `#!/usr/bin/env bash`, not `#!/bin/bash` — finds bash on PATH (macOS, Nix, BSD).
  Use `#!/bin/sh` *only* when the script must be POSIX and contains no bash-isms.
- `set -e` aborts on the first failed command; `set -u` errors on unset variables;
  `set -o pipefail` makes a pipeline fail if any stage fails. Together they stop a
  broken script from charging ahead. Details and caveats: `references/strict-mode.md`.
- `IFS=$'\n\t'` stops word-splitting on spaces — filenames with spaces survive.

Then, in priority order:

1. **Quote every expansion.** `"$var"`, `"$@"`, `"$(cmd)"`, `"${arr[@]}"`. This
   single rule prevents the majority of bash bugs. See
   `references/quoting-and-portability.md`.
2. **Centralize failure.** Define a `die()` that prints to stderr and exits, and a
   `log()`/`warn()` that go to stderr. Use exit code `2` for usage errors, `1` for
   runtime failures. See `references/error-handling.md`.
3. **Clean up with a trap.** `trap cleanup EXIT INT TERM` so temp files and
   background jobs are removed however the script ends. See
   `references/error-handling.md`.
4. **Parse arguments explicitly** with `getopts` (short flags) or a `while`/`case`
   loop (long flags), not positional `$1`/`$2` reaching. See
   `references/arguments.md`.
5. **Check dependencies up front** with `command -v tool || die "..."`, never
   `which`. See `references/quoting-and-portability.md`.
6. **Create temps with `mktemp`**, never a fixed `/tmp/name`. See
   `references/quoting-and-portability.md`.
7. **Lint with ShellCheck and aim for zero warnings.** See
   `references/testing-and-linting.md`.

## Code organization

Order a non-trivial script top-to-bottom so a reader hits intent before detail and
nothing executes before it is defined:

1. **Shebang** — `#!/usr/bin/env bash`.
2. **Strict mode** — `set -euo pipefail` and `IFS`.
3. **Constants / readonly globals** — `readonly` config, `SCRIPT_DIR`, version.

   ```bash
   SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
   readonly SCRIPT_DIR
   ```

4. **Helper functions** — `die`, `log`, `warn`, `require`, `usage`.
5. **Domain functions** — one job each, inputs as arguments, results to stdout,
   diagnostics to stderr. This is what makes the script testable.
6. **`main()`** — argument parsing, dependency checks, then the high-level flow.
   Keep it readable as the table of contents for the script.
7. **Entry guard** — call `main` last, guarded so the file can be sourced in tests:

   ```bash
   if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
     main "$@"
   fi
   ```

Keep functions short and single-purpose. Prefer bash parameter expansion
(`"${path##*/}"`, `"${var:-default}"`) over forking `basename`, `sed`, or `dirname`.
For multi-command tools, dispatch the first positional to a `cmd_*` function
(`references/arguments.md`).

## Gotchas

These trip up almost everyone. Internalize them.

- **`local x=$(cmd)` masks the exit code.** `local` returns 0, so `set -e` /
  `pipefail` never see `cmd` fail. Split it:

  ```bash
  local x
  x=$(cmd)
  ```

- **`set -e` does not fire in conditions.** Inside `if`, `while`, `&&`, `||`, or
  after `!`, a non-zero exit is expected, not fatal. Do not rely on `errexit` to
  catch a failure you have placed in a test.
- **`cd` can fail silently.** Always `cd -- "$dir" || die "no such dir: $dir"`
  (ShellCheck SC2164). A script that `cd`s and proceeds in the wrong directory is
  dangerous.
- **Unquoted `$var` in `[ ]`** breaks on empty or spaced values: `[ -n $x ]` errors
  when `$x` is empty. Use `[[ -n "$x" ]]`.
- **`for f in $(ls)`** breaks on spaces and is an antipattern. Glob directly:
  `for f in ./*.txt; do` — and handle the no-match case (`shopt -s nullglob` or a
  `[[ -e "$f" ]]` guard).
- **`echo` is not portable** for arbitrary data (flags, backslashes vary). Use
  `printf '%s\n' "$data"`.
- **Reading line-by-line** needs `while IFS= read -r line; do ... done < file` —
  without `-r`, backslashes are mangled; without `IFS=`, leading/trailing
  whitespace is stripped.
- **Arrays under `set -u`** on older bash: expand a possibly-empty array as
  `"${arr[@]:-}"` to avoid an unbound error.

## Reference catalog

Deep detail lives in `references/` so this body stays scannable. Read the file for
the topic you are working on:

- **`references/strict-mode.md`** — `set -euo pipefail`, `IFS`, the `errexit`
  exemptions, and when to relax strict mode safely.
- **`references/error-handling.md`** — `die`, exit codes, `trap` for `EXIT`/`ERR`/
  signals, cleanup that always runs, and bounded retries.
- **`references/arguments.md`** — `getopts` for short flags, hand-rolled long
  options, positional validation, and subcommand dispatch.
- **`references/quoting-and-portability.md`** — quoting rules, parameter expansion,
  logging, dependency checks, usage heredocs, `mktemp`, and bash-vs-POSIX / GNU-vs-BSD
  portability tables.
- **`references/testing-and-linting.md`** — running ShellCheck (and reaching zero
  warnings), narrow disable directives, plain-bash assertions, Bats, and designing
  functions for testability.

## Before you finish

- Run `shellcheck script.sh` and resolve every finding (install it if absent —
  `apt-get install shellcheck` / `brew install shellcheck`; or run it in CI). Zero
  warnings is the bar. `references/testing-and-linting.md` lists the common codes.
- Re-read every expansion and confirm it is quoted.
- Confirm `cd`, `rm`, and `mktemp` calls are guarded and cleaned up.
- Make `script.sh` executable: `chmod +x script.sh`.
