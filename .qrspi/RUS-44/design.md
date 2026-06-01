# Design — Add a standalone slugify utility

**Ticket:** RUS-44
**Research basis:** research.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Current State

This is a greenfield feature: neither `scripts/slugify.py` nor `scripts/slugify_test.py` exists, and a repo-wide search for `slug`/`slugify` returns zero hits outside this ticket's own QRSPI artifacts (ref: overarching finding). There is no prior slugification code, comment, or doc reference anywhere in the repo (ref: overarching finding). Because no implementation exists, there is no transformation pipeline, character-classification logic, function signature, CLI block, or import set to inspect (ref: Q1, Q2, Q3, Q4, Q6).

The repo does establish relevant conventions in the sibling `scripts/` directory that a new module would be expected to follow. All `scripts/` modules are stdlib-only Python 3, beginning with a `#!/usr/bin/env python3` shebang and importing only standard-library modules such as `argparse`, `json`, `re`, and `sys`, with no third-party packages and no cross-module repo imports (ref: Q6, Discovered Patterns). Helper functions are pure transformations that return values, with side effects confined to `main()`, and are type-annotated with a one-line docstring (ref: Q3, Q5, Discovered Patterns). The consistent CLI shape is a `main()` function guarded by `if __name__ == "__main__": main()` that parses arguments via `argparse`, prints to stdout, and calls `sys.exit(0 if ... else 1)` (ref: Q4, Q12, Discovered Patterns).

Two conventions diverge from what this ticket implies. Every existing CLI uses flag-style arguments such as `--log` rather than positional arguments, whereas the ticket implies a single positional argument (ref: Q4, Inconsistencies). The repo has no Python test suite at all — no `*_test.py` or `test_*.py` files exist, and there is no pytest/unittest dependency or runner config — so the bare-assert test approach the ticket calls for would be net-new with no in-repo precedent (ref: Q10, Q11, Discovered Patterns). No transliteration library or `unicodedata` import exists anywhere, so any unicode policy is undecided in code (ref: Q9, Q2, Inconsistencies).

## Desired End State

After this ships, the repo contains two new self-contained, stdlib-only files. Each acceptance criterion maps to the following behavior.

- A new file `scripts/slugify.py` exposes a pure function `slugify(text: str) -> str` that lowercases the input, replaces every run of non-alphanumeric characters with a single hyphen, strips leading and trailing hyphens, and never emits consecutive hyphens. This matches the house style of pure, type-annotated, docstringed helpers (ref: Q3, Q5).
- `slugify("")` returns `""`; `slugify("  Hello,  World!! ")` returns `"hello-world"`; `slugify("RUS-44: Add a thing")` returns `"rus-44-add-a-thing"`. The empty result is produced naturally by the strip-and-collapse pipeline when no alphanumeric characters survive (ref: Q7, Q8).
- A CLI invocation `python3 scripts/slugify.py "Some Title"` prints the resulting slug to stdout and exits 0. This reuses the existing `main()` + `if __name__ == "__main__"` shape but takes a single positional argument rather than a flag (ref: Q4, Q12).
- A new file `scripts/slugify_test.py` is a stdlib-only, assert-based test covering the three documented examples plus unicode input and all-symbol input, runnable as `python3 scripts/slugify_test.py` with no third-party framework (ref: Q10, Q11).
- Both files import only stdlib and nothing from elsewhere in the repo, preserving the self-contained `scripts/` convention (ref: Q6).

## Delta

New files:

- `scripts/slugify.py` — shebang line; module docstring; a single import of `re`; the pure `slugify(text: str) -> str` function; a `main()` that reads one positional argument, calls `slugify`, prints the result, and exits; an `if __name__ == "__main__"` guard.
- `scripts/slugify_test.py` — shebang line; an import of the `slugify` function from the sibling module; a sequence of bare `assert` statements (or small helper) covering all required cases; a success message and exit 0 when all asserts pass.

Modified files: none. Out of scope per the ticket: any integration into QRSPI workflow, SKILL, or existing scripts.

The transformation pipeline is: lowercase the input, then in one regex substitution replace each maximal run of non-alphanumeric characters with a single hyphen, then strip leading/trailing hyphens. Collapsing runs (not single characters) in one pass is what guarantees no consecutive hyphens, and the trailing strip plus run-collapse together produce `""` for empty and all-symbol input (ref: Q1, Q7, Q8).

## Pattern Decisions

### Decision 1: CLI argument style

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Positional argument via `argparse` (`add_argument("text")`) | Matches ticket's `python3 scripts/slugify.py "Some Title"` exactly; argparse still emits usage/exit-2 on missing arg | Diverges from the repo's flag-style convention (ref: Q4, Inconsistencies) |
| B | Flag argument via `argparse` (`--text`) | Consistent with every existing `scripts/` CLI (ref: Discovered Patterns) | Contradicts the ticket's documented invocation; would fail the acceptance criterion |
| C | Raw `sys.argv[1]` indexing, no argparse | Minimal, fewest imports | No usage message, ad-hoc error handling, least like house style (ref: Q4) |

**Recommendation:** Option A
**Rationale:** The acceptance criterion fixes the exact positional invocation `python3 scripts/slugify.py "Some Title"`, so a flag would fail it. Option A keeps `argparse` (closest to the established CLI shape at `scripts/check_scope.py:62-81`) while satisfying the literal contract, and argparse still gives a usage error and exit 2 on a missing argument for free (ref: Q4, Q12).
**NEW PATTERN?** Yes — positional argparse arguments are new to this repo; every existing script uses `--flags` (ref: Inconsistencies). Justified because the ticket dictates a positional CLI and existing flag style cannot satisfy it.

### Decision 2: Unicode handling policy

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | ASCII-only: treat any non-ASCII-alphanumeric as a separator (regex `[^a-z0-9]+`) | Deterministic, trivial, stdlib-only; accented/non-Latin chars become separators and drop out | Loses information; `café` → `caf`; non-Latin scripts collapse to `""` |
| B | Unicode-aware alphanumeric: keep Unicode letters/digits (e.g. `re` with `\w` and `re.UNICODE`, or `str.isalnum`) | Preserves accented and non-Latin characters in the slug | Slugs may not be ASCII/filesystem-portable across systems; "filesystem-safe" intent weakened |
| C | Transliteration to ASCII (e.g. via `unicodedata.normalize` NFKD + strip combining marks) | `café` → `cafe`; ASCII-safe and lossy-but-readable | More complex; partial for non-Latin scripts; needs `unicodedata` (still stdlib) |

**Recommendation:** Option A
**Rationale:** The ticket emphasizes "filesystem-safe" and gives only ASCII examples; no transliteration library or `unicodedata` usage exists in the repo, so the simplest stdlib-only ASCII policy best matches both the stated goal and house conventions (ref: Q9, Q2, Inconsistencies). Under Option A a string of only non-ASCII or only symbols yields `""`, consistent with the all-symbol edge case. The exact expected unicode test output must be pinned (see Open Questions).
**NEW PATTERN?** No — uses only `re`, already used elsewhere in `scripts/` (ref: Q6).

### Decision 3: Test file naming and runner

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `scripts/slugify_test.py`, bare asserts, run via `python3 scripts/slugify_test.py` | Exactly what the ticket specifies; stdlib-only; no new dependency | `_test.py` suffix differs from the unittest/pytest `test_*.py` default (ref: Inconsistencies) |
| B | `scripts/test_slugify.py` with pytest | Matches common discovery default | Adds a third-party dependency; contradicts stdlib-only criterion and repo convention (ref: Q11) |

**Recommendation:** Option A
**Rationale:** The acceptance criteria name the file `scripts/slugify_test.py` and require a stdlib-only, assert-based test with no framework. The repo has no existing Python test files to contradict this, so the ticket's naming governs (ref: Q10, Q11, Inconsistencies).
**NEW PATTERN?** Yes — this is the first Python test file in the repo; it establishes the bare-assert convention (ref: Discovered Patterns). Justified by the explicit acceptance criterion.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Unicode test expectation is ambiguous — the ticket requires a unicode case but does not state the expected slug, so test and implementation could disagree | high | med | Resolve OQ1 before coding; pin the exact unicode input and expected output in the test so implementation is written to it |
| Regex run-collapse mis-handles edge cases (leading/trailing/consecutive separators), emitting a stray or doubled hyphen | med | med | Use a single substitution over a maximal run `[^a-z0-9]+` then strip hyphens; cover empty, all-symbol, leading/trailing-space, and embedded-punctuation cases in asserts (ref: Q8) |
| Positional CLI diverges from repo flag convention, surprising future maintainers | med | low | Document the divergence in the module docstring; keep argparse so usage/error behavior stays consistent (ref: Q4) |
| Test file cannot import `slugify` if run from an unexpected working directory | low | med | Run tests as `python3 scripts/slugify_test.py` from repo root as specified; import the sibling module by name, relying on script-dir being on `sys.path` (ref: Q11) |

## Open Questions

- OQ1: What exact slug should the unicode test case expect? Under the recommended ASCII-only policy, an input like `"Héllo Wörld"` would slugify to `"h-llo-w-rld"` (non-ASCII letters treated as separators). Is that acceptable, or is transliteration (`"hello-world"`) desired? This determines Decision 2 and the unicode assertion.
- OQ2: For the all-symbol test case, confirm the expected return is `""` (consistent with the empty-input criterion) rather than an error or sentinel.
- OQ3: Should the CLI handle a missing argument with argparse's default usage error and exit 2, or is a specific message/exit code required? The ticket only specifies the success path (print slug, exit 0).
