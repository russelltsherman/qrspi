# Testing and linting

A bash script is code; lint it and test it like code. ShellCheck catches the
correctness bugs static analysis can find; a test harness catches behavioral
regressions.

## ShellCheck

[ShellCheck](https://www.shellcheck.net) is the standard static analyzer for shell.
It flags unquoted expansions, `set -e` exemptions, useless `cat`, non-portable
constructs, and dozens of other real bugs. Target **zero warnings**.

```bash
shellcheck script.sh
shellcheck -x script.sh            # follow `source`d files
shellcheck -s bash script.sh       # force the bash dialect
shellcheck --severity=warning *.sh # in CI, fail on warning and above
```

> ShellCheck may not be installed in every environment (it is absent from this
> container at authoring time). Where the `shellcheck` binary is available, run it
> and resolve every finding before considering a script done. Where it is absent,
> install it (`apt-get install shellcheck`, `brew install shellcheck`) or run it in
> CI; do not treat its absence as permission to skip the standard.

### Disable directives — narrowly and with a reason

When a finding is a genuine false positive, disable that one check on that one line
and say why. Never blanket-disable a whole file.

```bash
# shellcheck disable=SC2034  # used by sourced config below
default_region="us-east-1"
```

Common codes worth knowing: `SC2086` (quote to prevent splitting/globbing),
`SC2046` (quote `$(...)`), `SC2155` (declare and assign separately), `SC2164`
(`cd ... || exit`), `SC1090/SC1091` (can't follow dynamic `source`).

## A CI lint step

```yaml
# minimal CI: lint every tracked shell script, fail on any finding
shellcheck $(git ls-files '*.sh')
```

## Testing

Two practical approaches, in order of weight:

1. **Assertion functions in plain bash.** No dependency; good for small scripts.

   ```bash
   assert_eq() {
     [[ "$1" == "$2" ]] || { printf 'FAIL: expected %q got %q\n' "$2" "$1" >&2; exit 1; }
   }
   assert_eq "$(my_func abc)" "ABC"
   echo "all tests passed"
   ```

2. **[Bats](https://github.com/bats-core/bats-core)** (Bash Automated Testing
   System) for anything substantial. Each test is a function; `run` captures
   status and output.

   ```bash
   @test "build writes the artifact" {
     run ./tool build --out /tmp/x
     [ "$status" -eq 0 ]
     [ -f /tmp/x ]
   }
   ```

## Design for testability

- Put logic in **functions**, keep top-level code to argument parsing plus a single
  `main "$@"`. Functions are unit-testable; a 200-line top-level script is not.
- Guard the entry point so the file can be `source`d by a test without executing:

  ```bash
  if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
  fi
  ```

- Inject side-effecting commands (network, filesystem roots) via variables so tests
  can substitute fakes.
- Make functions pure where possible: take inputs as arguments, write results to
  stdout, send diagnostics to stderr. Pure functions are trivial to assert on.
