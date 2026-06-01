# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

> **Overarching finding:** Both target files named throughout the questions —
> `scripts/slugify.py` and `scripts/slugify_test.py` — **do not exist** in the
> repository. No `slug`/`slugify` token appears anywhere in the codebase.
> Searches performed:
> - `ls scripts/slugify*` → "no matches found"
> - `grep -rni "slugify" --include=*.py --include=*.md --include=*.js .` → 0 hits (excluding questions.md)
> - `grep -rni "slug" .` → 0 hits (excluding questions.md)
>
> Current `scripts/` contents: `check_scope.py`, `diagnose.py`, `grade.py`,
> `report.py`, `revise.py`, `run_eval.py`. None reference slugs.
>
> Consequently, Q1–Q12 each describe behavior of code that has not been written
> yet. Each is answered **NOT FOUND** below. Where the question concerns a
> *convention* the new file would be expected to follow, the closest existing
> evidence (CLI/test patterns in sibling `scripts/*.py`) is cited in the
> Discovered Patterns section so the design phase has a factual baseline.

## Q1: How does an input string travel from the CLI argument through to the printed slug, and what transformation steps occur in between (lowercasing, non-alphanumeric replacement, hyphen stripping)?

**Answer:** NOT FOUND. `scripts/slugify.py` does not exist. No `slugify` function or transformation pipeline is present in the repository.
**Evidence:**

```
$ ls scripts/slugify*
(eval):1: no matches found: scripts/slugify*
$ grep -rni "slugify" --include="*.py" .   # excluding questions.md
(no output)
```

— search results, no source file
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q2: What regular expression or character-class logic identifies a "run of non-alphanumeric characters," and does it operate on the raw input before or after lowercasing?

**Answer:** NOT FOUND. No regex or character-class logic for slug transformation exists. No `re` usage related to slugs in the repo. (Note: `scripts/check_scope.py:21,33` uses `re.finditer(r"`([^`]+\.\w+)`", ...)` for unrelated markdown path extraction — not a slug routine.)
**Evidence:** Search for `slugify`/`slug` returned no source matches.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q3: What is the exact signature, return type, and docstring of the public `slugify` function, and is anything else exported from the module?

**Answer:** NOT FOUND. No `slugify(text: str) -> str` function definition exists; no module to export from.
**Evidence:** `grep -rni "def slugify" .` → 0 hits.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q4: How does the CLI entrypoint parse the title argument, invoke `slugify`, print the result, and set the exit code to 0?

**Answer:** NOT FOUND. `scripts/slugify.py` has no `__main__` block because the file does not exist. (Existing sibling scripts use `argparse` + `if __name__ == "__main__": main()` — see Discovered Patterns — but none invoke `slugify`.)
**Evidence:** File absent; `grep -rni "slugify" .` → 0 hits.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q5: Is `slugify` implemented as a pure function with no module-level mutable state, caching, or side effects beyond the CLI print path?

**Answer:** NOT FOUND. No implementation exists to evaluate for purity.
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q6: How are the empty string, leading/trailing whitespace, and consecutive non-alphanumeric runs handled so that `slugify("")` returns `""` and `slugify("  Hello,  World!! ")` returns `"hello-world"` with no consecutive or edge hyphens?

**Answer:** NOT FOUND. No hyphen-collapsing or stripping logic exists. The cited expected behaviors (`slugify("") == ""`, `slugify("  Hello,  World!! ") == "hello-world"`) are unverifiable against any code.
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q7: How is an all-symbol input (e.g. a string containing only punctuation) handled, and what does the function return when every character is non-alphanumeric?

**Answer:** NOT FOUND. No function exists to determine the all-symbol return value.
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q8: How are unicode characters classified as alphanumeric or non-alphanumeric, and does the chosen regex/character test treat accented or non-ASCII letters as alphanumeric or as separators?

**Answer:** NOT FOUND. No alphanumeric-matching logic exists; the unicode classification decision (e.g. `str.isalnum()` vs. `re` with/without `re.UNICODE`, vs. ASCII-only `[a-z0-9]`) has not been made in any code.
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q9: How do the assert-based tests cover the ticket's specified cases (`""`, `"  Hello,  World!! "`, `"RUS-44: Add a thing"`) plus the unicode and all-symbol cases, and are they stdlib-only with no third-party test framework?

**Answer:** NOT FOUND. `scripts/slugify_test.py` does not exist; no slug tests are present. (Repo-wide, no test file imports a third-party test framework — see Discovered Patterns — but there is no slug test to confirm coverage of the cited cases.)
**Evidence:** `find . -name "*_test.py"` returns `revise.py`-style names? No — returns none matching slug; existing `_test.py` files: none found via `find . -name "*_test.py"`.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q10: How does `scripts/slugify_test.py` import the `slugify` function under test without importing any other repository module?

**Answer:** NOT FOUND. No test file exists, so its import statements cannot be examined.
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q11: How are the tests executed and what signals pass versus failure (exit code, assertion error output)?

**Answer:** NOT FOUND. No slug test runner exists. (Sibling scripts follow a `main()` + `sys.exit(0 if ok else 1)` convention — see Discovered Patterns — but this is not the slug test.)
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

## Q12: What does the CLI emit on stdout versus stderr, and how would a caller distinguish a successful slug output from an invocation error (e.g. missing argument)?

**Answer:** NOT FOUND. No slug CLI exists. (`argparse` — the convention in sibling scripts — automatically writes usage/errors to stderr and exits non-zero on a missing required argument, but no slug CLI wires this up.)
**Evidence:** File absent.
**Dependencies:** None present.
**Implicit contracts:** None present.

---

## Discovered Patterns

These are conventions observed in existing `scripts/*.py` files. They are NOT
the slug feature (which does not exist) but are the closest factual baseline for
how a new standalone utility in this repo is conventionally structured.

- **Shebang + module docstring.** Every script opens with `#!/usr/bin/env python3`
  followed by a triple-quoted module docstring describing purpose.
  — `scripts/check_scope.py:1-6`

- **`main()` + `argparse` CLI entrypoint.** Scripts parse args via
  `argparse.ArgumentParser`, define a `main()`, and guard with
  `if __name__ == "__main__": main()`.
  — `scripts/check_scope.py:55-74`

- **Exit-code convention.** Scripts signal success/failure with
  `sys.exit(0 if result["passed"] else 1)`; human-readable status (`PASS:`/`FAIL:`)
  is printed to stdout via `print(...)`.
  — `scripts/check_scope.py:63-70`

```python
if result["passed"]:
    print("PASS: All files within scope")
else:
    print(f"FAIL: Out-of-scope files: {result['out_of_scope']}")
...
sys.exit(0 if result["passed"] else 1)
```

— `scripts/check_scope.py:63-70`

- **Stdlib-only.** All six existing scripts import only stdlib modules
  (`argparse`, `json`, `re`, `sys`). No third-party dependency, no `pytest`,
  no `requirements.txt`/`pyproject.toml` declaring test deps was found in the
  repo. A stdlib-only, assert-based test (as Q9 anticipates) would be consistent
  with this baseline.
  — `scripts/check_scope.py:8-11`

- **Type hints on function signatures.** Existing functions annotate params and
  returns, e.g. `def load_allowed_files(worktree_session_path: str) -> set:`.
  — `scripts/check_scope.py:14`

- **No existing `*_test.py` / `test_*.py` files.** `find . -name "*_test.py" -o
  -name "test_*.py"` returned no results. The repo has no established test-file
  location or test runner for `scripts/`; the proposed `scripts/slugify_test.py`
  would be the first co-located test in `scripts/`.

## Inconsistencies

- **Questions describe code that does not exist.** Every question (Q1–Q12) is
  framed as if `scripts/slugify.py` and `scripts/slugify_test.py` were already
  implemented (e.g., "what regex... identifies a run", "how do the assert-based
  tests cover..."). In reality neither file is present. This is consistent with
  the ticket title prefix `[e2e-throwaway]`, indicating a greenfield
  create-from-scratch task rather than analysis of existing code. The Research
  phase can supply conventions (above) but cannot cite slug behavior.

- **Project CLAUDE.md path drift (informational, unrelated to slug).** The
  worktree's `.claude/CLAUDE.md` states "Agent prompt definitions live in
  `.qrspi/agents/`", while the repo-root `.claude/CLAUDE.md` (in the system
  context) states phase agent definitions live in `.claude/agents/`. Noted only
  as a doc/structure inconsistency encountered while orienting; it has no bearing
  on the slugify feature.
