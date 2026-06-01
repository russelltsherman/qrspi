# Design — [e2e-throwaway] Add a standalone slugify utility

**Ticket:** RUS-44
**Research basis:** research.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** revision-1 (design review feedback addressed)

## Current State

This is a greenfield addition. Neither target file exists today: `scripts/slugify.py` and `scripts/slugify_test.py` are absent, and no `slug`/`slugify` token appears anywhere in the repository (ref: overarching finding; Q1, Q3). There is no shared helper for turning an arbitrary string into a filesystem-safe slug; any slugging done elsewhere is ad hoc and uncited (ref: Q2).

The `scripts/` directory currently holds six unrelated utilities — `check_scope.py`, `diagnose.py`, `grade.py`, `report.py`, `revise.py`, `run_eval.py` — none of which reference slugs (ref: overarching finding). These establish the conventions a new standalone utility is expected to follow:

- Each script opens with `#!/usr/bin/env python3` and a triple-quoted module docstring (ref: Discovered Patterns, `check_scope.py:1-6`).
- CLIs are built with `argparse.ArgumentParser`, a `main()` function, and an `if __name__ == "__main__": main()` guard (ref: Discovered Patterns, `check_scope.py:55-74`).
- Success/failure is signaled with `sys.exit(0 if ... else 1)`, and human-readable status is printed to stdout (ref: Discovered Patterns, `check_scope.py:63-70`).
- All existing scripts are stdlib-only; no `pytest`, `requirements.txt`, or `pyproject.toml` test dependency exists (ref: Discovered Patterns, `check_scope.py:8-11`).
- Function signatures carry type hints (ref: Discovered Patterns, `check_scope.py:14`).
- There are no existing `*_test.py` or `test_*.py` files; `scripts/slugify_test.py` would be the first co-located test in `scripts/` (ref: Discovered Patterns).

The unicode-classification decision (ASCII-only versus unicode-aware alphanumeric matching) has not been made in any code and is open for this design (ref: Q8).

## Desired End State

After this ships, the repository exposes a self-contained slug utility that imports nothing from other repo modules and depends only on the standard library (ref: Q5, Q10). Each acceptance criterion maps to concrete behavior:

- **Pure function `slugify(text: str) -> str` in `scripts/slugify.py`** that lowercases input, replaces every run of non-alphanumeric characters with a single hyphen, strips leading/trailing hyphens, and never emits consecutive hyphens. No module-level mutable state or caching; the only side effect is the CLI print path (ref: Q1, Q3, Q5, Q6).
- **Specified case outputs:** `slugify("")` returns `""`; `slugify("  Hello,  World!! ")` returns `"hello-world"`; `slugify("RUS-44: Add a thing")` returns `"rus-44-add-a-thing"` (ref: Q6).
- **All-symbol input** (every character non-alphanumeric) returns `""` after stripping (ref: Q7).
- **CLI:** `python3 scripts/slugify.py "Some Title"` prints the slug to stdout and exits 0. A missing required argument routes argparse's usage/error to stderr with a non-zero exit, distinguishing error from success (ref: Q4, Q12).
- **Test file `scripts/slugify_test.py`** — stdlib-only, assert-based, no third-party framework — covering the three specified cases plus a unicode case and an all-symbol case. It imports `slugify` from the sibling module only, and a `main()`/`__main__` runner exits 0 on all-pass, non-zero on assertion failure (ref: Q9, Q10, Q11).
- **Stdlib only**, no third-party dependencies, no imports from other repo files (ref: Q5, Q10; ticket).
- **Project documentation stays aligned (design review feedback):** any documentation that enumerates or describes the repo's `scripts/` utilities is reviewed and updated to include `scripts/slugify.py`, so the docs remain consistent with this addition.

## Delta

- **New file `scripts/slugify.py`** — shebang, module docstring, `import re`, `import sys`, `import argparse`; the `slugify(text: str) -> str` function; a `main()` that defines one positional `text` argument, calls `slugify`, prints the result, and exits 0; the `__name__` guard.
- **New file `scripts/slugify_test.py`** — shebang, module docstring, imports `slugify` from the sibling module (path-resolution approach decided below), a sequence of `assert slugify(...) == ...` checks, and a runner that prints a pass marker and exits 0, allowing the assertion traceback to surface on failure.
- **Documentation alignment (design review feedback):** run a review pass over project documentation and update any place that lists or describes the repo's scripts/utilities so `scripts/slugify.py` is reflected, keeping docs aligned with this change. Edits are limited to documentation; code integration into the QRSPI workflow, any SKILL, or existing scripts remains out of scope (ref: ticket out-of-scope).

## Pattern Decisions

### Decision 1: Non-alphanumeric matching and unicode policy

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | ASCII-only: `re.sub(r"[^a-z0-9]+", "-", text.lower())` then strip `-` | Deterministic, filesystem-safe across all OSes; accented/non-ASCII letters collapse to separators, so `"Café"` → `"caf"` | Drops non-ASCII letters entirely; lossy for unicode-heavy titles |
| B | Unicode-aware: `re.sub(r"[^0-9a-z]+", ...)` with `str.isalnum()`/`\w` and `re.UNICODE` | Preserves accented letters as alphanumeric | `\w` includes underscore; non-ASCII in slugs is not reliably filesystem-safe; "filesystem-safe" goal undercut |

**Recommendation:** Option A
**Rationale:** The ticket's stated goal is a *filesystem-safe* slug, and the only cited convention baseline is the stdlib `re` usage in `check_scope.py:21,33` (ref: Q2). ASCII-only output is unambiguously filesystem-safe and matches all three specified-case expectations (ref: Q6). Lowercasing must happen before matching so the `[a-z0-9]` class is sufficient (ref: Q2). The unicode test case (ref: Q8, Q9) will assert the documented lossy behavior rather than letter preservation.
**NEW PATTERN?** No — uses the established stdlib `re` pattern already present in `scripts/`.

### Decision 2: Hyphen collapsing and stripping

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single regex replaces each *run* of non-alphanumerics with one hyphen, then `.strip("-")` | One pass; "single hyphen per run" guarantees no consecutive hyphens by construction; trivial empty/all-symbol handling | None material |
| B | Replace each non-alphanumeric char individually, then collapse `--+` to `-`, then strip | More explicit steps | Two-stage; redundant given the `+` quantifier already collapses runs |

**Recommendation:** Option A
**Rationale:** The `+` quantifier on the character class collapses each run to one hyphen in a single pass, satisfying "never emits consecutive hyphens" structurally (ref: Q6). `.strip("-")` removes edge hyphens, yielding `""` for empty and all-symbol inputs (ref: Q6, Q7). Simpler and fewer failure modes than Option B.
**NEW PATTERN?** No.

### Decision 3: How the test imports `slugify` without importing other repo modules

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Test and module are siblings in `scripts/`; run test from `scripts/` so a plain `from slugify import slugify` resolves | Simplest; zero path manipulation; no other repo module touched | Test must be run with `scripts/` on `sys.path` (cwd or `python3 scripts/slugify_test.py` resolving sibling) |
| B | Test prepends its own directory to `sys.path` via `os.path.dirname(__file__)` before importing | Runnable from any cwd | Adds `os`/`sys` path code; slightly more machinery |

**Recommendation:** Option B
**Rationale:** Running `python3 scripts/slugify_test.py` from the repo root (the natural invocation, consistent with how sibling scripts are run — ref: Discovered Patterns) puts the script's own directory on `sys.path[0]` automatically in CPython, so `from slugify import slugify` resolves without extra code; however, Option B's explicit `sys.path` insert makes the import robust regardless of cwd and keeps the test self-contained (ref: Q10). Either way, no other repo module is imported, satisfying the constraint. The human reviewer may prefer Option A's simplicity.
**NEW PATTERN?** Yes — `scripts/slugify_test.py` is the first co-located `*_test.py` in the repo (ref: Discovered Patterns). It establishes a test-file convention where none exists; flagged for reviewer confirmation of naming and runner style.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Unicode policy mismatch — reviewer expects accented letters preserved, design drops them (Option A) | med | low | Document lossy behavior in the docstring; the unicode assert pins the chosen behavior so intent is explicit and reviewable (ref: Q8) |
| Test import resolution fails depending on invocation cwd | low | med | Option B `sys.path` insert makes import cwd-independent; document the exact run command in the test docstring (ref: Q10, Q11) |
| New test-file convention conflicts with a future repo-wide standard | low | low | First `*_test.py` is greenfield (ref: Discovered Patterns); throwaway ticket, safe to discard; flagged as NEW PATTERN for reviewer |
| CLI accepts a title containing leading hyphens that argparse parses as a flag | low | low | Use a positional argument; argparse treats positionals after `--` literally, and the `[e2e-throwaway]` scope makes this acceptable (ref: Q4) |

## Open Questions

Both open questions were resolved in Design Review (PR #58):

- OQ1 — RESOLVED: **ASCII-only** (Decision 1, Option A). `slugify("Café")` yields `"caf"`; the unicode test asserts this lossy, filesystem-safe behavior (ref: Q8, Q9).
- OQ2 — RESOLVED: the **`slugify_test.py`** name with an assert-based `main()` runner is **confirmed** as the convention for this first co-located test (Decision 3; ref: Discovered Patterns).
