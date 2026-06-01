# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

> **Overarching finding:** This is a **greenfield** feature. Neither of the two
> target files referenced by every question exists in the repository:
>
> - `scripts/slugify.py` — `ls` returns "No such file or directory"
> - `scripts/slugify_test.py` — `ls` returns "No such file or directory"
>
> A repo-wide search for `slug`/`slugify` (case-insensitive, across `*.py`,
> `*.md`, `*.js`, `*.ts`) returns **zero hits** outside the QRSPI artifacts for
> this ticket itself. There is no prior art, partial implementation, comment,
> or doc reference to slugification anywhere in `REPO_ROOT`.
>
> Search commands run:
> - `find . -path ./.git -prune -o -iname '*slug*' -print` → no output
> - `grep -rin "slugify" . --include='*.py' --include='*.md' --include='*.js' --include='*.ts' -l` → no output (outside `.qrspi/RUS-44/`)
> - `ls -la scripts/slugify.py scripts/slugify_test.py` → both "No such file or directory"
>
> Because the implementation does not yet exist, **Q1–Q12 cannot be answered
> from existing code**. Each is marked NOT FOUND below. Where the codebase
> establishes a relevant *convention* a future implementation would follow,
> that convention is cited from the existing `scripts/` directory.

## Q1: What is the exact transformation order applied to the input string (lowercasing, non-alphanumeric replacement, hyphen stripping) and at which step is each acceptance-criteria case satisfied?

**Answer:** NOT FOUND — `scripts/slugify.py` does not exist, so no `slugify(text: str) -> str` function or transformation pipeline is present to inspect. There is no transformation order to report.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable.

## Q2: How is "non-alphanumeric" defined for the run-collapsing step — does it operate on ASCII only, or on the full Unicode notion of alphanumeric, and how does that determine the output for unicode input?

**Answer:** NOT FOUND — no character-classification logic exists because `scripts/slugify.py` is absent. The ASCII-vs-Unicode decision has not been made in code.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable.

## Q3: What is the signature, return type, and docstring contract of the public `slugify` function, and does it expose any parameters beyond `text`?

**Answer:** NOT FOUND — no `slugify` function definition exists. No signature, return type, or docstring is present to report.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** Existing `scripts/` modules type-annotate function signatures (e.g. `def load_allowed_files(worktree_session_path: str) -> set:` at `scripts/check_scope.py:14`) and open with a `"""..."""` docstring — a convention a future `slugify` would be expected to match.

## Q4: How does the CLI entry point read its argument, invoke `slugify`, print the result, and set the exit code, and is it guarded by an `if __name__ == "__main__"` block?

**Answer:** NOT FOUND — no CLI / `main` block exists for slugify. However, the repo has a consistent CLI convention across `scripts/`: a `main()` function guarded by `if __name__ == "__main__":` that parses args via `argparse`, prints to stdout, and calls `sys.exit(...)` with a status code.
**Evidence:**

```python
def main():
    parser = argparse.ArgumentParser(description="Check implementation scope")
    parser.add_argument("--log", required=True, help="Path to impl-log.md")
    ...
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
```

— `scripts/check_scope.py:62-81` (analogous existing script — NOT the target file)
**Dependencies:** `argparse`, `sys` are the stdlib modules used by existing CLI scripts.
**Implicit contracts:** Existing scripts use `argparse` with `--flag` arguments rather than positional `sys.argv` indexing; the questions (Q4/Q12) imply slugify reads a single positional argument, which would diverge from this convention. Flag this as an open design choice, not an established fact.

## Q5: Is `slugify` implemented as a pure function with no module-level mutable state, caches, or side effects beyond returning a value?

**Answer:** NOT FOUND — no function body or module-level scope exists to evaluate for purity.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** Existing helper functions in `scripts/` are pure transformations that return values (e.g. `load_allowed_files` / `check_scope` in `scripts/check_scope.py`), with side effects confined to `main()`. A future `slugify` matching house style would likewise be pure.

## Q6: Which standard-library modules does `scripts/slugify.py` import, and does it import any module from elsewhere in the repository?

**Answer:** NOT FOUND — no import statements exist because the file is absent.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable. For reference, existing sibling scripts import only stdlib (e.g. `import argparse`, `json`, `re`, `sys` at `scripts/check_scope.py:7-10`) and do not import from elsewhere in the repo.
**Implicit contracts:** `scripts/` modules are self-contained and stdlib-only; there is no shared internal package imported across them.

## Q7: What does `slugify` return for empty input `""` and for all-symbol input (e.g. a string of only punctuation), and where in the function is the empty-result case produced?

**Answer:** NOT FOUND — no function exists; empty-input and all-symbol behavior is undefined in code.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable.

## Q8: How does the function handle leading, trailing, and consecutive runs of non-alphanumeric characters so that no leading, trailing, or consecutive hyphens appear in the output?

**Answer:** NOT FOUND — no hyphen-collapsing or strip logic exists; the file is absent.
**Evidence:** none — file absent.

— `scripts/slugify.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable.

## Q9: How is unicode input (e.g. accented or non-Latin characters) treated — preserved, transliterated, or dropped — and what slug does the corresponding test expect?

**Answer:** NOT FOUND — neither `scripts/slugify.py` nor `scripts/slugify_test.py` exists, so there is no unicode-handling path and no test asserting unicode output.
**Evidence:** none — both files absent.

— `scripts/slugify.py` (does not exist), `scripts/slugify_test.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable. Note: no transliteration library (e.g. `unidecode`) appears anywhere in the repo, so transliteration would require either a new dependency or a stdlib `unicodedata` approach — an unresolved design choice.

## Q10: Which input/output cases does `scripts/slugify_test.py` assert, and does it cover the three documented examples plus unicode and all-symbol input?

**Answer:** NOT FOUND — `scripts/slugify_test.py` does not exist; no assertions are present to enumerate.
**Evidence:** none — file absent.

— `scripts/slugify_test.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable.

## Q11: How is the test invoked and what defines pass/fail — is it a plain `python3 scripts/slugify_test.py` run using bare `assert` statements with no third-party test framework?

**Answer:** NOT FOUND — no test file exists. There is also no existing test in the repo to establish a precedent: a search for `*_test.py` and `test_*.py` (excluding `.qrspi/`) returns **zero files**. No `pytest`/`unittest` usage, test runner config, or CI test invocation was found in `scripts/`.
**Evidence:** none — file absent; no sibling test files exist.

— `scripts/slugify_test.py` (does not exist)
**Dependencies:** none discoverable.
**Implicit contracts:** none discoverable — the repo has no established Python test pattern, so the "bare assert, `python3 scripts/slugify_test.py`" approach implied by the question would be net-new.

## Q12: When the CLI is run, what exactly is written to stdout versus stderr, and what exit codes are produced for valid input, missing arguments, or other failure modes?

**Answer:** NOT FOUND — no CLI exists for slugify. For reference, existing scripts write results to stdout and exit `0` on success / `1` on failure; `argparse` itself emits usage errors to stderr and exits `2` when a required argument is missing.
**Evidence:**

```python
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(0 if result["passed"] else 1)
```

— `scripts/check_scope.py:78-80` (analogous existing script — NOT the target file)
**Dependencies:** `sys` (for `sys.exit` and `sys.stdout`), `argparse` (emits its own stderr/exit-2 on bad args) in existing scripts.
**Implicit contracts:** Existing scripts use exit `0`/`1` semantics and print human-readable output to stdout. The exit-code behavior for slugify is otherwise undefined in code.

---

## Discovered Patterns

- **All `scripts/` modules are stdlib-only Python 3.** Each begins with
  `#!/usr/bin/env python3` and imports only standard-library modules
  (`argparse`, `json`, `re`, `sys`). No third-party packages and no
  cross-module repo imports were observed (`scripts/check_scope.py:1-11`).
- **Consistent CLI shape.** Scripts define pure helper functions plus a
  `main()` that uses `argparse` and is guarded by
  `if __name__ == "__main__": main()` (`scripts/check_scope.py:62-81`). Note
  these use **flag-style** args (`--log`, `--allowed`), not positional args.
- **Type-annotated, docstringed functions** are the house style
  (`def load_allowed_files(worktree_session_path: str) -> set:` with a
  one-line docstring, `scripts/check_scope.py:14-15`).
- **Exit-code discipline:** `sys.exit(0 if ... else 1)` for pass/fail
  (`scripts/check_scope.py:80`).
- **No Python test suite exists.** There are no `*_test.py` / `test_*.py`
  files anywhere in the repo (excluding `.qrspi/` artifacts), and no
  pytest/unittest dependency or runner config. The `scripts/run_eval.py`
  harness is for QRSPI evals, not unit tests.

## Inconsistencies

- **Naming convention mismatch (potential):** The ticket targets a test file
  named `scripts/slugify_test.py` (suffix `_test.py`), but the repo has *no*
  existing Python test files to confirm or contradict this convention. The
  unittest/pytest default is `test_*.py` (prefix). This is an unestablished
  choice, not a contradiction with existing code — flagged so the design phase
  resolves naming explicitly.
- **CLI arg style mismatch (potential):** Q4/Q12 describe a CLI that reads a
  single argument and prints the result — implying a positional argument.
  Every existing script in `scripts/` uses `argparse` with required `--flags`
  (`scripts/check_scope.py:64-66`). A positional-argument slugify CLI would
  diverge from the established pattern. Not a bug in existing code; an open
  design decision.
- **Unicode handling undecided:** No transliteration library
  (`unidecode`, etc.) exists in the repo, and `unicodedata` is not imported
  anywhere. Q2/Q9 assume a unicode policy that has no precedent in code.
