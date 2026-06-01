# Structure Outline — [e2e-throwaway] Add a standalone slugify utility

**Design basis:** design.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## New Types

None. This feature introduces no new data types — only a pure string-to-string function and a CLI entry point.

## Modified Types

None. No existing files or types are modified (ref: design.md §Delta — "No modifications to existing files").

## Contracts

- `slugify(text: str) -> str` — pure function; lowercases input, replaces each run of non-alphanumeric (ASCII `[a-z0-9]`) characters with a single hyphen, strips leading/trailing hyphens. No module-level mutable state. ASCII-only / lossy for non-ASCII letters (ref: design.md Decision 1, Option A).
- `main() -> None` — CLI entry point in `scripts/slugify.py`; defines one positional `text` argument via `argparse`, calls `slugify`, prints the slug to stdout, exits 0. Missing argument routes argparse usage/error to stderr with non-zero exit (ref: design.md §Desired End State).
- `from slugify import slugify` — the test module imports `slugify` from its sibling module only, after inserting its own directory onto `sys.path` (Option B), so the import is cwd-independent and touches no other repo module (ref: design.md Decision 3).

## Slice 1: slugify module + co-located test

**Goal:** Deliver the complete, self-contained slug utility as a testable end-to-end path: the pure `slugify` function, the CLI wrapper, and an assert-based test that imports and exercises it. Running the test verifies the function; running the CLI verifies the entry point.

**Rationale for single slice:** The module and its test are mutually dependent and cohesive — the test cannot run without the module, and the module's behavior has no verification signal without the test. There is no meaningful testability boundary between them. Per the over-slicing rules, separating "write code" from "write test that imports it" would be wrong. Two files, well under the 10-file limit.

**Files touched:**

- ✨ `scripts/slugify.py` — shebang `#!/usr/bin/env python3`, module docstring (documenting ASCII-only / lossy unicode behavior and the CLI run command), `import re`, `import sys`, `import argparse`; the `slugify(text: str) -> str` function implemented as `re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")`; a `main()` with one positional `text` argument that prints the slug and exits 0; an `if __name__ == "__main__": main()` guard (ref: design.md §Delta, Decisions 1 & 2).
- ✨ `scripts/slugify_test.py` — shebang, module docstring (documenting the `python3 scripts/slugify_test.py` invocation), a `sys.path` insert of the script's own directory (`os.path.dirname(__file__)`) before `from slugify import slugify`, a sequence of `assert slugify(...) == ...` checks covering the three specified cases (`""`→`""`, `"  Hello,  World!! "`→`"hello-world"`, `"RUS-44: Add a thing"`→`"rus-44-add-a-thing"`), a unicode case asserting the lossy ASCII behavior (`"Café"`→`"caf"`), and an all-symbol case (→`""`); a `main()`/`__main__` runner that prints a pass marker and exits 0 on all-pass, letting the assertion traceback surface (non-zero) on failure (ref: design.md §Desired End State, Decision 3).

**Verification:**

- [ ] `python3 scripts/slugify_test.py` exits 0 and prints the pass marker (all asserts pass, including the unicode lossy case and the all-symbol case).
- [ ] `python3 scripts/slugify.py "Some Title"` prints `some-title` to stdout and exits 0.
- [ ] `python3 scripts/slugify.py "RUS-44: Add a thing"` prints `rus-44-add-a-thing`.
- [ ] `python3 scripts/slugify.py` with no argument prints argparse usage to stderr and exits non-zero.
- [ ] `scripts/slugify.py` imports only `re`, `sys`, `argparse`; `scripts/slugify_test.py` imports only `os`, `sys`, and `slugify` — no other repo module is imported.

**Context cost:** S
**Depends on:** none

---

## Unverified Assumptions

- **CPython `sys.path[0]` behavior vs. explicit insert (Decision 3).** The design recommends Option B (explicit `sys.path` insert) while noting Option A (relying on `python3 scripts/slugify_test.py` putting the script dir on `sys.path[0]`) would also work and the reviewer may prefer it. The structure follows the design's recommendation (Option B), but the final choice between A and B is a reviewer preference flagged in the design, not a verified constraint.
- **New `*_test.py` convention (Decision 3, OQ2).** The `slugify_test.py` name and assert-based `main()` runner are confirmed in the design as the first co-located test convention, but no precedent exists in the repo to validate against (this is the first `*_test.py` file). The convention is established by this ticket, not verified against existing code.
- **Unicode lossiness acceptance (Risk Register, OQ1).** `slugify("Café")` → `"caf"` is the chosen ASCII-only behavior, resolved in Design Review. The structure pins this via an assert, but it remains a design decision (acceptable lossy behavior) rather than an externally verified requirement.
