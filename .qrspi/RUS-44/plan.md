# Implementation Plan — [e2e-throwaway] Add a standalone slugify utility

**Structure basis:** structure.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: slugify module + co-located test

### Setup

1. ✨ Create `scripts/slugify.py` (file skeleton) — add `#!/usr/bin/env python3` shebang, then a triple-quoted module docstring describing the utility and explicitly noting the ASCII-only, lossy-unicode behavior (e.g. `"Café"` → `"caf"`), then `import re`, `import sys`, `import argparse`. (ref: structure.md §Slice 1; design.md §Delta, Risk Register row 1)

### Core Logic

2. ✨ Add the `slugify` function to `scripts/slugify.py` — implement exactly the contract `slugify(text: str) -> str`. Body: `return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")`. Pure function, no module-level state, no side effects. (ref: structure.md §Contracts; design.md Decision 1 Option A, Decision 2 Option A)

3. ✨ Add the `main` function to `scripts/slugify.py` — implement contract `main() -> None`. Build `argparse.ArgumentParser`, add one required positional argument `text`, parse args, call `slugify(args.text)`, `print` the result to stdout, then `sys.exit(0)`. A missing `text` argument is handled by argparse (usage/error to stderr, non-zero exit) with no extra code. (ref: structure.md §Contracts; design.md §Delta, Q4, Q12)

4. ✨ Add the entrypoint guard to `scripts/slugify.py` — append `if __name__ == "__main__":` calling `main()`. (ref: structure.md §Slice 1; design.md Current State — established `scripts/` convention)

### Tests

5. ✨ Create `scripts/slugify_test.py` (file skeleton) — add `#!/usr/bin/env python3` shebang, then a module docstring documenting the exact run command `python3 scripts/slugify_test.py` (from repo root), then `import os`, `import sys`. (ref: structure.md §Slice 1; design.md Decision 3 Option B, Q11)

6. ✨ Add the import-resolution block to `scripts/slugify_test.py` — insert the script's own directory onto `sys.path` via `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`, then `from slugify import slugify`. Imports nothing from any other repo module. (ref: structure.md §Slice 1; design.md Decision 3 Option B, Q10)
   - **Note:** Structure assumes design Decision 3 Option B (`sys.path` insert). If the reviewer chose Option A, drop the insert line and rely on cwd-based sibling resolution — low-impact swap, no other step changes.

7. ✨ Add the assert cases and runner to `scripts/slugify_test.py` — define `main() -> None` containing these `assert slugify(...) == ...` checks, then print a pass marker and `sys.exit(0)`; assertion failure surfaces its traceback with non-zero exit. Append the `if __name__ == "__main__": main()` guard. Cases (ref: structure.md §Slice 1; design.md Desired End State, Q9):
   - `slugify("") == ""`
   - `slugify("  Hello,  World!! ") == "hello-world"`
   - `slugify("RUS-44: Add a thing") == "rus-44-add-a-thing"`
   - `slugify("Café") == "caf"` (pins lossy ASCII behavior)
   - `slugify("!!!") == ""` (all-symbol input)

8. Run: `python3 scripts/slugify_test.py` from repo root
   - **Expected:** exits 0 and prints the pass marker; all five asserts pass.

### Verify Slice 1

9. **Checkpoint:** run from repo root:
   - `python3 scripts/slugify_test.py`
   - `python3 scripts/slugify.py "Some Title"`
   - `python3 scripts/slugify.py`
   - [ ] `python3 scripts/slugify_test.py` exits 0 and prints the pass marker.
   - [ ] `python3 scripts/slugify.py "Some Title"` prints `some-title` and exits 0.
   - [ ] `python3 scripts/slugify.py` with no argument prints an argparse usage/error to stderr and exits non-zero.
   - [ ] `scripts/slugify.py` imports only `re`, `sys`, `argparse` (stdlib) — no imports from other repo modules.

---

## Slice 2: documentation alignment

### Setup

10. Discovery: from repo root, identify any documentation that enumerates or describes the repo's `scripts/` utilities. Run: `grep -rln -e "check_scope" -e "diagnose" -e "scripts/" --include="*.md" .` and inspect each hit for a list/description of `scripts/` utilities. (ref: structure.md §Unverified Assumptions — documentation location not confirmed by earlier phases)
    - **If no such documentation exists:** Slice 2 is a no-op review. Record that finding, skip steps 11–12, and proceed to the Verify checkpoint.

### Core Logic

11. ⚠️ Modify each documentation file found in step 10 that enumerates/describes `scripts/` utilities — add an entry for `scripts/slugify.py`.
    - **Current:** the `scripts/` utility list/description omits `scripts/slugify.py`.
    - **After:** the list/description includes `scripts/slugify.py` with its purpose (filesystem-safe slug utility) and CLI usage (`python3 scripts/slugify.py "Some Title"` → `some-title`). Edits limited to documentation only — no code, SKILL, workflow, or existing-script changes. (ref: structure.md §Slice 2; design.md §Delta — documentation alignment, ticket out-of-scope)

### Tests

12. Re-run the step 10 discovery search and visually confirm every place that enumerates `scripts/` utilities now includes `scripts/slugify.py`. (ref: structure.md §Slice 2 verification)

### Verify Slice 2

13. **Checkpoint:** `grep -rln "slugify" --include="*.md" .`
    - [ ] Every documentation place that enumerates/describes `scripts/` utilities now includes `scripts/slugify.py` (or it is recorded that no such documentation exists).
    - [ ] No code, SKILL, workflow, or existing-script changes were made in this slice (docs-only). Confirm via `git diff --name-only` showing only `*.md` paths changed for this slice.

---

14. **Final gate:** confirm both slice checkpoints (steps 9 and 13) are satisfied and the change set is limited to `scripts/slugify.py`, `scripts/slugify_test.py`, and documentation files only.

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this plan.
- Step 1–4 (`scripts/slugify.py`) and step 5–7 (`scripts/slugify_test.py`): both are new files. Rollback = delete the file; nothing else references them (stdlib-only, no repo imports).
- Step 11 (documentation edits): additive edits to existing docs. Rollback = revert the added `scripts/slugify.py` entries; no other content is touched.
