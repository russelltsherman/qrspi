# Strict mode

Strict mode turns silent failures into loud, early ones. Put it at the top of
every script, immediately after the shebang.

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

## What each flag does

| Flag | Effect | Why it matters |
|------|--------|----------------|
| `set -e` (`errexit`) | Exit immediately if any command exits non-zero. | Stops a script from charging ahead after a failed step. |
| `set -u` (`nounset`) | Treat an unset variable as an error. | Catches typos and missing arguments before they corrupt paths. |
| `set -o pipefail` | A pipeline fails if *any* element fails, not just the last. | `grep x file | sort` no longer "succeeds" when `grep` errors. |
| `IFS=$'\n\t'` | Word-split only on newline and tab, not spaces. | Filenames with spaces stop silently splitting into pieces. |

Use the long form `set -o errexit -o nounset -o pipefail` in scripts meant to be
read by people; it is self-documenting. The short `set -euo pipefail` is fine for
terse tooling.

## Caveats — `set -e` is not a substitute for handling errors

`set -e` has surprising exemptions. Know them so you do not assume protection you
do not have:

- **Commands in a condition are exempt.** `if cmd; then`, `while cmd`, `cmd && ...`,
  `cmd || ...`, and a `!`-negated command do not trigger `errexit`. This is by
  design — that is how you test exit codes.
- **The last command of a function/script sets its status**; a failure mid-function
  under `set -e` still aborts, but a function whose *final* command fails returns
  non-zero to its caller, which may itself be in an exempt context.
- **Command substitution** in older bash did not always propagate `-e`. Prefer
  explicit checks for `local x; x=$(cmd)` — declare and assign on separate lines,
  because `local x=$(cmd)` masks the substitution's exit code (`local` succeeds).

```bash
# WRONG: local masks the failure of cmd
local result=$(might_fail)        # always "succeeds" — local returns 0

# RIGHT: split declaration from assignment so pipefail/errexit see the status
local result
result=$(might_fail)
```

## Unset variables and intentional emptiness

Under `set -u`, reference a possibly-unset variable with a default to opt out
locally rather than disabling the flag:

```bash
echo "${OPTIONAL:-}"          # empty if unset, no error
echo "${1:?usage: need an argument}"   # error with message if unset
"${array[@]:-}"               # safe expansion of a possibly-empty array
```

Never expand a possibly-empty array as `"${arr[@]}"` under `set -u` on bash < 4.4;
use the `:-` guard above.

## When to relax it

Strict mode is the default, not dogma. If a single command is *expected* to fail
and you handle it, scope the relaxation rather than dropping the flag globally:

```bash
set +e
output=$(command_that_may_fail)
status=$?
set -e
```

Or, preferred, use a condition so `errexit` never fires:

```bash
if ! output=$(command_that_may_fail); then
  output="fallback"
fi
```
