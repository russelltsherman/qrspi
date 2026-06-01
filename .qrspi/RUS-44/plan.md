# Implementation Plan — [e2e-throwaway] Add a standalone slugify utility

**Structure basis:** structure.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft
**Total steps:** 11

## Slice 1: slugify module + co-located test

### Setup

1. ✨ Create `scripts/slugify.py` — add shebang `#!/usr/bin/env python3` and a triple-quoted module docstring documenting the ASCII-only / lossy-unicode behavior and the CLI run command `python3 scripts/slugify.py "Some Title"` (ref: structure.md Slice 1 files; design.md §Delta).
2. ⚠️ Modify `scripts/slugify.py` — add the imports `import re`, `import sys`, `import argparse` directly under the docstring (stdlib only; no repo imports — ref: structure.md Contracts; design.md Desired End State).
   - **Current:** file contains only shebang + docstring
   - **After:** file contains shebang + docstring + `import re` / `import sys` / `import argparse`

### Core Logic

3. ⚠️ Modify `scripts/slugify.py` — implement the pure function `slugify(text: str) -> str` as `return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")` with type-hinted signature and no module-level mutable state (ref: structure.md Contracts; design.md Decisions 1 & 2).
   - **Current:** no `slugify` function defined
   - **After:** `def slugify(text: str) -> str:` returning the regex-collapsed, stripped slug
4. ⚠️ Modify `scripts/slugify.py` — add `def main() -> None:` that builds `argparse.ArgumentParser`, defines one positional `text` argument, calls `slugify(args.text)`, prints the slug to stdout, and exits 0; missing argument lets argparse route usage/error to stderr with non-zero exit (ref: structure.md Contracts `main() -> None`; design.md §Desired End State, Decision 2).
   - **Current:** no `main` defined
   - **After:** `def main() -> None:` parses one positional `text`, prints `slugify(args.text)`, exits 0
5. ⚠️ Modify `scripts/slugify.py` — append the `if __name__ == "__main__": main()` guard at end of file (ref: structure.md Slice 1 files; design.md Current State conventions).
   - **Current:** no entry guard
   - **After:** trailing `if __name__ == "__main__": main()`

### Tests

6. ✨ Create `scripts/slugify_test.py` — add shebang `#!/usr/bin/env python3` and a module docstring documenting the invocation `python3 scripts/slugify_test.py` (ref: structure.md Slice 1 files; design.md §Delta).
7. ⚠️ Modify `scripts/slugify_test.py` — add `import os`, `import sys`, then `sys.path.insert(0, os.path.dirname(__file__))` before `from slugify import slugify`, so the import is cwd-independent and touches no other repo module (ref: structure.md Contracts import line; design.md Decision 3, Option B).
   - **Current:** file contains only shebang + docstring
   - **After:** file imports `os`, `sys`, inserts the script dir on `sys.path`, then `from slugify import slugify`
8. ⚠️ Modify `scripts/slugify_test.py` — add the assert checks: `slugify("") == ""`, `slugify("  Hello,  World!! ") == "hello-world"`, `slugify("RUS-44: Add a thing") == "rus-44-add-a-thing"`, the lossy unicode case `slugify("Café") == "caf"`, and an all-symbol case (e.g. `slugify("!!!@@@") == ""`) (ref: structure.md Slice 1 files; design.md §Desired End State).
   - **Current:** no assertions
   - **After:** five `assert slugify(...) == ...` checks covering the three specified cases, the unicode lossy case, and the all-symbol case
9. ⚠️ Modify `scripts/slugify_test.py` — add a `main()` runner that prints a pass marker and exits 0 on all-pass, guarded by `if __name__ == "__main__": main()`; assertion failures surface their traceback (non-zero) naturally (ref: structure.md Slice 1 files; design.md §Desired End State, Decision 3).
   - **Current:** no runner / entry guard
   - **After:** `main()` prints pass marker + `if __name__ == "__main__": main()` guard
10. Run: `python3 scripts/slugify_test.py`
    - **Expected:** exits 0 and prints the pass marker; all five asserts pass

### Verify Slice 1

11. **Checkpoint:** run each command and confirm the criteria
    - [ ] `python3 scripts/slugify_test.py` exits 0 and prints the pass marker (all asserts pass, including the unicode lossy case and the all-symbol case)
    - [ ] `python3 scripts/slugify.py "Some Title"` prints `some-title` to stdout and exits 0
    - [ ] `python3 scripts/slugify.py "RUS-44: Add a thing"` prints `rus-44-add-a-thing`
    - [ ] `python3 scripts/slugify.py` with no argument prints argparse usage to stderr and exits non-zero
    - [ ] `scripts/slugify.py` imports only `re`, `sys`, `argparse`; `scripts/slugify_test.py` imports only `os`, `sys`, and `slugify` — no other repo module is imported

---

## Rollback Notes

- Steps 1–5: to reverse, delete `scripts/slugify.py`. New file, no other code references it; removal is non-destructive (ref: structure.md Modified Types — "None").
- Steps 6–9: to reverse, delete `scripts/slugify_test.py`. New file, no other code references it; removal is non-destructive.
- No DB migrations, config changes, or destructive operations in this plan.
