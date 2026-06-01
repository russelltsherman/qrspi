# Structure Outline — [e2e-throwaway] Add a standalone slugify utility

**Design basis:** design.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## New Types

None. This feature introduces no new data types — `slugify` operates on and returns `str`.

## Modified Types

None.

## Contracts

- `slugify(text: str) -> str` — pure function: lowercases `text`, replaces every run of non-alphanumeric (ASCII `[a-z0-9]`) characters with a single hyphen, strips leading/trailing hyphens. Returns `""` for empty and all-symbol input. No side effects, no module-level state. (ref: design.md §Delta, Decision 1 Option A, Decision 2 Option A)
- `main() -> None` — CLI entrypoint in `scripts/slugify.py`: builds an `argparse.ArgumentParser` with one required positional `text` argument, calls `slugify(text)`, prints the result to stdout, exits 0. Missing argument → argparse routes usage/error to stderr with non-zero exit. (ref: design.md §Delta, Q4, Q12)
- `main() -> None` — test runner in `scripts/slugify_test.py`: prepends the script's own directory to `sys.path`, imports `slugify` from the sibling module, runs `assert slugify(...) == ...` checks, prints a pass marker, exits 0 on all-pass; an assertion failure surfaces its traceback with a non-zero exit. (ref: design.md §Delta, Decision 3 Option B, Q10, Q11)

## Slice 1: slugify module + co-located test

**Goal:** Deliver the complete, runnable slug utility — the `slugify` function, its CLI, and the assert-based test that verifies it — as one end-to-end path: invoke the CLI to get a slug on stdout, and run the test to confirm all specified cases pass. The module and test are mutually dependent (the test imports and exercises `slugify`; the module's correctness is only verifiable through the test), so they form a single unit of work.
**Files touched:**

- ✨ `scripts/slugify.py` — shebang, module docstring (noting ASCII-only lossy unicode behavior, ref: Risk Register), `import re`/`import sys`/`import argparse`, the `slugify(text: str) -> str` function (`re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")`), `main()` with one positional `text` arg that prints the slug and exits 0, and the `if __name__ == "__main__": main()` guard.
- ✨ `scripts/slugify_test.py` — shebang, module docstring documenting the exact run command (`python3 scripts/slugify_test.py` from repo root), `sys.path` insert of the script's own directory, `from slugify import slugify`, assert checks for the three specified cases (`""` → `""`, `"  Hello,  World!! "` → `"hello-world"`, `"RUS-44: Add a thing"` → `"rus-44-add-a-thing"`) plus a unicode case (`"Café"` → `"caf"`, pinning lossy ASCII behavior) and an all-symbol case (→ `""`), a `main()` that prints a pass marker and exits 0, and the `__name__` guard.
**Verification:**
- [ ] `python3 scripts/slugify_test.py` from repo root exits 0 and prints the pass marker.
- [ ] `python3 scripts/slugify.py "Some Title"` prints `some-title` and exits 0.
- [ ] `python3 scripts/slugify.py` with no argument prints an argparse usage/error to stderr and exits non-zero.
- [ ] `python3 -c "import scripts; ..."` not required — confirm `slugify.py` imports nothing from other repo modules (stdlib-only).
**Context cost:** S
**Depends on:** none

## Slice 2: documentation alignment

**Goal:** Ensure any project documentation that enumerates or describes the repo's `scripts/` utilities reflects the new `scripts/slugify.py`, keeping docs consistent with the shipped code. Independently verifiable: docs can be reviewed/rendered on their own once the script exists.
**Files touched:**

- ⚠️ Documentation files that list or describe `scripts/` utilities (e.g. a README or scripts index, if present) — add an entry for `scripts/slugify.py` describing its purpose and CLI usage. Edits limited to documentation; no code or workflow/SKILL integration (ref: design.md §Delta, ticket out-of-scope).
**Verification:**
- [ ] Search documentation for any enumeration of `scripts/` utilities; confirm each such place now includes `scripts/slugify.py`.
- [ ] Confirm no code, SKILL, or existing-script changes were made in this slice (docs-only).
**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- **Existence and location of documentation enumerating `scripts/` utilities.** Slice 2 derives from the design-review feedback in §Delta ("run a review pass over project documentation and update any place that lists or describes the repo's scripts/utilities"). The design does not cite a specific documentation file that contains such a list, and this agent cannot explore the codebase to confirm one exists. If no documentation enumerates the `scripts/` utilities, Slice 2 reduces to a no-op review with nothing to edit. The plan phase should resolve which file(s), if any, this targets.
- **Decision 3 carries a reviewer-deferred choice (Option A vs B).** The design recommends Option B (`sys.path` insert) but explicitly notes the reviewer may prefer Option A's simpler sibling import. The structure assumes Option B per the recommendation; if the reviewer chose Option A, Slice 1's test file drops the `sys.path` machinery and relies on cwd-based resolution. This is a low-impact swap within Slice 1, not a structural change.
